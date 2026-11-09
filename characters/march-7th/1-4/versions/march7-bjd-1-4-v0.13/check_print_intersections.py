"""Independent full nonadjacent triangle self-intersection check of actual binary STLs."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from triangle_intersection_helpers import intersection
R=Path(__file__).resolve().parent;eps=1e-6;started=time.time()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--expected-head-sha256',required=True,help='SHA256 of the confirmed final v0.13 head STL')
ap.add_argument('--expected-cap-sha256',required=True,help='SHA256 of the confirmed final v0.13 cap STL')
args=ap.parse_args()
expected={'head':args.expected_head_sha256.lower(),'cap':args.expected_cap_sha256.lower()}
for name,digest in expected.items():
 if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError(f'Invalid SHA256 for {name}')
parts={}
for name,stem in [('head','shell'),('cap','cap')]:
 p=R/f'march7-head-{stem}-v0.13-draft.stl';h=sha(p)
 if h!=expected[name]:raise RuntimeError(f'{name}: input SHA mismatch {h}')
 b=p.read_bytes();count=int.from_bytes(b[80:84],'little');dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);T=np.frombuffer(b,offset=84,dtype=dtype,count=count)['vertices'].astype('f8')
 if len(b)!=84+50*count:raise ValueError('Unexpected binary STL size')
 V,flat=np.unique(T.reshape(-1,3),axis=0,return_inverse=True);F=flat.reshape(-1,3)
 N=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);area2=np.linalg.norm(N,axis=1);norm=N/np.maximum(area2[:,None],1e-30)
 lo=T.min(1);hi=T.max(1);estimates=[]
 for ax in range(3):
  ii=np.argsort(lo[:,ax],kind='stable');estimate=int(np.sum(np.searchsorted(lo[ii,ax],hi[ii,ax]+eps,side='right')-np.arange(count)-1));estimates.append(estimate)
 axis=int(np.argmin(estimates));ids=np.argsort(lo[:,axis],kind='stable');ordered_lo=lo[ids,axis]
 tests=0;shared=0;plane_candidates=0;hits=[];begin=time.time()
 print('START',name,'triangles',count,'axis',axis,'broad_phase_estimated_pairs',estimates,'exact_unique_vertices',len(V),flush=True)
 for k,i in enumerate(ids):
  end=np.searchsorted(ordered_lo,hi[i,axis]+eps,side='right');js=ids[k+1:end]
  mask=np.all(lo[js]<=hi[i]+eps,axis=1)&np.all(hi[js]>=lo[i]-eps,axis=1);js=js[mask]
  if len(js):
   adjacent=np.any(F[i][None,:,None]==F[js][:,None,:],axis=(1,2));shared+=int(adjacent.sum());js=js[~adjacent];tests+=len(js)
  if len(js):
   da=np.einsum('nkj,nj->nk',T[i][None,:,:]-T[js,0,None,:],norm[js]);db=np.einsum('nkj,j->nk',T[js]-T[i,0],norm[i])
   js=js[(da.min(1)<=eps)&(da.max(1)>=-eps)&(db.min(1)<=eps)&(db.max(1)>=-eps)];plane_candidates+=len(js)
  for j in js:
   hit=intersection(T[i],T[j])
   if hit is None:continue
   hit.update(triangles=[int(i),int(j)],center_mm=np.vstack([T[i],T[j]]).mean(0).tolist(),triangle_vertices_mm=[T[i].tolist(),T[j].tolist()]);hits.append(hit)
   if len(hits)<=5:print('INTERSECTION_OR_CONTACT',name,json.dumps(hit),flush=True)
  if k and k%50000==0:print('PROGRESS',name,k,'/',count,'nonadjacent_pairs',tests,'hits',len(hits),'elapsed',round(time.time()-begin,1),flush=True)
 duplicate_keys=np.sort(F,axis=1);_,dupecount=np.unique(duplicate_keys,axis=0,return_counts=True)
 part={'file':str(p),'sha256':h,'sha256_after':sha(p),'unchanged':sha(p)==h,'triangles':count,'exact_unique_vertices':len(V),'stl_vertex_indexing':'Exact float32 coordinate equality; no tolerance merging or geometry processing. Triangle indices remain actual binary STL facet order.',
 'degenerate_triangles_double_area_lt_1e_12':int(np.sum(area2<1e-12)),'duplicate_facet_copies':int(np.sum(dupecount-1)),
 'sweep_axis':axis,'estimated_pair_counts_before_other_axes_culling':estimates,'shared_vertex_candidate_pairs_excluded':shared,'nonadjacent_aabb_pairs_tested':tests,'pairs_surviving_plane_separation':plane_candidates,'pairs':hits,
 'strict_intersection_count':sum(q['kind'] in ('transverse_crossing','coplanar_overlap') for q in hits),'ambiguous_contact_count':sum(q['kind'] not in ('transverse_crossing','coplanar_overlap') for q in hits),'duration_seconds':time.time()-begin}
 if not part['unchanged']:raise RuntimeError(f'{name}: STL changed during check')
 parts[name]=part
 report={'scope':'Full actual head STL and full actual cap STL independently; no head-cap assembly intersection test is performed.','distance_tolerance_mm':eps,'shared_vertex_policy':'Any pair sharing any exactly identical vertex coordinate is excluded; therefore adjacent-facet overlap away from shared vertices is not certified by this test. Duplicate facets and degenerate facets are counted separately.',
 'method':'Axis sweep of all triangle AABBs, full 3-axis AABB overlap, exact shared-vertex exclusion, triangle-plane separation, then triangle-plane interval intersection with projected polygon rejection. Strict transverse crossing and coplanar area overlap are reported separately from near-plane/coplanar numerical contacts.',
 'parts':parts,'duration_seconds':time.time()-started}
 (R/'print-intersection-check.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PART_DONE',name,json.dumps({k:v for k,v in part.items() if k!='pairs'}),flush=True)
report['completed_both_parts']=True;report['no_strict_nonadjacent_self_intersections']=all(p['strict_intersection_count']==0 for p in parts.values());report['all_inputs_unchanged']=all(sha(Path(p['file']))==p['sha256'] for p in parts.values());report['duration_seconds']=time.time()-started
(R/'print-intersection-check.json').write_text(json.dumps(report,indent=2)+'\n');print('FINAL',json.dumps({k:v for k,v in report.items() if k!='parts'}),flush=True)
