"""Paired local normal-ray chords on changed eye-region vertices; no mesh edits."""
from pathlib import Path
import json,hashlib,time
import numpy as np
import manifold3d as md
R=Path(__file__).resolve().parent
from final_eye_inputs import load_final,expected_head,confirm_unchanged
d,integrity=load_final(expected_head());h=integrity['solution_sha256'];hs=integrity['head_sha256']
B=d['before'].astype('f4').astype('f8');V=d['after'].astype('f4').astype('f8');F=d['triangles'];ids=np.flatnonzero(np.any(B!=V,axis=1)&d['free'])
n=np.zeros_like(B);fn=np.cross(B[F[:,1]]-B[F[:,0]],B[F[:,2]]-B[F[:,0]])
for j in range(3):np.add.at(n,F[:,j],fn)
n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
def solid(v):return md.Manifold(md.Mesh64(np.ascontiguousarray(v),np.ascontiguousarray(F,dtype=np.uint64)))
solids=[solid(B),solid(V)];started=time.time()
def chords(s,v):
 out=np.full(len(ids),np.nan);hitpoints=np.full((len(ids),3),np.nan)
 for k,i in enumerate(ids):
  p=v[i];direction=-n[i]
  hits=s.ray_cast((p+.025*direction).tolist(),(p+8*direction).tolist())
  for hit in hits:
   distance=float(np.dot(np.array(hit.position)-p,direction))
   if distance>.06 and np.dot(hit.normal,n[i])<-.2:
    out[k]=distance;hitpoints[k]=hit.position;break
 return out,hitpoints
before,hitb=chords(solids[0],B);after,hita=chords(solids[1],V);valid=np.isfinite(before)&np.isfinite(after)
def stats(a):
 a=a[np.isfinite(a)]
 return dict(count=len(a),minimum_mm=None if len(a)==0 else float(a.min()),p01_mm=None if len(a)==0 else float(np.percentile(a,1)),p05_mm=None if len(a)==0 else float(np.percentile(a,5)),median_mm=None if len(a)==0 else float(np.median(a)),below_0p4=int((a<.4).sum()),below_0p6=int((a<.6).sum()))
def row(k):
 return dict(vertex_id=int(ids[k]),baseline_point_mm=B[ids[k]].tolist(),candidate_point_mm=V[ids[k]].tolist(),baseline_direction=(-n[ids[k]]).tolist(),baseline_chord_mm=float(before[k]),candidate_chord_mm=float(after[k]),reduction_mm=float(before[k]-after[k]),baseline_opposing_hit_mm=hitb[k].tolist(),candidate_opposing_hit_mm=hita[k].tolist())
v=B[ids];x=np.abs(v[:,0]);z=v[:,2];y=v[:,1]
groups={'all_changed_eye_vertices':np.ones(len(ids),bool),'outer_corner':(x>=17)&(z>=26)&(z<=31.5)&(y<-18),'upper_eye':(z>=30.5)&(x>=6.5)&(x<=20.5)&(y<-18),'lower_eye':(z<=24.5)&(y<-18),'inner_eye':(x<=10)&(y<-20)}
reports={}
for name,mask in groups.items():
 paired=valid&mask;loss=before-after;worst=np.flatnonzero(paired)[np.argsort(loss[paired])[-8:][::-1]];smallest=np.flatnonzero(paired)[np.argsort(after[paired])[:8]]
 reports[name]=dict(sampled_vertices=int(mask.sum()),before=stats(before[mask]),after=stats(after[mask]),paired_valid=int(paired.sum()),missing_before=int((mask&~np.isfinite(before)).sum()),missing_after=int((mask&~np.isfinite(after)).sum()),new_below_0p4=int((paired&(before>=.4)&(after<.4)).sum()),new_below_0p6=int((paired&(before>=.6)&(after<.6)).sum()),worst_reductions=[row(k) for k in worst],smallest_candidate_chords=[row(k) for k in smallest])
confirm_unchanged(integrity)
report=dict(solution_sha256=h,actual_stl_sha256=hs,input_unchanged=True,input_integrity=integrity,method='All actual-float32 changed eye vertices: same baseline area-weighted vertex normal defines inward rays from before/after positions, starting0.025mm inward; accept first opposing-oriented hit (<−0.2 normal dot) beyond0.06mm and within8mm. This is a paired local regression screen, not a global minimum-wall certificate.',limitations=['Large chord reductions can change the opposing target from a distant surface across a concavity to a nearer rim; inspect hit coordinates rather than interpreting such values as physical material losses.','Normals are held to the baseline for paired comparison; curved rims and very oblique directions can give tangential chords rather than manufacturing wall thickness.','No physical printing or resin strength criterion is established. Threshold counts are descriptive regression flags, not acceptance certification.','A missing opposing hit is reported, never replaced by a fabricated thickness.'],groups=reports,duration_seconds=time.time()-started)
(R/'eye-wall-chord-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{q:v for q,v in val.items() if q not in ('worst_reductions','smallest_candidate_chords')} for k,val in reports.items()},indent=2),flush=True)
