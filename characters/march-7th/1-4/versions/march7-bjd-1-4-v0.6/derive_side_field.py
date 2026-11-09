"""Derive a side-skull retraction field from real v5 sections and raw-source side-face planes."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import trimesh,manifold3d as m
from scipy.interpolate import PchipInterpolator,RectBivariateSpline
from scipy.ndimage import gaussian_filter
from scipy.signal import savgol_filter
R=Path(__file__).resolve().parent;BASE=R.parent/'march7-bjd-1-4-v0.5'
from raw_surface import RawSurface
P=json.loads((R/'parameters.json').read_text());S=P['postauricular_retraction']
raw=np.load(R/'source-protection-masks.npz');source=RawSurface(raw['vertices_mm'],raw['faces'])
sample_z=np.arange(16,48.01,.5);source_rows=[]
for z in sample_z:
    hits=[]
    for y in np.linspace(*S['source_side_reference_y_mm'],5):
        for sign in [-1,1]:
            ray=source.ray_cast([sign*60,y,z],[0,y,z])
            if ray:hits.append(abs(ray[0].position[0]))
    if len(hits)>=6:source_rows.append([z,float(np.mean(hits)),float(min(hits)),float(max(hits))])
samples=np.array(source_rows)
smoothed=savgol_filter(samples[:,1],9,3)
profile=PchipInterpolator(samples[:,0],smoothed,extrapolate=False)
t=trimesh.load_mesh(R/'baseline-head.stl',process=True)
solid=m.Manifold(m.Mesh64(np.asarray(t.vertices,dtype='f8'),np.asarray(t.faces,dtype='u8')))
ys=np.arange(-10,26.001,.25);zs=np.arange(14,56.001,.25)
outer=np.zeros((len(zs),len(ys)))
for iz,z in enumerate(zs):
    for iy,y in enumerate(ys):
        vals=[]
        for sign in [-1,1]:
            hits=solid.ray_cast([sign*60,float(y),float(z)],[0,float(y),float(z)])
            if hits:vals.append(abs(hits[0].position[0]))
        outer[iz,iy]=np.mean(vals) if vals else 0
# Smooth section interpolation noise on a submillimeter scale only.
outer=gaussian_filter(outer,sigma=(1.5,1.5),mode='nearest')
ceiling=profile(np.clip(zs,samples[0,0],samples[-1,0]))+S['target_offset_mm']
excess=outer-ceiling[:,None]
# C2 soft positive part: exactly zero below the target and exact excess after h.
h=S['smooth_ceiling_width_mm'];q=np.clip(excess/h,0,1)
positive=np.where(excess<=0,0,np.where(excess>=h,excess,h*(3*q**5-8*q**4+6*q**3)))
ratio=np.divide(positive,np.maximum(outer,1),out=np.zeros_like(outer),where=outer>1)
def ramp(a,b,x):
    u=np.clip((x-a)/(b-a),0,1);return u**3*(u*(u*6-15)+10)
gate_y=ramp(S['y_front_start_mm'],S['y_front_full_mm'],ys)
gate_z=ramp(S['z_low_start_mm'],S['z_low_full_mm'],zs)*(1-ramp(S['z_high_full_mm'],S['z_high_end_mm'],zs))
cap_margin=29.5-(ys[None,:]+.3*zs[:,None])
gate_cap=ramp(S['cap_margin_start_mm'],S['cap_margin_full_mm'],cap_margin)
ratio*=gate_y[None,:]*gate_z[:,None]*gate_cap
np.savez_compressed(R/'side-retraction-field.npz',y=ys,z=zs,outer_x=outer,target_x=ceiling,ratio=ratio,source_samples=samples)
report={'method':'Source-side-face envelope sampled at Y=-12..-8 mm, outside the raw ears. Smooth inward X scaling of added side skull. No new facial sculpt.',
 'source_reference_samples_columns':['z','mean_abs_x','min_abs_x','max_abs_x'],
 'source_reference_samples':samples.tolist(),'maximum_proposed_retraction_mm':float((outer*ratio).max()),
 'field_max_ratio':float(ratio.max()),'settings':S,
 'baseline_stl_sha256':hashlib.sha256((R/'baseline-head.stl').read_bytes()).hexdigest(),
 'limitations':['Side-face continuation is a new skull design constraint, not an official posterior skull.','Source/ear and mechanical protection are applied separately in the mesh builder.']}
(R/'side-field-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('FIELD_DONE',report['maximum_proposed_retraction_mm'],report['field_max_ratio'],flush=True)
