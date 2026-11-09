"""Retract the added side skull behind each ear; preserve source sculpt by mesh provenance."""
from pathlib import Path
import json,hashlib,shutil
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text());S=P['postauricular_retraction']
BASE=ROOT/'baseline-v0.5.blend'
archive=np.load(ROOT/'v6-side-protection.npz');protect={k:archive[k] for k in archive.files}
visible_archive=np.load(ROOT/'head-visible-source-protection.npz')
visible={k:visible_archive[k] for k in visible_archive.files}
protect['head_locked']=visible['head_locked']
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==str(protect['baseline_blend_sha256'])
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.context.scene
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
master=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing'];reference=bpy.data.objects['SOURCE_Original_March7_Face_DoNotPrint']
cap_normal=Vector(P['cap_plane_normal']).normalized()
report=json.loads((ROOT/'baseline-build-report.json').read_text());report['version']=P['version']
report['baseline_processing_records']={key:report.pop(key) for key in ('face_fairing','junction_fairing') if key in report}
report['historical_target_girth_mm']=report.pop('girth_mm',190.0)
field=np.load(ROOT/'side-retraction-field.npz');ys=field['y'];zs=field['z'];ratios=field['ratio']
def log(v):print(v,flush=True)
def ramp(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t**3*(t*(t*6-15)+10)
def lookup(points):
    yi=np.clip((points[:,1]-ys[0])/(ys[1]-ys[0]),0,len(ys)-1-1e-8)
    zi=np.clip((points[:,2]-zs[0])/(zs[1]-zs[0]),0,len(zs)-1-1e-8)
    j=np.floor(yi).astype(int);i=np.floor(zi).astype(int);ty=yi-j;tz=zi-i
    result=(1-tz)*((1-ty)*ratios[i,j]+ty*ratios[i,j+1])+tz*((1-ty)*ratios[i+1,j]+ty*ratios[i+1,j+1])
    result[(points[:,1]<ys[0])|(points[:,1]>ys[-1])|(points[:,2]<zs[0])|(points[:,2]>zs[-1])]=0
    return result
def mechanical_gate(points):
    x,y,z=points.T
    radius=np.sqrt(x*x+(y-report['neck_center_y_mm'])**2)
    neck_gate=1-(1-ramp(report['neck_platform_top_mm'],25,z))*(1-ramp(15,18,radius))
    gate=neck_gate.copy()
    for center in report['magnet_centers_mm']:
        distance=np.linalg.norm(points-np.asarray(center),axis=1)
        gate*=ramp(7,12,distance)
    return gate
summary={}
for key,ob in [('master',master),('head',head)]:
    before=np.array([v.co[:] for v in ob.data.vertices])
    assert np.array_equal(before,protect[key+'_baseline_vertices']),key+' baseline mismatch'
    locked=protect[key+'_locked']
    # The scalar reduction is based on this actual outer point, never on an
    # ear's larger silhouette at the same Y/Z. It naturally vanishes where the
    # added surface already lies within the source-side envelope.
    distance=protect[key+'_distance_to_source_locked_mm_capped_at_5']
    weight=ramp(0,S['source_protection_feather_mm'],distance)
    if key=='master':
        x,y,z=before.T
        ceiling=np.interp(z,zs,field['target_x'])
        excess=np.abs(x)-ceiling;h=S['smooth_ceiling_width_mm'];q=np.clip((excess+h)/(2*h),0,1)
        # Integral of smootherstep: the resulting smooth-min has derivative
        # in [0,1], avoiding a reverse lip at the boundary of the flatter side.
        reduction=np.where(excess<=-h,0,np.where(excess>=h,excess,2*h*(q**6-3*q**5+2.5*q**4)))
        gate=ramp(S['y_front_start_mm'],S['y_front_full_mm'],y)*ramp(S['z_low_start_mm'],S['z_low_full_mm'],z)*(1-ramp(S['z_high_full_mm'],S['z_high_end_mm'],z))
        gate*=ramp(S['cap_margin_start_mm'],S['cap_margin_full_mm'],29.5-y-.3*z)
        movement=-np.sign(x)*reduction*gate*weight*mechanical_gate(before)*S['retraction_fraction']
    else:
        # A shared YZ displacement field for both skin and cavity walls:
        # nearest-surface projection can jump to a different height at ear roots.
        old_tree=BVHTree.FromPolygons(master_before.tolist(),added_triangles.tolist(),all_triangles=True)
        new_tree=BVHTree.FromPolygons(master_after.tolist(),added_triangles.tolist(),all_triangles=True)
        dy=np.arange(-10,26.001,.25);dz=np.arange(4,56.001,.25)
        grids=[]
        for sign in [-1,1]:
            grid=np.zeros((len(dz),len(dy)))
            for iz,zz in enumerate(dz):
                for iy,yy in enumerate(dy):
                    a=old_tree.ray_cast(Vector((sign*60,yy,zz)),Vector((-sign,0,0)),60)[0]
                    b=new_tree.ray_cast(Vector((sign*60,yy,zz)),Vector((-sign,0,0)),60)[0]
                    if a is not None and b is not None:grid[iz,iy]=b.x-a.x
            grids.append(grid)
        np.savez_compressed(ROOT/'shared-wall-displacement-field.npz',y=dy,z=dz,negative_side=grids[0],positive_side=grids[1])
        jv=np.clip((before[:,1]-dy[0])/.25,0,len(dy)-1-1e-8);iv=np.clip((before[:,2]-dz[0])/.25,0,len(dz)-1-1e-8)
        j=np.floor(jv).astype(int);i=np.floor(iv).astype(int);u=jv-j;t=iv-i
        movement=np.zeros(len(before))
        for sign,grid in zip([-1,1],grids):
            val=(1-t)*((1-u)*grid[i,j]+u*grid[i,j+1])+t*((1-u)*grid[i+1,j]+u*grid[i+1,j+1])
            mask=before[:,0]*sign>0;movement[mask]=val[mask]
        movement[(before[:,1]<dy[0])|(before[:,1]>dy[-1])|(before[:,2]<dz[0])|(before[:,2]>dz[-1])]=0
        movement*=mechanical_gate(before)
        movement*=ramp(S['cap_margin_start_mm'],S['cap_margin_full_mm'],29.5-before[:,1]-.3*before[:,2])
    movement[locked]=0
    after=before.copy();after[:,0]+=movement
    if key=='master' and (ROOT/'upper-junction-solution.npz').is_file():
        solution=np.load(ROOT/'upper-junction-solution.npz')
        expected=after.astype(np.float32).astype(np.float64)
        assert np.array_equal(solution['vertices_before'],expected),'Upper-junction solution input mismatch'
        after=solution['vertices_after']
    for v,co in zip(ob.data.vertices,after):v.co=co
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for poly in ob.data.polygons:poly.use_smooth=True
    ob.data.update()
    actual=np.array([v.co[:] for v in ob.data.vertices]);delta=np.linalg.norm(actual-before,axis=1)
    if key=='master':
        master_before=before;master_after=actual
        added_triangles=protect['master_baseline_triangles'][protect['master_triangle_source_class']==3]
    assert delta[locked].max()==0
    neck=(np.linalg.norm(before[:,:2]-np.array([0,report['neck_center_y_mm']]),axis=1)<=15)&(before[:,2]<=report['neck_platform_top_mm'])
    magnets=np.logical_or.reduce([np.linalg.norm(before-np.array(c),axis=1)<=7 for c in report['magnet_centers_mm']])
    summary[key]={'moved_vertices':int(np.sum(delta>1e-6)),'max_displacement_mm':float(delta.max()),
                  'source_protected_max_displacement_mm':float(delta[locked].max()),
                  'neck_mechanical_max_displacement_mm':float(delta[neck].max()),
                  'magnet_mechanical_max_displacement_mm':float(delta[magnets].max()),
                  'topology_preserved':True}
    np.savez_compressed(ROOT/(key+'-deformation.npz'),before=before,after=actual,displacement_mm=delta,locked=locked)
bpy.context.view_layer.update()
report['side_skull_retraction']={'method':'Retract only added side skull toward the raw source anterior-side-face envelope; original face, ears and closure retained by verified topology provenance.',
 'settings':S,'field_report':json.loads((ROOT/'side-field-report.json').read_text()),'objects':summary,
 'baseline_blend_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'cap_unchanged':True}
if (ROOT/'upper-junction-report.json').is_file():
    report['side_skull_retraction']['upper_junction_relaxation']=json.loads((ROOT/'upper-junction-report.json').read_text())
report['parts']={}
for ob in (head,cap):
    bm=bmesh.new();bm.from_mesh(ob.data)
    report['parts'][ob.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume(signed=True),'bounds_mm':list(ob.dimensions)};bm.free()
(ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n');log(json.dumps(summary))
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
active(head)
bpy.ops.wm.stl_export(filepath=str(ROOT/'march7-head-shell-v0.6-draft.stl'),export_selected_objects=True,apply_modifiers=True,global_scale=1.,use_scene_unit=False)
shutil.copy2(ROOT/'baseline-cap.stl',ROOT/'march7-head-cap-v0.6-draft.stl')
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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'march7-bjd-head-v0.6-draft.blend'),compress=True)
log('DONE')
