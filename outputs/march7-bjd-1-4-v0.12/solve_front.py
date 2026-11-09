"""Wide XYZ front-surface fairing; only writes candidate arrays, not models."""
from pathlib import Path
import numpy as np,json,hashlib
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.sparse.csgraph import dijkstra
P=Path(__file__).parent;R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs')
file11=R/'march7-bjd-1-4-v0.11/mother-surface.npz';file10=R/'march7-bjd-1-4-v0.10/mother-surface.npz'
a=np.load(file11);before=a['after'].copy();ref=np.load(file10)['after'].copy();f=a['triangles'];v=ref
m=np.load('/private/tmp/v11-source/v11-forehead-protection.npz');g=np.load(P/'actual-eye-geodesic.npz');eye_d=g['eye_edge_geodesic_mm'];boundary=g['eye_boundary_vertices']
def S(t):
 t=np.clip(t,0,1);return t**3*(t*(6*t-15)+10)
x,y,z=ref.T
# The old 2mm eye band is not the aperture: release upper non-feature skin,
# including closure-overlay skin where safely beyond the real .8mm eyelid ring.
oldcore=m['master_core_locked'];core=oldcore.copy();upper_release=(z>32.5)&(y<-13)&(eye_d>.8)
core[upper_release]=False
for key in ['master_raw_feature_mouth_geodesic_2mm_band','master_raw_feature_nose_roi','master_raw_feature_cheek_roi','master_raw_feature_chin_roi']:
 core|=m[key]
eye_guard=eye_d<=.8;core|=eye_guard
# All low inner eye/bridge and original features remain fixed.
core|=(abs(x)<6)&(z<=32.5)&(y<-15)
ears=m['master_ear_locked']
edges=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
el=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
graph=sparse.coo_matrix((np.r_[el,el],(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
d_core=dijkstra(graph,directed=False,indices=np.flatnonzero(core),min_only=True)
# Front-domain at low Z is strictly separated from the ear agent's support
# (ear stage: Y>-6 and Z<38). The support widens toward the crown without a
# horizontal Z64 shutdown; a small curved apex anchor protects height.
front_low=1-S((y+12)/4)
front_wide=1-S((y-2)/12)
front_support=front_low+(front_wide-front_low)*S((z-38)/8)
w=S(d_core/2.)*S((eye_d-.8)/3.2)*S((z-30)/3)*front_support
apex=int(np.argmax(z));apex_r=np.linalg.norm(v-v[apex],axis=1);apex_anchor=apex_r<.8
protected=core|ears|apex_anchor;w[protected]=0;free=np.flatnonzero(w>1e-5);fixed=w<=1e-5
A,B,C=v[f[:,0]],v[f[:,1]],v[f[:,2]];area2=np.linalg.norm(np.cross(B-A,C-A),axis=1)
cots=np.column_stack([np.einsum('ij,ij->i',B-A,C-A),np.einsum('ij,ij->i',C-B,A-B),np.einsum('ij,ij->i',A-C,B-C)])/np.maximum(area2[:,None],1e-12)
i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]]);dd=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
W=sparse.coo_matrix((np.r_[dd,dd],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free];Bend=(LF.T@sparse.diags(1/mass)@LF).tocsc()
# A smooth near-apex positional prior preserves the accepted rounded cap,
# while avoiding an entire fixed horizontal cap band.
alpha=.01+2*(1-S((apex_r-1)/6))
prior=alpha[free]*mass[free]/np.maximum(w[free],.03)**2
u=spsolve(Bend+sparse.diags(prior),-(LF.T@((L@v)/mass[:,None])))
after=v.copy();after[free]+=u
# Fixed values are the accepted v11 positions (these agree with v10 wherever
# w is zero); preserve exact inputs rather than inventing rounding tolerances.
after[fixed]=before[fixed]
move=np.linalg.norm(after-before,axis=1);refmove=np.linalg.norm(after-ref,axis=1)
n0=np.cross(before[f[:,1]]-before[f[:,0]],before[f[:,2]]-before[f[:,0]]);n1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]]);ar0=np.linalg.norm(n0,axis=1);ar1=np.linalg.norm(n1,axis=1);dot=np.einsum('ij,ij->i',n0,n1)/np.maximum(ar0*ar1,1e-30)
changed=move>1e-10;released=oldcore&~core
assert np.array_equal(after[core|ears],before[core|ears])
assert not np.any(changed&(before[:,1]>-6)&(before[:,2]<38))
np.savez_compressed(P/'front-solution.npz',before=before,baseline=before,reference_v10=ref,control=ref,after=after,vertices=after,triangles=f,protected=protected,locked=fixed,core_locked=core,ear_body_locked=ears,ear_locked=ears,front_free=~fixed,changed=changed,eye_guard=eye_guard,eye_boundary_vertices=boundary,eye_distance_mm=eye_d,released_upper_eye_skin=released,apex_anchor=apex_anchor,weights=w)
report={'method':'Wide full-XYZ cotangent bi-Laplacian fairing of v10 low-frequency reference, evaluated as delta from v11. This removes the v11 localized Y bulge, frees the actual outer-brow horn region, and allows the entire front crown to adjust instead of stopping at a Z64 plane.','reference_v10_sha256':hashlib.sha256(file10.read_bytes()).hexdigest(),'baseline_v11_sha256':hashlib.sha256(file11.read_bytes()).hexdigest(),'prior_base_alpha':.01,'eye_protection':'Actual 248-vertex opening boundary and its .8mm surface-geodesic eyelid ring fixed. Upper non-feature skin beyond this is released; nose/mouth/cheek/chin masks remain fixed.','protected_core_count':int(core.sum()),'released_old_core_upper_eye_skin_count':int(released.sum()),'apex_anchor_count':int(apex_anchor.sum()),'apex_anchor_radius_mm':.8,'near_apex_soft_prior_radius_mm':7.,'free_vertices':len(free),'maximum_move_from_v11_mm':float(move.max()),'maximum_fairing_move_from_v10_mm':float(refmove.max()),'released_upper_eye_skin_maximum_move_mm':float(move[released].max()) if released.any() else 0.,'eye_boundary_maximum_move_mm':float(move[boundary].max()),'eye_guard_maximum_move_mm':float(move[eye_guard].max()),'ear_maximum_move_mm':float(move[ears].max()),'core_maximum_move_mm':float(move[core].max()),'crown_before_after_z_mm':[float(before[:,2].max()),float(after[:,2].max())],'before_bounds_mm':[before.min(0).tolist(),before.max(0).tolist()],'after_bounds_mm':[after.min(0).tolist(),after.max(0).tolist()],'changed_support_bounds_mm':[before[changed].min(0).tolist(),before[changed].max(0).tolist()],'ear_support_overlap_vertices':int(np.sum(changed&(before[:,1]>-6)&(before[:,2]<38))),'normal_rotations_over90':int((dot<0).sum()),'minimum_normal_dot':float(dot.min()),'degenerate_triangles':int((ar1<1e-12).sum()),'horn_vertex_changes':{str(k):{'before':before[k].tolist(),'after':after[k].tolist(),'delta':(after[k]-before[k]).tolist(),'weight':float(w[k])} for k in [113,17599,80,9049]},'front_solution_sha256':hashlib.sha256((P/'front-solution.npz').read_bytes()).hexdigest(),'status':'One render candidate; independent intersections and close visual review required before combining with separate ear solution.'}
(P/'front-solution-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
