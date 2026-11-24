"""Render the saved meshes and a same-camera size comparison; never save models."""
from pathlib import Path
import hashlib
import json

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
NEW = HERE / 'march7-bjd-head-1-4-v19.blend'
OLD = HERE.parent / 'v18-lip-only/march7-bjd-head-1-4-v18.blend'
OUT = HERE / 'previews'
OUT.mkdir(exist_ok=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
hashes = {str(p): sha(p) for p in [NEW, OLD]}
records = []
VIEW_SCALE=1.1248968946833189


def studio(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj.name not in ['PRINT_01_Head_Shell', 'PRINT_02_Removable_Cap']
    for obj in list(bpy.data.objects):
        if obj.type in {'LIGHT','CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)
    # Set one neutral clay material in unsaved memory for both versions.
    material = bpy.data.materials.new('Comparison neutral clay')
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.58, 0.48, 0.43, 1)
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.inputs['Metallic'].default_value = 0
    for name in ['PRINT_01_Head_Shell', 'PRINT_02_Removable_Cap']:
        obj = bpy.data.objects[name]
        obj.hide_render = False
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for face in obj.data.polygons:
            face.material_index = 0
    camera_data = bpy.data.cameras.new('Comparison camera')
    camera = bpy.data.objects.new('Comparison camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.use_nodes = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.view_settings.use_curve_mapping = False
    for name, location, energy, size in [
        ('Key', (-110, -150, 210), 300000, 100),
        ('Fill', (130, -90, 100), 160000, 100),
        ('Rim', (20, 130, 170), 240000, 85),
    ]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy * VIEW_SCALE**2
        data.shape = 'DISK'
        data.size = size * VIEW_SCALE
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = tuple(v*VIEW_SCALE for v in location)
        obj.rotation_euler = (Vector((0, 0, 42*VIEW_SCALE)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (0.17, 0.20, 0.25, 1)
    background.inputs['Strength'].default_value = 0.5
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.camera.data.type = 'ORTHO'
    return scene


def render(scene, name, position, target, width, cap_visible=True):
    position=tuple(v*VIEW_SCALE for v in position)
    target=tuple(v*VIEW_SCALE for v in target)
    width*=VIEW_SCALE
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
 ('front', (0,-250,31), (0,0,31), 80),
 ('quarter', (-160,-240,60), (0,0,31), 82),
 ('side', (-250,0,31), (0,0,31), 80),
 ('mouth-front', (0,-160,10), (0,-24,10), 22),
 ('mouth-quarter', (-100,-140,16), (0,-24,10), 22),
 ('mouth-side', (-150,-24,10), (0,-24,10), 22),
]
for prefix,path in [('v18',OLD),('v19',NEW)]:
 scene=studio(path)
 for args in views: render(scene,prefix+'-'+args[0],*args[1:])
 # Additional side light emphasizes surface curvature and transition seams.
 key=bpy.data.objects['Key'];key.location=tuple(v*VIEW_SCALE for v in (-150,-95,50))
 key.rotation_euler=(Vector((0,-24*VIEW_SCALE,11*VIEW_SCALE))-key.location).to_track_quat('-Z','Y').to_euler()
 key.data.size=55*VIEW_SCALE
 bpy.data.objects['Fill'].data.energy*=.3
 render(scene,prefix+'-mouth-grazing',(0,-160,11),(0,-24,11),26)

for path, expected in hashes.items(): assert sha(Path(path))==expected
(HERE/'render-provenance.json').write_text(json.dumps({
 'source_models_sha256':{NEW.name:hashes[str(NEW)],OLD.name:hashes[str(OLD)]},
 'model_files_unchanged':True,
 'method':'Actual saved v18/v19 meshes; identical orthographic cameras, lighting, neutral clay material and AgX exposure. Scene changes are in unsaved memory; source model files never saved or retouched.',
 'views':records},ensure_ascii=False,indent=2)+'\n')
print('RENDERS_COMPLETE',flush=True)
