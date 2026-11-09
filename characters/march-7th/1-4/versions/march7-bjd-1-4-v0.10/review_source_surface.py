"""Read-only v9 -> v10 low-face/ear preservation and Blend/STL comparison.

Run: Blender -b -t 4 --python review_source_surface.py
The rebuilt PRINT meshes are never assumed to share indices.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;OLD=R.parent/'march7-bjd-1-4-v0.9'
FILES={'baseline_blend':R/'baseline-v0.9.blend','current_blend':R/'march7-bjd-head-v0.10-draft.blend',
 'baseline_mother':OLD/'mother-surface.npz','current_mother':R/'mother-surface.npz',
 'core_masks':R/'central-source-protection.npz',
 'baseline_head_stl':OLD/'march7-head-shell-v0.9-draft.stl','baseline_cap_stl':OLD/'march7-head-cap-v0.9-draft.stl',
 'current_head_stl':R/'march7-head-shell-v0.10-draft.stl','current_cap_stl':R/'march7-head-cap-v0.10-draft.stl'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={k:sha(p) for k,p in FILES.items()}
def read(p):
 with np.load(p) as d:return {k:d[k] for k in d.files}
mb=read(FILES['baseline_mother']);mc=read(FILES['current_mother']);masks=read(FILES['core_masks'])
checks={'baseline_is_final_v9':hashes['baseline_blend']=='554e10d8123171fac695229f22b8df7206eb26ae5f3b22a70c793bf421b42db3',
 'mother_topology_same':np.array_equal(mb['triangles'],mc['triangles']),
 'current_npz_before_is_actual_v9':np.array_equal(mc['before'],mb['after'])}
if not all(checks.values()):raise ValueError(checks)
v0=mb['after'];v1=mc['after'];md=np.linalg.norm(v1-v0,axis=1)
mother_regions={'central_core':mb['core_locked'],'ear_body':mb['ear_body_locked'],
 'all_original_ear_including_root':masks['master_source_ear_incident'],'all_z_le_40':v0[:,2]<=40}
for n,m in mother_regions.items():checks['mother_'+n+'_exact_zero']=bool(np.count_nonzero(md[m])==0)
t=np.clip((v0[:,2]-40)/(v0[:,2].max()-40),0,1);expected=v0.copy();expected[:,2]-=3*t**3*(10-15*t+6*t*t)
checks['mother_matches_requested_C2_formula']=bool(np.max(np.abs(v1-expected))<1e-12)
checks['mother_XY_unchanged']=np.array_equal(v0[:,:2],v1[:,:2])

NAMES={'head':'PRINT_01_Head_Shell','cap':'PRINT_02_Removable_Cap','master':'EDITABLE_Outer_Surface_Before_Hollowing'}
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for key,name in NAMES.items():
  o=bpy.data.objects[name];me=o.data;me.calc_loop_triangles();nm=o.matrix_world.to_3x3().inverted().transposed()
  nn=np.array([nm@p.normal for p in me.vertices]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-15)
  out[key]={'v':np.array([o.matrix_world@p.co for p in me.vertices]),'n':nn,
            'f':np.array([p.vertices[:] for p in me.loop_triangles],np.int32)}
 return out
b=snapshot(FILES['baseline_blend']);c=snapshot(FILES['current_blend'])
def stats(values):
 a=np.asarray(values,float)
 return {'count':len(a),'mean_mm':float(a.mean()),'median_mm':float(np.median(a)),
  'p95_mm':float(np.percentile(a,95)),'max_mm':float(a.max())} if len(a) else {'count':0}
def bvh(v,f):return BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
def bary(p,tri):
 a,b,c=tri;ab=b-a;ac=c-a;ap=p-a;aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=ap@ab;qc=ap@ac;den=aa*cc-bb*bb
 if abs(den)<1e-18:return np.array([1.,0.,0.])
 beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den;w=np.maximum([1-beta-gamma,beta,gamma],0);return w/w.sum()
mother_tree=bvh(v0,mb['triangles']);target_tree=bvh(c['head']['v'],c['head']['f'])
labels={'central_face':mb['core_locked'],'original_ear':masks['master_source_ear_incident']}
for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi'):
 labels[name]=masks['master_raw_feature_'+name]
results={name:[] for name in ['low_exterior_z_le_39',*labels]};worst={name:[] for name in results};normal_bad={name:0 for name in results}
rejected=0
for i in np.flatnonzero(b['head']['v'][:,2]<=39):
 p=b['head']['v'][i];n=b['head']['n'][i]
 q,mn,mi,dd=mother_tree.find_nearest(Vector(p))
 if mi is None or dd>.65 or float(np.dot(mn,n))<.25:rejected+=1;continue
 jj=mb['triangles'][mi];w=bary(np.array(q),v0[jj]);members=['low_exterior_z_le_39']
 members += [name for name,mask in labels.items() if float(w@mask[jj])>=.5]
 q,tn,ti,dd=target_tree.find_nearest(Vector(p))
 if ti is None:raise RuntimeError('No current head surface match')
 for name in members:
  results[name].append(float(dd));normal_bad[name]+=int(float(np.dot(tn,n))<.25)
  worst[name].append((float(dd),int(i),p.tolist(),list(q)))
surface={name:{'nearest_surface_distance':stats(vals),'nearest_normal_dot_below_0p25':normal_bad[name],
 'worst_samples':[{'distance_mm':d,'v9_vertex_id':i,'v9_point_mm':p,'v10_point_mm':q} for d,i,p,q in sorted(worst[name],reverse=True)[:3]]} for name,vals in results.items()}
checks['every_surface_region_has_samples']=all(bool(v) for v in results.values())

def oriented_sorted(tri):
 r=tri[np.arange(len(tri))[:,None],(np.argmin(tri,axis=1)[:,None]+np.arange(3))%3]
 return r[np.lexsort((r[:,2],r[:,1],r[:,0]))]
def verify_stl(path,obj):
 data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
 if len(data)!=84+50*count:raise ValueError('Not binary STL '+str(path))
 dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
 corners=np.frombuffer(data,offset=84,dtype=dt,count=count)['vertices'].reshape(-1,3)
 sv,si=np.unique(corners,axis=0,return_inverse=True)
 bv,bi=np.unique(obj['v'].astype(np.float32),axis=0,return_inverse=True)
 position_equal=np.array_equal(sv,bv)
 triangle_equal=position_equal and np.array_equal(oriented_sorted(si.reshape(-1,3)),oriented_sorted(bi[obj['f']]))
 return {'stl_triangles':count,'blend_triangles':len(obj['f']),'unique_float32_positions_equal':bool(position_equal),
   'oriented_triangle_multisets_equal':bool(triangle_equal),'verified':bool(position_equal and triangle_equal)}
exports={}
for part in ('head','cap'):
 exports[part]={}
 for version,prefix,objects in [('v9','baseline',b),('v10','current',c)]:
  rr=verify_stl(FILES[prefix+'_'+part+'_stl'],objects[part]);exports[part][version]=rr
  checks[part+'_'+version+'_stl_matches_blend']=rr['verified']
actual_master={}
same_master_topology=np.array_equal(b['master']['f'],c['master']['f']) and len(b['master']['v'])==len(c['master']['v'])
checks['actual_master_triangle_indices_same']=bool(same_master_topology)
if same_master_topology:
 ad=np.linalg.norm(c['master']['v']-b['master']['v'],axis=1)
 actual_master={name:stats(ad[mask]) for name,mask in mother_regions.items()}
 # Saved Blender float32 positions may differ by transform roundoff; NPZ
 # corresponding coordinates above are the exact mathematical-lock test.
 for name,rr in actual_master.items():checks['actual_master_'+name+'_within_0p00002mm']=rr['max_mm']<=.00002
report={'baseline_version':'v0.9','current_version':'v0.10','units':'mm',
 'files':{k:{'path':str(p),'sha256':hashes[k]} for k,p in FILES.items()},
 'mother_corresponding_displacement':{name:stats(md[m]) for name,m in mother_regions.items()},
 'mother_crown_z_mm':{'v9':float(v0[:,2].max()),'v10':float(v1[:,2].max())},
 'actual_blend_master_corresponding_displacement':actual_master,
 'v9_low_exterior_to_v10_print':surface,'baseline_non_exterior_candidates_rejected':rejected,
 'stl_correspondence':exports,'checks':checks,'all_integrity_checks_pass':all(checks.values()),
 'methods':{
  'mother':'Actual v9 mother after array versus current after, same triangle topology; exact core/ear/Z<=40 checks and independent requested quintic-formula evaluation.',
  'print_samples':'Use actual v9 PRINT vertex coordinates Z<=39 and its own v9 mother BVH. Visible outer samples require <=0.65mm to that mother and normal dot>=0.25. Regions come from barycentric membership on the mother. No v8 print indices/masks and no v9-to-v10 PRINT index assumption.',
  'distance':'Forward nearest-surface distances for all selected v9 exterior vertices. Normal disagreements are separate diagnostics. Max is a sampled surface distance, not a certified continuous Hausdorff bound. No exact-zero claim is imposed on remeshed prints.',
  'exports':'Each head/cap STL independently matches the corresponding actual Blender world float32 coordinates and oriented triangle multiset; cyclic triangle corner order is normalized, winding retained.'},
 'scope':'Central face/ear preservation measurements and export identity. Shell integrity, cap clearance, eye projection and physical fit are independently checked.'}
report['input_files_unchanged_during_audit']=all(sha(p)==hashes[k] for k,p in FILES.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit')
out=R/'source-surface-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'all_integrity_checks_pass':report['all_integrity_checks_pass'],
 'failed_checks':[k for k,v in checks.items() if not v],
 'surface_summary':{k:v['nearest_surface_distance'] for k,v in surface.items()},
 'head_stl_sha256':hashes['current_head_stl'],'blend_sha256':hashes['current_blend']},indent=2),flush=True)
