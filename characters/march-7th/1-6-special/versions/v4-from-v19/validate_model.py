#!/usr/bin/env python3
"""Independently validate the special-six STL exports against the accepted v19 meshes.

Needs numpy, scipy, trimesh and manifold3d. Does not repair meshes or modify any
input. Writes validation.json beside the new STL files. Units are millimeters.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
from scipy.spatial import cKDTree
import trimesh
import manifold3d as m3d


ROOT = Path(__file__).resolve().parent
EXPECTED_SCALE = 0.8889703622850876
POSITION_TOLERANCE = 3e-5
VOLUME_TOLERANCE = 1e-5
SOURCE_FILES = {
    'head': 'march7-head-shell-1-4-v19.stl',
    'cap': 'march7-head-cap-1-4-v19.stl',
}
TARGET_FILES = {
    'head': 'march7-head-shell-1-6-special-v4.stl',
    'cap': 'march7-head-cap-1-6-special-v4.stl',
}
SOURCE_HASHES = {
    'head': '4f725eb85a9964eca07883d8aec4e4f52bd2622ac20c60c3a333b25d5bf7ccfb',
    'cap': '83ee07951213b490a5203cd0a5663a4033c98d5f24131bd720559543a4cf824a',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def get_scale(params, build):
    for data in [params, build]:
        for name in ['scale_factor', 'uniform_scale_factor', 'uniform_scale', 'head_scale_factor', 'scale']:
            value = data.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        scaling = data.get('scaling', {})
        if isinstance(scaling, dict):
            for name in ['scale_factor', 'factor', 'uniform_scale']:
                if isinstance(scaling.get(name), (int, float)):
                    return float(scaling[name])
    return EXPECTED_SCALE


def as_solid(mesh):
    return m3d.Manifold(m3d.Mesh64(
        np.ascontiguousarray(mesh.vertices, dtype=np.float64),
        np.ascontiguousarray(mesh.faces, dtype=np.uint64)))


def mesh_checks(path, expected_euler):
    # Processing welds duplicate STL coordinates; validate=False prevents any
    # repair, face deletion or normal correction from concealing export errors.
    mesh = trimesh.load_mesh(path, process=True, validate=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f'{path.name} is not a single triangle mesh')
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, edge_counts = np.unique(edges, axis=0, return_counts=True)
    _, face_counts = np.unique(np.sort(faces, axis=1), axis=0, return_counts=True)
    labels = trimesh.graph.connected_component_labels(mesh.face_adjacency, node_count=len(faces))
    components = np.bincount(labels)
    areas = np.asarray(mesh.area_faces)
    repeated = np.any(np.diff(np.sort(faces, axis=1), axis=1) == 0, axis=1)
    solid = as_solid(mesh)
    report = {
        'file': path.name, 'sha256': digest(path),
        'vertices': len(vertices), 'triangles': len(faces),
        'finite_coordinates': bool(np.isfinite(vertices).all()),
        'watertight': bool(mesh.is_watertight),
        'consistent_winding': bool(mesh.is_winding_consistent),
        'connected_components': len(components),
        'component_triangles': components.tolist(),
        'boundary_edges': int(np.sum(edge_counts == 1)),
        'nonmanifold_overused_edges': int(np.sum(edge_counts > 2)),
        'degenerate_area_below_1e_10_mm2': int(np.sum(areas < 1e-10)),
        'repeated_vertex_triangles': int(np.sum(repeated)),
        'duplicate_triangles': int(np.maximum(face_counts - 1, 0).sum()),
        'euler_number': int(mesh.euler_number), 'expected_euler_number': expected_euler,
        'signed_volume_mm3': float(mesh.volume),
        'manifold_status': str(solid.status()), 'manifold_empty': bool(solid.is_empty()),
        'manifold_volume_mm3': float(solid.volume()),
        'bounds_mm': mesh.bounds.tolist(), 'dimensions_mm': mesh.extents.tolist(),
    }
    report['pass'] = bool(all([
        report['finite_coordinates'], report['watertight'], report['consistent_winding'],
        len(components) == 1, report['boundary_edges'] == 0,
        report['nonmanifold_overused_edges'] == 0,
        report['degenerate_area_below_1e_10_mm2'] == 0,
        report['repeated_vertex_triangles'] == 0, report['duplicate_triangles'] == 0,
        report['euler_number'] == expected_euler, report['signed_volume_mm3'] > 0,
        solid.status() == m3d.Error.NoError, not solid.is_empty(), solid.volume() > 0,
    ]))
    return report, mesh, solid


def intersection_check(first, second, contact_plane=None):
    overlap = first ^ second
    volume = float(overlap.volume())
    result = {
        'status': str(overlap.status()), 'volume_mm3': volume,
        'empty': bool(overlap.is_empty()), 'triangles': int(overlap.num_tri()),
        'volume_tolerance_mm3': VOLUME_TOLERANCE,
        'strict_volume_pass': bool(overlap.status() == m3d.Error.NoError and abs(volume) <= VOLUME_TOLERANCE),
    }
    result['pass'] = result['strict_volume_pass']
    if contact_plane is not None and not overlap.is_empty():
        points = np.asarray(overlap.to_mesh64().vert_properties)[:, :3]
        origin, normal = contact_plane
        distance = np.sum((points - origin) * normal, axis=1)
        max_distance = float(np.max(np.abs(distance))) if len(distance) else None
        planar = bool(overlap.status() == m3d.Error.NoError and len(points)
                      and np.isfinite(distance).all() and max_distance <= 1e-5)
        result['seam_plane_precision_contact'] = {
            'checked_vertices': len(points), 'max_distance_to_plane_mm': max_distance,
            'plane_tolerance_mm': 1e-5, 'is_precision_contact_sheet': planar,
            'note': 'Only a fully seated cap can use this plane-local classification; raw overlap volume is retained.',
        }
        result['pass'] = result['pass'] or planar
    return result


def nearest_record(query, target):
    distance, _ = cKDTree(target).query(query, workers=-1)
    worst = int(np.argmax(distance))
    return {
        'query_vertices': len(query), 'target_vertices': len(target),
        'maximum_distance_mm': float(distance[worst]),
        'rms_distance_mm': float(np.sqrt(np.mean(distance * distance))),
        'worst_query_point_mm': query[worst].tolist(),
        'points_at_or_above_tolerance': int(np.sum(distance >= POSITION_TOLERANCE)),
        'pass': bool(np.all(distance < POSITION_TOLERANCE)),
    }


def shape_preservation(source_meshes, meshes, scale, neck_y, platform_top, seat_radius):
    support_radius = seat_radius + 0.3
    support_min = np.array([-support_radius, neck_y - support_radius, -np.inf])
    support_max = np.array([support_radius, neck_y + support_radius, platform_top + 0.1])

    def protected(points):
        return ~np.all((points >= support_min) & (points <= support_max), axis=1)

    source_head = np.asarray(source_meshes['head'].vertices) * scale
    new_head = np.asarray(meshes['head'].vertices)
    source_cap = np.asarray(source_meshes['cap'].vertices) * scale
    new_cap = np.asarray(meshes['cap'].vertices)
    rows = {
        'head_source_protected_to_target': nearest_record(source_head[protected(source_head)], new_head),
        'head_target_protected_to_source': nearest_record(new_head[protected(new_head)], source_head),
        'whole_cap_source_to_target': nearest_record(source_cap, new_cap),
        'whole_cap_target_to_source': nearest_record(new_cap, source_cap),
    }
    return {
        'method': 'Bidirectional nearest-vertex distances after uniform scaling, without alignment, fitting or mesh repair.',
        'uniform_scale_factor': scale,
        'tolerance_mm_strictly_less_than': POSITION_TOLERANCE,
        'allowed_neck_change_box_mm': {
            'x': [-support_radius, support_radius], 'y': [neck_y - support_radius, neck_y + support_radius],
            'z': [None, platform_top + 0.1],
        },
        'checks': rows, 'pass': all(row['pass'] for row in rows.values()),
        'interpretation': 'All protected face, ears, cranium and the complete cap preserve v19 positions up to STL float precision; changes are confined to the neck support.',
    }


def ray_record(solid, start, end):
    hits = solid.ray_cast(tuple(start), tuple(end))
    return {
        'start_mm': list(start), 'end_mm': list(end), 'hit_count': len(hits),
        'hit_positions_mm': [list(hit.position) for hit in hits], 'clear': not bool(hits),
    }


def neck_checks(shell, mesh, neck_y, platform_top, sphere_center_z, seat_radius,
                slot_width, slot_length, roof, assumed_ball_diameter,
                source_shell, source_sphere_center_z, source_radius):
    # All slit measurements are above the ball's top, so the ball socket
    # cannot make an undersized or missing hook slit look artificially wider.
    z = platform_top - min(1.0, roof / 2.0)
    center = np.array([0.0, neck_y, z])
    axis_rows = {}
    for axis, expected in [(0, slot_width), (1, slot_length)]:
        distances = []
        positions = []
        for sign in [-1, 1]:
            direction = np.zeros(3)
            direction[axis] = sign
            hits = shell.ray_cast(tuple(center), tuple(center + direction * (seat_radius + slot_length + 2.0)))
            values = [(float(np.linalg.norm(np.asarray(h.position) - center)), list(h.position)) for h in hits]
            values = [item for item in values if item[0] > 1e-6]
            if values:
                distance, position = min(values, key=lambda item: item[0])
            else:
                distance, position = None, None
            distances.append(distance)
            positions.append(position)
        span = sum(distances) if all(d is not None for d in distances) else None
        axis_rows['width_x' if axis == 0 else 'length_y'] = {
            'nominal_mm': expected, 'measured_mm': span, 'first_hit_positions_mm': positions,
            'half_distances_mm': distances, 'tolerance_mm': 0.03,
            'pass': bool(span is not None and abs(span - expected) <= 0.03
                         and all(abs(d - expected / 2) <= 0.03 for d in distances)),
        }
    # A grid well inside the intended capsule checks straight-through access
    # from below the head to above the platform. No passage through solid is
    # permitted, even if the center ray alone happens to be clear.
    slot_radius = slot_width / 2.0
    half_straight = (slot_length - slot_width) / 2.0
    grid_margin = min(0.25, slot_radius / 10.0)
    grid_radius = slot_radius - grid_margin
    grid = []
    for x in np.linspace(-grid_radius, grid_radius, 5):
        for y in np.linspace(-slot_length / 2.0 + grid_margin, slot_length / 2.0 - grid_margin, 9):
            if x * x + max(abs(y) - half_straight, 0.0) ** 2 > grid_radius ** 2:
                continue
            grid.append(ray_record(shell, [x, neck_y + y, float(mesh.bounds[0, 2]) - 2.0],
                                   [x, neck_y + y, platform_top + 0.5]))
    # This is an open lower neck entrance with a partial spherical seat, not a
    # complete hemisphere. Check support only above the inherited open lower
    # rim and away from the hook slot; retain low-angle openings as unmeasured.
    sphere_center = np.array([0.0, neck_y, sphere_center_z])
    socket_rows = []
    for elevation in [45.0, 60.0]:
        z_component = np.sin(np.radians(elevation))
        radial = np.sqrt(1.0 - z_component ** 2)
        for theta in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            direction = np.array([radial * np.cos(theta), radial * np.sin(theta), z_component])
            expected_point = direction * seat_radius
            if expected_point[0] ** 2 + max(abs(expected_point[1]) - half_straight, 0.0) ** 2 < (slot_radius + 0.1) ** 2:
                continue
            hits = shell.ray_cast(tuple(sphere_center), tuple(sphere_center + direction * (seat_radius + 2.0)))
            distances = [float(np.linalg.norm(np.asarray(h.position) - sphere_center)) for h in hits]
            distances = [d for d in distances if d > 1e-6]
            distance = min(distances) if distances else None
            socket_rows.append({'direction': direction.tolist(), 'elevation_degrees': elevation,
                                'azimuth_degrees': float(np.degrees(theta)),
                                'first_hit_radius_mm': distance,
                                'pass': bool(distance is not None and abs(distance - seat_radius) <= 0.05)})
    lower_rows = []
    for theta in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        direction = np.array([np.sqrt(0.75) * np.cos(theta), np.sqrt(0.75) * np.sin(theta), 0.5])
        row = {'elevation_degrees': 30.0, 'azimuth_degrees': float(np.degrees(theta))}
        for name, solid, center_z, radius in [
                ('source_scaled_v19', source_shell, source_sphere_center_z, source_radius),
                ('new_socket', shell, sphere_center_z, seat_radius)]:
            origin = np.array([0.0, neck_y, center_z])
            hits = solid.ray_cast(tuple(origin), tuple(origin + direction * (radius + 2.0)))
            distances = [float(np.linalg.norm(np.asarray(h.position) - origin)) for h in hits]
            distance = min(distances) if distances else None
            row[name] = {'first_hit_radius_mm': distance,
                         'classification': 'surface_hit' if distance is not None else 'open_direction_unmeasured',
                         'used_as_support_pass': False}
        lower_rows.append(row)
    test_ball, min_support, enclosing_radius = enclosing_eye(assumed_ball_diameter / 2.0)
    ball_at_seat = test_ball.translate(sphere_center.tolist())
    ball_clearance = intersection_check(shell, ball_at_seat)
    ball_clearance.update({
        'nominal_analytic_diameter_mm': assumed_ball_diameter,
        'center_mm': sphere_center.tolist(),
        'enclosing_polyhedron_circumradius_mm': enclosing_radius,
        'unit_polyhedron_minimum_face_support': min_support,
        'minimum_clearance_mm_search_limited_to_1mm': float(shell.min_gap(ball_at_seat, 1.0)),
        'method': 'Convex polyhedron enclosing the complete analytic reference ball, including its lower half; strict intersection tolerance unchanged.',
    })
    roof_rows = []
    # Four cross-sections just outside the capsule independently check the
    # spherical ceiling and the platform top. Missing support remains a fail.
    offsets = [slot_radius + min(1.0, (seat_radius - slot_radius) / 4.0),
               slot_radius + min(2.5, (seat_radius - slot_radius) / 2.0)]
    for x in [-offsets[1], -offsets[0], offsets[0], offsets[1]]:
        expected_lower_z = sphere_center_z + np.sqrt(seat_radius ** 2 - x ** 2)
        hits = shell.ray_cast((x, neck_y, sphere_center_z), (x, neck_y, platform_top + 0.5))
        hit_z = sorted(float(h.position[2]) for h in hits)
        measured = hit_z[-1] - hit_z[0] if len(hit_z) == 2 else None
        expected_thickness = platform_top - expected_lower_z
        passed = bool(len(hit_z) == 2 and abs(hit_z[0] - expected_lower_z) <= 0.05
                      and abs(hit_z[1] - platform_top) <= 0.03
                      and abs(measured - expected_thickness) <= 0.06)
        roof_rows.append({'x_mm': x, 'y_mm': neck_y, 'hit_z_mm': hit_z,
                          'expected_spherical_ceiling_z_mm': float(expected_lower_z),
                          'expected_platform_top_z_mm': platform_top,
                          'measured_material_thickness_mm': measured,
                          'expected_material_thickness_mm': float(expected_thickness), 'pass': passed})
    wall_pass = bool(len(socket_rows) >= 16 and all(row['pass'] for row in socket_rows))
    roof_pass = bool(len(roof_rows) == 4 and all(row['pass'] for row in roof_rows))
    socket_pass = bool(wall_pass and roof_pass and ball_clearance['pass'])
    return {
        'center_y_mm': neck_y, 'platform_top_mm': platform_top,
        'slot_measurement_z_mm': z, 'slot_axes': axis_rows,
        'through_slot_rays': grid, 'through_slot_pass': all(row['clear'] for row in grid),
        'socket': {'nominal_diameter_mm': seat_radius * 2.0, 'center_mm': sphere_center.tolist(),
                   'nominal_roof_thickness_at_sphere_apex_mm': roof,
                   'sampled_spherical_wall_rays': socket_rows, 'radial_tolerance_mm': 0.05,
                   'upper_support_pass': wall_pass,
                   'lower_opening_diagnostics': lower_rows,
                   'lower_opening_note': 'No-hit lower directions are explicitly unmeasured openings, not successful spherical-wall checks. Source v19 already has open lower directions.',
                   'reference_ball_clearance': ball_clearance,
                   'roof_thickness_samples': roof_rows, 'roof_samples_pass': roof_pass,
                   'pass': socket_pass},
        'pass': bool(all(row['pass'] for row in axis_rows.values()) and grid
                     and all(row['clear'] for row in grid) and socket_pass),
        'limitation': 'Nominal local dimensions and straight passage samples only; no measured body, real S-hook, range-of-motion or physical neck fit is established.',
    }


def enclosing_eye(radius):
    unit = m3d.Manifold.sphere(1.0, 128)
    data = unit.to_mesh64()
    v = np.asarray(data.vert_properties)[:, :3]
    f = np.asarray(data.tri_verts)
    triangles = v[f]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    support = np.abs(np.einsum('ij,ij->i', normals, triangles[:, 0]))
    minimum = float(support.min())
    factor = radius / minimum
    return unit.scale([factor] * 3), minimum, factor


def validate(root, source):
    start = time.monotonic()
    params = read_json(root / 'parameters.json')
    build = read_json(root / 'build-report.json')
    source_build = read_json(root / 'source-interface-reference.json')
    source_params = read_json(source / 'parameters.json')
    scale = get_scale(params, build)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f'Invalid uniform scale {scale!r}')
    seat_radius = float(params.get('neck_seat_diameter_mm', build.get('neck_seat_diameter_mm', 32.0))) / 2.0
    slot_width = float(params.get('neck_slot_width_mm', 9.0))
    slot_length = float(params.get('neck_slot_length_mm', 18.0))
    roof = float(params.get('neck_roof_thickness_mm', build.get('neck_roof_nominal_mm', 4.0)))
    assumed_ball_diameter = float(params.get('assumed_neck_ball_diameter_mm', seat_radius * 2.0 - 0.5))
    nominal_eye_diameter = float(source_build.get('eye_nominal_diameter_mm', source_params.get('eye_diameter_mm', 16.0))) * scale
    if not all(np.isfinite(v) for v in [seat_radius, slot_width, slot_length, roof, assumed_ball_diameter]):
        raise ValueError('Non-finite neck dimensions')
    if not (seat_radius > slot_width / 2.0 > 0 and slot_length >= slot_width
            and roof > 0 and 0 < assumed_ball_diameter < seat_radius * 2.0):
        raise ValueError('Invalid ball socket or capsule dimensions')
    paths = [root / name for name in TARGET_FILES.values()] + [source / name for name in SOURCE_FILES.values()]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    hashes_before = {str(path): digest(path) for path in paths}
    source_hash_ok = all(hashes_before[str(source / filename)] == SOURCE_HASHES[key]
                         for key, filename in SOURCE_FILES.items())
    if not source_hash_ok:
        raise ValueError('Source STL is not the accepted immutable v19')
    report = {
        'version': 'march7-1-6-special-v4', 'units': 'mm', 'scale_factor': scale,
        'method': 'Independent STL reload; no rebuilding or mesh repair; scipy KDTree and Manifold geometric queries.',
        'trimesh_version': trimesh.__version__, 'parts': {},
        'source_v19_hashes_match': source_hash_ok,
        'physical_fit': 'NOT TESTED',
        'limitations': [
            'Digital validation does not verify resin shrinkage, printed strength, actual magnets, eye profiles or body-neck fit.',
            'Manifold accepts closed oriented solids; this is not an exhaustive independent all-triangle self-intersection test.',
            'Cap removal uses discrete straight-line collision samples, not a continuous swept-volume proof.',
            'Eye test verifies conservative scaled-nominal sphere endpoint clearance only; no new insertion route is proven.',
            'STL has no unit metadata. These files use millimeters by convention.',
        ],
    }
    source_meshes = {key: trimesh.load_mesh(source / filename, process=True, validate=False)
                     for key, filename in SOURCE_FILES.items()}
    meshes, solids = {}, {}
    for key, filename in TARGET_FILES.items():
        row, mesh, solid = mesh_checks(root / filename, -4 if key == 'head' else 2)
        report['parts'][key] = row
        meshes[key], solids[key] = mesh, solid
    ny = float(source_build.get('neck_center_y_mm', 6.59410659959549)) * scale
    top = float(source_build.get('neck_platform_top_mm', 19.78231979878647)) * scale
    old_center = float(source_build.get('neck_seat_center_z_mm', 5.082319798786472)) * scale
    source_radius = float(source_params.get('neck_seat_diameter_mm', 23.0)) / 2.0 * scale
    sphere_center = top - roof - seat_radius
    report['validated_parameters'] = {
        'uniform_scale': scale, 'neck_seat_diameter_mm': seat_radius * 2.0,
        'neck_slot_width_mm': slot_width, 'neck_slot_length_mm': slot_length,
        'neck_roof_thickness_mm': roof, 'assumed_neck_ball_diameter_mm': assumed_ball_diameter,
        'nominal_eye_diameter_mm': nominal_eye_diameter,
        'eye_diameter_basis': 'Source nominal eye diameter multiplied by the current uniform scale.',
    }
    report['shape_preservation'] = shape_preservation(source_meshes, meshes, scale, ny, top, seat_radius)
    if all(s.status() == m3d.Error.NoError and not s.is_empty() for s in solids.values()):
        shell, cap = solids['head'], solids['cap']
        normal = np.array(source_build.get('cap_plane_normal', [0.0, 1.0, 0.3]), dtype=float)
        normal /= np.linalg.norm(normal)
        origin = np.array(source_build.get('cap_plane_origin_mm', [0.0, 14.5, 50.0])) * scale
        gap = float(params.get('cap_gap_mm', float(source_params.get('cap_gap_mm', 0.25)) * scale))
        report['assembly_intersection'] = intersection_check(shell, cap)
        report['assembly_minimum_gap_mm_search_limited_to_1mm'] = float(shell.min_gap(cap, 1.0))
        seated = cap.translate((-gap * normal).tolist())
        report['fully_seated_cap_intersection'] = intersection_check(shell, seated, (origin, normal))
        report['fully_seated_cap_intersection']['translation_mm'] = (-gap * normal).tolist()
        exits = []
        for distance in [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0]:
            translation = distance * normal
            row = intersection_check(shell, cap.translate(translation.tolist()))
            row.update({'outward_distance_from_delivered_pose_mm': distance, 'translation_mm': translation.tolist()})
            exits.append(row)
        report['cap_exit_samples'] = {'outward_unit_axis': normal.tolist(), 'samples': exits,
                                      'pass': all(row['pass'] for row in exits)}
        scaled_source_head = source_meshes['head'].copy()
        scaled_source_head.apply_scale(scale)
        source_shell = as_solid(scaled_source_head)
        report['neck_interface'] = neck_checks(
            shell, meshes['head'], ny, top, sphere_center, seat_radius, slot_width,
            slot_length, roof, assumed_ball_diameter, source_shell, old_center, source_radius)
        eye, support, enclosing_radius = enclosing_eye(nominal_eye_diameter / 2.0)
        eye_rows = []
        eye_centers = np.asarray(source_build['eye_centers_mm'], dtype=float) * scale
        for center in eye_centers:
            placed = eye.translate(center.tolist())
            row = intersection_check(shell, placed)
            row.update({'center_mm': center.tolist(), 'nominal_analytic_diameter_mm': nominal_eye_diameter,
                        'minimum_clearance_mm_search_limited_to_1mm': float(shell.min_gap(placed, 1.0))})
            eye_rows.append(row)
        report['nominal_eye_sphere_clearance'] = {
            'method': 'A tessellated convex polyhedron enlarged until all face support planes enclose the analytic sphere.',
            'unit_sphere_minimum_face_support': support,
            'enclosing_polyhedron_circumradius_mm': enclosing_radius,
            'eyes': eye_rows, 'pass': all(row['pass'] for row in eye_rows),
        }
        if abs(nominal_eye_diameter - 20.0) < 1e-8:
            # Compatibility with the initial 1.25-scale delivery report.
            report['eyes_20mm'] = report['nominal_eye_sphere_clearance']
    unchanged = all(digest(path) == hashes_before[str(path)] for path in paths)
    report['input_files_unchanged'] = unchanged
    report['input_sha256'] = hashes_before
    required = ['shape_preservation', 'assembly_intersection', 'fully_seated_cap_intersection',
                'cap_exit_samples', 'neck_interface', 'nominal_eye_sphere_clearance']
    report['pass'] = bool(unchanged and all(p['pass'] for p in report['parts'].values())
                          and all(report.get(k, {}).get('pass', False) for k in required))
    report['duration_seconds'] = time.monotonic() - start
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT)
    parser.add_argument('--source-directory', type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    source = args.source_directory or root.parents[2] / '1-4/versions/v19-lip-refine'
    try:
        report = validate(root, source.resolve())
    except Exception as exc:
        report = {'pass': False, 'validation_error': f'{type(exc).__name__}: {exc}',
                  'physical_fit': 'NOT TESTED', 'inputs_modified': False}
    (root / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'report': str(root / 'validation.json'),
                      'protected_geometry_pass': report.get('shape_preservation', {}).get('pass'),
                      'neck_interface_pass': report.get('neck_interface', {}).get('pass'),
                      'eyes_20mm_pass': report.get('eyes_20mm', {}).get('pass'),
                      'nominal_eye_sphere_pass': report.get('nominal_eye_sphere_clearance', {}).get('pass'),
                      'error': report.get('validation_error')}, ensure_ascii=False))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
