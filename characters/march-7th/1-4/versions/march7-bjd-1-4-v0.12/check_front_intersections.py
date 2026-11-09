"""Read-only full mother-surface self-intersection check, with ear-region priority."""
from pathlib import Path
import sys,hashlib,json,time
import numpy as np
sys.path.insert(0,'/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.8')
from triangle_intersection_helpers import intersection
O=Path(__file__).resolve().parent;p=O/'front-solution.npz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();h=sha(p);s=np.load(p);t0=time.time();eps=1e-6
F=s['triangles'];V=s['after'];B=s['before'];T=V[F];TB=B[F]
def normals(t):
 n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);l=np.linalg.norm(n,axis=1);return n/np.maximum(l[:,None],1e-30),l
n,l=normals(T);nb,lb=normals(TB);dot=np.einsum('ij,ij->i',n,nb);anomalies=np.flatnonzero(dot<0);lo=T.min(1);hi=T.max(1);moved=np.linalg.norm(V-B,axis=1);changed=np.max(moved[F],axis=1)>eps
boxes=[];region=np.zeros(len(F),bool)
for lower,upper in boxes:region|=np.all(hi>=lower,axis=1)&np.all(lo<=upper,axis=1)
tests=0;hits=[];done=set()
def check(i,j):
 global tests
 a,b=sorted([int(i),int(j)])
 if a==b or (a,b) in done or np.any(F[a][:,None]==F[b][None,:]):return
 done.add((a,b));tests+=1;hit=intersection(T[a],T[b])
 if hit is None:return
 old=intersection(TB[a],TB[b]);hit.update(triangles=[a,b],center_mm=np.vstack([T[a],T[b]]).mean(0).tolist(),present_in_baseline=old is not None,baseline_hit=old,normal_anomaly_present=bool(dot[a]<0 or dot[b]<0),fixed_ear_triangle_present=bool(np.all(s['ear_body_locked'][F[a]]) or np.all(s['ear_body_locked'][F[b]])));hits.append(hit)
def sweep(ids,stage,changed_only=False):
 ids=ids[np.argsort(lo[ids,2],kind='stable')];zl=lo[ids,2]
 for k,i in enumerate(ids):
  end=np.searchsorted(zl,hi[i,2]+eps,side='right');js=ids[k+1:end];mask=np.all(lo[js]<=hi[i]+eps,axis=1)&np.all(hi[js]>=lo[i]-eps,axis=1)
  if changed_only:mask&=changed[i]|changed[js]
  for j in js[mask]:check(i,j)
  if k and k%20000==0:print(stage,k,'/',len(ids),'pairs',tests,'hits',len(hits),flush=True)
 return len(ids)
localcount=sweep(np.flatnonzero(region),'local');localpairs=tests;localhits=len(hits)
print('LOCAL',json.dumps({'triangles':localcount,'tested_pairs':tests,'hits_count':len(hits),'elapsed':time.time()-t0}),flush=True)
sweep(np.arange(len(F)),'global')
actual_before=np.load('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.11/mother-surface.npz')['after']
assert np.array_equal(B,actual_before), 'Before does not match delivered v11 mother'
r={'eye_guard_vertices':int(s['eye_guard'].sum()),'eye_guard_max_displacement_mm':float(moved[s['eye_guard']].max()),'actual_eye_boundary_vertices':len(s['eye_boundary_vertices']),'actual_eye_boundary_max_displacement_mm':float(moved[s['eye_boundary_vertices']].max()),'apex_anchor_max_displacement_mm':float(moved[s['apex_anchor']].max()),'top_before_after_mm':[float(B[:,2].max()),float(V[:,2].max())],'before_matches_actual_v11_exactly':True,'x_max_displacement_mm':float(abs(V[:,0]-B[:,0]).max()),'z_max_displacement_mm':float(abs(V[:,2]-B[:,2]).max()),'max_displacement_mm':float(moved.max()),'all_ear_locked_count':int(s['ear_locked'].sum()),'all_ear_locked_max_displacement_mm':float(moved[s['ear_locked']].max()),'core_locked_count':int(s['core_locked'].sum()),'released_upper_eye_skin_count':int(s['released_upper_eye_skin'].sum()),'released_upper_eye_skin_max_displacement_mm':float(moved[s['released_upper_eye_skin']].max()),'solution':str(p),'solution_sha256':h,'unchanged_during_analysis':sha(p)==h,'units':'mm','baseline_array':'before (actual v0.11 mother)' ,'normal_over_90_count':len(anomalies),'normal_anomaly_triangle_ids':anomalies.tolist(),'degenerate_triangles_count':int(np.sum(l<1e-12)),'min_double_area_mm2':float(l.min()),'min_area_ratio':float(np.min(l/np.maximum(lb,1e-30))),'locked_max_displacement_vs_baseline_mm':float(moved[s['locked']].max()),'core_locked_max_displacement_mm':float(moved[s['core_locked']].max()),'ear_body_locked_max_displacement_mm':float(moved[s['ear_body_locked']].max()),'scope':'Entire mother mesh, all nonadjacent triangle pairs whose AABBs overlap, including unchanged pairs. Does not certify hollow-wall or mechanical assembly geometry.','region_boxes_mm':boxes,'priority_region_triangle_count':localcount,'priority_nonadjacent_aabb_pairs':localpairs,'priority_hits':localhits,'total_triangle_count':len(F),'nonadjacent_aabb_pairs_tested':tests,'shared_vertex_pairs_excluded':True,'tolerance_mm':eps,'projected_polygon_rejection':True,'pairs':hits,'new_strict_intersections':sum(not x['present_in_baseline'] and x['kind'] in ('transverse_crossing','coplanar_overlap') for x in hits),'new_ambiguous_contacts':sum(not x['present_in_baseline'] and x['kind'] not in ('transverse_crossing','coplanar_overlap') for x in hits),'duration_seconds':time.time()-t0}
(O/'front-intersection-check.json').write_text(json.dumps(r,indent=2)+'\n');print('FINAL',json.dumps({k:v for k,v in r.items() if k not in ('pairs',)}),flush=True)
