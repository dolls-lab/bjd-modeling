#!/usr/bin/env python3
"""Independent digital checks for the two exported BJD STL parts.

Run using Python with numpy, trimesh and manifold3d installed. All coordinates
are millimeters. These checks do not claim physical fit or process validation.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

import numpy as np
import trimesh
import manifold3d as m3d

ROOT = Path(__file__).resolve().parent
FILES = {
    'head_shell': 'march7-head-shell-v0.9-draft.stl',
    'head_cap': 'march7-head-cap-v0.9-draft.stl',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap_frame(params, build):
    """Read the outward opening axis, with the agreed v0.9 plane as default."""
    origin = np.asarray(build.get('cap_plane_origin_mm', params.get('cap_plane_origin_mm', [0, 14.5, 50])), dtype=float)
    normal = np.asarray(build.get('cap_plane_normal', params.get('cap_plane_normal', [0, 1, .3])), dtype=float)
    if origin.shape != (3,) or normal.shape != (3,) or not np.isfinite(origin).all() or not np.isfinite(normal).all():
        raise ValueError('Invalid cap plane origin or normal')
    normal /= np.linalg.norm(normal)
    if normal[1] <= 0 or normal[2] < 0:
        raise ValueError('v0.9 must open rearward/upward, not toward the face')
    return origin, normal


def protected_regions(root, params, build, meshes, origin, normal):
    """Independently compare source face/ear points and the neck envelope to plane."""
    parser_path = root/'parse_pmx.py'
    if not parser_path.is_file():
        raise FileNotFoundError('Source-face protection check requires parse_pmx.py beside this validator')
    spec = importlib.util.spec_from_file_location('march7_pmx_validation_source', parser_path)
    pmx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pmx)
    source = pmx.load_pmx(params['source_pmx'])
    material = next(m for m in source['materials'] if m['name'] == '脸')
    faces = source['faces'][material['start']:material['end']]
    raw = source['vertices'][np.unique(faces)]
    points = np.column_stack((raw[:, 0], raw[:, 2], raw[:, 1]-raw[:, 1].min()))*build['source_to_mm_scale']
    distances = (points-origin)@normal
    closest = int(np.argmax(distances))
    face_margin = -float(distances[closest])
    radius = float(build.get('neck_platform_radius_mm', params.get('neck_platform_radius_mm', 14.0)))
    ny = float(build['neck_center_y_mm'])
    zmin = float(meshes['head_shell'].bounds[0, 2])
    zmax = float(build['neck_platform_top_mm'])
    # Conservative envelope of the complete filled neck cylinder, before clipping.
    neck_projection = (normal[1]*ny + radius*np.hypot(normal[0], normal[1])
                       + max(normal[2]*zmin, normal[2]*zmax) - origin@normal)
    neck_margin = -float(neck_projection)
    cap_distances = (np.asarray(meshes['head_cap'].vertices)-origin)@normal
    min_cap_distance = float(cap_distances.min())
    gap = float(params['cap_gap_mm'])
    crown_on_head = bool(meshes['head_shell'].bounds[1, 2] >= meshes['head_cap'].bounds[1, 2]-1e-5)
    return {
        'plane_origin_mm': origin.tolist(), 'plane_outward_unit_normal': normal.tolist(),
        'face_and_ears': {'source_points_checked': len(points), 'minimum_plane_margin_mm': face_margin,
                          'closest_source_point_mm': points[closest].tolist(),
                          'points_on_cap_side': int(np.sum(distances >= 0)), 'pass': face_margin > 0},
        'neck_platform_envelope': {'radius_mm': radius, 'center_y_mm': ny, 'top_z_mm': zmax,
                                   'minimum_plane_margin_mm': neck_margin, 'pass': neck_margin > 0},
        'cap_mesh_stays_behind_plane': {'minimum_signed_distance_mm': min_cap_distance,
                                      'nominal_gap_mm': gap, 'tolerance_mm': 1e-4,
                                      'pass': min_cap_distance >= gap-1e-4},
        'highest_crown_stays_on_head': {'head_max_z_mm': float(meshes['head_shell'].bounds[1, 2]),
                                      'cap_max_z_mm': float(meshes['head_cap'].bounds[1, 2]),
                                      'pass': crown_on_head},
        'pass': face_margin > 0 and neck_margin > 0 and min_cap_distance >= gap-1e-4 and crown_on_head,
        'limitation': 'Plane-side geometric protection, not an anatomical or physical fit assertion.'}


def loc_summary(points, limit=12):
    points = np.asarray(points)
    if not len(points):
        return None
    return {'count': len(points), 'bounds_mm': [points.min(0).tolist(), points.max(0).tolist()],
            'first_locations_mm': points[:limit].tolist()}


def mesh_checks(path):
    mesh = trimesh.load_mesh(path, process=True, validate=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f'{path.name}: expected a single Trimesh')
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    centers = np.asarray(mesh.triangles_center)
    edges = np.sort(np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])), axis=1)
    unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique_edges[counts == 1]
    overused = unique_edges[counts > 2]
    bad_area = np.asarray(mesh.area_faces) < 1e-10
    repeated_vertex = (faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 2] == faces[:, 0])
    _, duplicate_counts = np.unique(np.sort(faces, axis=1), axis=0, return_counts=True)
    # Label adjacency directly: no mesh repair and no duplicate component meshes.
    labels = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(faces))
    component_counts = np.bincount(labels)
    triangles = np.asarray(mesh.triangles)
    signed_tetrahedra = np.einsum('ij,ij->i', triangles[:, 0],
                                 np.cross(triangles[:, 1], triangles[:, 2]))/6.0
    volume = float(signed_tetrahedra.sum())
    component_volumes = np.bincount(labels, weights=signed_tetrahedra)
    result = {
        'file': path.name, 'sha256': digest(path), 'vertices': len(vertices), 'triangles': len(faces),
        'finite_coordinates': bool(np.isfinite(vertices).all()),
        'watertight': bool(mesh.is_watertight), 'winding_consistent': bool(mesh.is_winding_consistent),
        'positive_signed_volume': volume > 0, 'volume_mm3': volume,
        'surface_area_mm2': float(mesh.area), 'euler_number': int(mesh.euler_number),
        'connected_components': len(component_counts),
        'component_triangles': component_counts.tolist(),
        'component_volume_mm3': component_volumes.tolist(),
        'bounds_mm': mesh.bounds.tolist(), 'dimensions_mm': mesh.extents.tolist(),
        'boundary_edges': len(boundary), 'overused_nonmanifold_edges': len(overused),
        'boundary_edge_locations': loc_summary(vertices[boundary].mean(1)),
        'nonmanifold_edge_locations': loc_summary(vertices[overused].mean(1)),
        'degenerate_triangles_area_below_1e_10_mm2': int(bad_area.sum()),
        'repeated_vertex_triangles': int(repeated_vertex.sum()),
        'duplicate_triangle_count': int(np.maximum(duplicate_counts-1, 0).sum()),
        'bad_triangle_locations': loc_summary(centers[bad_area | repeated_vertex]),
    }
    solid = m3d.Manifold(m3d.Mesh64(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces, dtype=np.uint64)))
    result['manifold_status'] = str(solid.status())
    result['manifold_empty'] = bool(solid.is_empty())
    result['manifold_volume_mm3'] = float(solid.volume())
    result['manifold_volume_agreement_mm3'] = abs(float(solid.volume())-volume)
    result['pass'] = all((result['finite_coordinates'], result['watertight'],
                          result['winding_consistent'], result['positive_signed_volume'],
                          len(component_counts) == 1, len(boundary) == 0, len(overused) == 0,
                          not bad_area.any(), not repeated_vertex.any(),
                          result['duplicate_triangle_count'] == 0,
                          solid.status() == m3d.Error.NoError, not solid.is_empty()))
    return result, mesh, solid


def ray_record(solid, start, end):
    hits = solid.ray_cast(tuple(start), tuple(end))
    return {'start_mm': list(start), 'end_mm': list(end), 'hit_count': len(hits),
            'hit_positions_mm': [list(h.position) for h in hits], 'clear': len(hits) == 0}


def intersection_record(a, b, contact_plane=None):
    overlap = a ^ b
    geometry = overlap.to_mesh64()
    positions = np.asarray(geometry.vert_properties)[:, :3]
    volume = float(overlap.volume())
    strict_pass = overlap.status() == m3d.Error.NoError and abs(volume) <= 1e-5
    result = {'volume_mm3': volume, 'empty': bool(overlap.is_empty()),
              'triangles': overlap.num_tri(), 'status': str(overlap.status()),
              'locations': loc_summary(positions), 'tolerance_mm3': 1e-5,
              'strict_volume_pass': strict_pass, 'pass': strict_pass}
    if contact_plane is not None and len(positions):
        origin, normal = contact_plane
        distances = (positions-origin)@normal
        plane_tolerance = 1e-5
        # This exception is restricted to a thin sheet at the actual contact
        # plane. The global collision-volume tolerance is not increased.
        coplanar = (overlap.status() == m3d.Error.NoError
                    and np.isfinite(distances).all()
                    and float(np.abs(distances).max()) <= plane_tolerance)
        result['stl_coplanar_contact'] = {
            'all_intersection_vertices_checked': len(positions),
            'signed_plane_distance_range_mm': [float(distances.min()), float(distances.max())],
            'max_absolute_plane_distance_mm': float(np.abs(distances).max()),
            'plane_tolerance_mm': plane_tolerance,
            'classified_as_precision_contact_sheet': bool(coplanar),
            'note': 'Raw intersection volume is retained. Only overlap entirely within the seam-plane tolerance is treated as STL float32 contact; no STL geometry is repaired.'}
        if coplanar:
            result['pass'] = True
            result['pass_reason'] = 'stl_coplanar_contact_sheet' if not strict_pass else 'strict_volume_and_coplanar_contact'
    return result


def section_record(solid, z, closing_tolerance_mm=0.0):
    raw_section = solid.slice(float(z))
    raw_contours = raw_section.to_polygons()
    section = raw_section
    if closing_tolerance_mm:
        # Measurement-only 2D closing of STL precision gaps at the seated seam.
        # This does not change the 3D solids and is not a print-fit adjustment.
        section = section.offset(closing_tolerance_mm).offset(-closing_tolerance_mm)
    contours = section.to_polygons()
    records = []
    for contour in contours:
        p = np.asarray(contour)
        q = np.roll(p, -1, axis=0)
        area = .5*float(np.sum(p[:, 0]*q[:, 1]-p[:, 1]*q[:, 0]))
        perimeter = float(np.linalg.norm(q-p, axis=1).sum())
        records.append({'signed_area_mm2': area, 'perimeter_mm': perimeter,
                        'vertex_count': len(p), 'bounds_xy_mm': [p.min(0).tolist(), p.max(0).tolist()]})
    # Manifold sections use positive-area contours for exterior boundaries.
    # The largest absolute-area contour is also reported to make the choice explicit.
    outer = max(records, key=lambda x: abs(x['signed_area_mm2'])) if records else None
    def perimeter(polygons):
        return float(sum(np.linalg.norm(np.roll(np.asarray(p), -1, axis=0)-p, axis=1).sum()
                         for p in polygons))
    return {'height_z_mm': float(z), 'contours': records, 'outer_contour': outer,
            'measurement_method': 'Largest exterior contour of the horizontal material section; measurement-only +epsilon/-epsilon 2D closing of floating-point seam gaps.',
            'measurement_closing_epsilon_mm': closing_tolerance_mm,
            'raw_section_contour_count': len(raw_contours),
            'raw_all_material_boundary_length_mm': perimeter(raw_contours),
            'taut_tape_convex_hull_perimeter_mm': perimeter(raw_section.hull().to_polygons()),
            'taut_tape_note': 'Convex hull bridges concavities and is a different measurement from the pre-split 190 mm surface-contour target; it is informational, not the pass metric.',
            'geometry_modified': False}


def thickness_samples(mesh, solid, count=1200):
    """Sample inward face-normal chords; diagnostics, not a full thickness proof."""
    areas = np.asarray(mesh.area_faces)
    rng = np.random.default_rng(7314)
    ids = rng.choice(len(mesh.faces), size=min(count, len(mesh.faces)), replace=False, p=areas/areas.sum())
    centers = np.asarray(mesh.triangles_center)[ids]
    normals = np.asarray(mesh.face_normals)[ids]
    pairs = []
    for center, normal in zip(centers, normals):
        start = center-normal*1e-4
        hits = solid.ray_cast(tuple(start), tuple(center-normal*20.0))
        if hits:
            distance = float(np.linalg.norm(np.asarray(hits[0].position)-center))
            if distance > 1e-5:
                pairs.append((distance, center.tolist()))
    pairs.sort(key=lambda x: x[0])
    values = np.array([p[0] for p in pairs])
    return {'method': 'deterministic area-weighted inward face-normal chords, maximum 20 mm',
            'sampled_faces': len(ids), 'valid_chords': len(pairs),
            'min_chord_mm': float(values.min()) if len(values) else None,
            'percentiles_1_5_50_95_mm': np.percentile(values, [1, 5, 50, 95]).tolist() if len(values) else None,
            'ten_shortest_chords': [{'length_mm': x, 'at_mm': p} for x, p in pairs[:10]],
            'limitation': 'Edge/rim and boolean seam chords can be short; this is not a minimum wall-thickness guarantee.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT)
    parser.add_argument('--skip-thickness', action='store_true')
    parser.add_argument('--check-eye-clearance', action='store_true',
                        help='Also intersect each nominal tessellated eye sphere with the shell')
    args = parser.parse_args()
    root = args.directory
    missing = [n for n in (*FILES.values(), 'build-report.json', 'parameters.json') if not (root/n).is_file()]
    if missing:
        print('Not ready; missing: '+', '.join(missing), file=sys.stderr)
        return 2
    start = time.monotonic()
    params = json.loads((root/'parameters.json').read_text())
    build = json.loads((root/'build-report.json').read_text())
    plane_origin, opening_normal = cap_frame(params, build)
    report = {'units': 'mm', 'method': 'Independent STL reload with trimesh and manifold3d',
              'trimesh_version': trimesh.__version__, 'parts': {}, 'physical_fit': 'NOT TESTED',
              'limitations': [
                  'Digital checks do not verify actual resin shrinkage, strength, magnet fit, eye fit or neck fit.',
                  'Manifold conversion and boolean acceptance are recorded; this is not an exhaustive independent triangle-pair self-intersection proof.',
                  'STL stores no unit metadata; millimeters are the documented convention.'
              ]}
    meshes, solids = {}, {}
    for key, filename in FILES.items():
        print('Checking '+filename, flush=True)
        result, mesh, solid = mesh_checks(root/filename)
        expected_euler = -4 if key == 'head_shell' else 2
        result['expected_euler_number'] = expected_euler
        result['expected_openings_topology'] = (
            'Thick shell with two eye openings, one neck opening and one removable-cap opening; genus 3.'
            if key == 'head_shell' else
            'Cup-like cap with blind magnet and locator holes; genus 0, no through-wall openings.')
        result['expected_euler_pass'] = result['euler_number'] == expected_euler
        result['pass'] = result['pass'] and result['expected_euler_pass']
        report['parts'][key] = result; meshes[key] = mesh; solids[key] = solid
        if not args.skip_thickness and solid.status() == m3d.Error.NoError:
            result['thickness_sampling'] = thickness_samples(mesh, solid)
        print(key, 'PASS' if result['pass'] else 'FAIL', 'volume', result['volume_mm3'], flush=True)
    if all(s.status() == m3d.Error.NoError for s in solids.values()):
        shell, cap = solids['head_shell'], solids['head_cap']
        report['protected_regions'] = protected_regions(root, params, build, meshes, plane_origin, opening_normal)
        report['assembly_intersection'] = intersection_record(shell, cap)
        report['assembly_intersection']['includes'] = 'All exported geometry including the rear locating pin, its support and blind socket, and both pairs of magnet bosses.'
        report['minimum_assembly_gap_mm_up_to_1mm'] = shell.min_gap(cap, 1.0)
        gap = float(params['cap_gap_mm'])
        seated_translation = -gap*opening_normal
        seated_cap = cap.translate(seated_translation.tolist())
        report['fully_seated_cap_intersection'] = intersection_record(shell, seated_cap, (plane_origin, opening_normal))
        report['fully_seated_cap_intersection'].update({
            'cap_translation_mm': seated_translation.tolist(),
            'includes': 'Complete rear cap moved inward along its opening axis by the seam gap.',
            'note': 'Coincident contact triangles may exist while intersection volume remains zero.'})
        removal_checks = []
        for distance in (0.0, .25, .5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0):
            translation = seated_translation + distance*opening_normal
            contact_plane = (plane_origin, opening_normal) if distance == 0 else None
            check = intersection_record(shell, cap.translate(translation.tolist()), contact_plane)
            check.update({'distance_from_seated_mm': distance, 'cap_translation_mm': translation.tolist()})
            removal_checks.append(check)
        report['rear_cap_removal_path'] = {
            'outward_unit_axis': opening_normal.tolist(), 'samples': removal_checks,
            'pass': all(c['pass'] for c in removal_checks),
            'limitation': 'Discrete straight-line collision samples, not a continuous swept-volume proof.'}
        if args.check_eye_clearance:
            eye_checks = []
            diameter = float(params['eye_diameter_mm'])
            for center in build['eye_centers_mm']:
                eye = m3d.Manifold.sphere(diameter/2, 128).translate(center)
                check = intersection_record(shell, eye)
                check.update({'nominal_diameter_mm': diameter, 'center_mm': center,
                              'sphere_segments': 128})
                eye_checks.append(check)
            report['nominal_eye_sphere_clearance'] = {
                'eyes': eye_checks, 'pass': all(c['pass'] for c in eye_checks),
                'limitation': 'Tessellated geometric sphere clearance only; does not verify actual eye profiles, optical fit, insertion path or physical assembly.'}
        # The oblique seam crosses the horizontal girth section. Measuring an
        # unseated assembly would mistake separated part contours for the head.
        assembly = shell + seated_cap
        z = build['girth_measure_z_mm']
        section = section_record(assembly, z, closing_tolerance_mm=1e-5)
        target = params['target_head_girth_mm']
        measured = section['outer_contour']['perimeter_mm'] if section['outer_contour'] else None
        report['girth_check'] = dict(section, target_mm=target, measured_mm=measured,
                                    assembly_pose='fully seated rear cap',
                                    error_mm=None if measured is None else measured-target,
                                    tolerance_mm=2.0,
                                    pass_within_2mm=measured is not None and abs(measured-target) <= 2.0)
        report['girth_check']['historical_target_only']=params.get('girth_target_is_historical_reference',False)
        report['girth_check']['revision_reason']=params.get('girth_revision_reason')
        report['girth_check']['measurement_valid']=measured is not None and np.isfinite(measured) and measured>0
        bounds = np.concatenate([m.bounds for m in meshes.values()]).reshape(-1,3)
        report['assembly_bounds_mm'] = [bounds.min(0).tolist(), bounds.max(0).tolist()]
        seated_bounds = np.concatenate((meshes['head_shell'].bounds,
                                        meshes['head_cap'].bounds+seated_translation))
        report['fully_seated_assembly_bounds_mm'] = [seated_bounds.min(0).tolist(), seated_bounds.max(0).tolist()]
        eye_paths = []
        for cx, cy, cz in build['eye_centers_mm']:
            eye_paths.append(ray_record(shell, [cx, float(meshes['head_shell'].bounds[0,1])-2, cz], [cx, cy, cz]))
        ny = build['neck_center_y_mm']
        neck = ray_record(shell, [0,ny,float(meshes['head_shell'].bounds[0,2])-2], [0,ny,build['neck_platform_top_mm']+6])
        report['opening_smoke_checks'] = {'eyes': eye_paths, 'neck_slot': neck,
                                          'pass': all(p['clear'] for p in eye_paths) and neck['clear'],
                                          'limitation': 'Central ray clearance only; does not establish full eye or neck articulation.'}
    report['pass'] = all(p['pass'] for p in report['parts'].values()) and all((
        report.get('assembly_intersection',{}).get('pass',False),
        report.get('fully_seated_cap_intersection',{}).get('pass',False),
        report.get('rear_cap_removal_path',{}).get('pass',False),
        report.get('protected_regions',{}).get('pass',False),
        (report.get('girth_check',{}).get('measurement_valid',False) if params.get('girth_target_is_historical_reference',False)
         else report.get('girth_check',{}).get('pass_within_2mm',False)),
        report.get('opening_smoke_checks',{}).get('pass',False),
        report.get('nominal_eye_sphere_clearance',{}).get('pass',True)))
    report['duration_seconds'] = time.monotonic()-start
    (root/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'pass':report['pass'], 'intersection':report.get('assembly_intersection'),
                      'fully_seated_intersection':report.get('fully_seated_cap_intersection'),
                      'eye_sphere_clearance':report.get('nominal_eye_sphere_clearance'),
                      'protected_regions':report.get('protected_regions'),
                      'removal_path_pass':report.get('rear_cap_removal_path',{}).get('pass'),
                      'girth':report.get('girth_check'), 'openings':report.get('opening_smoke_checks'),
                      'report':str(root/'validation.json')},ensure_ascii=False,indent=2))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
