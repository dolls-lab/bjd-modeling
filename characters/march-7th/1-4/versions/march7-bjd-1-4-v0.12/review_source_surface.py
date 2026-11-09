"""Read-only v11 -> v12 feature protection, permitted ear finish, and export identity.
Run in Blender --background --python SCRIPT -- --expected-head-sha256 HASH --expected-cap-sha256 HASH.
PRINT topology can change; only the mother has corresponding vertex indices.
"""
from pathlib import Path
import hashlib,json,argparse,sys
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;OLD=R.parent/'march7-bjd-1-4-v0.11'
ap=argparse.ArgumentParser();ap.add_argument('--expected-head-sha256',required=True);ap.add_argument('--expected-cap-sha256',required=True);ap.add_argument('--ear-report');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
FILES={'baseline_blend':R/'baseline-v0.11.blend','current_blend':R/'march7-bjd-head-v0.12-draft.blend',
 'baseline_mother':OLD/'mother-surface.npz','current_mother':R/'mother-surface.npz',
 'reference_v10_mother':R.parent/'march7-bjd-1-4-v0.10/mother-surface.npz',
 'source_feature_reference':R/'source-feature-reference.npz','actual_eye_geodesic':R/'actual-eye-geodesic.npz',
 'baseline_head_stl':OLD/'march7-head-shell-v0.11-draft.stl','baseline_cap_stl':OLD/'march7-head-cap-v0.11-draft.stl',
 'current_head_stl':R/'march7-head-shell-v0.12-draft.stl','current_cap_stl':R/'march7-head-cap-v0.12-draft.stl'}
if args.ear_report:FILES['ear_finish_report']=Path(args.ear_report)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={k:sha(p) for k,p in FILES.items()}
assert hashes['current_head_stl']==args.expected_head_sha256 and hashes['current_cap_stl']==args.expected_cap_sha256,'Final STL SHA mismatch'
def read(p):
 with np.load(p) as d:return {k:d[k] for k in d.files}
mb=read(FILES['baseline_mother']);mc=read(FILES['current_mother']);masks=read(FILES['source_feature_reference']);eg=read(FILES['actual_eye_geodesic']);ref=read(FILES['reference_v10_mother'])['after']
v0=mb['after'];v1=mc['after'];md=np.linalg.norm(v1-v0,axis=1);eye_d=eg['eye_edge_geodesic_mm'];eye_boundary=np.zeros(len(v0),bool);eye_boundary[eg['eye_boundary_vertices']]=True
# Independently reconstruct the solver's revised protection, instead of trusting
# the obsolete whole-eye2mm or whole-source mask from v11.
x,y,z=ref.T;core=masks['master_core_locked'].copy();core[(z>32.5)&(y<-13)&(eye_d>.8)]=False
FEATURES=('mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
for name in FEATURES:core|=masks['master_raw_feature_'+name]
core|=eye_d<=.8;core|=(abs(x)<6)&(z<=32.5)&(y<-15)
released=masks['master_core_locked']&~core;ears=masks['master_ear_locked'];guard=eye_d<=.8
checks={'baseline_is_final_v11':hashes['baseline_blend']=='41422bbb781f7b3b6e0d7accc24892effdd5e1a75657f8bf1f46c9320de9df65',
 'mother_topology_same':np.array_equal(mb['triangles'],mc['triangles']),
 'current_npz_before_is_actual_v11':np.array_equal(mc['before'],v0),
 'solver_reference_is_actual_v10':np.array_equal(mc['reference_v10'],ref),
 'actual_eye_geodesic_topology_matches':np.array_equal(eg['triangles'],mb['triangles']),
 'current_core_matches_independently_reconstructed_18846':np.array_equal(core,mc['core_locked']) and int(core.sum())==18846,
 'true_eye_boundary_248_matches':np.array_equal(eg['eye_boundary_vertices'],mc['eye_boundary_vertices']) and int(eye_boundary.sum())==248,
 'true_eye_guard_1368_matches':np.array_equal(guard,mc['eye_guard']) and int(guard.sum())==1368,
 'release_951_matches':np.array_equal(released,mc['released_upper_eye_skin']) and int(released.sum())==951,
 'mother_all_ear_mask_1834_matches':np.array_equal(ears,mc['ear_locked']) and int(ears.sum())==1834,
 'crown_height_unchanged':float(v0[:,2].max())==float(v1[:,2].max())}
mother_regions={'revised_core_18846':core,'true_eye_boundary_248':eye_boundary,'true_eye_guard_0p8mm_1368':guard,'mother_all_original_ear_1834':ears,'curved_apex_anchor':mc['apex_anchor']}
for name in FEATURES:mother_regions[name]=masks['master_raw_feature_'+name]
for n,m in mother_regions.items():checks['mother_'+n+'_exact_zero']=bool(np.count_nonzero(md[m])==0)
if not all(checks.values()):raise ValueError({k:v for k,v in checks.items() if not v})
NAMES={'head':'PRINT_01_Head_Shell','cap':'PRINT_02_Removable_Cap','master':'EDITABLE_Outer_Surface_Before_Hollowing'}
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for key,name in NAMES.items():
  o=bpy.data.objects[name];me=o.data;me.calc_loop_triangles();nm=o.matrix_world.to_3x3().inverted().transposed()
  nn=np.array([nm@p.normal for p in me.vertices]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-15)
  out[key]={'v':np.array([o.matrix_world@p.co for p in me.vertices]),'n':nn,'f':np.array([p.vertices[:] for p in me.loop_triangles],np.int32)}
 return out
b=snapshot(FILES['baseline_blend']);c=snapshot(FILES['current_blend'])
def stats(values):
 a=np.asarray(values,float)
 return {'count':len(a),'mean_mm':float(a.mean()),'median_mm':float(np.median(a)),'p95_mm':float(np.percentile(a,95)),'max_mm':float(a.max())} if len(a) else {'count':0}
def bvh(v,f):return BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
def bary(p,tri):
 a,b,c=tri;ab=b-a;ac=c-a;ap=p-a;aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=ap@ab;qc=ap@ac;den=aa*cc-bb*bb
 if abs(den)<1e-18:return np.array([1.,0.,0.])
 beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den;w=np.maximum([1-beta-gamma,beta,gamma],0);return w/w.sum()
mother_tree=bvh(v0,mb['triangles']);target_tree=bvh(c['head']['v'],c['head']['f'])
labels={'central_protected_core':core,'actual_eye_guard_0p8mm':guard,'original_ear_including_permitted_print_finish':ears,'released_upper_eye_skin_951_projection':released}
for name in FEATURES:labels[name]=masks['master_raw_feature_'+name]
results={name:[] for name in labels};worst={name:[] for name in results};normal_bad={name:0 for name in results};rejected=0
for i in np.flatnonzero(b['head']['v'][:,2]<=42):
 p=b['head']['v'][i];n=b['head']['n'][i];q,mn,mi,dd=mother_tree.find_nearest(Vector(p))
 if mi is None or dd>.65 or float(np.dot(mn,n))<.25:rejected+=1;continue
 jj=mb['triangles'][mi];w=bary(np.array(q),v0[jj]);members=[name for name,mask in labels.items() if float(w@mask[jj])>=.5]
 if not members:continue
 q,tn,ti,dd=target_tree.find_nearest(Vector(p))
 if ti is None:raise RuntimeError('No current head surface match')
 for name in members:
  results[name].append(float(dd));normal_bad[name]+=int(float(np.dot(tn,n))<.25);worst[name].append((float(dd),int(i),p.tolist(),list(q)))
surface={name:{'nearest_surface_distance':stats(vals),'nearest_normal_dot_below_0p25':normal_bad[name], 'worst_samples':[{'distance_mm':d,'v11_vertex_id':i,'v11_point_mm':p,'v12_point_mm':q} for d,i,p,q in sorted(worst[name],reverse=True)[:3]]} for name,vals in results.items()}
checks['every_surface_region_has_samples']=all(bool(v) for v in results.values())
# Mother is exactly locked; a rebuilt voxel surface is compared with an explicit
# 0.05mm diagnostic tolerance, independently of the .05mm projected eye test.
for name in ['central_protected_core','actual_eye_guard_0p8mm',*FEATURES]:checks['print_'+name+'_sample_max_below_0p05mm']=bool(len(results[name]) and max(results[name])<=.05)
def oriented_sorted(tri):
 r=tri[np.arange(len(tri))[:,None],(np.argmin(tri,axis=1)[:,None]+np.arange(3))%3]
 return r[np.lexsort((r[:,2],r[:,1],r[:,0]))]
def verify_stl(path,obj):
 data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
 if len(data)!=84+50*count:raise ValueError('Not binary STL '+str(path))
 dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);corners=np.frombuffer(data,offset=84,dtype=dt,count=count)['vertices'].reshape(-1,3)
 sv,si=np.unique(corners,axis=0,return_inverse=True);bv,bi=np.unique(obj['v'].astype(np.float32),axis=0,return_inverse=True)
 position_equal=np.array_equal(sv,bv);triangle_equal=position_equal and np.array_equal(oriented_sorted(si.reshape(-1,3)),oriented_sorted(bi[obj['f']]))
 return {'stl_triangles':count,'blend_triangles':len(obj['f']),'unique_float32_positions_equal':bool(position_equal),'oriented_triangle_multisets_equal':bool(triangle_equal),'verified':bool(position_equal and triangle_equal)}
exports={}
for part in ('head','cap'):
 exports[part]={}
 for version,prefix,objects in [('v11','baseline',b),('v12','current',c)]:
  rr=verify_stl(FILES[prefix+'_'+part+'_stl'],objects[part]);exports[part][version]=rr;checks[part+'_'+version+'_stl_matches_blend']=rr['verified']
actual_master={};same_master_topology=np.array_equal(b['master']['f'],c['master']['f']) and len(b['master']['v'])==len(c['master']['v']);checks['actual_master_triangle_indices_same']=bool(same_master_topology)
actual_master_release={};actual_master_axis={}
if same_master_topology:
 ad=np.linalg.norm(c['master']['v']-b['master']['v'],axis=1);actual_master={name:stats(ad[mask]) for name,mask in mother_regions.items()};actual_master_release=stats(ad[released]);actual_master_axis={axis:float(np.max(np.abs(c['master']['v'][:,j]-b['master']['v'][:,j]))) for j,axis in enumerate(('X','Y','Z'))}
 checks['actual_master_matches_current_mother_within_0p00002mm']=bool(np.max(np.linalg.norm(c['master']['v']-v1,axis=1))<=.00002)
 for name,rr in actual_master.items():checks['actual_master_'+name+'_within_0p00002mm']=rr['max_mm']<=.00002
report={'baseline_version':'v0.11','current_version':'v0.12','units':'mm','files':{k:{'path':str(p),'sha256':hashes[k]} for k,p in FILES.items()},
 'mother_corresponding_displacement':{name:stats(md[m]) for name,m in mother_regions.items()},'mother_released_upper_eye_skin_951_displacement':stats(md[released]),'mother_all_vertices_displacement':stats(md),'mother_crown_z_mm':{'v11':float(v0[:,2].max()),'v12':float(v1[:,2].max())},
 'actual_blend_master_corresponding_displacement':actual_master,'actual_blend_master_released_upper_eye_skin_951_displacement':actual_master_release,'actual_blend_master_maximum_axis_change_mm':actual_master_axis,
 'v11_feature_exterior_to_v12_print':surface,'baseline_non_exterior_candidates_rejected':rejected,'stl_correspondence':exports,'checks':checks,'all_integrity_checks_pass':all(checks.values()),
 'ear_print_finish':{'permitted':True,'mother_ear_displacement_exactly_zero':bool(np.count_nonzero(md[ears])==0),'actual_print_ear_change_measured_separately':surface['original_ear_including_permitted_print_finish'],'supplementary_report':str(FILES.get('ear_finish_report','not supplied')),'note':'No whole-ear PRINT zero-displacement assertion. Ear backside/attachment microfinish and possible local retriangulation are authorized; its support and safety are independently audited in the ear-finish report.'},
 'methods':{'mother':'Compare actual v11/v12 mother arrays with identical topology. Independently reconstruct newcore18846, true-eye boundary248 and its .8mm geodesic ring1368. Raw nose/mouth/cheek/chin and mother ears1834 are fixed. Released nonfeature upper-eye951 points are explicitly allowed and measured; obsolete whole-eye2mm/all-closure locks are not imposed. Crown height is fixed by a tiny curved apex anchor, not a Z-plane.',
 'print_samples':'Actual v11 PRINT vertices Z<=42 are classified against its mother BVH. Exterior samples require distance<=.65mm and normal agreement>=.25. Barycentric majority of new masks identifies protected regions and separately permitted upper-eye/ear changes. No inter-version PRINT indexing assumption.',
 'distance':'Forward sampled nearest-surface distances, not a certified continuous Hausdorff bound. Protected actual-print region maxima must be<=.05mm; eye-aperture projection and installation are separately tested. Ear/backside changes and released upper-eye skin have no false zero threshold.',
 'exports':'Each head/cap STL equals actual saved Blend world float32 positions and oriented triangle multiset; cyclic corner order normalized, winding retained.'},'scope':'Source identity and export consistency. Self-intersection, wall samples, cap fit and physical print fit are separate.'}
report['input_files_unchanged_during_audit']=all(sha(p)==hashes[k] for k,p in FILES.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit')
(R/'source-surface-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_integrity_checks_pass':report['all_integrity_checks_pass'],'failed_checks':[k for k,v in checks.items() if not v],'surface_summary':{k:v['nearest_surface_distance'] for k,v in surface.items()},'head_stl_sha256':hashes['current_head_stl'],'blend_sha256':hashes['current_blend']},indent=2),flush=True)
