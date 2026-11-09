#!/usr/bin/env python3
"""Read-only v0.3/v0.4 cranium profile evidence, not a curvature proof."""
from pathlib import Path
import hashlib,json
import numpy as np
import trimesh,manifold3d as m
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'march7-bjd-1-4-v0.3'
ZS=np.arange(35.,70.001,.25)
CENTER_Y=3.3

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 t=trimesh.load_mesh(path,process=True,validate=False)
 s=m.Manifold(m.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)))
 if s.status()!=m.Error.NoError:raise ValueError(str(s.status()))
 return s

def raw_stl_vertices(path):
 data=path.read_bytes();n=int.from_bytes(data[80:84],'little')
 if len(data)!=84+50*n:raise ValueError('Expected binary STL')
 dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')])
 return np.frombuffer(data,dtype=dtype,offset=84,count=n)['vertices'].copy()

def metrics(r):
 valid=np.isfinite(r)
 if not valid.all():return {'all_samples_present':False,'missing_z_mm':ZS[~valid].tolist()}
 smooth=savgol_filter(r,17,3)
 slope=np.gradient(smooth,.25)
 second=np.gradient(slope,.25)
 curvature=second/(1+slope*slope)**1.5
 central=(ZS>=40)&(ZS<=62)
 upper=(ZS>=45)&(ZS<=65)
 k=int(np.argmax(np.where(upper,abs(curvature),-1)))
 positive=ZS[central&(second>.015)]
 return {'all_samples_present':True,'largest_radius_mm':float(r.max()),'largest_radius_z_mm':float(ZS[np.argmax(r)]),
         'upper_profile_max_abs_curvature_per_mm':float(abs(curvature[k])), 'upper_profile_peak_curvature_z_mm':float(ZS[k]),
         'central_max_positive_radial_second_derivative_per_mm':float(max(0.,second[central].max())),
         'central_positive_second_derivative_over_0_015_z_range_mm': [float(positive.min()),float(positive.max())] if len(positive) else None,
         'shape_note':'Positive radial second derivative can signal a concave shoulder; threshold is an exploratory diagnostic, not an acceptance criterion.'}

def main():
 paths={'v0.3':BASE/'march7-head-shell-v0.3-draft.stl','v0.4':ROOT/'march7-head-shell-v0.4-draft.stl'}
 solids={key:load(path) for key,path in paths.items()}
 labels=[('forehead_midline',-90),('front_side_right',-60),('front_side_left',-120),('temple_right',-30),('temple_left',-150),('side_right',0),('side_left',180)]
 results={}
 for label,angle in labels:
  direction=np.array([np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle)),0.])
  curves={}
  for version,solid in solids.items():
   rs=[]
   for z in ZS:
    center=np.array([0.,CENTER_Y,z])
    hits=solid.ray_cast((center+60*direction).tolist(),center.tolist())
    rs.append(float(np.dot(np.array(hits[0].position)-center,direction)) if hits else float('nan'))
   curves[version]=np.array(rs)
  delta=curves['v0.4']-curves['v0.3']
  results[label]={'azimuth_deg':angle,'radii_mm':{key:a.tolist() for key,a in curves.items()},
                  'metrics':{key:metrics(a) for key,a in curves.items()},
                  'max_abs_radial_change_mm':float(np.nanmax(abs(delta))),
                  'max_change_z_mm':float(ZS[np.nanargmax(abs(delta))]),
                  'all_z_35_samples_identical':bool(curves['v0.3'][0]==curves['v0.4'][0])}
 left_right={}
 for prefix in ['front_side','temple','side']:
  right=np.array(results[prefix+'_right']['radii_mm']['v0.4']);left=np.array(results[prefix+'_left']['radii_mm']['v0.4'])
  left_right[prefix]={'max_radius_difference_mm':float(np.nanmax(abs(right-left)))}
 raw={key:raw_stl_vertices(path) for key,path in paths.items()}
 same_shape=raw['v0.3'].shape==raw['v0.4'].shape
 protected={'comparison_method':'Corresponding vertex slots in the binary STL triangle stream; no mesh processing, nearest-point search or tolerance welding.',
            'same_triangle_stream_shape':same_shape,'baseline_triangles':len(raw['v0.3']),'current_triangles':len(raw['v0.4'])}
 if same_shape:
  old,new=raw['v0.3'].astype(np.float64),raw['v0.4'].astype(np.float64)
  low=old[:,:,2]<=35.;delta=np.linalg.norm(new-old,axis=2)
  protected.update({'all_z_coordinates_bitwise_equal':bool(np.array_equal(raw['v0.3'][:,:,2],raw['v0.4'][:,:,2])),
                    'lower_region_vertex_slots':int(low.sum()),'lower_region_coordinates_bitwise_equal':bool(np.array_equal(raw['v0.3'][low],raw['v0.4'][low])),
                    'lower_region_max_displacement_mm':float(delta[low].max()),'whole_head_max_vertex_displacement_mm':float(delta.max())})
 cap_paths={'v0.3':BASE/'march7-head-cap-v0.3-draft.stl','v0.4':ROOT/'march7-head-cap-v0.4-draft.stl'}
 caps={key:sha(path) for key,path in cap_paths.items()}
 fig,axs=plt.subplots(1,4,figsize=(14,6))
 for ax,label,title in zip(axs,['forehead_midline','front_side_right','temple_right','side_right'],['Forehead midline','Front-side 60 deg','Temple 30 deg','Side']):
  for version,color in [('v0.3','#9b718b'),('v0.4','#137c8b')]:
   ax.plot(results[label]['radii_mm'][version],ZS,label=version,color=color,lw=2)
  ax.set(title=title,xlabel='Radial distance from Y=3.3 mm',ylabel='Height Z (mm)',ylim=(35,72));ax.grid(alpha=.3);ax.legend()
 fig.suptitle('Actual exported STL: broad cranium profiles (fixed-height rays)',fontsize=13)
 fig.tight_layout();fig.savefig(ROOT/'cranium-profile-comparison.png',dpi=160);plt.close(fig)
 report={'units':'mm','sources':{key:{'file':str(path),'sha256':sha(path)} for key,path in paths.items()},
         'method':'At each Z, cast from 60 mm outside toward (0,3.3,Z), taking the first actual STL surface hit. Profiles are sampled independently from each exported head shell.',
         'z_samples_mm':ZS.tolist(),'derivative_diagnostic':{'smoothing':'Savitzky-Golay, 17 samples / 4 mm span, polynomial order 3','sample_step_mm':.25,'central_z_range_mm':[40,62],'upper_z_range_mm':[45,65]},
         'profiles':results,'left_right_profile_comparison':left_right,'protected_lower_head':protected,
         'cap_unchanged':{'sha256':caps,'byte_identical':caps['v0.3']==caps['v0.4']},
         'plot':'cranium-profile-comparison.png',
         'limitations':['Selected radial profiles document the large-scale shape, not a proof of convexity or smooth curvature everywhere.',
                        'Derivative estimates smooth STL triangulation over a 4 mm span; submillimeter features require separate visual and mesh review.',
                        'This report does not replace watertightness, collision, wall thickness, eye insertion or physical print checks.']}
 (ROOT/'cranium-profile-review.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'protected_lower_head':protected,'cap_unchanged':report['cap_unchanged'],'profiles':{k:{'max_radial_change':v['max_abs_radial_change_mm'],'metrics':v['metrics']} for k,v in results.items()}},indent=2))
if __name__=='__main__':main()
