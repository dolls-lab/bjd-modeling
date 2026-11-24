"""Smooth only the lip-retraction amplitude, capped by original source-depth bounds."""
from pathlib import Path
import hashlib,json
import numpy as np
import trimesh,manifold3d as m
from scipy.ndimage import gaussian_filter1d

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'v18-lip-only/march7-head-shell-1-4-v18.stl'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)=='3399309ae690b1a8cfa022442971c9480ea0d427d51a3e8a8f6e58a7bf4af062'
p=json.loads((HERE/'parameters.json').read_text())['lip_adjustment']
mesh=trimesh.load_mesh(SOURCE,process=True,validate=False)
solid=m.Manifold(m.Mesh64(np.asarray(mesh.vertices),np.asarray(mesh.faces,dtype=np.uint64)))

def front_y(x0,z0):
    hits=solid.ray_cast((float(x0),-80.,float(z0)),(float(x0),-10.,float(z0)))
    assert hits,('No source hit',x0,z0)
    return min(float(hit.position[1]) for hit in hits)

def smoothstep(t):
    t=np.clip(t,0.,1.)
    return t**3*(10.-15.*t+6.*t*t)

h=p['field_grid_step_mm']
rx=p['x_zero_weight_half_width_mm'];umin=p['min_relative_z_mm'];umax=p['max_relative_z_mm']
x=np.linspace(-rx,rx,round(2*rx/h)+1)
u=np.linspace(umin,umax,round((umax-umin)/h)+1)
raw=np.zeros((len(u),len(x)));outer=np.zeros_like(raw)
boundaries=np.zeros((len(x),4));amplitude=np.zeros(len(x));ordered=np.zeros(len(x),dtype=bool)
nominal=p['nominal_additional_retraction_mm'];fraction=p['lower_depth_fraction_limit']
ub=[umin,p['lower_plateau_relative_z_mm'],p['upper_plateau_relative_z_mm'],umax]
for i,x0 in enumerate(x):
    line=p['seam_center_z_mm']+p['seam_curve_per_mm']*x0*x0
    yb,yl,yu,yt=[front_y(x0,line+v) for v in ub];boundaries[i]=[yb,yl,yu,yt]
    outer[:,i]=[front_y(x0,line+v) for v in u]
    if not (yb>yl+1e-6 and yl>yu+1e-6 and yu>yt+1e-6):continue
    ordered[i]=True
    amplitude[i]=nominal*np.tanh(fraction*(yb-yl)/nominal)
    raw[:,i]=amplitude[i]*smoothstep((yb-outer[:,i])/(yb-yl))*smoothstep((outer[:,i]-yt)/(yu-yt))
raw[[0,-1],:]=0.
amplitude_smoothed=gaussian_filter1d(amplitude,p['displacement_x_smoothing_sigma_mm']/h,mode='nearest',truncate=4.)
amplitude_scale=float(np.min(amplitude[ordered]/amplitude_smoothed[ordered]))
amplitude_final=amplitude_smoothed*min(amplitude_scale,1.)
assert np.all(amplitude_final[ordered]<=amplitude[ordered]+1e-12)
smoothed=raw*np.divide(amplitude_final,amplitude,out=np.zeros_like(amplitude),where=amplitude>0)[None,:]
wx=1.-smoothstep((np.abs(x)-p['x_full_weight_half_width_mm'])/(rx-p['x_full_weight_half_width_mm']))
dy=smoothed*wx[None,:];dy[[0,-1],:]=0.;dy[:,[0,-1]]=0.
np.savez_compressed(HERE/'lip-field.npz',x=x,u=u,dy=dy,raw_unweighted_dy=raw,smoothed_unweighted_dy=smoothed,source_outer_y=outer,boundary_outer_y=boundaries,source_amplitude=amplitude,amplitude_smoothed=amplitude_smoothed,amplitude_final=amplitude_final,amplitude_global_scale=amplitude_scale,ordered=ordered)
report={'source_head_sha256':sha(SOURCE),'field_sha256':sha(HERE/'lip-field.npz'),'array_order':'[u_index, x_index]; u = Z - (9.85 + 0.033*X^2)','grid_shape':list(dy.shape),'grid_step_mm':h,'x_smoothing_sigma_mm':p['displacement_x_smoothing_sigma_mm'],'amplitude_global_scale':amplitude_scale,'amplitude_bounded_by_source':True,'smoothing':'Gaussian only on A(X), followed by one global factor so A never exceeds each original source-depth bound; preserve the original per-X source-depth transition and compact X window. No Z mixing and no source geometry smoothing.','raw_peak_mm':float((raw*wx[None,:]).max()),'final_peak_mm':float(dy.max()),'unordered_source_columns':int((~ordered).sum()),'source_unchanged':True,'boundary_zero':bool(np.all(dy[[0,-1],:]==0) and np.all(dy[:,[0,-1]]==0)),'limitations':'A-only smoothing preserves the continuous per-X depth-mapping bound; interpolation and final triangulation still require actual profile checks. Final STL profiles and appearance require independent checks.'}
(HERE/'lip-field-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FIELD_COMPLETE',json.dumps(report),flush=True)
