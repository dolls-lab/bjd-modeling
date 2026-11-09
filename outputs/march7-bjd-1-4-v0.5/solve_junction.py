"""Solve a source-constrained minimum-bending surface on the v3 topology."""
from pathlib import Path
import json
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
R=Path(__file__).resolve().parent
settings=json.loads((R/'parameters.json').read_text())['junction_fairing']
p=np.load(R/'fairing-problem.npz');v=p['vertices'];f=p['triangles'];weights=p['weights']
a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]]
cross=np.cross(b-a,c-a);twice_area=np.linalg.norm(cross,axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(twice_area[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);data=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[data,data],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr()
L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.bincount(f.ravel(),weights=np.repeat(twice_area/6,3),minlength=len(v));mass=np.maximum(mass,1e-9)
C=(L.T@sparse.diags(1/mass)@L).tocsr()
free=np.flatnonzero(weights>1e-5);locked=np.flatnonzero(weights<=1e-5)
Cff=C[free][:,free].tocsc();rhs=-(C[free][:,locked]@v[locked])
trials=[];chosen=None
for alpha in [settings['position_prior_alpha'],.01,.1,1,10]:
    prior=alpha*mass[free]/np.maximum(weights[free],.01)**2
    sol=spsolve(Cff+sparse.diags(prior),rhs+prior[:,None]*v[free])
    delta=sol-v[free];length=np.linalg.norm(delta,axis=1)
    record={'alpha':alpha,'max_displacement_mm':float(length.max()),'p95_displacement_mm':float(np.percentile(length,95))}
    trials.append(record);print(record,flush=True)
    if length.max()<=settings['maximum_displacement_mm']:
        chosen=sol;break
if chosen is None:raise RuntimeError('No bounded fairing solution')
result=v.copy();result[free]=chosen
field=result-v
np.savez(R/'fairing-solution.npz',vertices_before=v,vertices_after=result,field=field,triangles=f,weights=weights)
before=L@v;after=L@result
report={'method':'Constrained cotangent bi-Laplacian surface fairing; no ellipsoid projection; no pointwise displacement clipping','free_vertices':len(free),'locked_vertices':len(locked),'trials':trials,'selected':trials[-1],'locked_max_displacement_mm':float(np.linalg.norm(field[locked],axis=1).max()),'local_bending_energy_before':float(np.sum(before[free]**2/mass[free,None])),'local_bending_energy_after':float(np.sum(after[free]**2/mass[free,None]))}
(R/'fairing-solver-report.json').write_text(json.dumps(report,indent=2)+'\n')
