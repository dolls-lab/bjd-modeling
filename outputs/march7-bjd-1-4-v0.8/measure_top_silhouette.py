"""Read-only exact triangle-plane top-envelope diagnostic; no convex hull fitting."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
solution=ROOT/'head-solution.npz';s=np.load(solution);F=s['triangles'];shell=ROOT/'march7-head-shell-v0.8-draft.stl';cap=ROOT/'march7-head-cap-v0.8-draft.stl'
source=np.load(ROOT/'head-visible-source-protection.npz');ear=source['head_visible_source_ear'];earface=np.any(ear[F],axis=1)
def read_stl(p):
 b=p.read_bytes();d=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);return np.frombuffer(b,offset=84,dtype=d,count=int.from_bytes(b[80:84],'little'))['vertices'].astype('f8')
Tactual=read_stl(shell);Tcap=read_stl(cap);hash0=sha(shell)
Vactual=s['after'].astype('f4').astype('f8');assert np.array_equal(Tactual,Vactual[F])
versions={'v0.5':s['reference_v5'],'v0.7':s['before'],'v0.8':Vactual}
ymin=float(min(Tactual[:,:,1].min(),Tcap[:,:,1].min()));ymax=float(max(Tactual[:,:,1].max(),Tcap[:,:,1].max()))
ys=np.unique(np.r_[ymin,np.round(np.arange(np.ceil(ymin*10)/10,np.floor(ymax*10)/10+.0001,.1),5),ymax]);records=[]
for label,V in versions.items():
 T=np.concatenate([V[F],Tcap]);A=T.reshape(-1,3);B=np.roll(T,-1,axis=1).reshape(-1,3);D=B-A
 mn=np.minimum(A[:,1],B[:,1]);mx=np.maximum(A[:,1],B[:,1]);ef=np.repeat(np.r_[earface,np.zeros(len(Tcap),bool)],3)
 profiles={sign:{'full_x':[],'full_z':[],'full_ear':[],'non_ear_x':[],'non_ear_z':[]} for sign in [-1,1]}
 for y in ys:
  ids=np.flatnonzero((mn<=y)&(mx>=y)&(abs(D[:,1])>1e-12));H=A[ids]+D[ids]*((y-A[ids,1])/D[ids,1])[:,None];E=ef[ids]
  flat=np.flatnonzero((abs(D[:,1])<=1e-12)&(abs(A[:,1]-y)<=1e-10))
  if len(flat):H=np.concatenate([H,A[flat],B[flat]]);E=np.r_[E,ef[flat],ef[flat]]
  for sign in [-1,1]:
   r=profiles[sign]
   for mode,mask in [('full',np.ones(len(H),bool)),('non_ear',~E)]:
    hh=H[mask];ee=E[mask]
    if len(hh):
     k=np.argmax(sign*hh[:,0]);r[mode+'_x'].append(float(sign*hh[k,0]));r[mode+'_z'].append(float(hh[k,2]))
     if mode=='full':r['full_ear'].append(bool(ee[k]))
    else:
     r[mode+'_x'].append(None);r[mode+'_z'].append(None)
     if mode=='full':r['full_ear'].append(False)
 for sign,p in profiles.items():
  full=np.array(p['full_x'],float);non=np.array(p['non_ear_x'],float)
  def idxmax(a,lo,hi):
   ix=np.flatnonzero((ys>=lo)&(ys<=hi));return int(ix[np.nanargmax(a[ix])])
  anterior=idxmax(full,-1,1.5);rear=idxmax(full,3,10);ii=np.arange(anterior,rear+1);valley=int(ii[np.nanargmin(full[ii])]);drop=max(0,float(min(full[anterior],full[rear])-full[valley]))
  chordsel=(ys>=-6)&(ys<=6);yc=ys[chordsel];xc=non[chordsel];chord=np.interp(yc,[-6,6],[xc[0],xc[-1]]);res=xc-chord;j=int(np.argmin(res));mid=int(np.argmin(abs(yc)))
  records.append({'version':label,'side':'negative_x_user_right' if sign<0 else 'positive_x','y_mm':ys.tolist(),**p,
   'full_ear_to_posterior_waist':{'anterior_peak_y_x_z_mm':[float(ys[anterior]),float(full[anterior]),p['full_z'][anterior]],'anterior_peak_on_source_ear':p['full_ear'][anterior],
    'posterior_peak_y_x_z_mm':[float(ys[rear]),float(full[rear]),p['full_z'][rear]],'valley_y_x_z_mm':[float(ys[valley]),float(full[valley]),p['full_z'][valley]],'depth_below_lower_peak_mm':drop,
    'definition':'Largest anterior width in Y−1..1.5 and posterior width in Y3..10; minimum width between them. Includes the conserved ear silhouette.'},
   'ear_excluded_chord':{'y_interval_mm':[-6,6],'midpoint_residual_mm':float(res[mid]),'minimum_residual_mm':float(res[j]),'minimum_residual_y_mm':float(yc[j]),
    'definition':'Signed |X|max(Y) minus endpoint chord; negative denotes an inward S-shaped connector relative to that chord, even if the width is monotonically increasing.'}})
report={'actual_stl':str(shell),'actual_stl_sha256':hash0,'actual_stl_unchanged_during_analysis':sha(shell)==hash0,'solution_sha256':sha(solution),'actual_facets_match_solution_float32':True,
 'cap':str(cap),'cap_sha256':sha(cap),'units':'mm','sample_pitch_y_mm':.1,'method':'At each Y plane, intersect every head+cap triangle edge and select minimum/maximum X over every Z. Includes coplanar-Y edge endpoints. No convex hull, smoothing, circle or ellipse fit is used for measured envelopes.',
 'source_ear_exclusion':'Conservatively exclude every head triangle incident to a vertex in head_visible_source_ear; preserved v7 earback refinements retain this provenance. Non-ear data is diagnostic, not a changed model.',
 'source_ear_xyz_bounds_mm':[Vactual[ear].min(0).tolist(),Vactual[ear].max(0).tolist()],
 'limits':['Fixed-Z horizontal bow metrics cannot guarantee a convex top projection because the winning Z changes along Y.','The complete top outline includes a deliberate projecting ear. Its adjacent valley must not be conflated with a new isolated skull bump.','Ear-excluded contour still can have an S-shaped transition from locked original face/forehead to rounded rear skull.','The fixed cap is included at its exported design-gap position; these silhouette metrics are not assembly or collision tests.'], 'records':records}
(ROOT/'top-silhouette-review.json').write_text(json.dumps(report,indent=2)+'\n')
lookup={(r['version'],r['side']):r for r in records};colors={'v0.5':'#246ba7','v0.7':'#9399a0','v0.8':'#df653a'}
fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained')
for col,mode in enumerate(['full','non_ear']):
 ax=axes[0,col]
 for ver in versions:
  for side,ls in [('negative_x_user_right','-'),('positive_x','--')]:
   r=lookup[(ver,side)];ax.plot(ys,r[mode+'_x'],color=colors[ver],ls=ls,lw=1.8 if ls=='-' else 1,alpha=1 if ls=='-' else .65,label=ver if ls=='-' else None)
 ax.set_xlim(-10,18);ax.set_ylim(24.5,29);ax.grid(alpha=.2);ax.set_xlabel('Y: front to rear (mm)');ax.set_ylabel('Maximum |X| over all Z (mm)');ax.set_title('Complete top projection, ears included' if mode=='full' else 'Ear-provenance triangles excluded');ax.axvspan(-1,1.83,color='#b9b9b9',alpha=.18);ax.legend()
ax=axes[1,0]
for ver in versions:
 for side,sign in [('negative_x_user_right',-1),('positive_x',1)]:
  r=lookup[(ver,side)];ax.plot(sign*np.array(r['full_x'],float),ys,color=colors[ver],lw=1.5,label=ver if sign<0 else None)
ax.invert_yaxis();ax.set_aspect('equal');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm), rear downward');ax.grid(alpha=.2);ax.set_title('Actual top silhouette (not convex hull)')
ax=axes[1,1]
for mode,ls in [('full','-'),('non_ear','--')]:
 r=lookup[('v0.8','negative_x_user_right')];ax.plot(ys,r[mode+'_z'],ls=ls,lw=1.8,label=mode.replace('_',' '))
ax.set_xlim(-10,18);ax.set_ylim(10,60);ax.grid(alpha=.2);ax.legend();ax.set_xlabel('Y (mm)');ax.set_ylabel('Z of silhouette maximum (mm)');ax.set_title('v0.8 user-right: controlling surface height')
fig.suptitle('v0.8 final: all-height head + cap envelope\nSolid: user-right (−X); dashed: +X. SHA '+hash0[:16],fontsize=14)
fig.savefig(ROOT/'top-silhouette-review.png',dpi=160);plt.close(fig)
for r in records:
 if r['side']=='negative_x_user_right':print(r['version'],json.dumps({'waist':r['full_ear_to_posterior_waist'],'no_ear_chord':r['ear_excluded_chord']}))
print('OUTPUT',ROOT/'top-silhouette-review.json')
