#!/usr/bin/env python3
"""Read-only local transition comparison from actual v0.3/v0.5 STL exports."""
from pathlib import Path
import json,hashlib,argparse
from types import SimpleNamespace
import numpy as np,trimesh,manifold3d as m
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'march7-bjd-1-4-v0.3'
def load(path):
 t=trimesh.load_mesh(path,process=True,validate=False)
 s=m.Manifold(m.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)))
 if s.status()!=m.Error.NoError:raise ValueError(str(s.status()))
 return s
class RawSurface:
 """Ray intersections against an open master, without filling or changing it."""
 def __init__(self,vertices,faces):
  self.triangles=np.asarray(vertices)[np.asarray(faces)]
  self.lo=self.triangles.min(1);self.hi=self.triangles.max(1)
 def ray_cast(self,origin,endpoint):
  origin=np.array(origin,float);d=np.array(endpoint,float)-origin
  mask=np.ones(len(self.triangles),bool)
  for axis in range(3):
   if abs(d[axis])<1e-12:mask&=(self.lo[:,axis]<=origin[axis]+1e-10)&(self.hi[:,axis]>=origin[axis]-1e-10)
  tri=self.triangles[mask]
  if not len(tri):return []
  e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];q=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,q)
  valid=abs(det)>1e-12;inv=np.zeros(len(tri));inv[valid]=1/det[valid]
  a=origin-tri[:,0];u=np.einsum('ij,ij->i',a,q)*inv;cross=np.cross(a,e1)
  v=np.einsum('j,ij->i',d,cross)*inv;t=np.einsum('ij,ij->i',e2,cross)*inv
  valid&=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>=0)&(t<=1)
  return [SimpleNamespace(position=origin+x*d) for x in sorted(t[valid])]

def stats(k,domain):
 i=int(np.argmax(abs(k)))
 return {'max_abs_curvature_per_mm':float(abs(k[i])),'peak_coordinate':float(domain[i]),'curvature_min_max_per_mm':[float(k.min()),float(k.max())],'curvature_p95_abs_per_mm':float(np.quantile(abs(k),.95))}
def ear_back_profiles(solids):
 zs=np.arange(18.,40.001,.1);rows=[]
 for y in [2,4,6,8,10]:
  row={'y_mm':y,'z_mm':zs.tolist(),'versions':{}}
  for version,solid in solids.items():
   x=np.array([solid.ray_cast([60,y,float(z)],[0,y,float(z)])[0].position[0] for z in zs])
   smooth=savgol_filter(x,11,3);d=np.gradient(smooth,.1);k=np.gradient(d,.1)/(1+d*d)**1.5
   valid=(zs>=20)&(zs<=38);i=np.flatnonzero(valid)[np.argmax(abs(k[valid]))]
   row['versions'][version]={'x_mm':x.tolist(),'max_abs_curvature_per_mm':float(abs(k[i])),'peak_z_mm':float(zs[i]),
    'lower_z21_29':stats(k[(zs>=21)&(zs<=29)],zs[(zs>=21)&(zs<=29)]),
    'new_transition_z30_38':stats(k[(zs>=30)&(zs<=38)],zs[(zs>=30)&(zs<=38)])}
  delta=np.array(row['versions']['v0.5']['x_mm'])-row['versions']['v0.3']['x_mm']
  row['min_max_side_shift_mm']=[float(delta.min()),float(delta.max())]
  row['max_abs_shift_below_z30_mm']=float(abs(delta[zs<30]).max());rows.append(row)
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--master',action='store_true');args=ap.parse_args()
 prefix='master-' if args.master else ''
 paths={'v0.3':BASE/'march7-head-shell-v0.3-draft.stl','v0.5':ROOT/'march7-head-shell-v0.5-draft.stl'}
 if args.master:
  solution=ROOT/'fairing-solution.npz';p=np.load(solution)
  solids={'v0.3':RawSurface(p['vertices_before'],p['triangles']),'v0.5':RawSurface(p['vertices_after'],p['triangles'])}
  paths={'v0.3':solution,'v0.5':solution}
 else:solids={v:load(p) for v,p in paths.items()}
 source_hashes={v:hashlib.sha256(p.read_bytes()).hexdigest() for v,p in paths.items()}
 vertical=[];horizontal=[]
 z=np.arange(48,66.001,.1);deg=np.arange(-60,15.001,.25);theta=np.deg2rad(deg)
 for x in [0,10,20]:
  row={'x_mm':x,'z_mm':z.tolist(),'versions':{}}
  for v,s in solids.items():
   ys=[]
   for zz in z:
    hits=s.ray_cast([x,-60,float(zz)],[x,40,float(zz)])
    ys.append(hits[0].position[1] if hits else np.nan)
   a=np.array(ys);valid=np.isfinite(a)
   if not valid.all():
    # High X profiles cease below the crown. Analyze the contiguous present run.
    n=np.flatnonzero(valid)[-1]+1;a=a[:n];zz=z[:n]
   else:zz=z
   smooth=savgol_filter(a,11,3);d=np.gradient(smooth,.1);dd=np.gradient(d,.1);k=dd/(1+d*d)**1.5
   mask=(zz>=52)&(zz<=63)&(np.arange(len(zz))<len(zz)-6)
   row['versions'][v]={'y_mm':a.tolist(),'z_mm':zz.tolist(),'curvature_per_mm':k.tolist(),'stats_z_52_63':stats(k[mask],zz[mask])}
  common=min(len(r['y_mm']) for r in row['versions'].values())
  row['max_front_position_change_mm']=float(np.max(abs(np.array(row['versions']['v0.5']['y_mm'][:common])-row['versions']['v0.3']['y_mm'][:common])))
  vertical.append(row)
 for height in [40,45,50,55,60]:
  row={'z_mm':height,'angle_deg':deg.tolist(),'versions':{}}
  for v,s in solids.items():
   r=[]
   for a in theta:
    d=np.array([np.cos(a),np.sin(a),0]);c=np.array([0,3.3,height]);hits=s.ray_cast((c+60*d).tolist(),c.tolist())
    if not hits:raise ValueError('Missing horizontal outer sample')
    r.append(float(np.dot(np.array(hits[0].position)-c,d)))
   r=np.array(r);smooth=savgol_filter(r,9,3);dr=np.gradient(smooth,theta);ddr=np.gradient(dr,theta)
   k=(smooth*smooth+2*dr*dr-smooth*ddr)/(smooth*smooth+dr*dr)**1.5
   mask=(deg>=-50)&(deg<=5)
   row['versions'][v]={'radius_mm':r.tolist(),'curvature_per_mm':k.tolist(),'stats_angle_minus50_to5':stats(k[mask],deg[mask])}
  row['max_radius_change_mm']=float(np.max(abs(np.array(row['versions']['v0.5']['radius_mm'])-row['versions']['v0.3']['radius_mm'])))
  horizontal.append(row)
 fig,axs=plt.subplots(2,3,figsize=(13,8))
 for ax,row in zip(axs[0],vertical):
  for v,color in [('v0.3','#9b718b'),('v0.5','#137c8b')]:
   r=row['versions'][v];ax.plot(r['y_mm'],r['z_mm'],color=color,label=v)
  ax.set(title=f'Front profile at X={row["x_mm"]} mm',xlabel='Y (mm)',ylabel='Z (mm)');ax.grid(alpha=.3);ax.legend()
 for ax,index in zip(axs[1],[1,2,3]):
  row=horizontal[index]
  for v,color in [('v0.3','#9b718b'),('v0.5','#137c8b')]:
   ax.plot(deg,row['versions'][v]['curvature_per_mm'],color=color,label=v)
  ax.set(title=f'Temple horizontal curvature Z={row["z_mm"]} mm',xlabel='Azimuth (deg)',ylabel='Curvature (1/mm)',xlim=(-50,5),ylim=(-.25,.4));ax.grid(alpha=.3);ax.legend()
 fig.suptitle(('Open master before/after' if args.master else 'Actual STL')+' local transition comparison; derivatives smoothed over about 1 mm')
 fig.tight_layout();fig.savefig(ROOT/(prefix+'transition-profile-comparison.png'),dpi=160);plt.close(fig)
 ear_rows=ear_back_profiles(solids)
 fig,axs=plt.subplots(1,3,figsize=(11,5))
 for ax,row in zip(axs,[ear_rows[1],ear_rows[2],ear_rows[3]]):
  for version,col in [('v0.3','#9b718b'),('v0.5','#137c8b')]:ax.plot(row['versions'][version]['x_mm'],row['z_mm'],label=version,color=col)
  ax.set(title=f'Behind ear: Y={row["y_mm"]} mm',xlabel='Outer X (mm)',ylabel='Z (mm)');ax.grid(alpha=.3);ax.legend()
 fig.tight_layout();fig.savefig(ROOT/(prefix+'ear-back-profile-comparison.png'),dpi=160);plt.close(fig)
 report={'sources':{v:{'file':str(p),'sha256':source_hashes[v]} for v,p in paths.items()},'vertical_profiles':vertical,'horizontal_profiles':horizontal,
         'ear_back_followup':{'method':'Actual +X-to-center first hits, fixed Y, 0.1mm Z sampling and 1mm derivative filter; includes lower guard and upper transition.','profiles':ear_rows},
         'surface_kind':'master before/after arrays in fairing-solution.npz' if args.master else 'exported print STL',
         'method':'First surface ray hits; vertical 0.1 mm pitch/11-sample cubic Savitzky-Golay filter; horizontal 0.25 degree pitch/9-sample filter; approximately 1 mm derivative smoothing.',
         'limits':['Selected contours and derivative estimates, not an exhaustive normal/curvature proof.','STL triangulation and smoothing window affect peak values; compare alongside identical-light renders.','No automatic aesthetic pass threshold is imposed.'],
         'visual_review_required':True}
 if any(hashlib.sha256(p.read_bytes()).hexdigest()!=source_hashes[v] for v,p in paths.items()):raise RuntimeError('Source changed during review; report not written')
 (ROOT/(prefix+'transition-profile-review.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'vertical':[{k:r[k] for k in ['x_mm','max_front_position_change_mm']}|{'stats':{v:a['stats_z_52_63'] for v,a in r['versions'].items()}} for r in vertical],
                   'horizontal':[{k:r[k] for k in ['z_mm','max_radius_change_mm']}|{'stats':{v:a['stats_angle_minus50_to5'] for v,a in r['versions'].items()}} for r in horizontal]},indent=2))
if __name__=='__main__':main()
