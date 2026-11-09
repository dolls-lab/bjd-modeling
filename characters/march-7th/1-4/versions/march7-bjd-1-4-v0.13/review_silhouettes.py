"""Orthographic exterior-outline comparison on actual assembled binary STLs."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_fill_holes,binary_erosion,distance_transform_edt
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;OLD=P.parent/'march7-bjd-1-4-v0.12'
ap=argparse.ArgumentParser();ap.add_argument('--expected-head-sha256',required=True);ap.add_argument('--expected-cap-sha256',required=True);ap.add_argument('--pitch',type=float,default=.05);args=ap.parse_args()
paths={ver:{part:root/f'march7-head-{label}-{ver}-draft.stl' for part,label in [('head','shell'),('cap','cap')]} for ver,root in [('v0.12',OLD),('v0.13',P)]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={ver:{k:sha(p) for k,p in pp.items()} for ver,pp in paths.items()}
assert hashes['v0.13']['head']==args.expected_head_sha256 and hashes['v0.13']['cap']==args.expected_cap_sha256
assert hashes['v0.12']['cap']==hashes['v0.13']['cap'],'Cap should be byte-identical for surface-only v13'
def stl(p):
 b=p.read_bytes();n=int.from_bytes(b[80:84],'little');assert len(b)==84+n*50
 dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);return np.frombuffer(b,dtype=dt,offset=84,count=n)['vertices'].astype(float)
tri={v:np.concatenate([stl(p) for p in pp.values()]) for v,pp in paths.items()}
views={'front':(0,-1,0),'left':(-1,0,0),'right':(1,0,0),'front_left':(-1,-1,.25),'front_right':(1,-1,.25),'rear':(0,1,0),'rear_left':(-1,1,.25),'rear_right':(1,1,.25),'top':(0,0,1)}
rows={};fig,axs=plt.subplots(3,3,figsize=(13,13),constrained_layout=True)
for ax,(name,direction) in zip(axs.flat,views.items()):
 n=np.array(direction,float);n/=np.linalg.norm(n);up=np.array([0,0,1.] if name!='top' else [0,1.,0]);u=np.cross(up,n);u/=np.linalg.norm(u);v=np.cross(n,u)
 pt={ver:np.stack([q@u,q@v],axis=-1) for ver,q in tri.items()};lo=np.min([q.min((0,1)) for q in pt.values()],axis=0)-.2;hi=np.max([q.max((0,1)) for q in pt.values()],axis=0)+.2;shape=np.ceil((hi-lo)/args.pitch).astype(int)+1
 masks={}
 for ver,q in pt.items():
  xy=(q-lo)/args.pitch;a2=xy[:,1]-xy[:,0];b2=xy[:,2]-xy[:,0];area=a2[:,0]*b2[:,1]-a2[:,1]*b2[:,0];im=Image.new('1',tuple(shape));draw=ImageDraw.Draw(im)
  for t in xy[abs(area)>1e-12]:draw.polygon(tuple(map(tuple,t)),fill=1)
  masks[ver]=binary_fill_holes(np.array(im,dtype=bool))
 a,b=masks.values();ba=a&~binary_erosion(a);bb=b&~binary_erosion(b);delta=a^b
 distances=np.r_[distance_transform_edt(~bb)[ba],distance_transform_edt(~ba)[bb]]*args.pitch
 row={'sample_pitch_mm':args.pitch,'baseline_area_mm2':float(a.sum()*args.pitch**2),'current_area_mm2':float(b.sum()*args.pitch**2),'symmetric_difference_area_mm2':float(delta.sum()*args.pitch**2),'intersection_over_union':float((a&b).sum()/(a|b).sum()),'maximum_raster_boundary_distance_mm':float(distances.max()),'p95_raster_boundary_distance_mm':float(np.percentile(distances,95)),'identical_at_sampled_pitch':bool(np.array_equal(a,b)),'view_toward_camera':n.tolist()};rows[name]=row
 rgb=np.full((*a.shape,3),255,np.uint8);rgb[a&b]=[210,210,210];rgb[a&~b]=[220,40,110];rgb[b&~a]=[0,150,175];rgb[ba&bb]=[70,70,70];ax.imshow(rgb,origin='lower',extent=[lo[0],hi[0],lo[1],hi[1]]);ax.set(title=f'{name}: max outline delta {distances.max():.3f} mm',xlabel='projected mm',ylabel='projected mm');ax.set_aspect('equal')
 print(name,row,flush=True)
assert all(sha(p)==hashes[v][k] for v,pp in paths.items() for k,p in pp.items())
r={'baseline':'v0.12','current':'v0.13','inputs':{v:{k:{'path':str(p),'sha256':hashes[v][k]} for k,p in pp.items()} for v,pp in paths.items()},'method':'Project every actual assembled head/cap STL triangle into each orthographic plane, union rasterized projected material, then fill internal projection holes to measure only the outside silhouette. Compare both exterior raster boundaries by symmetric Euclidean distance. No convex-hull replacement.','limitations':'Raster comparison has approximately one-pixel uncertainty per edge (up to2*pitch in a difference). Interior facial detail and eye holes are not certified by exterior silhouettes; independent eye projection and protected-coordinate tests cover them. This is nine sampled views, not every possible viewpoint.','sample_pitch_mm':args.pitch,'boundary_difference_resolution_bound_mm':2*args.pitch,'views':rows,'all_inputs_unchanged':True,'maximum_sampled_view_boundary_distance_mm':max(a['maximum_raster_boundary_distance_mm'] for a in rows.values())}
(P/'silhouette-review.json').write_text(json.dumps(r,indent=2)+'\n');fig.suptitle('v12 → v13 actual assembled outer outlines; pink removed / teal added');fig.savefig(P/'silhouette-review.png',dpi=150)
