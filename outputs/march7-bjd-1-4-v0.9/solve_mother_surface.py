"""One continuous v9 outer mother surface; no cap or inherited cap constraints.
The existing source-face/ear topology is retained as an editable starting mesh.
A globally rounded low-frequency prior is fitted by constrained XYZ fairing.
This file writes arrays only, never changes a delivered Blender/STL model.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.6');OUT=Path(__file__).resolve().parent
p=np.load(R/'v6-side-protection.npz');v=p['master_baseline_vertices'].copy();f=p['master_baseline_triangles'].copy()
maskpath=Path('/private/tmp/v9-source/v9-central-source-protection.npz');m=np.load(maskpath)
core=m['master_core_locked'];ears=m['master_ear_body_locked'];source_soft=m['master_source_transition'];earroot=m['master_ear_root_transition'];w=m['master_combined_weight_10mm'].copy();protected=core|ears
w[protected]=0;free=np.flatnonzero(w>1e-5);fixed=np.flatnonzero(w<=1e-5)
# Fits existing overall size: crown Z72.8 and back pole Y30.5, approximately
# the current head limits. The entire rear/crown receives one target surface.
center=np.array([0.,0.,37.]);radii=np.array([27.,30.5,35.8])
direction=v-center;ellipsoid_target=center+direction/np.sqrt(np.sum((direction/radii)**2,axis=1))[:,None]
unit=(ellipsoid_target-center)/radii
# Smooth asymmetric egg parameterization: no piecewise equatorial join.
# qz=-1 => Z11.2, qz=0 => Z37, qz=+1 => Z72.8.
ellipsoid_target[:,2]=37.+30.8*unit[:,2]+5.*unit[:,2]**2
# Smoothly carry lower cranium towards the established neck axis Y~6.6.
ellipsoid_target[:,1]+=6.*np.maximum(-unit[:,2],0.)**3
target_delta=ellipsoid_target-v
# A bounded reference for the non-core original forehead/temple prevents the
# skull reference from overwriting the character facial sculpt. This is a prior,
# not a post-solve pointwise clipping operation.
length=np.linalg.norm(target_delta,axis=1)
qz=np.clip((v[:,2]-34.)/13.,0,1);upper_release=qz*qz*qz*(qz*(qz*6-15)+10)
factor=np.minimum(1,1.8/np.maximum(length,1e-12))
factor=1+(factor-1)*(1-upper_release)
target_delta[source_soft]*=factor[source_soft,None]
ear_distance=m['master_ear_body_geodesic_mm']; q=np.clip((ear_distance-1.)/5.,0,1); earfade=q*q*q*(q*(q*6-15)+10)
target_delta*=earfade[:,None]
target_delta[protected]=0
target=v+w[:,None]*target_delta

a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];area2=np.linalg.norm(np.cross(b-a,c-a),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);d=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[d,d],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free];C=(LF.T@sparse.diags(1/mass)@LF).tocsc();bend_rhs=-(LF.T@((earfade[:,None]*(L@v))/mass[:,None]))
print('mother free',len(free),'matrix',C.shape,C.nnz,flush=True)
trials=[];chosen=None
for source_alpha,ear_alpha in [(10.,100.),(30.,300.)]:
 alpha=np.full(len(v),.1);alpha[source_soft]=.1+(source_alpha-.1)*(1-upper_release[source_soft]);alpha[earroot]=ear_alpha
 prior=alpha[free]*mass[free]/np.maximum(w[free],.01)**2
 u=spsolve(C+sparse.diags(prior),bend_rhs+prior[:,None]*(target[free]-v[free]));after=v.copy();after[free]+=u
 dist=np.linalg.norm(after-v,axis=1)
 row={'source_prior_alpha':source_alpha,'ear_root_prior_alpha':ear_alpha,'added_prior_alpha':.1,'maximum_displacement_mm':float(dist.max()),'source_transition_max_mm':float(dist[source_soft].max()),'lower_source_transition_max_mm':float(dist[source_soft&(v[:,2]<=34)].max()),'upper_source_transition_max_mm':float(dist[source_soft&(v[:,2]>=47)].max()),'ear_root_max_mm':float(dist[earroot].max()),'core_max_mm':float(dist[core].max()),'ear_body_max_mm':float(dist[ears].max())};trials.append(row);print(row,flush=True)
 if row['lower_source_transition_max_mm']<=2.0 and row['ear_root_max_mm']<=.3:
  chosen=after;break
if chosen is None:raise RuntimeError('No source/ear bounded mother solution')
after=chosen;assert np.array_equal(after[protected],v[protected])
c0=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);c1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]]);a0=np.linalg.norm(c0,axis=1);a1=np.linalg.norm(c1,axis=1);dot=np.einsum('ij,ij->i',c0,c1)/np.maximum(a0*a1,1e-30)
np.savez_compressed(OUT/'mother-surface.npz',baseline=v,before=v,control=target,target=target,after=after,vertices=after,triangles=f,protected=protected,locked=np.isin(np.arange(len(v)),fixed),core_locked=core,ear_body_locked=ears,source_transition=source_soft,ear_root_transition=earroot,weights=w,upper_forehead_release=upper_release,position_alpha=alpha,center_mm=center,radii_mm=radii)
report={'upper_forehead_policy':'Non-core original forehead above Z47 has same unrestricted target and alpha0.1 as added cranium; C2 release Z34..47. Low ear-root equations remain exactly those of intersection-safe candidate3, avoiding unrelated low-region changes.', 'ear_safety':'Original Laplacian differential geometry retained near ear and C2 blended to zero over true earbody geodesic 1..6mm; prior displacement uses same continuous factor. This preserves legitimate thin folded ear-root anatomy while fairing the full cranium.', 'method':'One complete outer mother surface on v5 source topology; constrained XYZ cotangent bi-Laplacian with a globally rounded ellipsoid reference. There is no inherited cap, seam, magnet or old-neck constraint in this shape solve. Mechanical features must be rebuilt after hollowing and resplitting.','units':'mm','baseline':'v5 complete outer master, 45548 vertices','low_frequency_prior':{'center_mm':center.tolist(),'radii_mm':radii.tolist(),'asymmetric_z_mapping':'Z=37+30.8*qz+5*qz^2; upper pole72.8/lower pole11.2; no equatorial derivative break','lower_axis_mapping':'Y adds 6*max(-qz,0)^3 to carry lower pole to neck axis Y6','choice':'Retain approximately original crown and rear extent; introduce one smooth complete rear/crown shape. It is a position prior, not a hard projected final surface.','crown_z_mm':float(center[2]+radii[2]),'rear_y_mm':float(center[1]+radii[1])},'source_control':'Raw feature/central-face core exactly locked. Non-core source forehead/temples use a 1.8mm target only in lower transition region, smoothly removed from Z34 to47; above47 no source cap or category-specific prior; lower source actual<=2mm. Ear bodies exactly locked, roots allowed <=0.3mm. True graph-distance 10mm source collars and 3mm ear collars.','mask_file':str(maskpath),'mask_sha256':hashlib.sha256(maskpath.read_bytes()).hexdigest(),'free_vertices':len(free),'protected_vertices':int(protected.sum()),'trials':trials,'selected':trials[-1],'baseline_bounds_mm':[v.min(0).tolist(),v.max(0).tolist()],'after_bounds_mm':[after.min(0).tolist(),after.max(0).tolist()],'triangles_normal_rotation_over_90':int((dot<0).sum()),'minimum_normal_dot':float(dot.min()),'degenerate_triangles':int((a1<1e-12).sum()),'mother_surface_sha256':hashlib.sha256((OUT/'mother-surface.npz').read_bytes()).hexdigest(),'status':'First complete outer-surface render candidate. Eye openings and source core are retained; shell thickness, new cap and round mechanical holes are not generated by this script.'}
(OUT/'mother-surface-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
