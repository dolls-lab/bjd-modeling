"""Paired crown exterior wall samples on final saved coordinates; no edits."""
from pathlib import Path
import numpy as np,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with np.load(R/'final-change-solution.npz') as z:s={k:z[k] for k in z.files}
with np.load(R/'crown-postprocess/crown-solution.npz') as z:cs={k:z[k] for k in z.files}
O=np.array([0.,14.5,50.]);N=np.array([0.,1.,.3]);N/=np.linalg.norm(N);centers=np.array([[-16.63362693786621,14.5,50],[16.63362693786621,14.5,50],[0,11.274858474731445,60.75047302246094]])
files=[R/'final-change-solution.npz',R/'march7-head-shell-v0.14-draft.stl',R/'march7-head-cap-v0.14-draft.stl'];hs={str(p):sha(p) for p in files};result={}
def stats(x):
 x=np.array(x);return {'count':len(x),'min_mm':float(x.min()),'p01_mm':float(np.percentile(x,1)),'p05_mm':float(np.percentile(x,5)),'median_mm':float(np.median(x))} if len(x) else {'count':0}
for tag in ['head','cap']:
 b=s[tag+'_before'];a=s[tag+'_after'];f=s[tag+'_triangles'];n=np.zeros_like(b);fn=np.cross(b[f[:,1]]-b[f[:,0]],b[f[:,2]]-b[f[:,0]])
 for j in range(3):np.add.at(n,f[:,j],fn)
 n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
 cut=np.sum((b-O)*N,axis=1);dm=np.linalg.norm(b[:,None]-centers[None],axis=2).min(1)
 eligible=(cs[tag+'_outer_distance_mm']<.2)&(b[:,2]>50)&(np.abs(cut)>1.25)&s[tag+'_crown_free']
 trees=[BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True) for v in [b,a]]
 def ray(v,tree,i):
  p=v[i];direction=-n[i];travel=.025
  for _ in range(8):
   q,nn,ti,dd=tree.ray_cast(Vector(p+direction*travel),Vector(direction),8.-travel)
   if ti is None:return {'status':'missing_opposing_exit'}
   total=travel+dd
   if total>.06 and np.dot(nn,n[i])<-.25:
    cutexit=abs(float(np.sum((np.array(q)-O)*N)))
    if cutexit<.6:return {'status':'seam_exit_short_chord','distance_mm':total,'exit_seam_distance_mm':cutexit}
    return {'status':'valid','thickness_mm':total,'exit_seam_distance_mm':cutexit}
   travel=total+.025
   if travel>=8:break
  return {'status':'no_unambiguous_opposing_exit'}
 groups={}
 for label,mask,limit in [('ordinary_shell',eligible&(dm>=9),900),('near_internal_hardware',eligible&(dm<9),450)]:
  ids=np.flatnonzero(mask);ids=ids[np.linspace(0,len(ids)-1,min(limit,len(ids)),dtype=int)] if len(ids) else ids
  rows=[]
  for i in ids:rows.append({'vertex_id':int(i),'before':ray(b,trees[0],i),'after':ray(a,trees[1],i)})
  paired=[q for q in rows if q['before']['status']=='valid' and q['after']['status']=='valid'];newthin=[q for q in paired if q['before']['thickness_mm']>=.6 and q['after']['thickness_mm']<.6]
  reductions=sorted(paired,key=lambda q:q['before']['thickness_mm']-q['after']['thickness_mm'],reverse=True)
  groups[label]={'eligible_vertices':int(mask.sum()),'sampled':len(ids),'paired_valid':len(paired),'before':stats([q['before']['thickness_mm'] for q in paired]),'after':stats([q['after']['thickness_mm'] for q in paired]),'new_paired_below0p6mm_count':len(newthin),'excluded_status_counts':{period:{status:sum(q[period]['status']==status for q in rows) for status in ['seam_exit_short_chord','missing_opposing_exit','no_unambiguous_opposing_exit']} for period in ['before','after']},'worst_reductions':reductions[:8],'sample_vertex_ids':ids.tolist()}
 result[tag]=groups
r={'files':hs,'method':'Deterministic original vertex-normal inward rays from corresponding v13/v14 exterior points. Original external-distance<0.2mm; z>50; start farther than1.25mm from cut plane. Accept opposing wall within8mm, exclude exits within0.6mm of seam as seam chords. Ordinary and within9mm of actual internal hardware reported separately.','parts':result,'new_paired_below0p6mm_count':sum(g['new_paired_below0p6mm_count'] for part in result.values() for g in part.values()),'limitations':'Finite directional samples, not a continuous minimum-wall certificate; missing/seam-exit rays are retained as counts and never treated as wall thickness. Independent complete assembly and intersection checks are separate.','inputs_unchanged':all(sha(Path(p))==h for p,h in hs.items())}
(R/'crown-wall-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({tag:{k:{q:v[q] for q in ['sampled','paired_valid','before','after','new_paired_below0p6mm_count']} for k,v in val.items()} for tag,val in result.items()},indent=2),flush=True)
p=R/'preservation-report.json';j=json.loads(p.read_text());j['crown_wall_sampling']={'report':'crown-wall-review.json','sha256':sha(R/'crown-wall-review.json'),'new_paired_below0p6mm_count':r['new_paired_below0p6mm_count'],'not_a_global_minimum_certificate':True};p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
