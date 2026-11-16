"""Saved Blender mesh renders of the enlarged crown/rear split.

Colors, cameras and exploded translations are review aids in unsaved memory.
No mesh vertices, source files, or printed part files are edited by this script.
Run Blender --background --threads 2 --python THIS -- quarter [third special-six].
"""
from pathlib import Path
import sys, json, hashlib
import bpy
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
CHAR = HERE.parents[1]
REPO = CHAR.parents[1]
PRINT = ['PRINT_01_Head_Shell', 'PRINT_02_Removable_Cap']
SPECS = {
    'quarter': ('1-4/versions/v31-large-rear-cap', '1-4/versions/v30-pass-turn-seat'),
    'third': ('1-3/versions/v15-large-rear-cap', '1-3/versions/v14-pass-turn-seat'),
    'special-six': ('1-6-special/versions/v16-large-rear-cap', '1-6-special/versions/v15-pass-turn-seat'),
}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
records = []

def material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.)
    bsdf.inputs['Roughness'].default_value = .52
    bsdf.inputs['Metallic'].default_value = 0.
    m.diffuse_color = (*color, 1.)
    return m

def studio(path, scale):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(ob, do_unlink=True)
        elif ob.type == 'MESH':
            ob.hide_render = ob.name not in PRINT
    body = material('REVIEW ONLY light ivory resin', (.68, .62, .55))
    pink = material('REVIEW ONLY muted pink removable cap', (.52, .28, .30))
    for name, mat in zip(PRINT, [body, pink]):
        ob = bpy.data.objects[name]
        ob.hide_set(False)
        ob.hide_viewport = False
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        for f in ob.data.polygons:
            f.material_index = 0
    camera = bpy.data.objects.new('Review camera', bpy.data.cameras.new('Review camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_start = .01
    camera.data.clip_end = 1500.
    for name, location, power, size in [
        ('Review key', (-100, 80, 160), 260000, 90),
        ('Review fill', (110, 30, 80), 140000, 80),
        ('Review front', (0, -130, 140), 160000, 90),
    ]:
        ob = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
        scene.collection.objects.link(ob)
        ob.location = Vector(location) * scale
        ob.rotation_euler = (Vector((0, 0, 34)) * scale - ob.location).to_track_quat('-Z', 'Y').to_euler()
        ob.data.energy = power * scale ** 2
        ob.data.shape = 'DISK'
        ob.data.size = size * scale
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.16, .20, .24, 1)
    bg.inputs['Strength'].default_value = .5
    scene.use_nodes = False
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.view_settings.use_curve_mapping = False
    return scene, body, pink

VIEWS = {
    'side': ((-200, 0, 36), (0, 0, 35), 82, True, True, (0, 0, 0), False),
    'open': ((-75, 130, 112), (0, 0, 35), 83, True, False, (0, 0, 0), False),
    'exploded': ((-140, 160, 135), (23, 14, 43), 132, True, True, (55, 25, 22.5), False),
    'front': ((0, -200, 34), (0, 0, 35), 82, True, True, (0, 0, 0), True),
    'cap-interior': ((-75, -140, -55), (0, 2, 45), 82, False, True, (0, 0, 0), False),
    'top': ((0, 0, 230), (0, 0, 35), 82, True, True, (0, 0, 0), False),
}

def render(label, state, view, path, scale, scene, body, pink):
    camera, target, width, show_head, show_cap, cap_offset, neutral = VIEWS[view]
    head, cap = [bpy.data.objects[n] for n in PRINT]
    head.hide_render = not show_head
    cap.hide_render = not show_cap
    cap.matrix_world = Matrix.Translation(Vector(cap_offset) * scale)
    cap.data.materials.clear()
    cap.data.materials.append(body if neutral else pink)
    scene.camera.location = Vector(camera) * scale
    aim = Vector(target) * scale
    scene.camera.rotation_euler = (aim - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = width * scale
    bounce = bpy.data.objects.get('Review cap interior fill')
    if bounce is None:
        bounce = bpy.data.objects.new('Review cap interior fill', bpy.data.lights.new('Review cap interior fill', 'AREA'))
        scene.collection.objects.link(bounce)
        bounce.data.energy = 180000 * scale ** 2
        bounce.data.shape = 'DISK'
        bounce.data.size = 90 * scale
    bounce.hide_render = view != 'cap-interior'
    bounce.location = Vector((-30, -110, -45)) * scale
    bounce.rotation_euler = (Vector((0, 0, 44)) * scale - bounce.location).to_track_quat('-Z', 'Y').to_euler()
    output = HERE / (f'{label}-{state}-{view}' + ('-quick' if quick else '') + '.png')
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    records.append({
        'image': output.name, 'image_sha256': sha(output),
        'model': str(path.relative_to(REPO)), 'model_sha256': sha(path),
        'size': label, 'state': state, 'view': view,
        'camera_mm': list(scene.camera.location), 'target_mm': list(aim),
        'ortho_width_mm': width * scale, 'head_visible': show_head,
        'cap_visible': show_cap, 'cap_translation_mm': list(Vector(cap_offset) * scale),
        'review_material': 'ivory both pieces' if neutral else 'ivory face shell and muted pink rear cap',
        'vertex_coordinates_unchanged': True, 'reference_hardware_visible': False,
        'cap_interior_fill_enabled': view == 'cap-interior',
    })
    cap.matrix_world = Matrix.Identity(4)

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
labels = [a for a in args if a in SPECS] or list(SPECS)
old_only = '--old-only' in args
new_only = '--new-only' in args
quick = '--quick' in args
view_filter = next((a.split('=', 1)[1].split(',') for a in args if a.startswith('--views=')), None)
for label in labels:
    new_rel, old_rel = SPECS[label]
    states = [('old', old_rel)] if old_only else ([('new', new_rel)] if new_only else ([('old', old_rel), ('new', new_rel)] if label == 'quarter' else [('new', new_rel)]))
    for state, rel in states:
        folder = CHAR / rel
        p = json.loads((folder / 'parameters.json').read_text())
        path = folder / p['output_files']['blend']
        original_hash = sha(path)
        scale = p['source_uniform_scale']
        scene, body, pink = studio(path, scale)
        if quick:
            scene.cycles.samples = 8
            scene.render.resolution_percentage = 50
        views = ['side', 'open'] if state == 'old' else (['side', 'open', 'exploded', 'front', 'cap-interior', 'top'] if label == 'quarter' else ['open', 'exploded'])
        for view in views:
            if view_filter and view not in view_filter: continue
            render(label, state, view, path, scale, scene, body, pink)
        assert sha(path) == original_hash, 'Source Blender file changed'
    print('RENDERS_COMPLETE', label, flush=True)
report = {
    'method': 'Direct render of final saved Blender PRINT meshes, unsaved material/camera/exploded-object transforms only. No bitmap repainting or geometry manipulation.',
    'color_legend': 'Ivory = front face shell. Muted pink = removable rear cap; illustrative colors, not proposed resin colors. Neutral front view uses ivory on both.',
    'source_files_unchanged': True, 'views': records,
}
(HERE / ('render-provenance-' + '-'.join(labels) + ('-old' if old_only else '-new' if new_only else '') + ('-quick' if quick else '') + ('-' + '-'.join(view_filter) if view_filter else '') + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
