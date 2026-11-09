"""One v11 local-Y fairing candidate. Never edits delivered v10 geometry."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.signal import savgol_filter
R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs');O=Path(__file__).parent
base=R/'march7-bjd-1-4-v0.10/mother-surface.npz';b=np.load(base);v=b['after'].copy();f=b['triangles'].copy();maskpath=Path('/private/tmp/v11-source/v11-forehead-protection.npz');m=np.load(maskpath)
core=m['master_core_locked'];ears=m['master_ear_locked'];released=m['master_nonfeature_forehead_release']
def S(t):
 t=np.clip(t,0,1);return t**3*(t*(6*t-15)+10)
x,y,z=v.T
wcore=m['master_combined_weight_5mm'];wx=1-S((abs(x)-16)/8);wz=S((z-34)/8)*(1-S((z-55)/9));wy=1-S((y+10)/8)
w=wcore*wx*wz*wy;w[core|ears]=0;free=np.flatnonzero(w>1e-5);fixed=w<=1e-5
# Compare only central actual-print profiles after placing v8 at the same crown
# lowering as v10. No lateral v8 target or v8 X coordinates are used.
p=np.load(O/'forehead-profiles.npz');zz=p['z_mm'];a=p['y_v8'];bb=p['y_v10'];z8=zz-3*S((zz-40)/(72.79233785101658-40))
deltas=[]
for idx in [0,1]:
 ok=np.isfinite(a[idx]);lowered=np.interp(zz,z8[ok],a[idx,ok]);deltas.append(lowered-bb[idx])
delta=np.mean(deltas,axis=0);ok=np.isfinite(delta);delta=np.interp(zz,zz[ok],delta[ok]);delta=savgol_filter(delta,41,3)
# Smooth bounded prior; actual solve movement is measured, not hard-clipped.
central_delta=2.2*np.tanh(.75*np.interp(z,zz,delta)/2.2)
target_pull=central_delta*(1-S((abs(x)-8)/12))*w
target=v.copy();target[:,1]+=target_pull
A,B,C=v[f[:,0]],v[f[:,1]],v[f[:,2]];area2=np.linalg.norm(np.cross(B-A,C-A),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',B-A,C-A),np.einsum('ij,ij->i',C-B,A-B),np.einsum('ij,ij->i',A-C,B-C)])/np.maximum(area2[:,None],1e-12)
ii=np.concatenate([f[:,1],f[:,2],f[:,0]]);jj=np.concatenate([f[:,2],f[:,0],f[:,1]]);dd=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[dd,dd],(np.r_[ii,jj],np.r_[jj,ii])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free];Bend=(LF.T@sparse.diags(1/mass)@LF).tocsc();alpha=.12;prior=alpha*mass[free]/np.maximum(w[free],.03)**2
rhs=-(LF.T@((L@y)/mass))+prior*target_pull[free]
u=spsolve(Bend+sparse.diags(prior),rhs);after=v.copy();after[free,1]+=u
move=np.linalg.norm(after-v,axis=1)
n0=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);n1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]]);a0=np.linalg.norm(n0,axis=1);a1=np.linalg.norm(n1,axis=1);dot=np.einsum('ij,ij->i',n0,n1)/np.maximum(a0*a1,1e-30)
assert np.array_equal(after[:,[0,2]],v[:,[0,2]]) and np.array_equal(after[core|ears],v[core|ears])
np.savez_compressed(O/'mother-surface.npz',baseline=v,before=v,control=target,target=target,after=after,vertices=after,triangles=f,protected=core|ears,locked=fixed,core_locked=core,ear_body_locked=ears,ear_locked=ears,released_forehead=released,weights=w,reference_central_delta_z_mm=zz,reference_central_delta_y_mm=delta)
report={'version':'v0.11-candidate1','method':'Local scalar-Y cotangent bi-Laplacian minimum bending on accepted v10 mother. X/Z, crown, back, original eyes/nose/mouth/cheek/chin and all original ears fixed. One candidate, no parameter sweep.','baseline_file':str(base),'baseline_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'mask_file':str(maskpath),'mask_sha256':hashlib.sha256(maskpath.read_bytes()).hexdigest(),'reference':'Mean of v8 central X0/8mm front profiles after applying same 3mm C2 Z lowering; outer v8 forehead never copied. Reference delta softened by 2.2*tanh(.75*delta/2.2), feathered from |X|8 to20.','support':{'z_mm':[34,42,55,64],'lateral_abs_x_mm':[16,24],'front_y_mm':[-10,-2],'core_geodesic_feather_mm':5},'alpha':alpha,'free_vertices':len(free),'protected_core_vertices':int(core.sum()),'protected_ear_vertices':int(ears.sum()),'released_old_forehead_vertices':int(released.sum()),'maximum_displacement_mm':float(move.max()),'released_old_forehead_maximum_mm':float(move[released].max()),'core_maximum_mm':float(move[core].max()),'ear_maximum_mm':float(move[ears].max()),'crown_before_after_z_mm':[float(v[:,2].max()),float(after[:,2].max())],'X_Z_exactly_unchanged':True,'back_y_ge_0_exactly_unchanged':bool(np.array_equal(after[y>=0],v[y>=0])),'outer_abs_x_ge_24_exactly_unchanged':bool(np.array_equal(after[abs(x)>=24],v[abs(x)>=24])),'maximum_abs_x_ge_20_move_mm':float(move[abs(x)>=20].max()),'minimum_normal_dot':float(dot.min()),'normal_rotation_over_90_triangles':int((dot<0).sum()),'degenerate_triangles':int((a1<1e-12).sum()),'mother_surface_sha256':hashlib.sha256((O/'mother-surface.npz').read_bytes()).hexdigest(),'status':'Geometry candidate pending independent self-intersection and actual quarter/side/top review; hollow shell not generated here.'}
(O/'mother-surface-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
