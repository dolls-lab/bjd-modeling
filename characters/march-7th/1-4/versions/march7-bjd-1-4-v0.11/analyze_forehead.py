from pathlib import Path
import numpy as np,json,hashlib
import trimesh,manifold3d as md
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs');O=Path(__file__).parent
paths={n:R/f'march7-bjd-1-4-v0.{n}'/f'march7-head-shell-v0.{n}-draft.stl' for n in [8,10]}
ss={}
for n,p in paths.items():
 t=trimesh.load_mesh(p,process=True);s=md.Manifold(md.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)));assert s.status()==md.Error.NoError;ss[n]=s
Z=np.arange(32.,68.01,.1);X=np.array([0.,8.,14.,20.,24.]);profiles={}
for n,s in ss.items():
 a=np.full((len(X),len(Z)),np.nan)
 for i,x in enumerate(X):
  for j,z in enumerate(Z):
   h=s.ray_cast([x,-60,z],[x,5,z])
   if h:a[i,j]=h[0].position[1]
 profiles[n]=a
np.savez_compressed(O/'forehead-profiles.npz',x_mm=X,z_mm=Z,y_v8=profiles[8],y_v10=profiles[10])
fig,axs=plt.subplots(2,len(X),figsize=(17,9),constrained_layout=True);report={'sources':{str(n):{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in paths.items()},'sections':{}}
for i,x in enumerate(X):
 row=[]
 for z0 in [34,36,38,40,42,44,46,48,50,52,55,58,60,63,65]:
  j=int(round((z0-Z[0])/.1));a=profiles[8][i,j];b=profiles[10][i,j];row.append({'z_mm':z0,'v8_front_y_mm':float(a),'v10_front_y_mm':float(b),'v8_minus_v10_mm':float(a-b)})
 report['sections'][str(x)]=row
 for n,col in [(8,'#bd6b18'),(10,'#1565c0')]:
  y=profiles[n][i];keep=np.isfinite(y);z=Z[keep];y=y[keep];axs[0,i].plot(y,z,color=col,label=f'v{n}');axs[1,i].plot(z,savgol_filter(y,31,3,deriv=1,delta=.1),color=col)
 axs[0,i].set_title(f'Front profile X={x:g}mm');axs[0,i].set(xlabel='Y front (mm)',ylabel='Z (mm)');axs[0,i].legend();axs[0,i].grid(alpha=.2);axs[0,i].set_aspect('equal')
 axs[1,i].set(xlabel='Z (mm)',ylabel='dY/dZ',ylim=(-1,2.5));axs[1,i].grid(alpha=.2)
fig.suptitle('Actual STL: v8 central forehead reference vs accepted v10 cranium\nDerivative curves smoothed over 3.1mm; clipped graph avoids crown singularity')
fig.savefig(O/'forehead-profile-comparison.png',dpi=140);(O/'forehead-profile-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report['sections'].items() if k in ['0.0','14.0','20.0']},indent=2))
