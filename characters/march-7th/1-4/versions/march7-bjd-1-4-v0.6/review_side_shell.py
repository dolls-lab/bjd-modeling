"""Read-only side-skull residual and lateral chord diagnostics, v5 -> v6."""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as md
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'march7-bjd-1-4-v0.5';OUT=ROOT
def load(p):
 t=trimesh.load_mesh(p,process=True,validate=False);m=md.Manifold(md.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)))
 if m.status()!=md.Error.NoError:raise ValueError(str(m.status()))
 return m
def hit_pairs(s,y,z,sign):
 raw=s.ray_cast([sign*60,float(y),float(z)],[0,float(y),float(z)])
 hits=[]
 for h in raw:
  if not hits or np.linalg.norm(np.array(h.position)-np.array(hits[-1].position))>1e-5:hits.append(h)
 if len(hits)<2:return {'valid':False,'intersection_count':len(hits)}
 outer=abs(float(hits[0].position[0]));inner=abs(float(hits[1].position[0]));chord=outer-inner
 return {'valid':chord>0,'intersection_count':len(hits),'outer_x_mm':outer,'inner_x_mm':inner,'x_chord_mm':chord,
         'outer_normal_x_abs':abs(float(hits[0].normal[0])),'position_mm':[sign*outer,float(y),float(z)]}
def main():
 paths={'v0.5':BASE/'march7-head-shell-v0.5-draft.stl','v0.6':ROOT/'march7-head-shell-v0.6-draft.stl'}
 shas={v:hashlib.sha256(p.read_bytes()).hexdigest() for v,p in paths.items()};solids={v:load(p) for v,p in paths.items()}
 fieldpath=ROOT/'side-retraction-field.npz';field=np.load(fieldpath);fieldsha=hashlib.sha256(fieldpath.read_bytes()).hexdigest();ys=np.arange(3,15.001,.5);zs=np.arange(23,42.001,.5)
 rows=[];heat={};summaries={}
 for sign in [1,-1]:
  err=np.zeros((len(zs),len(ys)));thick=np.zeros_like(err);records=[]
  for iz,z in enumerate(zs):
   target=float(np.interp(z,field['z'],field['target_x']))
   for iy,y in enumerate(ys):
    before=hit_pairs(solids['v0.5'],y,z,sign);after=hit_pairs(solids['v0.6'],y,z,sign)
    if not before['valid'] or not after['valid']:raise ValueError(f'Invalid chord at {sign}, {y}, {z}')
    record={'side_sign':sign,'y_mm':float(y),'z_mm':float(z),'target_x_mm':target,'baseline':before,'current':after,
            'residual_above_target_mm':after['outer_x_mm']-target,'actual_x_retraction_mm':before['outer_x_mm']-after['outer_x_mm']}
    records.append(record);rows.append(record);err[iz,iy]=record['residual_above_target_mm'];thick[iz,iy]=after['x_chord_mm']
  peak=max(records,key=lambda x:x['residual_above_target_mm']);thin=min(records,key=lambda x:x['current']['x_chord_mm'])
  summaries[str(sign)]={'samples':len(records),'residual_min_median_p95_max_mm':[float(err.min()),float(np.median(err)),float(np.quantile(err,.95)),float(err.max())],
      'residual_above_0_5mm_count':int((err>.5).sum()),'residual_above_1mm_count':int((err>1).sum()),'largest_residual_location':peak,
      'x_chord_min_p05_median_max_mm':[float(thick.min()),float(np.quantile(thick,.05)),float(np.median(thick)),float(thick.max())],
      'x_chord_below_2mm_count':int((thick<2).sum()),'thinnest_chord_location':thin,
      'more_than_two_ray_intersections_count':sum(r['current']['intersection_count']>2 for r in records)}
  near=[r for r in records if r['current']['outer_normal_x_abs']>=.9]
  chord=np.array([r['current']['x_chord_mm'] for r in near])
  summaries[str(sign)]['near_orthogonal_samples']={'criterion':'abs(outer normal X)>=0.9','count':len(near),'x_chord_min_p05_median_max_mm':[float(chord.min()),float(np.quantile(chord,.05)),float(np.median(chord)),float(chord.max())],'x_chord_below_2mm_count':int((chord<2).sum())}
  heat[sign]=(err,thick)
 fig,axs=plt.subplots(2,2,figsize=(11,9))
 for row,sign in enumerate([1,-1]):
  for col,(data,title) in enumerate(zip(heat[sign],['Outer X minus source-derived ceiling','Lateral outer-to-inner X chord'])):
   im=axs[row,col].imshow(data,origin='lower',extent=[ys[0],ys[-1],zs[0],zs[-1]],aspect='auto',cmap='viridis');fig.colorbar(im,ax=axs[row,col],label='mm')
   axs[row,col].set(title=f'{"+X" if sign>0 else "-X"}: {title}',xlabel='Posterior Y (mm)',ylabel='Height Z (mm)')
 fig.tight_layout();fig.savefig(OUT/'side-shell-heatmap.png',dpi=160);plt.close(fig)
 section_rows=[];fig,axs=plt.subplots(1,5,figsize=(16,4))
 for ax,z in zip(axs,[24,28,32,36,40]):
  points={}
  for version,s in solids.items():
   p=[]
   for y in np.arange(-12,23.001,.2):
    hits=s.ray_cast([60,float(y),z],[0,float(y),z])
    if hits:p.append([float(y),float(hits[0].position[0])])
   points[version]=p;a=np.array(p);ax.plot(a[:,0],a[:,1],label=version)
  target=float(np.interp(z,field['z'],field['target_x']));ax.axhline(target,ls='--',color='#555555',label='source ceiling')
  ax.set(title=f'Z={z} mm',xlabel='Y (mm)',ylabel='Outer X (mm)',xlim=(-12,23),ylim=(17,30));ax.grid(alpha=.3);ax.legend(fontsize=7)
  section_rows.append({'z_mm':z,'target_x_mm':target,'points_yx_mm':points})
 fig.tight_layout();fig.savefig(OUT/'side-envelope-comparison.png',dpi=160);plt.close(fig)
 if any(hashlib.sha256(p.read_bytes()).hexdigest()!=shas[v] for v,p in paths.items()):raise RuntimeError('STL changed during diagnostic')
 report={'units':'mm','sources':{v:{'file':str(p),'sha256':shas[v]} for v,p in paths.items()},'field_sha256':fieldsha,
         'sampling':{'y_mm':[3,15,.5],'z_mm':[23,42,.5],'sides':[1,-1]},'summary':summaries,'samples':rows,'section_profiles':section_rows,
         'method':'Use actual exported meshes. Source ceiling read from the generated field. From outside each side, the first two distinct ray intersections define the material chord. All original face, ear and mechanical geometry remains in the test.',
         'limitations':['X chord is directional wall thickness, not the global minimum normal wall thickness.','Source-plane continuation is a design reference, not an official posterior skull.','Residuals near ear/feature locks or seam protection may be intentional but remain visible shape tradeoffs.','This does not replace full topology, cap collision, eye insertion or physical printing checks.']}
 (OUT/'side-shell-review.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'sources':report['sources'],'summary':summaries},indent=2))
if __name__=='__main__':main()
