"""Round the face-to-cranium junction of the validated v0.3 mesh.

Run with Blender 4.5. Units are millimeters. No remeshing or topological edits.
The packaged baseline contains the prior sculpt and mechanical assembly.
"""
from pathlib import Path
import json, math, hashlib, shutil
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'baseline-v0.3.blend'))
scene=bpy.context.scene
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
master=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing']
reference=bpy.data.objects['SOURCE_Original_March7_Face_DoNotPrint']
cap_normal=Vector(P['cap_plane_normal']).normalized()
report=json.loads((ROOT/'baseline-build-report.json').read_text())
report['version']=P['version']

def log(s):print(s,flush=True)
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def stl(o,name):
    active(o);bpy.ops.wm.stl_export(filepath=str(ROOT/name),export_selected_objects=True,apply_modifiers=True,global_scale=1.,use_scene_unit=False)

def smoother(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*t*(t*(t*6.-15.)+10.)

# This BVH is the complete exterior BEFORE hollowing, not the inner shell.
# Freeze it before any deformation so all objects use the same continuous field.
tree=BVHTree.FromPolygons([v.co[:] for v in master.data.vertices],[list(f.vertices) for f in master.data.polygons],all_triangles=False)
settings=P['cranium_rounding'];cy=settings['center_y_mm'];cz=settings['center_z_mm']
rx,ry,rz=settings['ellipsoid_radii_mm']
low,high=settings['lower_blend_z_mm'];guard,full=settings['cap_protection_distance_mm']
changes={}
for ob in (head,master):
    original=np.array([v.co[:] for v in ob.data.vertices]);movements=[];misses=0
    for vertex in ob.data.vertices:
        x,y,z=vertex.co
        if z<=low or z>=cz+rz:continue
        planar=Vector((x,y-cy,0));radius=planar.length
        if radius<1e-5:continue
        direction=planar/radius
        hit,normal,faceid,outer_radius=tree.ray_cast(Vector((0,cy,z)),direction,120)
        if hit is None:misses+=1;continue
        distance_to_cap=29.5-(hit.y+.3*hit.z)
        back_weight=smoother(guard,full,distance_to_cap)
        ear_weight=1-smoother(18,22,abs(hit.x))*(1-smoother(39,54,z))
        weight=smoother(low,high,z)*back_weight*ear_weight
        if weight<1e-8:continue
        height_fraction=max(0.,1-((z-cz)/rz)**2)
        a=rx*math.sqrt(height_fraction);b=ry*math.sqrt(height_fraction)
        target_radius=1/math.sqrt((direction.x/a)**2+(direction.y/b)**2)
        offset=(target_radius-outer_radius)*weight
        vertex.co+=direction*offset
        movements.append(abs(offset))
    ob.data.update()
    changes[ob.name]={'moved_vertices':len(movements),'maximum_displacement_mm':max(movements,default=0),'median_displacement_mm':float(np.median(movements)) if movements else 0,'ray_misses':misses,'vertex_count_unchanged':len(ob.data.vertices)==len(original),'minimum_changed_z_mm':float(original[np.linalg.norm(np.array([v.co[:] for v in ob.data.vertices])-original,axis=1)>1e-7,2].min())}
    log(json.dumps(changes[ob.name]))
# Recompute normals without rebuilding faces or touching mechanical geometry.
for ob in (head,master):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for poly in ob.data.polygons:poly.use_smooth=True
head['revision']='v0.4 continuous face/cranium transition'
report['cranium_rounding']={'settings':settings,'objects':changes,'cap_geometry':'unchanged from v0.3','method':'Analytic fixed-height elliptical sections with C2 masks, same radial displacement for inner and outer walls; topology preserved','baseline_blend_sha256':hashlib.sha256((ROOT/'baseline-v0.3.blend').read_bytes()).hexdigest()}
report['parts']={}
for part in (head,cap):
    bm=bmesh.new();bm.from_mesh(part.data)
    report['parts'][part.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume(signed=True),'bounds_mm':list(part.dimensions)}
    bm.free()
(ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
stl(head,'march7-head-shell-v0.4-draft.stl')
shutil.copy2(ROOT/'baseline-cap.stl',ROOT/'march7-head-cap-v0.4-draft.stl')
for ob in (master,reference):ob.hide_set(True);ob.hide_render=True
# Replace the baseline studio so the old and new renders use identical lights.
for ob in list(bpy.data.objects):
    if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
# A neutral studio scene, with editable print parts and hidden original reference.
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX'
def light(name,loc,energy,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-90,-100,150),220000,90);light('Fill',(100,-40,75),120000,70);light('Rim',(10,90,130),200000,60)
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
def view(name,loc,target,ortho=105):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=ortho
    scene.render.filepath=str(ROOT/name);bpy.ops.render.render(write_still=True)
view('preview-front.png',(0,-180,37),(0,0,37))
view('preview-quarter.png',(115,-180,100),(0,0,37))
view('preview-side.png',(180,0,40),(0,0,37))
view('preview-back.png',(0,180,60),(0,0,37))
cap.location=cap_normal*28
view('preview-exploded.png',(150,150,85),(0,15,38),125)
cap.hide_render=True
view('preview-interior.png',(0,180,100),(0,0,36),105)
view('preview-neck.png',(55,-65,-110),(0,0,25),105)
cap.hide_render=False;cap.location=(0,0,0)
head.hide_render=True
view('preview-cap-interior.png',(0,-140,10),(0,20,45),90)
head.hide_render=False
cam.location=(115,-180,100);cam.rotation_euler=(Vector((0,0,37))-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=105
active(head)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=130
        area.spaces.active.region_3d.view_location=Vector((0,0,36))
        area.spaces.active.clip_end=10000
        area.spaces.active.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'march7-bjd-head-v0.4-draft.blend'),compress=True)
log('DONE')
