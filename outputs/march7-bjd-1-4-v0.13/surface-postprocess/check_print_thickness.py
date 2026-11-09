"""Paired local opposing-wall rays; a regression screen, not a global certificate."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
O=Path(args[0]) if args else Path(__file__).parent/'print-v11-test'
p=O/'print-solution.npz';d=np.load(p);f=d['triangles'];v=d['before'];a=d['after'];ids=np.flatnonzero(d['free'])
n=np.zeros_like(v);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
for j in range(3):np.add.at(n,f[:,j],fn)
n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
def rays(vertices):
 tree=BVHTree.FromPolygons(vertices.tolist(),f.tolist(),all_triangles=True);out=np.full(len(ids),np.nan)
 for k,i in enumerate(ids):
  p=vertices[i];direction=-n[i];travel=.025
  for j in range(6):
   q,nn,ti,dd=tree.ray_cast(Vector(p+direction*travel),Vector(direction),8.-travel)
   if ti is None:break
   total=travel+dd
   if total>.06 and np.dot(nn,n[i])<-.2:out[k]=total;break
   travel=total+.025
   if travel>=8:break
 return out
b=rays(v);c=rays(a);valid=np.isfinite(b)&np.isfinite(c)
def st(x):
 x=x[np.isfinite(x)];return {'count':len(x),'min_mm':float(x.min()),'p01_mm':float(np.percentile(x,1)),'p05_mm':float(np.percentile(x,5)),'median_mm':float(np.median(x)),'below_0p4':int((x<.4).sum()),'below_0p6':int((x<.6).sum())}
loss=b-c;worst=np.flatnonzero(valid)[np.argsort(loss[valid])[-10:][::-1]]
r={'solution_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'method':'Same baseline vertex-normal inward rays from before/after changed exterior positions, accepting an opposing oriented wall within8mm; skips immediate same-surface hits. Local regression sampling only, not global minimum thickness.',
 'before':st(b),'after':st(c),'paired_valid':int(valid.sum()),'missing_before':int((~np.isfinite(b)).sum()),'missing_after':int((~np.isfinite(c)).sum()),
 'maximum_thickness_reduction_mm':float(loss[valid].max()),'new_below_0p4_count':int(np.sum(valid&(b>=.4)&(c<.4))),
 'worst_reductions':[{'vertex_id':int(ids[k]),'point_mm':v[ids[k]].tolist(),'before_mm':float(b[k]),'after_mm':float(c[k]),'reduction_mm':float(loss[k])} for k in worst]}
(O/'print-local-thickness.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
