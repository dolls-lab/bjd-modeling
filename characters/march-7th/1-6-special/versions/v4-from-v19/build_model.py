"""Build a special-six prototype from immutable v19 geometry. Run with Blender --python."""
from pathlib import Path
import hashlib
import json

import bpy
import bmesh
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
CHARACTER = HERE.parents[2]
SOURCE = CHARACTER / '1-4/versions/v19-lip-refine'
BLEND = HERE / 'march7-bjd-head-1-6-special-v4.blend'
FILES = {
    'PRINT_01_Head_Shell': HERE / 'march7-head-shell-1-6-special-v4.stl',
    'PRINT_02_Removable_Cap': HERE / 'march7-head-cap-1-6-special-v4.stl',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arrays(obj):
    obj.data.calc_loop_triangles()
    vertices = np.asarray([v.co[:] for v in obj.data.vertices], dtype=np.float64)
    faces = np.asarray([f.vertices[:] for f in obj.data.loop_triangles], dtype=np.int32)
    return vertices, faces


def main():
    params = json.loads((HERE / 'parameters.json').read_text())
    base = json.loads((HERE / 'source-interface-reference.json').read_text())
    source_params = json.loads((SOURCE / 'parameters.json').read_text())
    source_blend = SOURCE / 'march7-bjd-head-1-4-v19.blend'
    source_sha = sha(source_blend)
    assert source_sha == '62c142e53949baefc35cc869112f584ce03a612c0e8e0a76e6d32337a0dbdebb'
    scale = float(params['uniform_scale'])
    assert 0.7 < scale < 1.1
    radius = float(params['neck_seat_diameter_mm']) / 2
    slot_width = float(params['neck_slot_width_mm'])
    slot_length = float(params['neck_slot_length_mm'])
    assert radius >= source_params['neck_seat_diameter_mm'] * scale / 2
    assert slot_width >= source_params['neck_slot_width_mm'] * scale
    assert slot_length >= source_params['neck_slot_length_mm'] * scale
    assert slot_length >= slot_width > 0
    roof = float(params['neck_roof_thickness_mm'])
    # Keep the original scaled spherical cavity inside the enlarged cutter.
    assert 0 < roof <= 3.2 * scale + 1e-7
    neck_y = float(base['neck_center_y_mm']) * scale
    platform_top = float(base['neck_platform_top_mm']) * scale
    seat_center_z = platform_top - roof - radius
    print('OPEN_SOURCE', flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    scene = bpy.context.scene
    # Retain only actual print objects; historical mother meshes are not this size.
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH' and obj.name not in FILES:
            bpy.data.objects.remove(obj, do_unlink=True)
    before = {}
    for name in FILES:
        obj = bpy.data.objects[name]
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        before[name] = arrays(obj)[0].copy()
        obj.data.transform(Matrix.Diagonal((scale, scale, scale, 1)))
        obj.data.update()
        obj['size_class'] = 'special-six prototype'
        obj['source_v19_uniform_scale'] = scale
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            obj.location *= scale
            obj.data.energy *= scale * scale
            if obj.data.type == 'AREA':
                obj.data.size *= scale
        elif obj.type == 'CAMERA':
            obj.location *= scale
            obj.data.ortho_scale *= scale
    head = bpy.data.objects['PRINT_01_Head_Shell']

    def subtract(cutter):
        bpy.ops.object.select_all(action='DESELECT')
        head.select_set(True)
        bpy.context.view_layer.objects.active = head
        modifier = head.modifiers.new('Local neck sizing only', 'BOOLEAN')
        modifier.operation = 'DIFFERENCE'
        modifier.solver = 'EXACT'
        modifier.object = cutter
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter, do_unlink=True)

    # The lowered center keeps the ball-seat top and roof thickness fixed.
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=int(params['neck_boolean_sphere_segments']),
        ring_count=int(params['neck_boolean_sphere_rings']),
        radius=radius, location=(0, neck_y, seat_center_z))
    subtract(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=256, radius=radius, depth=100,
        location=(0, neck_y, seat_center_z - 50))
    subtract(bpy.context.object)
    # A Y-directed capsule, open through the reinforced neck platform.
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, neck_y, platform_top - 20))
    box = bpy.context.object
    box.dimensions = (slot_width, slot_length - slot_width, 50)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    subtract(box)
    for sign in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=128, radius=slot_width / 2, depth=50,
            location=(0, neck_y + sign * (slot_length - slot_width) / 2, platform_top - 20))
        subtract(bpy.context.object)
    # Only numerical artifacts at the neck intersections are merged/dissolved.
    bm = bmesh.new()
    bm.from_mesh(head.data)
    region = [v for v in bm.verts if v.co.z < platform_top + 1.3
              and abs(v.co.x) < radius + 2
              and abs(v.co.y - neck_y) < radius + 2]
    bmesh.ops.remove_doubles(bm, verts=region, dist=params['local_merge_tolerance_mm'])
    region_ids = {v.index for v in region if v.is_valid}
    edges = [e for e in bm.edges if all(v.index in region_ids for v in e.verts)]
    bmesh.ops.dissolve_degenerate(bm, edges=edges, dist=params['local_degenerate_tolerance_mm'])
    # Triangulate only local Boolean polygons, then collapse numerical slivers.
    # This never touches the protected face, ears, skull or cap.
    def in_neck(v):
        return (v.co.z < platform_top + 1.3 and abs(v.co.x) < radius + 2
                and abs(v.co.y - neck_y) < radius + 2)
    local_ngons = [f for f in bm.faces if len(f.verts) > 3 and all(in_neck(v) for v in f.verts)]
    bmesh.ops.triangulate(bm, faces=local_ngons)
    sliver_cleanup = []
    for _ in range(20):
        candidates = [f for f in bm.faces if len(f.verts) == 3
                      and f.calc_area() < params['local_sliver_area_mm2']
                      and all(in_neck(v) for v in f.verts)]
        if not candidates:
            break
        face = candidates[0]
        edge = min(face.edges, key=lambda e: e.calc_length())
        assert edge.calc_length() < params['local_sliver_max_edge_mm']
        sliver_cleanup.append({'area_mm2': face.calc_area(),
                              'collapsed_edge_mm': edge.calc_length(),
                              'center_mm': list(face.calc_center_median())})
        bmesh.ops.collapse(bm, edges=[edge], uvs=False)
    assert not any(f.calc_area() < params['local_sliver_area_mm2']
                   for f in bm.faces if all(in_neck(v) for v in f.verts))
    bm.normal_update()
    assert all(e.is_manifold for e in bm.edges), 'Neck operation left a non-manifold edge'
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    head['neck_seat_diameter_mm'] = radius * 2
    head['neck_slot_dimensions_mm'] = [slot_width, slot_length]
    head['neck_only_boolean_no_global_remesh'] = True
    parts = {}
    snapshot = {}
    for name, path in FILES.items():
        obj = bpy.data.objects[name]
        v, f = arrays(obj)
        snapshot[name] = {'vertices': v, 'triangles': f}
        if name == 'PRINT_02_Removable_Cap':
            assert np.max(np.abs(v - before[name] * scale)) < 1e-5
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True,
                             apply_modifiers=True, global_scale=1.0, use_scene_unit=False)
        parts[name] = {'file': path.name, 'sha256': sha(path), 'vertices': len(v),
                       'triangles': len(f), 'bounds_mm': [v.min(0).tolist(), v.max(0).tolist()],
                       'dimensions_mm': np.ptp(v, axis=0).tolist()}
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene['model_version'] = params['version']
    scene['physical_fit'] = params['physical_fit']
    scene['source_v19_sha256'] = source_sha
    scene['notes'] = f'Face and cranium uniformly scaled {scale:.9f}. Only neck socket and hook slot resized locally.'
    # A readable default view for opening the saved file.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_distance *= scale
                area.spaces.active.region_3d.view_location *= scale
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    model_sha = sha(BLEND)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    for name, expected in snapshot.items():
        actual_v, actual_f = arrays(bpy.data.objects[name])
        assert np.array_equal(actual_v, expected['vertices'])
        assert np.array_equal(actual_f, expected['triangles'])
    assert sha(source_blend) == source_sha
    report = {
        'version': params['version'], 'units': 'mm', 'uniform_scale': scale,
        'source_blend': str(source_blend.relative_to(CHARACTER)), 'source_blend_sha256': source_sha,
        'source_blend_unchanged': True, 'blend': BLEND.name, 'blend_sha256': model_sha,
        'saved_reopened_meshes_identical': True, 'parts': parts,
        'neck_center_y_mm': neck_y, 'neck_platform_top_mm': platform_top,
        'neck_seat_center_z_mm': seat_center_z, 'neck_seat_diameter_mm': radius * 2,
        'neck_roof_nominal_mm': roof, 'neck_slot_mm': [slot_width, slot_length],
        'cap_plane_origin_mm': (np.asarray(base['cap_plane_origin_mm']) * scale).tolist(),
        'cap_plane_normal': base['cap_plane_normal'],
        'eye_centers_mm': (np.asarray(base['eye_centers_mm']) * scale).tolist(),
        'head_girth_reference_section_mm': params['source_head_girth_at_reference_section_mm'] * scale,
        'girth_measure_z_mm': params['source_girth_section_z_mm'] * scale,
        'change_scope': params['policy'], 'physical_fit': params['physical_fit'],
        'neck_cleanup_only': {'merge_mm': params['local_merge_tolerance_mm'],
                              'dissolve_degenerate_mm': params['local_degenerate_tolerance_mm'],
                              'local_slivers_collapsed': sliver_cleanup},
    }
    (HERE / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('BUILD_SAVED', json.dumps({'blend_sha256': model_sha, 'parts': parts}), flush=True)


if __name__ == '__main__':
    main()
