"""Tiny, source-classified rear-ear-only fairing after candidate2; array output."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
OUT=Path(__file__).resolve().parent;BASE=OUT.parent/'candidate2/head-solution.npz';R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.6')
maskpath=Path(sys.argv[1]);q=np.load(maskpath);print('mask keys',q.files,flush=True)
release=q['head_earback_release'].astype(bool)
weights=q['head_earback_weight'] if 'head_earback_weight' in q else release.astype(float)
p=np.load(BASE);v=p['after'].copy();f=p['triangles'];source=p['source_locked'];assert np.all(~release|source)
weights=np.where(release,weights,0);free=np.flatnonzero(weights>1e-5);assert len(free)>0
# Source ear rear only. Everything else, including the finished candidate2
# skull and the front/silhouette band of the ears, is a Dirichlet boundary.
a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];area2=np.linalg.norm(np.cross(b-a,c-a),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);d=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[d,d],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free];C=(LF.T@sparse.diags(1/mass)@LF).tocsc();rhs=-(LF.T@((L@v)/mass[:,None]));trials=[]
for alpha in [.1,1,10,100,1000,10000]:
 prior=alpha*mass[free]/np.maximum(weights[free],.01)**2
 u=spsolve(C+sparse.diags(prior),rhs);norm=np.linalg.norm(u,axis=1);rec={'alpha':alpha,'maximum_correction_mm':float(norm.max()),'p95_correction_mm':float(np.quantile(norm,.95))};trials.append(rec);print(rec,flush=True)
 if norm.max()<=.15:break
else:raise RuntimeError('No bounded micro-fair solution')
after=v.copy();after[free]+=u;assert np.array_equal(after[~release],v[~release])
locked=p['locked'].copy();locked[release]=False;source_after=source&~release
assert np.array_equal(after[source_after],p['before'][source_after])
np.savez_compressed(OUT/'head-solution.npz',before=p['before'],after=after,locked=locked,source_locked=source_after,original_source_locked=source,earback_release_mask=release,earback_correction=after-v,candidate2_after=v,triangles=f,free=p['free'],earback_free=free,weights=p['weights'],earback_weights=weights)
r={'method':'Small 3D cotangent bi-Laplacian fairing on semantically classified original ear-back interior only, with every other candidate2 vertex fixed. No post-solve clipping.','mask_file':str(maskpath),'mask_sha256':hashlib.sha256(maskpath.read_bytes()).hexdigest(),'candidate2_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'released_count':int(release.sum()),'solved_count':len(free),'trials':trials,'selected':trials[-1],'nonreleased_change_from_candidate2_mm':float(np.max(np.linalg.norm(after[~release]-v[~release],axis=1))),'source_except_released_change_from_v6_mm':float(np.max(np.linalg.norm(after[source_after]-p['before'][source_after],axis=1))),'release_bounds_mm':[v[release].min(0).tolist(),v[release].max(0).tolist()],'head_solution_sha256':hashlib.sha256((OUT/'head-solution.npz').read_bytes()).hexdigest(),'status':'Bounded rear-ear micro-fairing candidate; requires visual and local intersection review.'}
(OUT/'head-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
