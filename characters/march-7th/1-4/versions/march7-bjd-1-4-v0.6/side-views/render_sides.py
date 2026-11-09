"""Read-only camera study of the delivered v6 head: six side views and four ear closeups."""
from pathlib import Path
import hashlib,json,math
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent;ROOT=R.parent
BASE=ROOT/'march7-bjd-head-v0.6-draft.blend'
before=hashlib.sha256(BASE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE));s=bpy.context.scene
for ob in list(bpy.data.objects):
    if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.type=='MESH':ob.hide_render=not ob.name.startswith('PRINT_')
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
head.hide_render=False;cap.hide_render=False;cap.location=(0,0,0)
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=40;s.cycles.use_denoising=True
s.render.resolution_x=1200;s.render.resolution_y=1200;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
s.world=bpy.data.worlds.new('Side review studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5;s.view_settings.view_transform='AgX'
for name,loc,energy,size in [('Key',(-90,-100,150),220000,90),('Fill',(100,-40,75),120000,70),('Rim',(10,90,130),200000,60)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);s.collection.objects.link(cam);s.camera=cam;data.type='ORTHO'
views=[]
for side,sign in [('left',1),('right',-1)]:
    for suffix,angle in [('front-side',55),('side',90),('rear-side',125)]:
        theta=math.radians(angle);loc=(sign*200*math.sin(theta),-200*math.cos(theta),40)
        views.append(('v6-'+side+'-'+suffix+'.png',loc,(0,0,37),101))
    views.extend([
        ('v6-'+side+'-ear-front.png',(sign*160,-80,70),(sign*23,0,32),55),
        ('v6-'+side+'-ear-rear.png',(sign*160,80,65),(sign*23,3,31),55),
    ])
for name,loc,target,ortho in views:
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=ortho
    s.render.filepath=str(R/name);bpy.ops.render.render(write_still=True)
assert before==hashlib.sha256(BASE.read_bytes()).hexdigest()
report={'model_file':str(BASE),'model_sha256':before,'input_model_modified':False,
        'resolution':[1200,1200],'source':'Actual v6 Blender mesh renders; no image shape edits.',
        'camera':'orthographic','lighting':'same fixed studio lights for every view',
        'views':[{'file':name,'camera_position_mm':loc,'target_mm':target,'ortho_width_mm':ortho} for name,loc,target,ortho in views]}
(R/'render-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SIDE_VIEWS_DONE',flush=True)
