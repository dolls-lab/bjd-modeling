#!/usr/bin/env python3
"""Read-only continuous swept-sphere insertion checks for the v0.8 BJD head.

Only this script's JSON report is written. The source meshes are never changed.
The removed cap is intentionally absent from insertion-path obstacles.
"""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
import trimesh
import manifold3d as md

ROOT = Path(__file__).resolve().parent
VOLUME_TOLERANCE = 1e-5


def load_solid(path):
    mesh = trimesh.load_mesh(path, process=True, validate=False)
    solid = md.Manifold(md.Mesh64(np.ascontiguousarray(mesh.vertices, dtype=np.float64),
                                  np.ascontiguousarray(mesh.faces, dtype=np.uint64)))
    if solid.status() != md.Error.NoError:
        raise ValueError(f'{path.name}: {solid.status()}')
    return solid


def enclosing_ball(radius):
    """Circumscribe the analytic ball with a convex tessellated sphere."""
    unit = md.Manifold.sphere(1.0, 128)
    geometry = unit.to_mesh64()
    verts = np.asarray(geometry.vert_properties)[:, :3]
    tris = verts[np.asarray(geometry.tri_verts)]
    normals = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0])
    distances = np.abs(np.einsum('ij,ij->i', normals, tris[:, 0]))/np.linalg.norm(normals, axis=1)
    support_min = float(distances.min())
    scale = radius/support_min
    ball = unit.scale((scale, scale, scale))
    return ball, {
        'nominal_analytic_diameter_mm': 2*radius,
        'sphere_segments': 128,
        'unit_polyhedron_minimum_face_support_distance': support_min,
        'polyhedron_circumradius_mm': scale,
        'polyhedron_maximum_diameter_mm': 2*scale,
        'method': 'Scale a convex tessellated unit sphere until every face plane is at least the nominal radius from its center. The resulting polyhedron encloses the analytic ball.'}


def point_segment_distance(point, a, b):
    direction = b-a
    t = np.clip(np.dot(point-a, direction)/np.dot(direction, direction), 0, 1)
    return float(np.linalg.norm(point-(a+t*direction)))


def check_path(shell, ball, points, other_eye, nominal_diameter):
    segments = []
    for a, b in zip(points, points[1:]):
        swept = md.Manifold.batch_hull([ball.translate(a.tolist()), ball.translate(b.tolist())])
        overlap = shell ^ swept
        volume = float(overlap.volume())
        passed = overlap.status() == md.Error.NoError and abs(volume) <= VOLUME_TOLERANCE
        clearance = float(shell.min_gap(swept, 1.0)) if passed else 0.0
        other_distance = point_segment_distance(other_eye, a, b)
        record = {
            'start_mm': a.tolist(), 'end_mm': b.tolist(), 'length_mm': float(np.linalg.norm(b-a)),
            'swept_polyhedron_status': str(swept.status()),
            'intersection_status': str(overlap.status()), 'intersection_volume_mm3': volume,
            'intersection_triangles': overlap.num_tri(), 'intersection_empty': bool(overlap.is_empty()),
            'minimum_head_clearance_mm_search_limited_to_1mm': clearance,
            'minimum_center_distance_to_other_installed_eye_mm': other_distance,
            'other_eye_collision_free': other_distance >= nominal_diameter,
            'pass': passed and other_distance >= nominal_diameter}
        if not passed:
            geometry = overlap.to_mesh64()
            vv = np.asarray(geometry.vert_properties)[:, :3]
            record['collision_bounds_mm'] = [vv.min(0).tolist(), vv.max(0).tolist()] if len(vv) else None
        segments.append(record)
    return {'waypoints_mm': [p.tolist() for p in points], 'segments': segments,
            'pass': all(s['pass'] for s in segments)}


def main():
    start_time = time.monotonic()
    model_path = ROOT/'march7-head-shell-v0.8-draft.stl'
    build = json.loads((ROOT/'build-report.json').read_text())
    params = json.loads((ROOT/'parameters.json').read_text())
    center = np.asarray(build['cap_plane_origin_mm'], dtype=float)
    axis = np.asarray(build['cap_plane_normal'], dtype=float)
    axis /= np.linalg.norm(axis)
    u = np.array([1.0, 0.0, 0.0])
    v = np.cross(axis, u)
    diameter = float(params['eye_diameter_mm'])
    targets = np.asarray(build['eye_centers_mm'], dtype=float)
    shell = load_solid(model_path)
    ball, ball_info = enclosing_ball(diameter/2)
    outside = center+30*axis
    results = []
    for i, target in enumerate(targets):
        sign = 1 if target[0] >= 0 else -1
        routes = [
            ('direct_from_rear_opening', [outside, target]),
            ('central_entry_waypoint', [outside, center-10*axis, target]),
            ('lower_entry_waypoint', [outside+4*v, center+4*v-10*axis, target]),
            ('side_entry_waypoint', [outside+sign*6*u, center+sign*6*u-10*axis, target]),
        ]
        trials = []
        for name, points in routes:
            result = check_path(shell, ball, points, targets[1-i], diameter)
            result['route_name'] = name
            trials.append(result)
            print(f'Eye {i+1} {name}: '+('PASS' if result['pass'] else 'collision'), flush=True)
            if result['pass']:
                break
        results.append({'eye_index': i+1, 'target_center_mm': target.tolist(),
                        'path_found': any(t['pass'] for t in trials),
                        'selected_path': next((t for t in trials if t['pass']), None),
                        'attempts': trials})
    report = {
        'version': 'v0.8-draft', 'units': 'mm',
        'head_shell_file': model_path.name,
        'head_shell_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'cap_state': 'Removed; all head-shell geometry, including magnet bosses, locating pin and neck platform, remains present.',
        'opening_plane_origin_mm': center.tolist(), 'opening_outward_unit_axis': axis.tolist(),
        'outside_start_center_mm': outside.tolist(), 'ball_enclosure': ball_info,
        'continuous_path_method': 'For every straight path segment, intersect the head with the convex hull of the same enclosing ball at both endpoints. This hull contains the entire continuous sphere sweep, not just sampled placements.',
        'intersection_volume_tolerance_mm3': VOLUME_TOLERANCE,
        'eyes': results, 'pass': all(r['path_found'] for r in results),
        'limitations': [
            'Only nominal spherical eyes are checked; stems, protruding irises, tools, fingers and eye-fixing putty are not modeled.',
            'Reported clearance applies to the conservative digital polyhedron and the current STL, not to measured printed parts.',
            'Printer tolerances, resin shrinkage, strength and the actual eye shape have not been physically verified.',
            'Failure of a tested simple path would not prove that no curved or other piecewise path exists.',
            'Other-eye avoidance uses analytic centerline distance against a stationary nominal sphere at the other seat.'
        ], 'duration_seconds': time.monotonic()-start_time}
    path = ROOT/'eye-insertion-check.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'pass': report['pass'], 'report': str(path),
                      'enclosing_diameter_mm': ball_info['polyhedron_maximum_diameter_mm'],
                      'eyes': [{'index':r['eye_index'], 'path_found':r['path_found'],
                                'selected':r['selected_path']} for r in results]}, ensure_ascii=False, indent=2))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
