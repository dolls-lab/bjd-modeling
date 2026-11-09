from pathlib import Path
import json,hashlib,time
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.6');OUT=Path(__file__).resolve().parent
p=np.load(R/'head-deformation.npz');v=p['after'].copy();metric=p['before'];q=np.load(R/'v6-side-protection.npz');f=q['head_baseline_triangles'];vis=np.load(R/'head-visible-source-protection.npz');source=vis['head_locked'];report0=json.loads((R/'build-report.json').read_text())
def ramp(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t**3*(t*(t*6-15)+10)
x,y,z=metric.T
weights=ramp(-5,-1,y)*(1-ramp(11,17,y))*ramp(13,18,z)*(1-ramp(43,52,z))*ramp(17,20,abs(x))
weights*=ramp(3,6,29.5-y-.3*z)
radius=np.hypot(x,y-report0['neck_center_y_mm']);weights*=1-(1-ramp(report0['neck_platform_top_mm'],25,z))*(1-ramp(15,18,radius))
for center in report0['magnet_centers_mm']:weights*=ramp(7,12,np.linalg.norm(metric-np.array(center),axis=1))
weights[source]=0
free=np.flatnonzero(weights>1e-5);locked=weights<=1e-5;print('free',len(free),'fixed',locked.sum(),flush=True)
a,b,c=metric[f[:,0]],metric[f[:,1]],metric[f[:,2]];area2=np.linalg.norm(np.cross(b-a,c-a),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);data=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[data,data],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9)
# Only columns incident to the free domain enter the solve; the rest is the exact
# fixed v6 print geometry. Using the pre-transfer metric avoids conditioning the
# fairness operator on the already stretched narrow ear triangles.
LF=L[:,free];Cff=(LF.T@sparse.diags(1/mass)@LF).tocsc();base_lap=L@v[:,0]
alpha=.03;prior=alpha*mass[free]/np.maximum(weights[free],.01)**2
rhs=-(LF.T@(base_lap/mass))
print('matrix',Cff.shape,Cff.nnz,flush=True)
u=spsolve(Cff+sparse.diags(prior),rhs);after=v.copy();after[free,0]+=u
assert np.array_equal(after[locked],v[locked]);assert np.array_equal(after[:,1:],v[:,1:])
np.savez_compressed(OUT/'head-solution.npz',before=v,after=after,locked=locked,source_locked=source,free=free,weights=weights,triangles=f,input_v6_head_sha256=np.array(hashlib.sha256((R/'march7-head-shell-v0.6-draft.stl').read_bytes()).hexdigest()))
e=q['head_baseline_edges'];length=np.linalg.norm(metric[e[:,1]]-metric[e[:,0]],axis=1);old_delta=v[:,0]-metric[:,0];new_delta=after[:,0]-metric[:,0]
boundary=source[e[:,0]]!=source[e[:,1]];zone=(abs(metric[e].mean(1)[:,0])>17)&(metric[e].mean(1)[:,1]>-3)&(metric[e].mean(1)[:,1]<10)&(metric[e].mean(1)[:,2]>16)&(metric[e].mean(1)[:,2]<40);bb=boundary&zone
cross0=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);cross1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]])
ln0=np.linalg.norm(cross0,axis=1);ln1=np.linalg.norm(cross1,axis=1);dot=np.einsum('ij,ij->i',cross0,cross1)/np.maximum(ln0*ln1,1e-30)
r={'method':'Local scalar-X constrained cotangent bi-Laplacian geometry fairing on final v6 head, using pre-transfer v5 print metric; position prior to v6; source and interface locks inside the solve.', 'alpha':alpha,'free_vertices':len(free),'maximum_correction_mm':float(abs(u).max()),'p95_correction_mm':float(np.quantile(abs(u),.95)),'source_max_displacement_mm':float(abs(after[source]-v[source]).max()),'yz_max_displacement_mm':float(abs(after[:,1:]-v[:,1:]).max()),'boundary_edges_tested':int(bb.sum()),'boundary_step_max_before_after_mm':[float(abs(np.diff(old_delta[e[bb]],axis=1)).max()),float(abs(np.diff(new_delta[e[bb]],axis=1)).max())],'boundary_step_p95_before_after_mm':[float(np.quantile(abs(np.diff(old_delta[e[bb]],axis=1)),.95)),float(np.quantile(abs(np.diff(new_delta[e[bb]],axis=1)),.95))],'normal_rotation_over_90_triangles':int((dot<0).sum()),'degenerate_triangles':int((ln1<1e-12).sum()),'solution_sha256':hashlib.sha256((OUT/'head-solution.npz').read_bytes()).hexdigest(),'status':'Candidate arrays for rendering; topology/self-intersection/thickness must be reviewed before acceptance.'}
(OUT/'head-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
