from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
import numpy as np
import bpy
from mathutils import Vector
OUT=Path(__file__).parent;OUT.mkdir(exist_ok=True)
ROOT=OUT.parent/'march7-bjd-1-4-v0.13'
BASE=OUT.parent/'march7-bjd-1-4-v0.12';sys.path.insert(0,str(BASE))
from parse_pmx import load_pmx
SOURCE=Path(json.loads((ROOT/'parameters.json').read_text())['source_pmx'])
SCALE=27.47544416498121;CHIN=18.16621208190918
args=SimpleNamespace(unlit=False)
src=load_pmx(SOURCE)
BLEND=ROOT/'march7-bjd-head-v0.13-draft.blend'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial={str(p):digest(p) for p in [SOURCE,BLEND]}
bpy.ops.wm.open_mainfile(filepath=str(BLEND));scene=bpy.context.scene
for ob in list(bpy.data.objects):
 if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
 elif ob.type=='MESH':ob.hide_render=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Source review studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,loc,power,size in [('Key',(-90,-100,150),220000,65),('Fill',(100,-40,75),120000,65),('Rim',(10,90,130),200000,50)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.clip_start=.1;cd.clip_end=3000
vertices = src['vertices']
world = np.column_stack((vertices[:, 0], vertices[:, 2], vertices[:, 1] - CHIN)) * SCALE
normals = src['normals'][:, [0, 2, 1]]
images = {}
material_records = []
geometry_max_roundoff = 0.0

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for spec in src['materials']:
    faces = src['faces'][spec['start']:spec['end']]
    ids = np.unique(faces)
    mapping = np.full(len(vertices), -1, dtype=int)
    mapping[ids] = np.arange(len(ids))
    # The axis exchange is a reflection, so reverse winding to retain the
    # original outward surface orientation. Vertex positions are untouched.
    local_faces = mapping[faces][:, ::-1]
    mesh = bpy.data.meshes.new('PMX_original_' + spec['name'])
    mesh.from_pydata(world[ids].tolist(), [], local_faces.tolist())
    mesh.update()
    uv = mesh.uv_layers.new(name='Original_PMX_UV')
    for loop in mesh.loops:
        su, sv = src['uvs'][ids[loop.vertex_index]]
        uv.data[loop.index].uv = (float(su), 1.0 - float(sv))
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals[ids].tolist())
    ob = bpy.data.objects.new('PMX_original_' + spec['name'], mesh)
    scene.collection.objects.link(ob)
    geometry_max_roundoff = max(geometry_max_roundoff, float(np.max(np.abs(
        np.asarray([v.co[:] for v in mesh.vertices]) - world[ids]))))

    mat = bpy.data.materials.new('Original_Texture_' + spec['name'])
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    if args.unlit:
        bsdf = nodes.new('ShaderNodeEmission')
        bsdf.inputs['Strength'].default_value = 1.0
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        alpha_mix = nodes.new('ShaderNodeMixShader')
        links.new(transparent.outputs[0], alpha_mix.inputs[1])
        links.new(bsdf.outputs[0], alpha_mix.inputs[2])
        links.new(alpha_mix.outputs[0], output.inputs['Surface'])
        color_socket = bsdf.inputs['Color']
        alpha_socket = alpha_mix.inputs[0]
    else:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        color_socket = bsdf.inputs['Base Color']
        alpha_socket = bsdf.inputs['Alpha']
    color_socket.default_value = spec['diffuse']
    alpha_socket.default_value = spec['diffuse'][3]
    texture_path = None
    ti = spec['texture_index']
    if 0 <= ti < len(src['textures']):
        texture_path = SOURCE.parent / src['textures'][ti].replace('\\', '/')
        if not texture_path.is_file():
            raise FileNotFoundError(texture_path)
        if texture_path not in images:
            images[texture_path] = bpy.data.images.load(str(texture_path), check_existing=True)
            images[texture_path].colorspace_settings.name = 'sRGB'
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = images[texture_path]
        tex.interpolation = 'Linear'
        color = nodes.new('ShaderNodeMixRGB')
        color.blend_type = 'MULTIPLY'
        color.inputs[0].default_value = 1.0
        color.inputs[2].default_value = spec['diffuse']
        links.new(tex.outputs['Color'], color.inputs[1])
        links.new(color.outputs[0], color_socket)
        alpha = nodes.new('ShaderNodeMath')
        alpha.operation = 'MULTIPLY'
        alpha.inputs[1].default_value = spec['diffuse'][3]
        links.new(tex.outputs['Alpha'], alpha.inputs[0])
        links.new(alpha.outputs[0], alpha_socket)
    mesh.materials.append(mat)
    material_records.append({
        'original_material': spec['name'], 'triangles': len(faces),
        'diffuse_rgba': spec['diffuse'],
        'texture': str(texture_path) if texture_path else None,
        'geometry_modifiers': [],
    })

clay=bpy.data.materials.new('Shared review clay');clay.use_nodes=True
bs=clay.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.65,.58,.53,1);bs.inputs['Roughness'].default_value=.75;bs.inputs['Specular IOR Level'].default_value=.25
for ob in bpy.data.objects:
 if ob.name.startswith('PRINT_'):ob.data.materials.clear();ob.data.materials.append(clay)
views=[('front',(0,-200,28),(0,0,28),120),('quarter',(-160,-110,60),(0,0,28),120),('side',(-200,0,28),(0,0,28),120)]
records=[]
for variant in ['original-textured','original-face','bjd-v13']:
 for ob in bpy.data.objects:
  if ob.type=='MESH':ob.hide_render=True
 if variant=='original-textured':
  for ob in bpy.data.objects:
   if ob.name.startswith('PMX_original_'):ob.hide_render=False
 elif variant=='original-face':
  ob=bpy.data.objects['PMX_original_脸'];ob.hide_render=False;ob.data.materials.clear();ob.data.materials.append(clay)
 else:
  for ob in bpy.data.objects:
   if ob.name.startswith('PRINT_'):ob.hide_render=False
 for name,loc,target,scale in views:
  cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale
  scene.render.filepath=str(OUT/f'{variant}-{name}.png');bpy.ops.render.render(write_still=True);records.append({'file':f'{variant}-{name}.png','camera_mm':loc,'target_mm':target,'ortho_width_mm':scale})
assert all(digest(Path(p))==h for p,h in initial.items())
(OUT/'render-provenance.json').write_text(json.dumps({'inputs':initial,'source_transform':'[PMX X,PMX Z,PMX Y-18.16621208190918]*27.47544416498121','views':records,'geometry_modified':False,'geometry_max_float32_roundoff_mm':geometry_max_roundoff,'source_face':'Raw PMX face material only; no reconstructed rear skull. Original transformed custom normals retained.','source_textured':'Original geometry and textures with Blender diffuse lighting; not an in-game screenshot or official shader reproduction.','comparability':'Same cameras, scale and lighting. Clay source face/current shell share a single material. BJD is final actual PRINT objects.','textures':[{'path':str(p),'sha256':digest(p)} for p in images],'materials':material_records},ensure_ascii=False,indent=2)+'\n')
print('ORIGINAL_COMPARISON_DONE',flush=True)
