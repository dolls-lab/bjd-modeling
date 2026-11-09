from pathlib import Path
import hashlib,json
import numpy as np,trimesh,manifold3d as md
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
R=Path(__file__).resolve().parent
from final_eye_inputs import HEAD as P,load_final,expected_head,confirm_unchanged
geometry,integrity=load_final(expected_head());h=integrity['head_sha256']
MODEL=R.parent;OUTPUTS=MODEL.parent
old=json.loads((OUTPUTS/'march7-bjd-1-4-v0.13-original-review/eye-original-comparison.json').read_text())
d=np.load(MODEL/'eye-postprocess/eye-solution.npz')
mesh=trimesh.load_mesh(P,process=True,validate=False);solid=md.Manifold(md.Mesh64(np.ascontiguousarray(mesh.vertices),np.ascontiguousarray(mesh.faces,dtype=np.uint64)))
base=md.Manifold(md.Mesh64(np.ascontiguousarray(geometry['before']),np.ascontiguousarray(geometry['triangles'],dtype=np.uint64)))
base_mesh=trimesh.Trimesh(geometry['before'],geometry['triangles'],process=False)
import importlib.util
spec=importlib.util.spec_from_file_location('readonly_raw_pmx',MODEL/'parse_pmx.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=Path(json.loads((MODEL/'parameters.json').read_text())['source_pmx']);pmx=module.load_pmx(source);material=next(q for q in pmx['materials'] if q['name']=='脸')
v=pmx['vertices'][:,[0,2,1]].copy();v[:,2]-=18.16621208190918;v*=27.47544416498121
raw_mesh=trimesh.Trimesh(v,pmx['faces'][material['start']:material['end']],process=False)
raw_loop=np.asarray(next(q for q in old['raw_face_boundary_loops'] if q['vertex_count']==31 and q['centroid_of_vertices_mm'][0]>0)['vertices_xyz_mm'])
configs=[('outer_corner_horizontal',2,28.3,[0,1],[17.5,20.5],[-23.,-18.]),('upper_rim_vertical',0,13.663962920147602,[1,2],[-26.,-20.5],[31.5,33.]),('lower_rim_vertical',0,13.663962920147602,[1,2],[-25.,-19.],[22.3,24.0]),('depth_minus24p5',1,-24.5,[0,2],[6.,21.],[21.,34.5]),('depth_minus21',1,-21.,[0,2],[6.,21.],[21.,34.5]),('depth_minus19p5',1,-19.5,[0,2],[6.,21.],[21.,34.5])]
previous={'sections':[]}
for name,axis,position,proj,xlim,ylim in configs:
 local={}
 for key,obj in [('raw',raw_mesh),('print',base_mesh)]:
  seg=trimesh.intersections.mesh_plane(obj,np.eye(3)[axis],np.eye(3)[axis]*position);pp=seg[:,:,proj]
  keep=(pp[:,:,0].max(1)>=xlim[0])&(pp[:,:,0].min(1)<=xlim[1])&(pp[:,:,1].max(1)>=ylim[0])&(pp[:,:,1].min(1)<=ylim[1]);local[key]=seg[keep]
 points=[]
 for a,b in zip(raw_loop,np.roll(raw_loop,-1,axis=0)):
  if (a[axis]-position)*(b[axis]-position)<=0 and abs(b[axis]-a[axis])>1e-12:
   p=a+(position-a[axis])/(b[axis]-a[axis])*(b-a)
   if xlim[0]<=p[proj[0]]<=xlim[1] and ylim[0]<=p[proj[1]]<=ylim[1]:points.append(p)
 nearest=[]
 for p in points:
  seg=local['print'];ab=seg[:,1]-seg[:,0];t=np.clip(np.einsum('ij,ij->i',p-seg[:,0],ab)/np.einsum('ij,ij->i',ab,ab),0,1);qq=seg[:,0]+t[:,None]*ab;dist=np.linalg.norm(qq-p,axis=1);j=int(dist.argmin());nearest.append({'raw_rim_point':p.tolist(),'nearest_v13_section_point':qq[j].tolist(),'distance_mm':float(dist[j]),'v13_minus_raw':(qq[j]-p).tolist()})
 previous['sections'].append({'name':name,'plane_axis':'XYZ'[axis],'plane_position_mm':position,'projection_axes':''.join('XYZ'[j] for j in proj),'plot_bounds':[xlim,ylim],'raw_segments_xyz_mm':local['raw'].tolist(),'print_segments_xyz_mm':local['print'].tolist(),'raw_eye_loop_intersections_xyz_mm':[p.tolist() for p in points],'raw_rim_to_current_section_nearest':nearest})
def cast(solid,p,y=-13.289332231246028):return solid.ray_cast((float(p[0]),-40,float(p[1])),(float(p[0]),float(y),float(p[1])))
def boundary(solid,c,u,y):
 lo=0.;hi=None
 for r in np.arange(.1,12.01,.1):
  if cast(solid,c+r*u,y):hi=r;break
  lo=r
 if hi is None:return None
 for _ in range(22):
  mid=(lo+hi)/2
  if cast(solid,c+mid*u,y):hi=mid
  else:lo=mid
 return float(hi)
rows=[]
for e,c in enumerate(d['center_xz']):
 records=[]
 for idx in range(0,720,2):
  angle=d['angles'][idx];u=np.array([np.cos(angle),np.sin(angle)]);target=float(d['target_radii'][e,idx]);raw_y=float(d['raw_rim_y'][e,idx]);radius=boundary(solid,c,u,-13.289332231246028)
  hit=cast(solid,c+(radius+.001)*u)[0]
  rec={'theta_global_deg':float(np.rad2deg(angle)),'raw_target_radius_mm':target,'v14_effective_radius_mm':radius,'residual_radial_deficit_mm':target-radius,'v14_limit_position_mm':list(hit.position),'v14_limit_normal':list(hit.normal),'raw_rim_y_mm':raw_y,'v14_limit_dy_mm':hit.position[1]-raw_y}
  if target-radius>.2:
   y=float(hit.position[1]);q=c+(target+2)*u;endpoint=cast(base,q,y);actual=boundary(base,c,u,y)
   rec['partial_depth_bracketing_evidence']={'depth_y_mm':y,'baseline_hi_radius_mm':target+2,'baseline_hi_endpoint_hit_count':len(endpoint),'baseline_actual_first_blocked_radius_mm':actual,'target_minus_actual_partial_radius_mm':None if actual is None else target-actual}
  records.append(rec)
 rows.append({'eye_index':e,'center_xz_mm':c.tolist(),'radial_samples':records,'worst_deficits':sorted(records,key=lambda q:q['residual_radial_deficit_mm'],reverse=True)[:12]})
 print('WORST',e,json.dumps(rows[-1]['worst_deficits'][:3]),flush=True)
fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained');sections=[]
for ax,section in zip(axes.ravel(),previous['sections']):
 axis='XYZ'.index(section['plane_axis']);origin=np.eye(3)[axis]*section['plane_position_mm'];proj=['XYZ'.index(s) for s in section['projection_axes']];xlim,ylim=section['plot_bounds']
 ss=trimesh.intersections.mesh_plane(mesh,np.eye(3)[axis],origin);pts=ss[:,:,proj]
 keep=(pts[:,:,0].max(1)>=xlim[0])&(pts[:,:,0].min(1)<=xlim[1])&(pts[:,:,1].max(1)>=ylim[0])&(pts[:,:,1].min(1)<=ylim[1]);ss=ss[keep]
 for segments,color,lw in [(section['raw_segments_xyz_mm'],'#159da5',2),(section['print_segments_xyz_mm'],'#b6b6b6',1.3),(ss,'#e07926',1.5)]:
  arr=np.array(segments)
  if len(arr):ax.add_collection(LineCollection(arr[:,:,proj],colors=color,linewidths=lw))
 points=section['raw_eye_loop_intersections_xyz_mm'];nearest=[]
 for point in points:
  pp=np.array(point);ab=ss[:,1]-ss[:,0];t=np.clip(np.einsum('ij,ij->i',pp-ss[:,0],ab)/np.einsum('ij,ij->i',ab,ab),0,1);qq=ss[:,0]+t[:,None]*ab;dd=np.linalg.norm(qq-pp,axis=1);j=int(dd.argmin());nearest.append({'raw_rim_point':point,'nearest_v14_section_point':qq[j].tolist(),'distance_mm':float(dd[j]),'v14_minus_raw':(qq[j]-pp).tolist()})
 if points:
  pp=np.array(points)[:,proj];ax.scatter(pp[:,0],pp[:,1],color='#e04771',s=25,zorder=4)
 ax.set_xlim(xlim);ax.set_ylim(ylim);ax.set_aspect('equal');ax.set_title(section['name'].replace('_',' '));ax.set_xlabel(section['projection_axes'][0]+' mm');ax.set_ylabel(section['projection_axes'][1]+' mm');ax.grid(alpha=.2)
 sections.append({'name':section['name'],'plane_axis':section['plane_axis'],'plane_position_mm':section['plane_position_mm'],'v14_segments_xyz_mm':ss.tolist(),'raw_rim_to_v14_nearest':nearest,'baseline_raw_rim_nearest':section['raw_rim_to_current_section_nearest']})
fig.suptitle('Final combined v14: orange = v14; gray = v13; cyan = original PMX skin; pink = original rim')
fig.savefig(R/'eye-section-comparison.png',dpi=160);plt.close(fig)
confirm_unchanged(integrity)
report={'input_integrity':integrity,'raw_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'v14_stl_sha256':h,'input_unchanged':True,'radial_definition':'Actual PMX projected polygon area centroid; same centers and target polar data as v14 solver; robust first-blocked radial scan before binary search. Theta is global XZ angle, not mirrored anatomical angle.','eyes':rows,'sections':sections,'limitations':'Cross-section nearest points are geometric proximity only, not point correspondence. Partial-depth no-hit at one outer radius does not imply the interior radii are unobstructed.'}
(R/'eye-section-and-residual-review.json').write_text(json.dumps(report,indent=2)+'\n')
print('DONE',flush=True)
