from pathlib import Path
import numpy as np,json,hashlib,trimesh
P=Path(__file__).parent;Q=P.parent/'candidate2';d=np.load(Q/'eye-solution.npz');a={k:d[k] for k in d.files};b=a['before'];v=a['after'].copy();original=v.copy();f=a['triangles'];n0=np.cross(b[f[:,1]]-b[f[:,0]],b[f[:,2]]-b[f[:,0]]);length=np.linalg.norm(n0,axis=1);unit=n0/length[:,None]
fixed_faces=np.array([9861]);neighbors=np.unique(np.flatnonzero(np.isin(f,f[fixed_faces].ravel()).any(1)))
for iteration in range(40):
 normals=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);proj=np.einsum('ij,ij->i',normals,unit);bad=neighbors[proj[neighbors]<.30*length[neighbors]]
 if not len(bad):break
 for i in bad:
  ids=f[i];p=v[ids];n=unit[i];grad=np.array([np.cross(n,p[2]-p[1]),np.cross(p[2]-p[0],n),np.cross(n,p[0]-p[1])]);grad[:,1]=0
  need=.31*length[i]-np.dot(np.cross(p[1]-p[0],p[2]-p[0]),n);v[ids]+=grad*(need/(grad*grad).sum())
normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);dot=np.einsum('ij,ij->i',normal,n0);repair=np.linalg.norm(v-original,axis=1);a['after']=v;a['sliver_repair_delta']=v-original;a['sliver_repair_vertices']=repair>0
np.savez_compressed(P/'eye-solution.npz',**a);trimesh.Trimesh(v,f,process=False).export(P/'eye-candidate.stl')
r=json.loads((Q/'eye-solution-report.json').read_text());r['postprocess']={'method':'Local positive projected-area constraint for one pre-existing extremely slender inner-upper triangle. Three vertex XZ positions corrected by minimum-norm gradient steps; Y remains exact. No hole curve retargeting or remeshing.','triangle_id':9861,'repaired_vertices':np.flatnonzero(repair>0).tolist(),'maximum_extra_vertex_move_mm':float(repair.max()),'iterations':iteration,'projected_area_ratio_final':float(np.dot(normal[9861],unit[9861])/length[9861])};r['normal_over90']=int((dot<0).sum());r['minimum_normal_dot']=float(np.min(dot/(np.linalg.norm(normal,axis=1)*length)));r['solution_sha256']=hashlib.sha256((P/'eye-solution.npz').read_bytes()).hexdigest();r['candidate_stl_sha256']=hashlib.sha256((P/'eye-candidate.stl').read_bytes()).hexdigest();(P/'eye-solution-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
