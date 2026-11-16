"""Save both new print parts while preserving actual hidden source hardware meshes."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/private/tmp/bjd-hook-groove-deps')
import bpy,bmesh,numpy as np,trimesh
from mathutils import Vector,Matrix
D=Path(sys.argv[sys.argv.index('--')+1]).resolve();p=json.loads((D/'parameters.json').read_text());CHAR=D.parents[2];src=CHAR/p['source_directory']
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
for k,f in p['source_files'].items():assert sha(src/f)==p['source_sha256'][k]
bpy.ops.wm.open_mainfile(filepath=str(src/p['source_files']['blend']))
s=p['source_uniform_scale'];n=np.array(p['magnet_axis']);offset=p['cap_plane_intercept_mm']/np.linalg.norm(p['cap_plane_normal']);gap=p['cap_gap_mm'];oldn=np.array([0,1,.3]);oldn/=np.linalg.norm(oldn);oldo=np.array([0,14.5,50])*s
reports={}
for tag,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
 obj=bpy.data.objects[name];assert obj.matrix_world==Matrix.Identity(4)
 mats=list(obj.data.materials);a=np.load(D/(tag+'-stage.npz'))
 data=bpy.data.meshes.new(name+'_large_rear_split');data.from_pydata(a['vertices'].tolist(),[],a['faces'].tolist());data.update();obj.data=data
 for m in mats:data.materials.append(m)
 bm=bmesh.new();bm.from_mesh(data);before=[len(bm.verts),len(bm.faces)]
 def local(v):
  co=np.array(v.co);new=abs(float(np.dot(co,n))-offset)<5*s;old=abs(float(np.dot(co-oldo,oldn)))<7*s
  return bool((new or old) and co[2]>27*s)
 bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if local(v)],dist=0.)
 for _ in range(4):
  bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
  bmesh.ops.dissolve_degenerate(bm,edges=[e for e in bm.edges if all(local(v) for v in e.verts)],dist=1e-6)
  bad=[f for f in bm.faces if (f.calc_area()<1e-9 or any(e.calc_length()<1e-5 for e in f.edges)) and all(local(v) for v in f.verts)]
  if bad:bmesh.ops.remove_doubles(bm,verts=list({v for f in bad for v in f.verts}),dist=1e-5)
 bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
 coords=np.asarray([v.co[:] for v in data.vertices]);seam=offset+(gap if tag=='cap' else 0)
 for f in data.polygons:
  c=coords[list(f.vertices)]
  f.use_smooth=not (np.max(np.abs(np.einsum('ij,j->i',c,n)-seam))<1e-5 or np.ptp(c[:,2])<1e-6)
 obj['partition_version']=p['version'];obj['magnet_configuration']=f"2 blind pockets per part: diameter {p['magnet_hole_diameter_mm']}mm depth {p['magnet_hole_depth_mm']}mm"
 obj['part_description']='Face, ears and neck bearing' if tag=='head' else 'Complete crown and occipital cap'
 obj.hide_render=False;obj.hide_set(False)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.wm.stl_export(filepath=str(D/p['output_files'][tag]),export_selected_objects=True,apply_modifiers=False,global_scale=1.,use_scene_unit=False)
 tm=trimesh.load_mesh(D/p['output_files'][tag],process=True,validate=False)
 labels=trimesh.graph.connected_component_labels(tm.face_adjacency,node_count=len(tm.faces))
 reports[tag]={'sha256':sha(D/p['output_files'][tag]),'watertight':bool(tm.is_watertight),'winding_consistent':bool(tm.is_winding_consistent),'components':len(np.unique(labels)),'min_triangle_area_mm2':float(tm.area_faces.min()),'before_cleanup':before,'after_cleanup':[len(data.vertices),len(data.polygons)]}
 assert tm.is_watertight and tm.is_winding_consistent and len(np.unique(labels))==1 and tm.area_faces.min()>0,reports[tag]
scene=bpy.context.scene;scene['model_version']=p['version'];scene['notes']='Large crown+rear cap. Head shape and facial sculpt retained, former seam reconstructed locally, magnets relocated. Existing neck passage/seat/reference hook retained.'
# Present closed model at useful whole-head scale when opened interactively.
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.clip_end=10000;sp.clip_start=.01
   sp.region_3d.view_location=(0,0,35*s);sp.region_3d.view_distance=125*s
   sp.region_3d.view_rotation=(Vector((0,0,35*s))-Vector((100*s,-180*s,70*s))).to_track_quat('-Z','Y')
bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=bpy.data.objects['PRINT_01_Head_Shell']
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(D/p['output_files']['blend']),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(D/p['output_files']['blend']))
for tag,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
 obj=bpy.data.objects[name];tm=trimesh.load_mesh(D/p['output_files'][tag],process=True,validate=False)
 v=np.array([x.co[:] for x in obj.data.vertices]);f=np.array([list(x.vertices) for x in obj.data.polygons])
 def digest(t):
  t=np.array(t,dtype=np.float32);t[t==0]=0;rows=np.sort(t.view('V12').reshape(-1,3),axis=1).reshape(-1).view('V36');return hashlib.sha256(np.sort(rows).tobytes()).hexdigest()
 assert digest(v[f])==digest(tm.triangles)
 reports[tag]['saved_blend_stl_triangles_equal']=True
for k,f in p['source_files'].items():assert sha(src/f)==p['source_sha256'][k]
(D/'build-report.json').write_text(json.dumps({'version':p['version'],'parts':reports,'source_unchanged':True,'saved_reopened':True,'blend_sha256':sha(D/p['output_files']['blend']),'physical_fit':'Prototype only; no physical fit/load test.'},indent=2)+'\n')
print('FINALIZED',p['version'],flush=True)
