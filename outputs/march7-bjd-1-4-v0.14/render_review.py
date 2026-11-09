"""Read-only, identically lit actual-print closeups and whole-head comparisons."""
from pathlib import Path
import sys, hashlib, json
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent;D=R/'comparison-renders';D.mkdir(exist_ok=True)
versions=['v13'] if '--baseline-only' in sys.argv else (['v14'] if '--current-only' in sys.argv else ['v13','v14'])
views=[
 ('front',(0,-200,37),(0,0,37),101),
 ('quarter',(-160,-110,60),(0,0,37),101),
 ('side',(-200,0,37),(0,0,37),101),
 ('top',(0,0,240),(0,0,35),101),
 ('crown-front',(0,-200,59),(0,0,59),62),
 ('eye-front',(0,-200,28),(0,-20,28),51),
 ('eye-quarter',(-85,-115,53),(-13,-24,28),31),
]
for version in versions:
    path=R.parent/'march7-bjd-1-4-v0.13'/'march7-bjd-head-v0.13-draft.blend' if version=='v13' else R/'march7-bjd-head-v0.14-draft.blend'
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
        elif ob.type=='MESH':ob.hide_render=not ob.name.startswith('PRINT_')
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=56;s.cycles.use_denoising=True
    s.render.resolution_x=1100;s.render.resolution_y=1100;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.film_transparent=False
    s.world=bpy.data.worlds.new('Review studio');s.world.use_nodes=True
    s.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
    s.world.node_tree.nodes['Background'].inputs[1].default_value=.5;s.view_settings.view_transform='AgX'
    for name,loc,power,size in [('Key',(-90,-100,150),220000,65),('Fill',(100,-40,75),120000,65),('Rim',(10,90,130),200000,50)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);s.collection.objects.link(cam);s.camera=cam;data.type='ORTHO'
    for suffix,loc,target,scale in views:
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
        s.render.filepath=str(D/f'{version}-{suffix}.png');bpy.ops.render.render(write_still=True)
    assert sha==hashlib.sha256(path.read_bytes()).hexdigest()
    (D/f'{version}-render-provenance.json').write_text(json.dumps({'model_file':str(path),'model_sha256':sha,
      'input_model_modified':False,'source':'Actual PRINT objects. Camera and lighting changes in unsaved memory only. No raster retouching.',
      'resolution':[1100,1100],'views':[{'file':f'{version}-{n}.png','camera_mm':loc,'target_mm':target,'ortho_width_mm':scale} for n,loc,target,scale in views]},indent=2)+'\n')
    print('REVIEW_RENDER_DONE '+version,flush=True)
