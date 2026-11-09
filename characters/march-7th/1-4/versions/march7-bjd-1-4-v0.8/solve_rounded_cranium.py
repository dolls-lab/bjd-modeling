"""Recover a smooth rounded side cranium on the delivered v7 print topology.
The v5 curved surface is a position prior, never a constant-X ceiling.
Only a proposed array solution is written; existing models remain read-only.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
ROOT=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs');OUT=Path(__file__).resolve().parent
V7=ROOT/'march7-bjd-1-4-v0.7';V6=ROOT/'march7-bjd-1-4-v0.6'
v=np.load(V7/'head-deformation.npz')['after'].copy();metric=np.load(V6/'head-deformation.npz')['before'].copy();q=np.load(V7/'v6-side-protection.npz');f=q['head_baseline_triangles'];source=np.load(V7/'head-visible-source-protection.npz')['head_locked'];report0=json.loads((V7/'build-report.json').read_text())
assert v.shape==metric.shape

def ramp(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t**3*(t*(t*6-15)+10)
x,y,z=v.T
# Broad collars keep restored curvature continuous with the fixed original face,
# ear, underside and cap. Interface guards are part of the constrained solve.
weights=ramp(-6,-1,y)*(1-ramp(18,24,y))*ramp(11,20,z)*(1-ramp(49,57,z))*ramp(15,20,abs(x))
weights*=ramp(3,8,29.5-y-.3*z)
radius=np.hypot(x,y-report0['neck_center_y_mm']);weights*=1-(1-ramp(report0['neck_platform_top_mm'],26,z))*(1-ramp(15,19,radius))
for center in report0['magnet_centers_mm']:weights*=ramp(7,12,np.linalg.norm(v-np.array(center),axis=1))
weights[source]=0
free=np.flatnonzero(weights>1e-5);locked=weights<=1e-5
restore_fraction=.625;alpha=.03
target=v.copy();target[:,0]+=restore_fraction*weights*(metric[:,0]-v[:,0]);target[locked]=v[locked]
print('free',len(free),'fixed',locked.sum(),flush=True)
a,b,c=metric[f[:,0]],metric[f[:,1]],metric[f[:,2]];area2=np.linalg.norm(np.cross(b-a,c-a),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);d=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[d,d],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free];C=(LF.T@sparse.diags(1/mass)@LF).tocsc()
prior=alpha*mass[free]/np.maximum(weights[free],.01)**2
rhs=-(LF.T@((L@v[:,0])/mass))+prior*(target[free,0]-v[free,0]);print('matrix',C.shape,C.nnz,flush=True)
u=spsolve(C+sparse.diags(prior),rhs);after=v.copy();after[free,0]+=u
assert np.array_equal(after[locked],v[locked]);assert np.array_equal(after[source],v[source]);assert np.array_equal(after[:,1:],v[:,1:]);assert np.isfinite(after).all()
np.savez_compressed(OUT/'head-solution.npz',before=v,after=after,locked=locked,source_locked=source,weights=weights,free=free,triangles=f,target=target,reference_v5=metric)
c0=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);c1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]]);l0=np.linalg.norm(c0,axis=1);l1=np.linalg.norm(c1,axis=1);dot=np.einsum('ij,ij->i',c0,c1)/np.maximum(l0*l1,1e-30)
e=q['head_baseline_edges'];delta=after[:,0]-v[:,0];boundary=source[e[:,0]]!=source[e[:,1]]
r={'method':'Constrained scalar-X cotangent bi-Laplacian on final v7 print mesh, with a mass-weighted v5 curved-surface position prior; not a plane or ellipsoid projection. Broad C2 spatial collars and fixed source/interface regions are inside the solve.','baseline':'v0.7 delivered print mesh','curvature_metric':'v0.5 pre-retraction print geometry, identical indexed topology','prior_restore_fraction':restore_fraction,'alpha':alpha,'free_vertices':len(free),'maximum_displacement_mm':float(abs(u).max()),'p95_displacement_mm':float(np.quantile(abs(u),.95)),'source_max_displacement_mm':0.,'yz_max_displacement_mm':0.,'source_boundary_max_delta_step_mm':float(abs(np.diff(delta[e[boundary]],axis=1)).max()),'normal_rotation_over_90_count':int((dot<0).sum()),'minimum_normal_dot':float(dot.min()),'degenerate_triangles':int((l1<1e-12).sum()),'minimum_area_ratio':float((l1/np.maximum(l0,1e-30)).min()),'baseline_head_sha256':hashlib.sha256((V7/'march7-head-shell-v0.7-draft.stl').read_bytes()).hexdigest(),'solution_sha256':hashlib.sha256((OUT/'head-solution.npz').read_bytes()).hexdigest(),'status':'Geometry proposal for identical-light render and section review; no automatic aesthetic pass.'}
(OUT/'head-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
