"""Run with Blender 4.5: blender -b -t 4 --python build_head.py.

Actual source PMX face is retained; scalp and BJD structure are newly modeled.
Blender mesh coordinates and STL coordinates are millimeters.
"""
from pathlib import Path
import sys, json, math, hashlib, argparse
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from parse_pmx import load_pmx, topology
P = json.loads((ROOT / 'parameters.json').read_text())
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
STAGE = args[0] if args else 'final'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .001
scene.unit_settings.length_unit = 'MILLIMETERS'

def log(s): print(s, flush=True)
def active(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
def apply(o, mod):
    active(o); bpy.ops.object.modifier_apply(modifier=mod.name)
def mesh(name, verts, faces):
    m=bpy.data.meshes.new(name); m.from_pydata(verts, [], faces); m.update()
    o=bpy.data.objects.new(name,m); scene.collection.objects.link(o)
    bm=bmesh.new(); bm.from_mesh(m)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(m); bm.free()
    return o
def smooth(o):
    for p in o.data.polygons: p.use_smooth=True
def copy(o,name):
    n=o.copy();n.data=o.data.copy();n.name=name;scene.collection.objects.link(n);return n
def remove(o): bpy.data.objects.remove(o,do_unlink=True)
def boolean(o, tool, operation='DIFFERENCE',keep=False):
    m=o.modifiers.new(operation,'BOOLEAN');m.operation=operation;m.solver='MANIFOLD';m.object=tool
    apply(o,m)
    if not keep:remove(tool)
def cube(name, loc, dims):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def cylinder(name,loc,radius,depth):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth, location=loc)
    o=bpy.context.object;o.name=name;return o
def sphere(name,loc,radius):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=radius, location=loc)
    o=bpy.context.object;o.name=name;return o
def material(name,color,rough=.42):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;return m
def setmat(o,m): o.data.materials.clear();o.data.materials.append(m)
def stl(o,name):
    active(o);bpy.ops.wm.stl_export(filepath=str(ROOT/name),export_selected_objects=True,apply_modifiers=True,global_scale=1.0,use_scene_unit=False)
def section_segments(o,z):
    o.data.calc_loop_triangles()
    vv=np.array([v.co[:] for v in o.data.vertices]); ff=np.array([t.vertices for t in o.data.loop_triangles])
    tris=vv[ff];lo=tris[:,:,2].min(1);hi=tris[:,:,2].max(1);tris=tris[(lo<z)&(hi>z)]
    segs=[]
    for tr in tris:
        pts=[]
        for a,b in zip(tr,np.roll(tr,-1,axis=0)):
            if (a[2]-z)*(b[2]-z)<0:
                pts.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
        if len(pts)==2:segs.append(pts)
    return np.array(segs)

log('Reading original PMX and lowered v10 mother surface')
src=load_pmx(P['source_pmx']);mat=next(m for m in src['materials'] if m['name']=='脸')
top,raw,ff=topology(src['vertices'],src['faces'][mat['start']:mat['end']])
chin=float(raw[:,1].min());loops=top['boundary_loops']
scale=P['fixed_source_scale_mm'];zg=P['girth_measure_z_mm']/scale
with np.load(ROOT/'mother-surface.npz') as arc:mother={k:arc[k] for k in arc.files}
o=mesh('March7_Master_Outer_Surface',mother['after'].tolist(),mother['triangles'].tolist())
smooth(o)
# Rear cap plane: Y + 0.3 Z = 29.5; n points backward/up.
cap_origin=Vector(P['cap_plane_origin_mm'])
cap_normal=Vector(P['cap_plane_normal']).normalized()
u=Vector((1,0,0));v_axis=cap_normal.cross(u)
# v_axis points down along the tilted cut, retaining a right-handed frame.
R=Matrix((u,v_axis,cap_normal)).transposed()
local_to_world=R.to_4x4();local_to_world.translation=cap_origin
world_to_local=local_to_world.inverted()
cut=0.0
raw_mm=np.column_stack([raw[:,0],raw[:,2],raw[:,1]-chin])*scale
reference=mesh('SOURCE_Original_March7_Face_DoNotPrint',raw_mm,ff.tolist());reference.hide_render=True;reference.hide_set(True)
reference['source_sha256']=hashlib.sha256(Path(P['source_pmx']).read_bytes()).hexdigest()
reference['credit']='miHoYo / 神帝宇; local personal derivative; see source-usage-rules.txt'
master=copy(o,'EDITABLE_Outer_Surface_Before_Hollowing');master.hide_render=True;master.hide_set(True)
envelope=copy(o,'TOOL_Closed_Exterior_Envelope')
bm=bmesh.new();bm.from_mesh(envelope.data)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(envelope.data);bm.free()
envelope.hide_render=True;envelope.hide_set(True)
boss_envelope=copy(envelope,'TOOL_Inset_Magnet_Limit')
for vertex in boss_envelope.data.vertices:vertex.co-=vertex.normal*.65
boss_envelope.data.update();boss_envelope.hide_render=True;boss_envelope.hide_set(True)
log(f'Scale {scale:.5f}; historical girth reference {P["target_head_girth_mm"]} mm, actual girth measured separately in validation; rear cap plane {list(cap_origin)} / {list(cap_normal)}')
shell=o.modifiers.new(f'{P["wall_mm"]} mm inward shell','SOLIDIFY');shell.thickness=P['wall_mm'];shell.offset=-1
shell.use_even_offset=False;shell.use_quality_normals=True
apply(o,shell)
log('Repairing shell volume using voxel union')
rem=o.modifiers.new('Printable shell repair','REMESH');rem.mode='VOXEL';rem.voxel_size=P['voxel_mm'];rem.use_smooth_shade=True;apply(o,rem)
sm=o.modifiers.new('Gentle surface finish','SMOOTH');sm.factor=.22;sm.iterations=2;apply(o,sm)
boolean(o,envelope,'INTERSECT',keep=True)
rem=o.modifiers.new('Closed clipped shell','REMESH');rem.mode='VOXEL';rem.voxel_size=P['voxel_mm'];rem.use_smooth_shade=True;apply(o,rem)
sm=o.modifiers.new('Final voxel surface fairing','SMOOTH');sm.factor=.45;sm.iterations=6;apply(o,sm)
dec=o.modifiers.new('Compact printable surface','DECIMATE');dec.ratio=.32;apply(o,dec)
log(f'Shell faces: {len(o.data.polygons)}')
eye_centers=[]
for loop in (l for l in loops if l['vertex_count']==31):
    rr=raw_mm[loop['vertex_ids']];cx=float((rr[:,0].min()+rr[:,0].max())/2);cz=float((rr[:,2].min()+rr[:,2].max())/2)
    r=P['eye_diameter_mm']/2+.20
    # Keep cutter behind the original visible eye rim, retaining >=0.8 mm there.
    radial=(rr[:,0]-cx)**2+(rr[:,2]-cz)**2
    cy=float(np.max(rr[:,1]+np.sqrt(np.maximum(r*r-radial,0)))+.80)
    eye_centers.append((cx,cy,cz))
    boolean(o,sphere('16 mm eye seat', (cx,cy,cz),r))
log('Making reinforced neck cup and hook slot')
neck_y=.24*scale
platform_top=.72*scale
neck_base=cylinder('Reinforced neck platform',(0,neck_y,platform_top-20.0),14.0,40.0)
boolean(neck_base,boss_envelope,'INTERSECT',keep=True)
boolean(o,neck_base,'UNION')
seat_r=P['neck_seat_diameter_mm']/2
seat_center_z=platform_top-3.2-seat_r
boolean(o,sphere('Neck ball seat - prototype',(0,neck_y,seat_center_z),seat_r))
# Clear the lower approach to the ball seat, and add a capsule hook opening.
boolean(o,cylinder('Neck entry',(0,neck_y,seat_center_z-20),seat_r,40.0))
w=P['neck_slot_width_mm'];lng=P['neck_slot_length_mm']
slot=cube('Hook slot center',(0,neck_y,platform_top+5),(w,lng-w,30))
for dy in (-(lng-w)/2,(lng-w)/2):boolean(slot,cylinder('Hook slot end',(0,neck_y+dy,platform_top+5),w/2,30),'UNION')
boolean(o,slot)
log('Separating rear cap in local cut-plane coordinates')
for obj in (o,master,envelope,boss_envelope):
    obj.data.transform(world_to_local);obj.data.update()
head=copy(o,'PRINT_01_Head_Shell');cap=copy(o,'PRINT_02_Removable_Cap');remove(o)
boolean(head,cube('Keep complete face and neck',(0,0,cut-100),(220,220,200)),'INTERSECT')
gap=P['cap_gap_mm'];boolean(cap,cube('Rear occipital cap',(0,0,cut+gap+100),(220,220,200)),'INTERSECT')
# Magnet bosses lie just inside the seam on left/right; preserve smooth outside.
segs=section_segments(master,cut)
pts=segs.reshape(-1,3); near=pts[np.abs(pts[:,1])<1.0]
halfwidth=float(np.max(np.abs(near[:,0])))
bossx=halfwidth-4.6;boss_radius=4.5
for x in (-bossx,bossx):
    for part,z in ((head,cut-3.0),(cap,cut+gap+3.0)):
        boss=cylinder('Internal magnet boss',(x,0,z),boss_radius,6.0)
        boolean(boss,boss_envelope,'INTERSECT',keep=True)
        boolean(part,boss,'UNION')
    depth=P['magnet_hole_depth_mm'];rad=P['magnet_hole_diameter_mm']/2
    boolean(head,cylinder('Magnet recess head',(x,0,cut-depth/2+.02),rad,depth+.04))
    boolean(cap,cylinder('Magnet recess cap',(x,0,cut+gap+depth/2-.02),rad,depth+.04))
upper=float(pts[np.abs(pts[:,0])<1.0,1].min())
pin_y=upper+7.5
# Fully internal pin-and-blind-hole registration. A notch in the curved scalp
# could pierce the external cap wall, so the receiver has its own inside pad.
for part,z,h in ((head,cut-2.0,4.0),(cap,cut+gap+3.0,6.0)):
    pad=cube('Internal upper rear alignment pad',(0,upper+4.5,z),(8.5,11.0,h))
    boolean(pad,boss_envelope,'INTERSECT',keep=True)
    boolean(part,pad,'UNION')
boolean(head,cylinder('Rear alignment pin',(0,pin_y,cut+1.0),2.0,4.0),'UNION')
boolean(cap,cylinder('Rear blind locating bore',(0,pin_y,cut+gap+1.85-.02),2.25,3.74))
remove(envelope)
remove(boss_envelope)
for obj in (head,cap,master):
    obj.data.transform(local_to_world);obj.data.update()
cleanup_counts={}
for part in (head,cap):
    bm=bmesh.new();bm.from_mesh(part.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.001)
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    seen=set();duplicates=[]
    for face in bm.faces:
        key=tuple(sorted(v.index for v in face.verts))
        if key in seen:duplicates.append(face)
        else:seen.add(key)
    if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
    todo=set(bm.faces);components=[]
    while todo:
        seed=todo.pop();component={seed};stack=[seed]
        while stack:
            for edge in stack.pop().edges:
                for face in edge.link_faces:
                    if face in todo:todo.remove(face);component.add(face);stack.append(face)
        components.append(component)
    components.sort(key=len,reverse=True)
    removed=sum(len(c) for c in components[1:])
    for comp in components[1:]:
        pp=np.array([v.co[:] for f in comp for v in f.verts])
        if float(np.linalg.norm(pp.max(0)-pp.min(0)))>.5:
            raise ValueError('Unexpected separate geometry: '+part.name)
        bmesh.ops.delete(bm,geom=list(comp),context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    cleanup_counts[part.name]={'duplicate_faces_removed':len(duplicates),'microscopic_fragment_faces_removed':removed}
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(part.data);bm.free()
for part in (head,cap):smooth(part)
skin=material('Warm ivory resin',(.67,.49,.41),.38)
for part in (head,cap):setmat(part,skin)
head['units']='mm';head['physical_fit']='UNTESTED DRAFT';head['target_body']='UFdoll 1/4 Lady (囡囡体); neck circumference reference 66 mm'
cap['magnets']='2 magnets each part; nominal 4x2 mm; confirm polarity before gluing'
stl(head,'march7-head-shell-v0.10-draft.stl');stl(cap,'march7-head-cap-v0.10-draft.stl')
for ob in (master,reference):ob.hide_set(True);ob.hide_render=True

report={'version':P['version'],'source_sha256':reference['source_sha256'],'source_face_triangles':len(ff),
        'source_to_mm_scale':scale,'units':'mm','historical_target_girth_mm':P['target_head_girth_mm'],'girth_measure_z_mm':zg*scale,
        'cap_plane_origin_mm':list(cap_origin),'cap_plane_normal':list(cap_normal),'cap_local_axes':{'u':list(u),'v':list(v_axis),'n':list(cap_normal)},'eye_centers_mm':eye_centers,'eye_nominal_diameter_mm':P['eye_diameter_mm'],
        'magnet_centers_mm':[list(local_to_world @ Vector((x,0,0))) for x in (-bossx,bossx)],'rear_pin_center_mm':list(local_to_world @ Vector((0,pin_y,0))),'neck_center_y_mm':neck_y,'neck_platform_top_mm':platform_top,
        'neck_seat_center_z_mm':seat_center_z,'parts':{},'cleanup':cleanup_counts,'physical_fit':'Not printed or physically fitted','unified_mother_surface':json.loads((ROOT/'mother-surface-report.json').read_text())}
for part in (head,cap):
    bm=bmesh.new();bm.from_mesh(part.data)
    report['parts'][part.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume(signed=True),'bounds_mm':list(part.dimensions)}
    bm.free()
(ROOT/'build-report.json').write_text(json.dumps(report,indent=2))
log(json.dumps(report['parts']))

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
cam.location=(115,-180,100);cam.rotation_euler=(Vector((0,0,37))-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=105
active(head)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=130
        area.spaces.active.region_3d.view_location=Vector((0,0,36))
        area.spaces.active.clip_end=10000
        area.spaces.active.shading.color_type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'march7-bjd-head-v0.10-draft.blend'),compress=True)
log('DONE')
