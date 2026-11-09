from pathlib import Path
import hashlib,json,sys
import numpy as np,trimesh,manifold3d as md
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;P7=OUT/'march7-head-shell-v0.7-draft.stl'
paths={'v5':ROOT/'march7-bjd-1-4-v0.5/march7-head-shell-v0.5-draft.stl','v6':ROOT/'march7-bjd-1-4-v0.6/march7-head-shell-v0.6-draft.stl','v7':P7}
sha={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()}
def load(p):
 t=trimesh.load_mesh(p,process=True,validate=False);m=md.Manifold(md.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)))
 assert m.status()==md.Error.NoError,str(m.status());return m
m={k:load(p) for k,p in paths.items()}
def chords(s,y,z,sign):
 h=s.ray_cast([sign*60,y,z],[0,y,z]);q=[]
 for a in h:
  if not q or np.linalg.norm(np.array(a.position)-np.array(q[-1].position))>1e-5:q.append(a)
 xs=[abs(float(a.position[0])) for a in q];th=[xs[i]-xs[i+1] for i in range(0,len(xs)-1,2)]
 return {'hits':len(q),'absolute_x_mm':xs,'outer_normal_x_abs':None if not q else abs(float(q[0].normal[0])),'material_intervals_mm':th,'innermost_chord_mm':None if len(q)%2 or not th else th[-1],'innermost_outer_normal_x_abs':None if len(q)%2 or not th else abs(float(q[-2].normal[0]))}
rows=[]
for sign in [-1,1]:
 for z in np.arange(16,43.001,.5):
  for y in np.arange(-1,15.001,.5):
   rr={k:chords(s,float(y),float(z),sign) for k,s in m.items()}
   rows.append({'side':sign,'y_mm':float(y),'z_mm':float(z),'versions':rr})
summary={}
for sign in [-1,1]:
 for name,select in [('narrow_ear_root',lambda r:-1<=r['y_mm']<=3),('side_skull',lambda r:3<r['y_mm']<=15)]:
  rr=[r for r in rows if r['side']==sign and select(r) and r['versions']['v7']['innermost_chord_mm'] is not None];a=np.array([r['versions']['v7']['innermost_chord_mm'] for r in rr]);i=int(a.argmin())
  thin=[r for r in rr if r['versions']['v7']['innermost_chord_mm']<2]
  newlythin=[r for r in thin if r['versions']['v5']['innermost_chord_mm'] is not None and r['versions']['v5']['innermost_chord_mm']>=2]
  summary[f'{sign}:{name}']={'samples':len(rr),'chord_min_p05_median_max_mm':[float(a.min()),float(np.quantile(a,.05)),float(np.median(a)),float(a.max())],'minimum_location':rr[i],'below_2mm_count':len(thin),'new_below_2mm_vs_v5_count':len(newlythin),'new_thin_examples':newlythin[:15],'rays_with_detached_pinna_interval':sum(r['versions']['v7']['hits']>2 for r in rr)}
for key,s in summary.items():
 sign=int(key.split(':')[0]);region=key.split(':')[1]
 zone=[r for r in rows if r['side']==sign and ((-1<=r['y_mm']<=3) if region=='narrow_ear_root' else 3<r['y_mm']<=15)]
 s['total_rays']=len(zone);s['unpaired_or_missing_count']=sum(r['versions']['v7']['innermost_chord_mm'] is None for r in zone)
 near=[r['versions']['v7']['innermost_chord_mm'] for r in zone if r['versions']['v7']['innermost_chord_mm'] is not None and r['versions']['v7']['innermost_outer_normal_x_abs']>=.9]
 s['near_orthogonal_wall_chords']={'criterion':'abs(innermost material interval entry normal X)>=.9','count':len(near),'minimum_mm':float(min(near)) if near else None}
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha[k] for k,p in paths.items())
r={'sources':{k:{'file':str(p),'sha256':sha[k]} for k,p in paths.items()},'method':'Ray from +/-X60 toward X0; all material intervals retained. Use innermost pair for shell when an outer detached ear segment produces four hits. Values are X-direction chords, not a full normal minimum-thickness proof.','sample_grid':{'y_mm':[-1,15,.5],'z_mm':[16,43,.5]},'summary':summary,'samples':rows}
(OUT/'side-shell-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'sha256':sha,'summary':summary},indent=2))
