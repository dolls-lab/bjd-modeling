"""Render scaled v19 derivatives using the identical v19 comparison studio."""
from pathlib import Path
import hashlib,json,shutil
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
CHAR=REPO/'characters/march-7th'
OUT=HERE/'previews';OUT.mkdir(exist_ok=True)
QUARTER=CHAR/'1-4/versions/v19-lip-refine'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
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


views=[
 ('front',(0,-250,31),(0,0,31),80),
 ('quarter',(-160,-240,60),(0,0,31),82),
 ('side',(-250,0,31),(0,0,31),80),
 ('mouth-quarter',(-100,-140,16),(0,-24,10),22),
]
# Reuse the already verified four v19 source renders; the studio above is identical.
source_prov=json.loads((QUARTER/'render-provenance.json').read_text())
source_blend=QUARTER/'march7-bjd-head-1-4-v19.blend'
assert sha(source_blend)==source_prov['source_models_sha256'][source_blend.name]
models=[{'label':'quarter-v19','path':str(source_blend.relative_to(REPO)),'uniform_scale':1.,'sha256':sha(source_blend)}]
for args in views:
 name='v19-'+args[0];src=QUARTER/'previews'/f'{name}.png'
 item=next(i for i in source_prov['views'] if i['file']=='previews/'+name+'.png')
 assert sha(src)==item['sha256'];dst=OUT/f'quarter-v19-{args[0]}.png';shutil.copyfile(src,dst)
 records.append({**item,'file':str(dst.relative_to(HERE)),'model':'quarter-v19','reuse_source':str(src.relative_to(REPO)),'scale_normalized_in_camera':True})
for label,folder in [('third-v3','1-3/versions/v3-from-v19'),('special-six-v4','1-6-special/versions/v4-from-v19')]:
 folder=CHAR/folder
 params=json.loads((folder/'parameters.json').read_text())
 paths=list(folder.glob('*.blend'));assert len(paths)==1,paths
 path=paths[0];s=float(params['uniform_scale']);initial=sha(path)
 models.append({'label':label,'path':str(path.relative_to(REPO)),'uniform_scale':s,'sha256':initial})
 VIEW_SCALE=1.1248968946833189*s
 scene=studio(path)
 for args in views:
  render(scene,label+'-'+args[0],*args[1:])
  records[-1]['model']=label;records[-1]['scale_normalized_in_camera']=True
 assert sha(path)==initial
for item in models:assert sha(REPO/item['path'])==item['sha256']
(HERE/'render-provenance.json').write_text(json.dumps({'models':models,'views':records,'method':'Actual saved PRINT meshes, same normalized cameras, neutral material, area-light geometry and irradiance. Source v19 images copied with verified hashes from its existing actual renders. No mesh writes or image retouching.','model_files_unchanged':True},ensure_ascii=False,indent=2)+'\n')
print('RENDERS_COMPLETE',flush=True)
