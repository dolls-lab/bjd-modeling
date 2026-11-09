"""Render the saved meshes and a same-camera size comparison; never save models."""
from pathlib import Path
import hashlib
import json

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
NEW = HERE / 'march7-bjd-head-1-3-v1.blend'
OLD = HERE.parents[2] / '1-4/versions/march7-bjd-1-4-v0.14/march7-bjd-head-v0.14-draft.blend'
OUT = HERE / 'previews'
OUT.mkdir(exist_ok=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
hashes = {str(p): sha(p) for p in [NEW, OLD]}
records = []


def studio(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj.name not in ['PRINT_01_Head_Shell', 'PRINT_02_Removable_Cap']
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    for name, location, energy, size in [
        ('Key', (-110, -150, 210), 300000, 100),
        ('Fill', (130, -90, 100), 160000, 100),
        ('Rim', (20, 130, 170), 240000, 85),
    ]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy
        data.shape = 'DISK'
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0, 0, 42)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (0.17, 0.20, 0.25, 1)
    background.inputs['Strength'].default_value = 0.5
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 40
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.camera.data.type = 'ORTHO'
    return scene


def render(scene, name, position, target, width, cap_visible=True):
    scene.camera.location = position
    scene.camera.rotation_euler = (Vector(target) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = width
    bpy.data.objects['PRINT_02_Removable_Cap'].hide_render = not cap_visible
    path = OUT / (name + '.png')
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    records.append({'file': 'previews/' + path.name, 'sha256': sha(path),
                    'camera_mm': position, 'target_mm': target,
                    'ortho_width_mm': width, 'cap_visible': cap_visible})


views = [
    ('front', (0, -250, 43.5), (0, 0, 43.5), 110),
    ('quarter', (-160, -240, 85), (0, 0, 43.5), 118),
    ('side', (-250, 0, 43.5), (0, 0, 43.5), 110),
    ('rear', (0, 250, 43.5), (0, 0, 43.5), 110),
    ('top', (0, -35, 280), (0, 0, 43.5), 110),
    ('neck', (55, -85, -130), (0, 8, 12), 75),
]
scene = studio(NEW)
for args in views:
    render(scene, 'third-' + args[0], *args[1:])
render(scene, 'third-interior', (0, 180, 100), (0, 3, 40), 105, cap_visible=False)
scene = studio(OLD)
for args in [views[0], views[2]]:
    render(scene, 'quarter-' + args[0], *args[1:])
for path, expected in hashes.items():
    assert sha(Path(path)) == expected
(HERE / 'render-provenance.json').write_text(json.dumps({
    'source_models_sha256': {NEW.name: hashes[str(NEW)], OLD.name: hashes[str(OLD)]},
    'model_files_unchanged': True,
    'method': 'Actual saved mesh renders; same studio and orthographic camera for four/three size comparisons. No retouching.',
    'views': records,
}, ensure_ascii=False, indent=2) + '\n')
print('RENDERS_COMPLETE', flush=True)
