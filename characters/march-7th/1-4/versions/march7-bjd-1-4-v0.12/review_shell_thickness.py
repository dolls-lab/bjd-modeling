"""Read-only actual STL wall samples, independent of mother/head vertex indexing."""
from pathlib import Path
import json,hashlib,argparse
import numpy as np,trimesh,manifold3d as md
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
OUT=Path(__file__).parent
paths={k:OUT/f'march7-head-{s}-v0.12-draft.stl' for k,s in [('head','shell'),('cap','cap')]}
ap=argparse.ArgumentParser();ap.add_argument('--expected-head-sha256',required=True);ap.add_argument('--expected-cap-sha256',required=True);args=ap.parse_args()
sha={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()}
assert sha['head']==args.expected_head_sha256 and sha['cap']==args.expected_cap_sha256,'Expected SHA mismatch; refusing wrong version'
r=json.loads((OUT/'build-report.json').read_text());N=np.array(r['cap_plane_normal']);C=np.array(r['cap_plane_origin_mm']);magnets=np.array(r['magnet_centers_mm']);pin=np.array(r['rear_pin_center_mm'])
solids={}
for k,p in paths.items():
 t=trimesh.load_mesh(p,process=True,validate=False)
 s=md.Manifold(md.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)))
 assert s.status()==md.Error.NoError,(k,s.status());solids[k]=s
print('solids loaded',flush=True)
def hits(s,start,end):
 q=[]
 for h in s.ray_cast(start,end):
  if not q or np.linalg.norm(np.asarray(h.position)-np.asarray(q[-1].position))>1e-5:q.append(h)
 return q
def normal_thickness(s,h):
 p=np.array(h.position);n=np.array(h.normal);n/=np.linalg.norm(n)
 q=hits(s,p+.15*n,p-18*n)
 if len(q)<2:return None
 # Require start surface agreement and an opposite-facing inner surface.
 if np.linalg.norm(np.array(q[0].position)-p)>.3:return None
 return {'normal_ray_mm':float(np.linalg.norm(np.array(q[1].position)-np.array(q[0].position))),'entry_point_mm':p.tolist(),'entry_normal':n.tolist(),'exit_point_mm':list(q[1].position),'exit_normal_dot_entry':float(np.dot(q[1].normal,n)),'normal_ray_hits':len(q)}
def ordinary(p):
 p=np.asarray(p)
 if abs(np.dot(p-C,N))<3:return False
 if np.min(np.linalg.norm(magnets-p,axis=1))<7:return False
 if np.linalg.norm(pin-p)<7:return False
 return bool((p[1]>3 and p[2]>22) or p[2]>47)
rows=[]
# Circumferential sampling covers forehead, top side wall and new cap.
for k,s in solids.items():
 for z in np.arange(18.,69.01,1.):
  for theta in np.arange(0.,360.,5.):
   a=np.deg2rad(theta);q=hits(s,[60*np.cos(a),60*np.sin(a),z],[0,0,z])
   if len(q)<2:continue
   h=q[0]
   if not ordinary(h.position):continue
   v=normal_thickness(s,h)
   if v is not None:
    v.update(part=k,region='ordinary_cranium',sample_z_mm=float(z),sample_angle_deg=float(theta));rows.append(v)
print('radial samples',len(rows),flush=True)
# Around the ear select the innermost paired material interval so a detached
# outer pinna segment is not mistaken for shell wall.
for sign in [-1,1]:
 for z in np.arange(18.,43.01,.5):
  for y in np.arange(-1.,15.01,.5):
   q=hits(solids['head'],[sign*60,y,z],[0,y,z])
   if len(q)<2 or len(q)%2:continue
   h=q[-2];p=np.asarray(h.position)
   if abs(np.dot(p-C,N))<3:continue
   if abs(h.normal[0])<.65:continue
   v=normal_thickness(solids['head'],h)
   if v is not None:
    v.update(part='head',region='ear_root' if y<=3 else 'side_cranium',sample_z_mm=float(z),sample_y_mm=float(y),sample_side=sign);rows.append(v)
# Classify the actual outer hits against the reconstructed mother triangles;
# source-ear skin is allowed to be thinner than the surrounding hollow skull.
mom=np.load(OUT/'mother-surface.npz');mf=mom['triangles'];mt=mom['after'][mf]
points=np.array([a['entry_point_mm'] for a in rows]);tree=cKDTree(mt.mean(1));cand=tree.query(points,k=32)[1]
cp=trimesh.triangles.closest_point(mt[cand.reshape(-1)],np.repeat(points,32,axis=0));dd=np.linalg.norm(cp-points.repeat(32,axis=0),axis=1).reshape(-1,32);pick=dd.argmin(1);near=cand[np.arange(len(rows)),pick];eartri=np.mean(mom['ear_locked'][mf],axis=1)>=2/3
for i,a in enumerate(rows):
 a['nearest_mother_triangle']=int(near[i]);a['mother_surface_distance_mm']=float(dd[i,pick[i]]);a['source_ear_outer_hit']=bool(eartri[near[i]] and dd[i,pick[i]]<.5)
def summary(rr):
 valid=[a for a in rr if a['exit_normal_dot_entry']<-.25 and a['normal_ray_mm']<8]
 vals=np.array([a['normal_ray_mm'] for a in valid]);tiny=[a for a in valid if a['normal_ray_mm']<2.0]
 return {'samples':len(rr),'opposite_inner_surface_valid_count':len(valid),'validity_rule':'exit normal dot entry normal < -0.25 and crossing <8mm; other crossings retained as ambiguous/mechanical, not called wall minima','minimum_p05_median_max_mm':[float(vals.min()),float(np.quantile(vals,.05)),float(np.median(vals)),float(vals.max())] if len(vals) else None,'below_2mm_count':len(tiny),'thin_examples':sorted(tiny,key=lambda a:a['normal_ray_mm'])[:12],'minimum_location':min(valid,key=lambda a:a['normal_ray_mm']) if valid else None}
sums={}
for k in solids:
 for reg in ['ordinary_cranium','ear_root','side_cranium']:
  rr=[a for a in rows if a['part']==k and a['region']==reg]
  if rr:sums[k+':'+reg]=summary(rr)
sums['head:ear_neighborhood_excluding_source_ear']=summary([a for a in rows if a['part']=='head' and a['region']=='ear_root' and not a['source_ear_outer_hit']])
sums['head:source_ear_skin']=summary([a for a in rows if a['part']=='head' and a['source_ear_outer_hit']])
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha[k] for k,p in paths.items())
report={'sources':{k:{'path':str(p),'sha256':sha[k]} for k,p in paths.items()},'method':'Actual STL first intersected by radial or lateral rays, then a second inward ray is cast along the actual outer triangle normal to find the paired inner exit. No mother/head topology correspondence is assumed. Ear samples choose innermost lateral material pair to bypass pinna. Cut-plane +/-3mm and magnet/pin neighborhoods excluded from ordinary-cranium sampling.','limitations':'Discrete surface-normal crossing measurements; not a certified global minimum wall thickness or print/material strength guarantee. Grazing rays, intentional openings, seam faces and complex ear folds require separate interpretation.','source_ear_classification':'Actual outer hit is matched to 32 nearest-centroid mother triangles and exact closest point; majority source-ear incidence and surface distance<0.5mm identifies original pinna skin. Raw ear-region minima remain reported separately; ear-skin thickness is not claimed as hollow-cranium wall thickness.', 'nominal_shell_thickness_mm':2.6,'summary':sums,'samples':rows}
(OUT/'side-shell-review.json').write_text(json.dumps(report,indent=2)+'\n')
fig,axs=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
for ax,part in zip(axs,['head','cap']):
 q=[a for a in rows if a['part']==part and a['exit_normal_dot_entry']<-.25 and a['normal_ray_mm']<8];pos=np.array([a['entry_point_mm'] for a in q]);val=np.array([a['normal_ray_mm'] for a in q]);h=ax.scatter(pos[:,0],pos[:,2],c=val,cmap='viridis',vmin=2,vmax=3,s=4);ax.set_title(part+' actual STL normal-ray wall samples');ax.set_aspect('equal');ax.set_xlabel('X mm');ax.set_ylabel('Z mm');ax.grid(alpha=.2)
fig.colorbar(h,ax=axs,label='Normal-ray crossing (mm)');fig.savefig(OUT/'side-shell-review.png',dpi=140)
print(json.dumps({'sha256':sha,'summary':sums},indent=2))
