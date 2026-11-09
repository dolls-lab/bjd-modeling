from pathlib import Path
import sys
import bpy
from mathutils import Vector
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from apply_face_material import create_textured_head
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
ob=create_textured_head(OUT/'face-uv-transfer.npz')
# Unlit color diagnostic removes lighting ambiguity from UV/mask assessment.
mat=ob.data.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links
bs=nodes.get('Principled BSDF');color_link=next(x for x in links if x.to_socket==bs.inputs['Base Color']);color_socket=color_link.from_socket
out=nodes.get('Material Output');em=nodes.new('ShaderNodeEmission');links.new(color_socket,em.inputs['Color']);links.new(em.outputs[0],out.inputs['Surface'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.world.color=(.18,.18,.18);scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('UVCheck');cam=bpy.data.objects.new('UVCheck',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=84;cd.clip_start=.1;cd.clip_end=1000
for name,loc,target in [('front',(0,-200,32),(0,0,32)),('quarter',(-140,-150,53),(0,0,33)),('side',(-200,0,37),(0,0,33))]:
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/f'uv-check-{name}.png');bpy.ops.render.render(write_still=True)
print('UV_RENDER_DONE',flush=True)
