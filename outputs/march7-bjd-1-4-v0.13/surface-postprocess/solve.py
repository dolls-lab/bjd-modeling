"""Constrained actual-print temple skin fairing; output arrays only."""
from pathlib import Path
import sys,json,hashlib,heapq
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve,splu
O=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent
p=O/'print-protection.npz';d=np.load(p);v=d['before'];f=d['triangles'];w=d['weights'].copy();initial=d['free']
rim=d['rim_weight'] if 'rim_weight' in d else np.zeros(len(v))
# Feather against the actual printable patch border, including any hole in
# semantic projection, so a missing nearest-source label cannot become a step.
edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
boundary=np.zeros(len(v),bool);ee=edges[initial[edges[:,0]]!=initial[edges[:,1]]];boundary[ee[initial[ee]]]=True
adj={int(i):[] for i in np.flatnonzero(initial)}
for a,b in edges[initial[edges].all(1)]:
 ll=float(np.linalg.norm(v[a]-v[b]));adj[int(a)].append((int(b),ll));adj[int(b)].append((int(a),ll))
dist=np.full(len(v),np.inf);dist[boundary]=0.;queue=[(0.,int(i)) for i in np.flatnonzero(boundary)];heapq.heapify(queue)
while queue:
 di,i=heapq.heappop(queue)
 if di>dist[i]+1e-12:continue
 for j,ll in adj[i]:
  nd=di+ll
  if nd<dist[j] and nd<.7:dist[j]=nd;heapq.heappush(queue,(nd,j))
t=np.clip(dist/.7,0,1);w*=t*t*t*(10+t*(-15+6*t));w[~initial]=0.;free=np.flatnonzero(w>1e-5)
a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];n0=np.cross(b-a,c-a);area2=np.linalg.norm(n0,axis=1)
co=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
ii=np.concatenate([f[:,1],f[:,2],f[:,0]]);jj=np.concatenate([f[:,2],f[:,0],f[:,1]]);dd=.5*np.concatenate([co[:,0],co[:,1],co[:,2]])
W=sparse.coo_matrix((np.r_[dd,dd],(np.r_[ii,jj],np.r_[jj,ii])),shape=(len(v),len(v))).tocsr();L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9);LF=L[:,free]
B=(LF.T@sparse.diags(1/mass)@LF).tocsc();rhs=-(LF.T@((L@v)/mass[:,None]));trials=[]
local=np.full(len(v),-1,int);local[free]=np.arange(len(free))
def orient_constrained(C,u0):
 # A small active set prevents the few tiny print triangles at the groove
 # from turning over, without weakening the whole smoothing field.
 lu=splu(C);u=u0.copy();active=set();history=[]
 for iteration in range(12):
  q=v.copy();q[free]+=u
  nn=np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]])
  ratio=np.einsum('ij,ij->i',n0,nn)/np.maximum(area2*area2,1e-24)
  bad=np.flatnonzero(ratio<.25)
  history.append({'iteration':iteration,'below_quarter_projected_area':len(bad),'minimum_projected_area_ratio':float(ratio.min())})
  if not len(bad):return u,history,True
  active.update(map(int,bad));tt=np.array(sorted(active),int);jj=f[tt]
  g=np.stack([np.cross(q[jj[:,1]]-q[jj[:,2]],n0[tt]),np.cross(q[jj[:,2]]-q[jj[:,0]],n0[tt]),np.cross(q[jj[:,0]]-q[jj[:,1]],n0[tt])],axis=1)
  g/=np.maximum(area2[tt,None,None]**2,1e-24)
  row=np.repeat(np.arange(len(tt)),3);col=local[jj.ravel()];ok=col>=0;Gs=[];Zs=[]
  for axis in range(3):
   G=sparse.coo_matrix((g[:,:,axis].ravel()[ok],(row[ok],col[ok])),shape=(len(tt),len(free))).tocsr();Gs.append(G);Zs.append(lu.solve(G.T.toarray()))
  desired=.35-ratio[tt]+sum(Gs[k]@u[:,k] for k in range(3))
  Schur=sum(Gs[k]@Zs[k] for k in range(3));residual=desired-sum(Gs[k]@u0[:,k] for k in range(3))
  lam=np.linalg.lstsq(Schur,residual,rcond=1e-12)[0]
  u=u0+np.column_stack([Zs[k]@lam for k in range(3)])
 return u,history,False
for alpha in [.1,.3,1,3,10,30,100,300,1000,3000]:
 prior=alpha*mass[free]*(1+7*rim[free])/np.maximum(w[free],.01)**2
 C=(B+sparse.diags(prior)).tocsc();u=spsolve(C,rhs);length=np.linalg.norm(u,axis=1);orientation_history=[];orientation_success=False
 if length.max()<=.45:
  u,orientation_history,orientation_success=orient_constrained(C,u);length=np.linalg.norm(u,axis=1)
 after=v.copy();after[free]+=u
 n1=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]])
 dot=np.einsum('ij,ij->i',n0,n1)/np.maximum(area2*np.linalg.norm(n1,axis=1),1e-30)
 rim_max=float(length[rim[free]>.5].max()) if np.any(rim[free]>.5) else 0.
 flips=int((dot<0).sum());rec={'alpha':alpha,'max_mm':float(length.max()),'rim_max_mm':rim_max,'p95_mm':float(np.percentile(length,95)),'normal_over_90_count':flips,'orientation_constraints':orientation_history};trials.append(rec);print(rec,flush=True)
 if length.max()<=.45 and rim_max<=.17 and flips==0 and orientation_success:break
else:raise RuntimeError('No safe bounded print fairing candidate')
delta=after-v;move=np.linalg.norm(delta,axis=1);locked=np.ones(len(v),bool);locked[free]=False
assert np.array_equal(after[locked],v[locked])

extras={k:d[k] for k in ['outer_skin_support','inner_wall_locked','major_features_locked','ear_locked','eye_guard','eye_distance_mm','nearest_mother_distance_mm']}
np.savez_compressed(O/'print-solution.npz',before=v,after=after,triangles=f,free=~locked,locked=locked,weights=w,delta=delta,region_class=d['region_class'],rim_weight=rim,baseline_blend=d['baseline_blend'],baseline_blend_sha256=d['baseline_blend_sha256'],**extras)
# Global support function bounds quantify overall head envelope, not merely XYZ extents.
dirs=[]
for el in np.linspace(-90,90,19):
 for az in np.linspace(0,360,73)[:-1]:
  e=np.deg2rad(el);a=np.deg2rad(az);dirs.append([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
dirs=np.array(dirs);env=[]
for dr in dirs:env.append(float((after@dr).max()-(v@dr).max()))
r={'baseline_blend':str(d['baseline_blend']),'baseline_blend_sha256':str(d['baseline_blend_sha256']),'method':'Local actual-print temple skin fairing only, cotangent minimum bending + position prior; broad C2 domain and 0.7 mm mesh-border feather; small active-set projected area constraints, no clipping/remesh','free_vertices':len(free),'trials':trials,'selected':trials[-1],'maximum_displacement_mm':float(move.max()),'mean_displacement_mm':float(move[~locked].mean()),'p95_displacement_mm':float(np.percentile(move[~locked],95)),'normal_over_90_count':int((dot<0).sum()),'minimum_normal_dot':float(dot.min()),'outside_support_exactly_unchanged':bool(np.array_equal(v[locked],after[locked])),'ear_exactly_unchanged':bool(np.array_equal(v[extras['ear_locked']],after[extras['ear_locked']])),'eye_guard_exactly_unchanged':bool(np.array_equal(v[extras['eye_guard']],after[extras['eye_guard']])),'inner_wall_exactly_unchanged':bool(np.array_equal(v[extras['inner_wall_locked']],after[extras['inner_wall_locked']])),'envelope_direction_count':len(dirs),'maximum_global_support_change_mm':float(np.abs(env).max()),'before_bounds_mm':np.ptp(v,axis=0).tolist(),'after_bounds_mm':np.ptp(after,axis=0).tolist(),'solution_sha256':hashlib.sha256((O/'print-solution.npz').read_bytes()).hexdigest()}
(O/'print-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
