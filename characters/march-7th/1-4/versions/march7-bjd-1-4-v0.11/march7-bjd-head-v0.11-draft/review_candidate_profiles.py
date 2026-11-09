from pathlib import Path
import numpy as np,json,hashlib
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;d=np.load(P/'mother-surface.npz');f=d['triangles'];before=d['before'];after=d['after'];X=np.array([0.,8.,14.,20.,24.]);Z=np.arange(35.,64.001,.1)
def profile(v,x):
 t=v[f];x+=1e-6;t=t[(t[:,:,0].min(1)<x)&(t[:,:,0].max(1)>x)];segments=[]
 for q in t:
  pts=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   if (q[i,0]-x)*(q[j,0]-x)<0:pts.append(q[i]+(q[j]-q[i])*(x-q[i,0])/(q[j,0]-q[i,0]))
  if len(pts)==2:segments.append(pts)
 seg=np.asarray(segments);a=seg[:,0];b=seg[:,1];ys=[]
 for z in Z:
  k=(np.minimum(a[:,2],b[:,2])<=z)&(np.maximum(a[:,2],b[:,2])>=z)&(abs(b[:,2]-a[:,2])>1e-10)
  q=a[k]+(b[k]-a[k])*(z-a[k,2])[:,None]/(b[k,2]-a[k,2])[:,None];ys.append(q[:,1].min() if len(q) else np.nan)
 return np.asarray(ys)
report={'input_npz_sha256':hashlib.sha256((P/'mother-surface.npz').read_bytes()).hexdigest(),'method':'Actual v10 mother before and v11 candidate after intersected by X-constant planes; frontmost Y at Z35..64 every0.1mm. 3.1mm cubic Savitzky-Golay derivatives suppress mesh tessellation noise. X planes use +1e-6mm offset to avoid coincident edges.','limitations':'A few diagnostic profiles, not a claim of all-surface curvature uniformity. Feature-core and lateral guards are separately exact in the arrays.','sections':{}}
fig,axs=plt.subplots(2,5,figsize=(17,9),constrained_layout=True)
for j,x in enumerate(X):
 yy={};kk={};sl={}
 for name,v,col in [('v10',before,'#777777'),('v11',after,'#1565c0')]:
  y=profile(v,x);valid=np.isfinite(y);z=Z[valid];y=y[valid];dy=savgol_filter(y,31,3,deriv=1,delta=.1);ddy=savgol_filter(y,31,3,deriv=2,delta=.1);curv=ddy/(1+dy*dy)**1.5
  yy[name]=(z,y);kk[name]=(z,curv);sl[name]=(z,dy)
  axs[0,j].plot(y,z,label=name,color=col);axs[1,j].plot(z,curv,label=name,color=col)
 z,a=yy['v10'];_,b=yy['v11'];zone=(z>=36.5)&(z<=min(52,z.max()-1.5));row={'max_abs_y_change_mm':float(abs(b-a).max()),'mean_signed_y_change_36p5_to52_mm':float((b-a)[zone].mean()),'curvature_abs_max_36p5_to52_per_mm':{},'curvature_p95_abs_36p5_to52_per_mm':{},'slope_at_selected_z':{}}
 for name in yy:
  k=kk[name][1];row['curvature_abs_max_36p5_to52_per_mm'][name]=float(abs(k[zone]).max());row['curvature_p95_abs_36p5_to52_per_mm'][name]=float(np.quantile(abs(k[zone]),.95));row['slope_at_selected_z'][name]={str(zi):float(np.interp(zi,sl[name][0],sl[name][1])) for zi in [38,40,42,44,46,48,50] if zi<z.max()-1.5}
 report['sections'][str(x)]=row
 axs[0,j].set(title=f'X={x:g} mm front profile',xlabel='Y (mm)',ylabel='Z (mm)');axs[0,j].set_aspect('equal');axs[0,j].legend();axs[1,j].set(xlabel='Z (mm)',ylabel='signed curvature (1/mm)',ylim=(-.15,.3))
 for ax in axs[:,j]:ax.grid(alpha=.2)
fig.suptitle('One local-Y forehead candidate: v10 baseline vs v11\nX/Z, original features, ears and accepted crown/back remain fixed')
fig.savefig(P/'candidate-profile-review.png',dpi=140);(P/'candidate-profile-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
