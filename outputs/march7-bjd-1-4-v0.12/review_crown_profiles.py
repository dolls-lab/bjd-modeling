from pathlib import Path
import numpy as np,json,hashlib
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;d=np.load((P/'front-solution.npz' if (P/'front-solution.npz').exists() else P/'mother-surface.npz'));f=d['triangles'];before=d['before'];after=d['after'];X=[0.,8.,14.,20.,24.];Z=np.arange(35.,69.701,.1)
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
r={'input_npz_sha256':hashlib.sha256(((P/'front-solution.npz' if (P/'front-solution.npz').exists() else P/'mother-surface.npz')).read_bytes()).hexdigest(),'method':'Actual triangle-plane intersections at X=0/8/14/20/24, frontmost Y samples every0.1mm in Z. Derivatives use 3.1mm cubic Savitzky-Golay. Upper arc measured from Z50, or 7mm below each section maximum if that is lower, excluding the last1.6mm before that maximum to avoid endpoint singularity. Negative signed curvature corresponds to local reverse bend in Y(Z).','limitations':'Diagnostic sampled sections, not a global all-directions convexity proof. Crown apex and full surface have also been directly visually reviewed. Raw mother shading differs from final voxelized printable surface.','sections':{},'visual_review':'Brow close and crown close inspected directly: prominent outer-eye horn and previous upper-forehead bump removed. Eye corner sculpted fold remains. Central forehead is slightly steeper than v11 in Z44-50; this is explicitly retained as a tradeoff for one uninterrupted crown arc, not claimed to replicate v8 slope.'}
fig,axs=plt.subplots(2,5,figsize=(17,9),constrained_layout=True)
for j,x in enumerate(X):
 row={}
 for name,v,col in [('v11',before,'#888888'),('v12front',after,'#1565c0')]:
  y=profile(v,x);good=np.isfinite(y);z=Z[good];y=y[good];dy=savgol_filter(y,31,3,deriv=1,delta=.1);ddy=savgol_filter(y,31,3,deriv=2,delta=.1);k=ddy/(1+dy*dy)**1.5;lo=min(50.,z.max()-7);zone=(z>=lo)&(z<=z.max()-1.6)
  row[name]={'section_sample_max_z_mm':float(z.max()),'upper_arc_evaluation_z_mm':[float(lo),float(z[zone].max())],'upper_arc_min_curvature_per_mm':float(k[zone].min()),'upper_arc_max_curvature_per_mm':float(k[zone].max()),'upper_arc_reverse_curvature_samples_below_minus0p002':int(np.sum(k[zone]<-.002)),'upper_arc_min_dY_dZ':float(dy[zone].min()),'local_Y_extrema_in_upper_arc':int(np.sum(np.diff(np.sign(dy[zone]))!=0))}
  axs[0,j].plot(y,z,label=name,color=col);axs[1,j].plot(z,k,label=name,color=col)
 r['sections'][str(x)]=row
 axs[0,j].set(title=f'X={x:g} mm',xlabel='Y (mm)',ylabel='Z (mm)');axs[0,j].set_aspect('equal');axs[0,j].legend();axs[1,j].set(xlabel='Z (mm)',ylabel='signed curvature (1/mm)',ylim=(-.04,.15));axs[1,j].axhline(0,color='k',linewidth=.5)
 for ax in axs[:,j]:ax.grid(alpha=.2)
r['candidate_upper_arc_reverse_bend_detected']=any(a['v12front']['upper_arc_reverse_curvature_samples_below_minus0p002'] for a in r['sections'].values())
fig.suptitle('Forehead-to-crown profiles: v11 vs v12 wide XYZ fairing')
fig.savefig(P/'crown-profile-review.png',dpi=140);(P/'crown-profile-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
