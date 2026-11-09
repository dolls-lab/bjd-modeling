"""Read-only actual Blend v12->v13 surface-only preservation and STL export audit."""
from pathlib import Path
import json,hashlib,argparse,sys
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;OLD=P.parent/'march7-bjd-1-4-v0.12'
ap=argparse.ArgumentParser();ap.add_argument('--solution',required=True);ap.add_argument('--expected-head-sha256',required=True);ap.add_argument('--expected-cap-sha256',required=True);ap.add_argument('--provenance');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
files={'baseline_blend':OLD/'march7-bjd-head-v0.12-draft.blend','current_blend':P/'march7-bjd-head-v0.13-draft.blend','baseline_head':OLD/'march7-head-shell-v0.12-draft.stl','baseline_cap':OLD/'march7-head-cap-v0.12-draft.stl','current_head':P/'march7-head-shell-v0.13-draft.stl','current_cap':P/'march7-head-cap-v0.13-draft.stl','solution':Path(args.solution),'baseline_mother':OLD/'mother-surface.npz'}
if args.provenance:files['provenance']=Path(args.provenance)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={k:sha(p) for k,p in files.items()};assert hashes['current_head']==args.expected_head_sha256 and hashes['current_cap']==args.expected_cap_sha256
sol=np.load(files['solution']);mom=np.load(files['baseline_mother']);headname='PRINT_01_Head_Shell';capname='PRINT_02_Removable_Cap'
def snapshot(p):
 bpy.ops.wm.open_mainfile(filepath=str(p));out={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();nm=o.matrix_world.to_3x3().inverted().transposed();n=np.array([nm@q.normal for q in o.data.vertices]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
  out[o.name]={'v':np.array([o.matrix_world@q.co for q in o.data.vertices]),'n':n,'f':np.array([q.vertices[:] for q in o.data.loop_triangles],np.int32)}
 return out
b=snapshot(files['baseline_blend']);c=snapshot(files['current_blend']);bv=b[headname]['v'];cv=c[headname]['v'];bf=b[headname]['f'];cf=c[headname]['f']
checks={'same_mesh_object_names':set(b)==set(c),'head_topology_exactly_unchanged':np.array_equal(bf,cf),'cap_STL_bytes_exactly_unchanged':hashes['baseline_cap']==hashes['current_cap'],'solution_before_matches_actual_v12':np.array_equal(sol['before'],bv),'solution_triangles_match_actual_v12':np.array_equal(sol['triangles'],bf)}
assert checks['head_topology_exactly_unchanged'],'This audit expects the announced same-topology surface edit; do not silently compare unrelated indices.'
delta=cv-bv;length=np.linalg.norm(delta,axis=1);changed=length>0;support=sol['outer_skin_support'].astype(bool)
checks['outside_authorized_outer_skin_support_exactly_unchanged']=bool(np.count_nonzero(delta[~support])==0)
checks['solution_after_matches_saved_Blend_within_float32_roundoff']=float(np.linalg.norm(cv-sol['after'],axis=1).max())<=2e-5
maskstats={}
for key in ['locked','inner_wall_locked','major_features_locked','mechanical_locked','eye_guard_locked','eye_guard','ear_locked']:
 if key not in sol.files:continue
 mask=sol[key].astype(bool);maskstats[key]={'vertices':int(mask.sum()),'changed_vertices':int(changed[mask].sum()),'maximum_displacement_mm':float(length[mask].max()) if mask.any() else 0.};checks[key+'_actual_exactly_unchanged']=bool(np.count_nonzero(delta[mask])==0)
for required in ['locked','inner_wall_locked','major_features_locked']:checks[required+'_mask_supplied']=required in sol.files
other={}
for name in sorted(set(b)&set(c)-{headname}):
 samef=np.array_equal(b[name]['f'],c[name]['f']);samev=np.array_equal(b[name]['v'],c[name]['v']);other[name]={'topology_exact':samef,'world_coordinates_exact':samev};checks['other_mesh_'+name+'_unchanged']=samef and samev
# Independent exterior check: changed positions must remain close to the visible
# mother surface with compatible normals, excluding the deep inner wall.
mt=BVHTree.FromPolygons(mom['after'].tolist(),mom['triangles'].tolist(),all_triangles=True);distance=[];normaldot=[]
for i in np.flatnonzero(changed):
 q,n,face,d=mt.find_nearest(Vector(bv[i]));distance.append(float(d));normaldot.append(float(np.dot(n,b[headname]['n'][i])))
checks['all_changed_vertices_on_mother_exterior_within0p65mm']=bool(distance and max(distance)<=.6501 and min(normaldot)>=.25)
def sorted_tri(t):
 r=t[np.arange(len(t))[:,None],(np.argmin(t,axis=1)[:,None]+np.arange(3))%3];return r[np.lexsort((r[:,2],r[:,1],r[:,0]))]
def stl_equal(path,obj):
 data=path.read_bytes();n=int.from_bytes(data[80:84],'little');assert len(data)==84+n*50
 dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);q=np.frombuffer(data,dtype=dt,offset=84,count=n)['vertices'].reshape(-1,3);sv,si=np.unique(q,axis=0,return_inverse=True);vv,vi=np.unique(obj['v'].astype(np.float32),axis=0,return_inverse=True);positions=np.array_equal(sv,vv);tri=positions and np.array_equal(sorted_tri(si.reshape(-1,3)),sorted_tri(vi[obj['f']]));return {'stl_triangles':n,'blend_triangles':len(obj['f']),'unique_float32_positions_equal':positions,'oriented_triangles_equal':tri,'pass':positions and tri}
exports={}
for part,name in [('head',headname),('cap',capname)]:
 exports[part]={}
 for version,objects in [('baseline',b),('current',c)]:
  rr=stl_equal(files[version+'_'+part],objects[name]);exports[part][version]=rr;checks[version+'_'+part+'_STL_matches_Blend']=rr['pass']
checks['inputs_unchanged_during_audit']=all(sha(p)==hashes[k] for k,p in files.items())
r={'baseline_version':'v0.12','current_version':'v0.13','files':{k:{'path':str(p),'sha256':hashes[k]} for k,p in files.items()},'checks':checks,'all_integrity_checks_pass':all(checks.values()),'head_actual_changed_vertices':int(changed.sum()),'head_actual_maximum_displacement_mm':float(length.max()),'changed_support_bounds_mm':[bv[changed].min(0).tolist(),bv[changed].max(0).tolist()] if changed.any() else None,'protected_actual_regions':maskstats,'all_other_meshes':other,'independent_changed_exterior_check':{'samples':len(distance),'max_mother_surface_distance_mm':max(distance) if distance else None,'minimum_normal_dot':min(normaldot) if normaldot else None},'stl_correspondence':exports,'scope':'Same-topology actual PRINT skin microfinish only. Outside support, inner wall, major features and all other mesh objects compared exactly in saved world coordinates. Mother proximity independently checks changed vertices are outer skin. Mechanical cap remains byte-identical. Eye projection, outside silhouette and local intersection/thickness are separate reports.','limitations':'Support labels originate from the documented solver masks; mother distance/normal validates outer skin independently but does not replace anatomical review. No physical print or material test.'}
(P/'surface-only-review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':r['all_integrity_checks_pass'],'failed':[k for k,v in checks.items() if not v],'changed':int(changed.sum()),'max_displacement_mm':float(length.max()),'exports':exports},indent=2),flush=True)
