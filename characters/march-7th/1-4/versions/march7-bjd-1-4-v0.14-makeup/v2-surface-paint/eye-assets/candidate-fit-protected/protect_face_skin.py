"""Blender read-only-head adaptation: retract preview-eye skin overlap behind v14.
Only the eye arrays in this directory are written. Main sphere and texture XZ remain.
"""
from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;B=P.parent/'candidate-fit';UV=P.parent.parent.parent/'uv-transfer'/'face-uv-transfer.npz'
d=np.load(B/'hemisphere-eye-geometry.npz');a={k:d[k].copy() for k in d.files};u=np.load(UV)
hv=u['head_vertices'];hf=u['head_triangles'];head=BVHTree.FromPolygons(hv.tolist(),hf.tolist(),all_triangles=True)
# Same source-exterior correspondence independently used by face-color transfer.
front=(u['head_source_outward_visible'])&(u['head_source_distance_mm']<1.0)&(u['head_source_normal_dot']>.25)&(hv[:,1]<-12)
def bary(p,t):
 a,b,c=t;e=b-a;f=c-a;q=p-a;ee=e@e;ef=e@f;ff=f@f;eq=e@q;fq=f@q;den=ee*ff-ef*ef
 if abs(den)<1e-20:return np.array([1.,0,0])
 v=(ff*eq-ef*fq)/den;w=(ee*fq-ef*eq)/den;x=np.clip([1-v-w,v,w],0,1);return x/x.sum()
records=[]
for side in ['negative','positive']:
 v=a['vertices_'+side];f=a['faces_'+side];center=a['center_'+side];n=len(v)//2;delta=np.zeros(n);skin_y=np.full(n,np.nan);hits=np.zeros(n,bool)
 for i,p in enumerate(v[:n]):
  loc,no,ti,dep=head.ray_cast(Vector((p[0],-60,p[2])),Vector((0,1,0)),60+center[1]+1)
  if loc is None or loc.y>=-12:continue
  bc=bary(np.array(loc),hv[hf[ti]])
  if bc@front[hf[ti]].astype(float)<.5:continue
  skin_y[i]=loc.y;hits[i]=True
  delta[i]=max(0,loc.y+.35-p[1])
 # Fill the immediately adjacent spherical facet support; this prevents a face
 # between protected samples from cutting across the painted skin edge.
 outerf=f[np.all(f<n,axis=1)]
 edges=np.unique(np.sort(np.vstack([outerf[:,[0,1]],outerf[:,[1,2]],outerf[:,[2,0]]]),axis=1),axis=0)
 degree=np.bincount(edges.ravel(),minlength=n)
 raw=delta.copy();expanded=delta.copy()
 np.maximum.at(expanded,edges[:,0],delta[edges[:,1]]);np.maximum.at(expanded,edges[:,1],delta[edges[:,0]])
 smooth=expanded.copy()
 for _ in range(5):
  sums=np.zeros(n);np.add.at(sums,edges[:,0],smooth[edges[:,1]]);np.add.at(sums,edges[:,1],smooth[edges[:,0]])
  smooth=np.maximum(expanded,.5*smooth+.5*sums/np.maximum(degree,1))
 after=v.copy();after[:n,1]+=smooth;after[n:,1]+=smooth
 a['vertices_'+side]=after;a['skin_retraction_'+side]=smooth;a['unadapted_vertices_'+side]=v
 # Verify same offset on corresponding inner/outer vertices and no XZ changes.
 assert np.array_equal(after[:,[0,2]],v[:,[0,2]])
 beforefn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
 afterfn=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]])
 dots=np.einsum('ij,ij->i',beforefn,afterfn)
 records.append({'eye':side,'direct_front_skin_samples':int(hits.sum()),'direct_retraction_vertices':int((raw>1e-8).sum()),'expanded_outer_vertices':int((smooth>1e-8).sum()),'paired_inner_vertices_same_delta':True,'maximum_retraction_mm':float(smooth.max()),'mean_nonzero_retraction_mm':float(smooth[smooth>1e-8].mean()) if (smooth>1e-8).any() else 0,'margin_mm':.35,'new_normal_over90_relative_to_initial_sphere':int((dots<0).sum()),'zero_area_faces':int((np.linalg.norm(afterfn,axis=1)<1e-10).sum()),'front_skin_sample_min_y_clearance_mm':float((after[:n,1]-skin_y)[raw>0].min()) if (raw>0).any() else None})
np.savez_compressed(P/'hemisphere-eye-geometry.npz',**a)
for side in ['negative','positive']:shutil.copy2(B/f'march7-hemisphere-eye-{side}.png',P/f'march7-hemisphere-eye-{side}.png')
r=json.loads((B/'eye-assets-report.json').read_text());r['geometry_npz_sha256']=hashlib.sha256((P/'hemisphere-eye-geometry.npz').read_bytes()).hexdigest();r['meshing']['outer_vertices_on_analytic_sphere']=False;r['meshing']['note']='Base spherical cup is locally retracted at the hidden skin edge; nominal R9/8.4 does not assert every final point lies on those spheres.';r['skin_retraction']={'method':'Actual head +Y ray first hit, corresponding to source-visible outer-front face only; eye vertices in front of that skin are retracted behind it by0.35mm, with one-facet expanded support and smooth positive feather. Matching inner cup point receives the same Y displacement.','head_uv_transfer_sha256':hashlib.sha256(UV.read_bytes()).hexdigest(),'records':records,'head_geometry_modified':False,'eye_XZ_coordinates_and_texture_unchanged':True,'note':'Spherical main cup with a small locally adapted hidden edge; not a perfect mathematical hemisphere and not a printable eye fit certificate.'}
(P/'eye-assets-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
s=(B/'build_hemisphere_eyes.py').read_text().replace("'fit_report':'candidate-head-overlap.json','oblique_coverage_report':'../oblique-candidate-comparison-fine.json','fit_note':'Appearance-only R9 adaptation has about31.25mm3 socket-wall overlap per eye; not an installation clearance pass.'", "'fit_report':'eye-assets-report.json','fit_note':'Spherical main cup with local hidden-edge retraction to protect actual head skin; appearance-only, not a physical eye clearance pass.'")
s=s.replace("'cup_wall_mm':.6,", "'cup_wall_mm':.6,'shape':'Spherical main cup with hidden-edge skin retraction','exact_sphere':False,")
s=s.replace("ob['emission_strength']=0.", "ob['emission_strength']=0.;ob['skin_edge_adaptation']='Locally retracted behind v14 front skin by0.35mm; paired inner surface follows'")
(P/'build_hemisphere_eyes.py').write_text(s)
print(json.dumps({'npz_sha256':r['geometry_npz_sha256'],'records':records},ensure_ascii=False),flush=True)
