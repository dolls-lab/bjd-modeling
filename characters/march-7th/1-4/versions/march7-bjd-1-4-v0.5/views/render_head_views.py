"""Render v5 views and an exact raw-PMX face comparison. Never save/edit the input blend."""
from pathlib import Path
import sys,json,hashlib
import bpy
import numpy as np
from mathutils import Vector

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
sys.path.insert(0,str(ROOT))
from parse_pmx import load_pmx
P=json.loads((ROOT/'parameters.json').read_text())
BLEND=ROOT/'march7-bjd-head-v0.5-draft.blend'
input_hash=hashlib.sha256(BLEND.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BLEND));scene=bpy.context.scene
for ob in list(bpy.data.objects):
    if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.type=='MESH':ob.hide_render=not ob.name.startswith('PRINT_')
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
head.hide_render=False;cap.hide_render=False;cap.location=(0,0,0)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('Review studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX'
for name,loc,energy,size in [('Key',(-90,-100,150),220000,90),('Fill',(100,-40,75),120000,70),('Rim',(10,90,130),200000,60)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
VIEWS=[
 ('front',(0,-180,37),(0,0,37),105),
 ('left-quarter',(115,-180,100),(0,0,37),105),
 ('right-quarter',(-115,-180,100),(0,0,37),105),
 ('left-side',(180,0,40),(0,0,37),105),
 ('right-side',(-180,0,40),(0,0,37),105),
 ('back',(0,180,40),(0,0,37),105),
 ('top',(0,-.001,220),(0,0,37),105),
 ('rear-quarter',(115,180,100),(0,0,37),105),
 ('low-front',(0,-180,-40),(0,0,31),105),
]
def render(name,loc,target,ortho):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=ortho
    scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
for name,loc,target,ortho in VIEWS:render('v5-'+name+'.png',loc,target,ortho)

# Raw PMX material face: exact positions, normal directions and triangle order.
# No subdivision, filling, sculpting, symmetry operation or hollowing.
src=load_pmx(P['source_pmx']);material=next(m for m in src['materials'] if m['name']=='脸')
fs=src['faces'][material['start']:material['end']];ids=np.unique(fs)
mapping=np.full(len(src['vertices']),-1,int);mapping[ids]=np.arange(len(ids))
v=src['vertices'][ids];n=src['normals'][ids]
chin=18.16621208190918;scale=P['fixed_source_scale_mm']
vertices=np.column_stack([v[:,0],v[:,2],v[:,1]-chin])*scale
normals=np.column_stack([n[:,0],n[:,2],n[:,1]])
mesh=bpy.data.meshes.new('ExactOriginalPMXFace');mesh.from_pydata(vertices.tolist(),[],mapping[fs][:,::-1].tolist());mesh.update()
for poly in mesh.polygons:poly.use_smooth=True
mesh.normals_split_custom_set_from_vertices(normals.tolist())
source=bpy.data.objects.new('OriginalMarch7Face_NoGeometryChanges',mesh);scene.collection.objects.link(source)
clay=bpy.data.materials.new('Same neutral clay for direct geometry comparison');clay.use_nodes=True
bs=clay.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.42,.42,.42,1);bs.inputs['Roughness'].default_value=.38
for ob in (source,head,cap):ob.data.materials.clear();ob.data.materials.append(clay)
comparison=[('front',(0,-180,37),(0,0,37),105),('quarter',(115,-180,100),(0,0,37),105),('side',(180,0,40),(0,0,37),105)]
for name,loc,target,ortho in comparison:
    source.hide_render=False;head.hide_render=True;cap.hide_render=True
    render('raw-face-'+name+'.png',loc,target,ortho)
    source.hide_render=True;head.hide_render=False;cap.hide_render=False
    render('v5-clay-'+name+'.png',loc,target,ortho)
assert input_hash==hashlib.sha256(BLEND.read_bytes()).hexdigest()
report={'input_blend':str(BLEND),'input_blend_sha256':input_hash,'source_pmx':P['source_pmx'],
 'source_pmx_sha256':hashlib.sha256(Path(P['source_pmx']).read_bytes()).hexdigest(),
 'source_material':'脸','source_faces':len(fs),'source_geometry_modified':False,'input_model_files_modified':False,
 'transform':{'axes':'(X,Z,Y-chin)*scale','chin':chin,'scale':scale},
 'render':{'engine':'Blender Cycles','resolution':[1200,1200],'samples':48,'camera':'orthographic','face_comparison_same_camera_scale_lights_material':True},
 'views':[{'name':name,'camera':loc,'target':target,'ortho_mm':ortho} for name,loc,target,ortho in VIEWS],
 'limitations':['Raw original face is an open animation mesh with eye and mouth gaps and no skin rear skull.','Texture-free views remove hair, eyes and makeup, showing the raw face geometry only.','These are renders of actual model geometry, not in-game screenshots.']}
(OUT/'views-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('HEAD_VIEWS_DONE',flush=True)
