#!/usr/bin/env python3
"""Compare final front-visible eye apertures without altering either STL.

Coordinates and sampling pitch are mm. Run only after final v0.4 STL export.
Requires numpy, scipy, trimesh and manifold3d. PNG encoding uses the stdlib.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import time
import zlib

import numpy as np
from scipy import ndimage
import trimesh
import manifold3d as m3d

ROOT = Path(__file__).resolve().parent


def load_solid(path):
    mesh = trimesh.load_mesh(path, process=True, validate=False)
    solid = m3d.Manifold(m3d.Mesh64(np.ascontiguousarray(mesh.vertices, dtype=np.float64),
                                 np.ascontiguousarray(mesh.faces, dtype=np.uint64)))
    if solid.status() != m3d.Error.NoError or solid.is_empty():
        raise ValueError(f'Invalid manifold: {path.name}: {solid.status()}')
    return mesh, solid


def png_rgb(path, rgb):
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    h, w, channels = rgb.shape
    assert channels == 3
    def chunk(name, payload):
        return struct.pack('>I', len(payload))+name+payload+struct.pack('>I', zlib.crc32(name+payload) & 0xffffffff)
    raw = b''.join(b'\0'+row.tobytes() for row in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                     +chunk(b'IDAT', zlib.compress(raw, 8))+chunk(b'IEND', b''))


def metrics(mask, xs, zs, pitch):
    rows, cols = np.nonzero(mask)
    if not len(rows):
        return None
    return {'pixel_count': len(rows), 'width_mm': float((cols.max()-cols.min()+1)*pitch),
            'height_mm': float((rows.max()-rows.min()+1)*pitch), 'area_mm2': float(len(rows)*pitch*pitch),
            'centroid_xz_mm': [float(xs[cols].mean()), float(zs[rows].mean())],
            'bbox_xz_mm': [[float(xs[cols.min()]-pitch/2), float(zs[rows.min()]-pitch/2)],
                           [float(xs[cols.max()]+pitch/2), float(zs[rows.max()]+pitch/2)]]}


def project_eye(solid, xs, zs, start_y, end_y, reference_center):
    clear = np.zeros((len(zs), len(xs)), dtype=bool)
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            clear[j, i] = len(solid.ray_cast((float(x), start_y, float(z)),
                                            (float(x), end_y, float(z)))) == 0
    labels, count = ndimage.label(clear, structure=ndimage.generate_binary_structure(2, 1))
    ci = int(np.argmin(np.abs(xs-reference_center[0])))
    cj = int(np.argmin(np.abs(zs-reference_center[2])))
    label = int(labels[cj, ci])
    # A blocked eye center is a real diagnostic. Never substitute the exterior
    # background or a different open component to force a successful result.
    if label == 0:
        return np.zeros_like(clear), {'valid': False, 'reason': 'reference eye center is obstructed',
                                     'clear_components_in_roi': int(count)}
    mask = labels == label
    touches = bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())
    return mask, {'valid': not touches, 'clear_components_in_roi': int(count),
                  'selected_component': label, 'touches_roi_boundary': touches,
                  'reason': 'eye-connected aperture identified' if not touches else 'aperture touches ROI: enlarge ROI or investigate a broken rim'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-dir', type=Path, default=ROOT.parent/'march7-bjd-1-4-v0.3')
    ap.add_argument('--current-dir', type=Path, default=ROOT)
    ap.add_argument('--pitch-mm', type=float, default=.1)
    ap.add_argument('--roi-size-mm', type=float, default=24.)
    args = ap.parse_args()
    if args.pitch_mm <= 0 or args.roi_size_mm < 16:
        raise ValueError('Positive pitch and at least 16 mm ROI required')
    started = time.monotonic()
    dirs = {'baseline': args.baseline_dir, 'current': args.current_dir}
    versions = {'baseline': 'v0.3', 'current': 'v0.4'}
    builds, meshes, solids, sources = {}, {}, {}, {}
    for key, directory in dirs.items():
        builds[key] = json.loads((directory/'build-report.json').read_text())
        path = directory/f'march7-head-shell-{versions[key]}-draft.stl'
        meshes[key], solids[key] = load_solid(path)
        sources[key] = {'file': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'source_to_mm_scale': builds[key]['source_to_mm_scale']}
    centers = sorted(builds['baseline']['eye_centers_mm'], key=lambda c: c[0])
    current_centers = sorted(builds['current']['eye_centers_mm'], key=lambda c: c[0])
    if len(centers) != 2 or len(current_centers) != 2:
        raise ValueError('Expected two eye centers per model')
    pitch = args.pitch_mm
    n = int(np.ceil(args.roi_size_mm/pitch))
    offsets = (np.arange(n)+.5-n/2)*pitch
    start_y = float(min(m.bounds[0, 1] for m in meshes.values())-3)
    results, overlays = [], []
    for index, center in enumerate(centers):
        xs, zs = center[0]+offsets, center[2]+offsets
        # Identical ray endpoints and grids isolate aperture change from framing.
        end_y = float(center[1])
        masks, measures, diagnostics = {}, {}, {}
        for key in ('baseline', 'current'):
            print(f'Projecting eye {index+1}: {key}', flush=True)
            masks[key], diagnostics[key] = project_eye(solids[key], xs, zs, start_y, end_y, center)
            measures[key] = metrics(masks[key], xs, zs, pitch)
        before, after = measures['baseline'], measures['current']
        union = masks['baseline'] | masks['current']; both = masks['baseline'] & masks['current']
        changes = None
        if before and after:
            delta = np.array(after['centroid_xz_mm'])-before['centroid_xz_mm']
            changes = {'width_mm': after['width_mm']-before['width_mm'],
                       'height_mm': after['height_mm']-before['height_mm'],
                       'area_mm2': after['area_mm2']-before['area_mm2'],
                       'area_percent': 100*(after['area_mm2']/before['area_mm2']-1),
                       'centroid_shift_xz_mm': delta.tolist(),
                       'centroid_shift_distance_mm': float(np.linalg.norm(delta)),
                       'intersection_over_union': float(both.sum()/union.sum()),
                       'symmetric_difference_area_mm2': float(np.logical_xor(masks['baseline'], masks['current']).sum()*pitch*pitch)}
        results.append({'eye_id': 'x_negative' if center[0] < 0 else 'x_positive',
                        'baseline_eye_center_mm': center, 'current_eye_center_mm': current_centers[index],
                        'ray_y_interval_mm': [start_y, end_y], 'metrics': measures,
                        'diagnostics': diagnostics, 'changes_current_minus_baseline': changes})
        image = np.full((n, n, 3), 245, np.uint8)
        image[both] = (48, 55, 64)
        image[masks['baseline'] & ~masks['current']] = (225, 93, 125)
        image[masks['current'] & ~masks['baseline']] = (28, 167, 174)
        overlays.append(np.flipud(image))
    divider = np.full((n, 12, 3), 255, np.uint8)
    board = np.concatenate((overlays[0], divider, overlays[1]), axis=1)
    board = np.repeat(np.repeat(board, 3, axis=0), 3, axis=1)
    png_rgb(args.current_dir/'eye-aperture-comparison.png', board)
    report = {'units': 'mm', 'sources': sources, 'sample_pitch_mm': pitch, 'roi_size_mm': n*pitch,
              'projection': 'Orthographic +Y rays on one shared world X-Z grid, ending at the baseline eye-center Y depth.',
              'aperture_selection': '4-connected clear component containing each baseline eye center; exterior background is excluded.',
              'eyes': results,
              'all_projections_valid': all(v['valid'] for r in results for v in r['diagnostics'].values()),
              'overlay': {'file': 'eye-aperture-comparison.png', 'left_panel': 'x_negative', 'right_panel': 'x_positive',
                          'dark': 'open in both', 'pink': 'baseline only (current aperture reduced)',
                          'teal': 'current only (current aperture enlarged)'},
              'limits': ['Measurements are raster estimates; width/height boundary precision is approximately one grid pitch per edge.',
                         'Projection includes rim thickness and the path to eye-center depth; it is not a 3D geodesic rim measurement.',
                         'This compares eye apertures only, not visual facial likeness, mouth shape, physical eye fit or print tolerance.',
                         'No automatic appearance-acceptance threshold is imposed; use the metrics and overlay together with model previews.'],
              'duration_seconds': time.monotonic()-started}
    output = args.current_dir/'face-opening-comparison.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'all_projections_valid': report['all_projections_valid'],
                      'eyes': [{'eye_id': r['eye_id'], 'metrics': r['metrics'],
                                'changes': r['changes_current_minus_baseline']} for r in results],
                      'report': str(output)}, ensure_ascii=False, indent=2))
    return 0 if report['all_projections_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
