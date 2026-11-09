"""Same-camera renders of actual baseline and revised meshes; no geometry edits."""
from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent
for source,prefix in [('baseline-v0.5.blend','preview-before-v0.5-'),('march7-bjd-head-v0.6-draft.blend','preview-')]:
    bpy.ops.wm.open_mainfile(filepath=str(R/source))
    scene=bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
        elif ob.type=='MESH':ob.hide_render=not ob.name.startswith('PRINT_')
    bpy.data.objects['PRINT_01_Head_Shell'].hide_render=False
    bpy.data.objects['PRINT_02_Removable_Cap'].hide_render=False
    bpy.data.objects['PRINT_02_Removable_Cap'].location=(0,0,0)
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Comparison world');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    scene.view_settings.view_transform='AgX'
    for name,loc,energy,size in [('Key',(-90,-100,150),220000,90),('Fill',(100,-40,75),120000,70),('Rim',(10,90,130),200000,60)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
    for name,loc,target,ortho in [('front',(0,-180,37),(0,0,37),105),('side',(180,0,40),(0,0,37),105),('top',(0,-.001,220),(0,0,37),105),('quarter',(115,-180,100),(0,0,37),105),('ear-detail',(160,-80,70),(23,0,34),53),('forehead-detail',(115,-180,100),(0,-4,54),68)]:
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=ortho
        scene.render.filepath=str(R/(prefix+name+'.png'));bpy.ops.render.render(write_still=True)
print('DETAIL_COMPARISON_DONE',flush=True)
