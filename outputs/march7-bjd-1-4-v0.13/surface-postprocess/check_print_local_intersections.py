from pathlib import Path
import sys,json,time,hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from triangle_intersection_helpers import intersection
O=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent/'print-v11-test'
p=O/'print-solution.npz';h=hashlib.sha256(p.read_bytes()).hexdigest();d=np.load(p);F=d['triangles'];V=d['after'];B=d['before'];T=V[F];TB=B[F]
lo=T.min(1);hi=T.max(1);changed=np.any(d['free'][F],axis=1);clo=lo[changed].min(0);chi=hi[changed].max(0)
region=np.all(lo<=chi+1e-6,axis=1)&np.all(hi>=clo-1e-6,axis=1)
ids=np.flatnonzero(region);ids=ids[np.argsort(lo[ids,2],kind='stable')];zl=lo[ids,2];hits=[];tests=0;t0=time.time()
for k,i in enumerate(ids):
 end=np.searchsorted(zl,hi[i,2]+1e-6,side='right');js=ids[k+1:end]
 ok=np.all(lo[js]<=hi[i]+1e-6,axis=1)&np.all(hi[js]>=lo[i]-1e-6,axis=1)&(changed[i]|changed[js])
 for j in js[ok]:
  if np.any(F[i][:,None]==F[j][None,:]):continue
  tests+=1;hit=intersection(T[i],T[j])
  if hit is not None:
   old=intersection(TB[i],TB[j]);hit.update(triangles=[int(i),int(j)],present_in_baseline=old is not None,center_mm=np.vstack([T[i],T[j]]).mean(0).tolist());hits.append(hit)
r={'solution_sha256':h,'scope':'Every changed triangle against every nonadjacent head triangle whose AABB overlaps the changed-region bounds; unchanged-only pairs are excluded.',
 'changed_triangles':int(changed.sum()),'candidate_region_triangles':len(ids),'nonadjacent_aabb_pairs':tests,'hits':hits,
 'new_strict_intersections':sum(not x['present_in_baseline'] and x['kind'] in ('transverse_crossing','coplanar_overlap') for x in hits),
 'new_ambiguous_contacts':sum(not x['present_in_baseline'] and x['kind'] not in ('transverse_crossing','coplanar_overlap') for x in hits),
 'elapsed_seconds':time.time()-t0,'unchanged_input':hashlib.sha256(p.read_bytes()).hexdigest()==h}
(O/'print-local-intersections.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='hits'},indent=2),flush=True)
