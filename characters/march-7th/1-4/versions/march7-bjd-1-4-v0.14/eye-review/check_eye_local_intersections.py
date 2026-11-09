from pathlib import Path
import sys,json,time,hashlib
import numpy as np
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from triangle_intersection_helpers import intersection
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from final_eye_inputs import HEAD as STL,SOLUTION as P,load_final,expected_head,confirm_unchanged
d,integrity=load_final(expected_head());h=integrity['solution_sha256'];hs=integrity['head_sha256']
F=d['triangles'];V=d['after'].astype('f4').astype('f8');B=d['before'].astype('f4').astype('f8');T=V[F];TB=B[F]
N=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);NB=np.cross(TB[:,1]-TB[:,0],TB[:,2]-TB[:,0]);A=np.linalg.norm(N,axis=1);AB=np.linalg.norm(NB,axis=1)
dot=np.einsum('ij,ij->i',N,NB)/np.maximum(A*AB,1e-30);abnormal=np.flatnonzero((dot<0)&np.any(d['free'][F],axis=1))
records=[]
for i in abnormal:
 records.append({'triangle_id':int(i),'vertices':F[i].tolist(),'before_xyz_mm':TB[i].tolist(),'after_xyz_mm':T[i].tolist(),'center_mm':T[i].mean(0).tolist(),'normal_dot_before_after':float(dot[i]),'before_double_area_mm2':float(AB[i]),'after_double_area_mm2':float(A[i]),'area_ratio':float(A[i]/AB[i]),'edge_lengths_mm':np.linalg.norm(np.roll(T[i],-1,axis=0)-T[i],axis=1).tolist()})
print('NORMAL_REVIEW',json.dumps(records),flush=True)
changedv=np.any(V!=B,axis=1)&d['free'];changed=np.any(changedv[F],axis=1);lo=T.min(1);hi=T.max(1);clo=lo[changed].min(0);chi=hi[changed].max(0)
region=np.all(lo<=chi+1e-6,axis=1)&np.all(hi>=clo-1e-6,axis=1)
ids=np.flatnonzero(region);ids=ids[np.argsort(lo[ids,2],kind='stable')];ordered=lo[ids,2];tests=0;hits=[];t0=time.time();shared=0
for k,i in enumerate(ids):
 end=np.searchsorted(ordered,hi[i,2]+1e-6,side='right');js=ids[k+1:end]
 ok=np.all(lo[js]<=hi[i]+1e-6,axis=1)&np.all(hi[js]>=lo[i]-1e-6,axis=1)&(changed[i]|changed[js]);js=js[ok]
 if len(js):
  adj=np.any(F[i][None,:,None]==F[js][:,None,:],axis=(1,2));shared+=int(adj.sum());js=js[~adj];tests+=len(js)
 for j in js:
  hit=intersection(T[i],T[j])
  if hit is None:continue
  old=intersection(TB[i],TB[j]);hit.update(triangles=[int(i),int(j)],present_in_baseline=old is not None,baseline_kind=None if old is None else old['kind'],center_mm=np.vstack([T[i],T[j]]).mean(0).tolist(),triangles_xyz_mm=[T[i].tolist(),T[j].tolist()]);hits.append(hit)
  if len(hits)<=10:print('HIT',json.dumps(hit),flush=True)
 if k and k%30000==0:print('PROGRESS',k,len(ids),'pairs',tests,'hits',len(hits),flush=True)
# The normal rotations also receive a shared-one-vertex check: positive-length
# triangle-plane overlap cannot be explained by their common vertex alone.
adjacent_one_vertex=[];adjacent_two_vertex_coplanar=[]
for i in abnormal:
 js=np.flatnonzero(np.all(lo<=hi[i]+1e-6,axis=1)&np.all(hi>=lo[i]-1e-6,axis=1))
 for j in js:
  if i==j:continue
  common=np.intersect1d(F[i],F[j])
  if len(common) not in (1,2):continue
  hit=intersection(T[i],T[j])
  if hit is None:continue
  old=intersection(TB[i],TB[j]);entry={'triangles':[int(i),int(j)],'shared_vertices':common.tolist(),'hit':hit,'baseline_hit':old}
  if len(common)==1:adjacent_one_vertex.append(entry)
  elif hit['kind'] in ('coplanar_overlap','near_coplanar_contact'):adjacent_two_vertex_coplanar.append(entry)
confirm_unchanged(integrity)
report={'solution_sha256':h,'actual_stl_sha256':hs,'input_integrity':integrity,'scope':'Every changed triangle against every nonadjacent head triangle whose AABB overlaps changed-region bounds. Unchanged-only pairs excluded. Normal-rotation faces also checked for shared-one-vertex intersections and coplanar shared-edge overlaps.',
 'distance_tolerance_mm':1e-6,'changed_vertices':int(changedv.sum()),'changed_triangles':int(changed.sum()),'candidate_region_triangles':len(ids),'nonadjacent_aabb_pairs':tests,'shared_vertex_aabb_pairs_excluded':shared,'normal_over90':records,'degenerate_triangles':int((A<1e-12).sum()),'hits':hits,
 'new_strict_intersections':sum(not q['present_in_baseline'] and q['kind'] in ('transverse_crossing','coplanar_overlap') for q in hits),'new_ambiguous_contacts':sum(not q['present_in_baseline'] and q['kind'] not in ('transverse_crossing','coplanar_overlap') for q in hits),
 'abnormal_shared_one_vertex_positive_overlap':adjacent_one_vertex,'abnormal_shared_edge_coplanar_overlap':adjacent_two_vertex_coplanar,'input_unchanged':True,'duration_seconds':time.time()-t0}
(R/'eye-local-intersection-check.json').write_text(json.dumps(report,indent=2)+'\n');print('FINAL',json.dumps({k:v for k,v in report.items() if k not in ('normal_over90','hits','abnormal_shared_one_vertex_positive_overlap','abnormal_shared_edge_coplanar_overlap')}),flush=True)
