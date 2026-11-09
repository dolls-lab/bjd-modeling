from pathlib import Path
import json,hashlib,time
import numpy as np,trimesh,manifold3d as md
from scipy.ndimage import gaussian_filter1d
P=Path(__file__).parent;O=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs');base=np.load(P.parent/'baseline.npz');v=base['head_vertices'].copy();f=base['head_triangles'];before=v.copy();orig=json.loads((O/'march7-bjd-1-4-v0.13-original-review/eye-original-comparison.json').read_text());meta=json.loads((O/'march7-bjd-1-4-v0.13/build-report.json').read_text())
mesh=trimesh.Trimesh(v,f,process=False);solid=md.Manifold(md.Mesh64(np.ascontiguousarray(v),np.ascontiguousarray(f,dtype=np.uint64)));assert solid.status()==md.Error.NoError
loops=[np.array(q['vertices_xyz_mm']) for q in orig['raw_face_boundary_loops'] if q['vertex_count']==31];loops.sort(key=lambda q:q[:,0].mean());angles=np.arange(720)*2*np.pi/720;dirs=np.column_stack([np.cos(angles),np.sin(angles)]);rel=np.arange(-.6,3.401,.2);grids=[];allweights=np.zeros(len(v));rows=[]
def S(t):t=np.clip(t,0,1);return t**3*(t*(6*t-15)+10)
def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
def periodic(a,theta):
 t=(theta%(2*np.pi))*len(a)/(2*np.pi);j=np.floor(t).astype(int);q=t-j;return a[j%len(a)]*(1-q)+a[(j+1)%len(a)]*q
def limit(c,u,hi,yend):
 # A partial-depth eye wall is a narrow annulus: a distant radial endpoint
 # may be outside skin and clear again. Find the FIRST obstruction, not an
 # assumed monotone whole interval ending at r_target+2.
 lo=0.;found=False
 for probe in np.arange(.2,hi+.20001,.2):
  probe=min(float(probe),hi);q=c+probe*u
  if solid.ray_cast((q[0],-40,q[1]),(q[0],yend,q[1])):hi=probe;found=True;break
  lo=probe
 if not found:return hi
 for _ in range(13):
  r=(lo+hi)/2;q=c+r*u
  if solid.ray_cast((q[0],-40,q[1]),(q[0],yend,q[1])):hi=r
  else:lo=r
 return (lo+hi)/2
for eye,loop in enumerate(loops):
 xz=loop[:,[0,2]];cr=cross(xz,np.roll(xz,-1,axis=0));center=((xz+np.roll(xz,-1,axis=0))*cr[:,None]).sum(0)/(3*cr.sum());target=[];rawy=[]
 for u in dirs:
  candidates=[]
  for a,b in zip(loop,np.roll(loop,-1,axis=0)):
   edge=b[[0,2]]-a[[0,2]];den=cross(u,edge)
   if abs(den)<1e-14:continue
   r=cross(a[[0,2]]-center,edge)/den;t=cross(a[[0,2]]-center,u)/den
   if r>0 and -.00001<=t<=1.00001:candidates.append((r,a[1]+t*(b[1]-a[1])))
  r,y=min(candidates);target.append(r);rawy.append(y)
 target=np.array(target);rawy=np.array(rawy);current=np.array([limit(center,u,r+2,-13.289332231246028) for u,r in zip(dirs,target)]);delta=target-current
 # For enlargement, measure the constriction as it appears with depth.
 # Front skin already outside the original opening receives no enlargement;
 # only the rounded rim/throat blocking the raw target gets the required flare.
 flare=np.zeros((len(angles),len(rel)))
 for j,(u,r,y) in enumerate(zip(dirs,target,rawy)):
  if delta[j]<=0:continue
  for k,rr in enumerate(rel):flare[j,k]=max(0,r-limit(center,u,r+2,y+rr))
 flare=gaussian_filter1d(flare,.65,axis=0,mode='wrap');flare=gaussian_filter1d(flare,.5,axis=1,mode='nearest')
 p=v[:,[0,2]]-center;rad=np.linalg.norm(p,axis=1);theta=np.arctan2(p[:,1],p[:,0]);rnow=periodic(current,theta);rgoal=periodic(target,theta);yraw=periodic(rawy,theta);da=rgoal-rnow
 t=(theta%(2*np.pi))*len(angles)/(2*np.pi);j=np.floor(t).astype(int);q=t-j;frows=flare[j%len(angles)]*(1-q[:,None])+flare[(j+1)%len(angles)]*q[:,None]
 yr=(v[:,1]-yraw-rel[0])/(rel[1]-rel[0]);k=np.floor(np.clip(yr,0,len(rel)-1.00000001)).astype(int);b=np.clip(yr,0,len(rel)-1.00000001)-k;enlarge=frows[np.arange(len(v)),k]*(1-b)+frows[np.arange(len(v)),k+1]*b
 enlarge*=S((v[:,1]-yraw+.8)/.2)
 shrink=np.minimum(da,0)*S((v[:,1]-yraw+1.2)/.6)*(1-S((v[:,1]-yraw-1)/2.5))
 # Radius-band mapping is constant across the rim, then C2 fades to the accepted
 # skin. Cavity enlargement cannot intrude into the eye sphere; inward shaping
 # fades out before the deep seat.
 weight=(1-S((abs(rad-rnow)-.75)/1.75))*(1-S((v[:,1]+17)/3.7))*S((abs(v[:,0])-5)/1.)
 weight*=S((v[:,2]-19)/1.5)*(1-S((v[:,2]-35.5)/1.5))
 shift=(enlarge+shrink)*weight;shift[rad<1e-5]=0
 v[:,0]+=p[:,0]/np.maximum(rad,1e-12)*shift;v[:,2]+=p[:,1]/np.maximum(rad,1e-12)*shift
 allweights=np.maximum(allweights,weight*(abs(enlarge+shrink)>1e-12));grids.append(dict(center=center,target=target,current=current,rawy=rawy,flare=flare,delta=delta))
 rows.append({'eye':eye,'original_polygon_center_xz_mm':center.tolist(),'target_minus_v13_effective_radius_range_mm':[float(delta.min()),float(delta.max())],'maximum_local_radial_shift_mm':float(abs(shift).max())});print('eye',eye,rows[-1],flush=True)
move=np.linalg.norm(v-before,axis=1);n0=np.cross(before[f[:,1]]-before[f[:,0]],before[f[:,2]]-before[f[:,0]]);n1=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);a0=np.linalg.norm(n0,axis=1);a1=np.linalg.norm(n1,axis=1);dot=np.einsum('ij,ij->i',n0,n1)/np.maximum(a0*a1,1e-30);changed=move>1e-10
np.savez_compressed(P/'eye-solution.npz',before=before,after=v,triangles=f,free=changed,locked=~changed,weights=allweights,original_eye_loops=np.stack(loops),angles=angles,relative_depth_grid_mm=rel,center_xz=np.stack([g['center'] for g in grids]),target_radii=np.stack([g['target'] for g in grids]),v13_effective_radii=np.stack([g['current'] for g in grids]),raw_rim_y=np.stack([g['rawy'] for g in grids]),depth_flare=np.stack([g['flare'] for g in grids]))
trimesh.Trimesh(v,f,process=False).export(P/'eye-candidate.stl')
r={'method':'Local depth-aware radial XZ warp. Original PMX31-point aperture polygon gives target. Rounded rim/throat enlargement is measured cumulatively by actual solid ray tests versus raw rim depth; the already adequate front skin is not blindly widened. Upper/lower oversized aperture receives small inward shaping. Continuous compact C2 radial/depth support, Y fixed, no remeshing.','baseline':'v13 actual saved Blend head','rows':rows,'changed_vertices':int(changed.sum()),'maximum_displacement_mm':float(move.max()),'changed_bounds_mm':[before[changed].min(0).tolist(),before[changed].max(0).tolist()],'Y_exact':bool(np.array_equal(before[:,1],v[:,1])),'Z50_and_above_exact':bool(np.array_equal(before[before[:,2]>=50],v[before[:,2]>=50])),'normal_over90':int((dot<0).sum()),'minimum_normal_dot':float(dot.min()),'degenerate_triangles':int((a1<1e-12).sum()),'minimum_triangle_area_ratio':float((a1/a0).min()),'solution_sha256':hashlib.sha256((P/'eye-solution.npz').read_bytes()).hexdigest(),'candidate_stl_sha256':hashlib.sha256((P/'eye-candidate.stl').read_bytes()).hexdigest()}
(P/'eye-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
