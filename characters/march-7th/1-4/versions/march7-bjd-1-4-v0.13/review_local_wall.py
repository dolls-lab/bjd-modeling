"""Paired actual STL normal-ray wall samples only near the v13 skin edit."""
from pathlib import Path
import json,hashlib,argparse
import numpy as np,trimesh,manifold3d as md
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;OLD=P.parent/'march7-bjd-1-4-v0.12'
ap=argparse.ArgumentParser();ap.add_argument('--solution',required=True);ap.add_argument('--expected-head-sha256',required=True);ap.add_argument('--maximum-samples',type=int,default=3000);args=ap.parse_args()
paths={'baseline':OLD/'march7-head-shell-v0.12-draft.stl','current':P/'march7-head-shell-v0.13-draft.stl'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={k:sha(v) for k,v in paths.items()};assert hashes['current']==args.expected_head_sha256
solpath=Path(args.solution);solsha=sha(solpath);sol=np.load(solpath);v0=sol['before'];v1=sol['after'];f=sol['triangles'];m=trimesh.Trimesh(v0,f,process=False);n=m.vertex_normals
changed=np.flatnonzero(np.linalg.norm(v1-v0,axis=1)>1e-9);ids=changed[np.linspace(0,len(changed)-1,min(len(changed),args.maximum_samples)).astype(int)]
solids={}
for k,p in paths.items():
 t=trimesh.load_mesh(p,process=True,validate=False);s=md.Manifold(md.Mesh64(np.ascontiguousarray(t.vertices,dtype=np.float64),np.ascontiguousarray(t.faces,dtype=np.uint64)));assert s.status()==md.Error.NoError;solids[k]=s
print('actual STL solids loaded',flush=True)
def crossing(s,p,n):
 hits=[]
 for h in s.ray_cast(p+.15*n,p-10*n):
  if not hits or np.linalg.norm(np.array(h.position)-np.array(hits[-1].position))>1e-5:hits.append(h)
 if len(hits)<2:return None
 if np.linalg.norm(np.asarray(hits[0].position)-p)>.10:return None
 thickness=float(np.linalg.norm(np.asarray(hits[1].position)-np.asarray(hits[0].position)));dot=float(np.dot(hits[1].normal,n))
 if thickness>8 or dot>=-.25:return None
 return {'thickness_mm':thickness,'entry_distance_from_solution_point_mm':float(np.linalg.norm(np.array(hits[0].position)-p)),'entry_mm':list(hits[0].position),'exit_mm':list(hits[1].position),'exit_normal_dot_baseline_outer_normal':dot}
rows=[]
for i in ids:
 a=crossing(solids['baseline'],v0[i],n[i]);b=crossing(solids['current'],v1[i],n[i]);rows.append({'source_vertex':int(i),'baseline':a,'current':b,'displacement_mm':float(np.linalg.norm(v1[i]-v0[i]))})
def summary(key):
 a=np.array([q[key]['thickness_mm'] for q in rows if q[key] is not None]);return {'valid_samples':len(a),'min_p01_p05_median_mm':[float(a.min()),float(np.quantile(a,.01)),float(np.quantile(a,.05)),float(np.median(a))] if len(a) else None,'below_1mm_count':int(np.sum(a<1)),'below_2mm_count':int(np.sum(a<2))}
pairs=[q for q in rows if q['baseline'] and q['current']];newthin=[q for q in pairs if q['baseline']['thickness_mm']>=1 and q['current']['thickness_mm']<1]
assert all(sha(p)==hashes[k] for k,p in paths.items()) and sha(solpath)==solsha
r={'sources':{k:{'path':str(p),'sha256':hashes[k]} for k,p in paths.items()},'solution':{'path':str(solpath),'sha256':solsha},'method':'Deterministic up to3000 samples among changed outer-skin vertices. At corresponding before/after positions cast inward along the same baseline area-weighted vertex normal, independently against each actual STL solid. Accept first entry within0.10mm of the exterior point and opposing exit dot<-0.25 within8mm.','scope':'Local surface-edit regression only; unchanged cap and whole other regions are certified by coordinate audit, not redundantly sampled here.','limitations':'Discrete ray crossings do not certify global minimum thickness. Complex thin rims may yield ambiguous or changing exit branches; missing samples and paired reductions retained for interpretation.','sampled_changed_vertices':len(ids),'total_changed_vertices':len(changed),'summary':{k:summary(k) for k in paths},'paired_valid_samples':len(pairs),'new_paired_below_1mm_count':len(newthin),'new_paired_below_1mm_examples':newthin[:15],'maximum_paired_reduction_mm':max((q['baseline']['thickness_mm']-q['current']['thickness_mm'] for q in pairs),default=None),'samples':rows,'all_inputs_unchanged':True}
(P/'side-shell-review.json').write_text(json.dumps(r,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(8,7),constrained_layout=True);valid=[q for q in rows if q['current']];pos=np.array([q['current']['entry_mm'] for q in valid]);val=np.array([q['current']['thickness_mm'] for q in valid]);im=ax.scatter(pos[:,0],pos[:,2],c=val,s=5,cmap='viridis',vmin=1,vmax=3);ax.set_aspect('equal');ax.set(xlabel='X mm',ylabel='Z mm',title='Actual v13 STL local skin-region inward ray wall samples');fig.colorbar(im,ax=ax,label='wall crossing mm');fig.savefig(P/'side-shell-review.png',dpi=150)
print(json.dumps({k:r[k] for k in ['summary','paired_valid_samples','new_paired_below_1mm_count','maximum_paired_reduction_mm']},indent=2))
