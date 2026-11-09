"""Source-constrained junction fairing on the validated v0.3 topology.
No v0.4 ellipsoid, no remeshing, no other doll face geometry.
"""
from pathlib import Path
import json,math,hashlib,shutil,heapq,sys
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text());S=P['junction_fairing']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'baseline-v0.3.blend'))
scene=bpy.context.scene
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
master=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing'];reference=bpy.data.objects['SOURCE_Original_March7_Face_DoNotPrint']
cap_normal=Vector(P['cap_plane_normal']).normalized()
def log(v):print(v,flush=True)
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def stl(o,name):
    active(o);bpy.ops.wm.stl_export(filepath=str(ROOT/name),export_selected_objects=True,apply_modifiers=True,global_scale=1.,use_scene_unit=False)
def ramp(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*t*(t*(t*6-15)+10)
archive=np.load(ROOT/'source-protection-masks.npz')
source={key:archive[key] for key in archive.files}
sv=source['vertices_mm'];sf=source['faces'];geod=source['outer_boundary_geodesic_mm']
src_tree=BVHTree.FromPolygons(sv.tolist(),sf.tolist(),all_triangles=True)
sk=KDTree(len(sv))
for i,co in enumerate(sv):sk.insert(Vector(co),i)
sk.balance()
# Dense sampling of the true source boundary, not the old circular ring target.
edge_counts={}
for f in sf:
    for a,b in zip(f,np.roll(f,-1)):
        key=tuple(sorted((int(a),int(b))));edge_counts[key]=edge_counts.get(key,0)+1
rim=[]
for (a,b),count in edge_counts.items():
    if count==1 and geod[a]<1e-5 and geod[b]<1e-5:
        for t in np.linspace(0,1,max(3,int(np.linalg.norm(sv[a]-sv[b])/.2))):rim.append(sv[a]*(1-t)+sv[b]*t)
rk=KDTree(len(rim))
for i,co in enumerate(rim):rk.insert(Vector(co),i)
rk.balance()
original=np.array([v.co[:] for v in master.data.vertices]);weights=np.zeros(len(original))
for i,co in enumerate(original):
    x,y,z=co
    if z<S['lower_fairing_start_z_mm']:continue
    sourcehit,normal,fi,dist=src_tree.find_nearest(Vector(co))
    nearest=sk.find(sourcehit)[1]
    sa,sb,sc=sv[sf[fi]];u=sb-sa;v=sc-sa;q=np.array(sourcehit)-sa
    aa=u@u;ab=u@v;bb=v@v;aq=u@q;bq=v@q;det=aa*bb-ab*ab
    if abs(det)<1e-14:gi=float(np.mean(geod[sf[fi]]))
    else:
        s=(bb*aq-ab*bq)/det;t=(aa*bq-ab*aq)/det
        bary=np.maximum([1-s-t,s,t],0);bary/=sum(bary)
        gi=float(bary@geod[sf[fi]])
    # Hard constraints have priority over smoothing, including the entire ear.
    if dist<2.0 and gi>=S['source_interior_lock_mm']:continue
    if dist<3.0 and any(source[k][nearest] for k in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')):continue
    if abs(x)>20 and 17<z<36 and dist<1.5:continue
    distance=rk.find(Vector(co))[2]
    edge_weight=1-ramp(2.0,S['outer_boundary_band_mm'],distance)
    src_weight=1-ramp(.5,S['source_interior_lock_mm'],gi)*(1-ramp(2.0,4.0,dist))
    cap_weight=ramp(5,12,29.5-(y+.3*z))
    weights[i]=edge_weight*src_weight*cap_weight*ramp(S['lower_fairing_start_z_mm'],S['lower_fairing_full_z_mm'],z)
# Diffuse weights along the surface graph, never through an ear fold.
adjacency=[set() for _ in original]
for edge in master.data.edges:
    a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
# Feather the free-side weights while keeping every protected vertex fixed.
# This prevents a sharp displacement step at the boundary of a protected face.
locked=weights==0
edgepairs=np.array([[i,j] for i,ns in enumerate(adjacency) for j in ns],dtype=int)
degrees=np.bincount(edgepairs[:,0],minlength=len(weights))
for _ in range(S['weight_feather_iterations']):
    totals=np.bincount(edgepairs[:,0],weights=weights[edgepairs[:,1]],minlength=len(weights))
    weights=.5*weights+.5*totals/np.maximum(degrees,1)
    weights[locked]=0
active_ids=np.flatnonzero(weights>1e-5)
log(f'Junction fairing: {len(active_ids)} / {len(original)} exterior vertices, protected interiors locked')
if '--export-fairing' in sys.argv:
    master.data.calc_loop_triangles()
    tris=np.array([t.vertices for t in master.data.loop_triangles])
    np.savez(ROOT/'fairing-problem.npz',vertices=original,triangles=tris,weights=weights)
    log('Fairing problem exported');raise SystemExit(0)

solution=np.load(ROOT/'fairing-solution.npz')
assert np.array_equal(solution['vertices_before'],original), 'Fairing solution baseline mismatch'
for vertex,co in zip(master.data.vertices,solution['vertices_after']):vertex.co=co
log('Constrained minimum-bending solution applied')
# Interpolate one exterior displacement field onto both outer and inner print walls.
# Freeze topology and use barycentric interpolation on the original exterior.
master.data.calc_loop_triangles();triangles=np.array([t.vertices for t in master.data.loop_triangles])
frozen_tree=BVHTree.FromPolygons(original.tolist(),triangles.tolist(),all_triangles=True)
field=np.array([v.co[:] for v in master.data.vertices])-original
head_before=np.array([v.co[:] for v in head.data.vertices]);count=0
protection=np.load(ROOT/'head-protection-weights.npz')
assert np.array_equal(protection['baseline_vertices_mm'],head_before), 'Print protection index mismatch'
print_feather=protection['feather_weight'];print_locked=protection['locked']
for vertex in head.data.vertices:
    co=vertex.co
    if co.z<S['lower_fairing_start_z_mm'] or 29.5-(co.y+.3*co.z)<5:continue
    loc,normal,idx,distance=frozen_tree.find_nearest(co)
    a,b,c=original[triangles[idx]];ab=b-a;ac=c-a;ap=np.array(loc)-a
    d00=ab@ab;d01=ab@ac;d11=ac@ac;d20=ap@ab;d21=ap@ac;den=d00*d11-d01*d01
    if abs(den)<1e-15:continue
    beta=(d11*d20-d01*d21)/den;gamma=(d00*d21-d01*d20)/den
    coeff=np.maximum([1-beta-gamma,beta,gamma],0);coeff/=sum(coeff)
    lower_gate=ramp(S['lower_fairing_start_z_mm'],S['lower_fairing_full_z_mm'],co.z)
    move=(coeff@field[triangles[idx]])*print_feather[vertex.index]*lower_gate
    if print_locked[vertex.index]:move*=0
    if np.linalg.norm(move)>1e-8:vertex.co+=Vector(move);count+=1
head.data.update();master.data.update()
for ob in (head,master):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for poly in ob.data.polygons:poly.use_smooth=True
report=json.loads((ROOT/'baseline-build-report.json').read_text());report['version']=P['version']
head_delta=np.linalg.norm(np.array([v.co[:] for v in head.data.vertices])-head_before,axis=1)
report['junction_fairing']={'method':'Source-constrained minimum-bending surface on v0.3; transferred to print walls with strict source ROI locks and a 2 mm feather; topology unchanged','settings':S,'master_vertices_moved':int(np.sum(np.linalg.norm(field,axis=1)>1e-7)),'master_max_displacement_mm':float(np.linalg.norm(field,axis=1).max()),'solver_report':json.loads((ROOT/'fairing-solver-report.json').read_text()),'head_strict_protection_max_displacement_mm':float(head_delta[protection['locked']].max()),'head_vertices_moved':count,'head_max_displacement_mm':float(head_delta.max()),'locked_master_vertices_max_displacement_mm':float(np.linalg.norm(field[weights==0],axis=1).max()),'head_below_z21_max_displacement_mm':float(head_delta[head_before[:,2]<21].max()),'baseline_blend_sha256':hashlib.sha256((ROOT/'baseline-v0.3.blend').read_bytes()).hexdigest()}
report['parts']={}
for part in (head,cap):
    bm=bmesh.new();bm.from_mesh(part.data);report['parts'][part.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume(signed=True),'bounds_mm':list(part.dimensions)};bm.free()
(ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
log(json.dumps(report['junction_fairing']))
stl(head,'march7-head-shell-v0.5-draft.stl');shutil.copy2(ROOT/'baseline-cap.stl',ROOT/'march7-head-cap-v0.5-draft.stl')
for ob in (master,reference):ob.hide_set(True);ob.hide_render=True
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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'march7-bjd-head-v0.5-draft.blend'),compress=True)
log('DONE')
