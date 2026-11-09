"""Read-only ear/temple junction intersection check for final v8 STL geometry."""
from pathlib import Path
import json,hashlib,time
import numpy as np,trimesh
from triangle_intersection_helpers import intersection
R=Path(__file__).resolve().parent;B=R.parent/'march7-bjd-1-4-v0.7';start=time.time();eps=1e-6
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stl=R/'march7-head-shell-v0.8-draft.stl';stlsha=sha(stl);solpath=R/'head-solution.npz';solsha=sha(solpath)
s=np.load(solpath);before=np.load(B/'head-deformation.npz')['after'];after=np.load(R/'head-deformation.npz')['after'];f=s['triangles']
assert np.array_equal(before,s['before']);assert np.array_equal(after,s['after'].astype(np.float32).astype(np.float64))
T0=before[f];T1=after[f]
t=trimesh.load_mesh(stl,process=False,validate=False)
assert np.array_equal(t.triangles,T1),'actual STL facets differ from indexed final arrays'
c0=np.cross(T0[:,1]-T0[:,0],T0[:,2]-T0[:,0]);c1=np.cross(T1[:,1]-T1[:,0],T1[:,2]-T1[:,0]);a0=np.linalg.norm(c0,axis=1);a1=np.linalg.norm(c1,axis=1);dot=np.einsum('ij,ij->i',c0,c1)/np.maximum(a0*a1,1e-30)
delta=after-before;changed=np.max(np.linalg.norm(delta,axis=1)[f],axis=1)>eps;lo=T1.min(1);hi=T1.max(1)
region=(hi[:,1]>=-7)&(lo[:,1]<=12)&(hi[:,2]>=16)&(lo[:,2]<=53)&((hi[:,0]>=17)|(lo[:,0]<=-17))
ids=np.flatnonzero(region);ids=ids[np.argsort(lo[ids,2],kind='stable')];lz=lo[ids,2];tests=0;hits=[]
print('region triangles',len(ids),'changed',int((changed&region).sum()),flush=True)
for k,i in enumerate(ids):
 end=np.searchsorted(lz,hi[i,2]+eps,side='right');js=ids[k+1:end]
 possible=np.all(lo[js]<=hi[i]+eps,axis=1)&np.all(hi[js]>=lo[i]-eps,axis=1)&(changed[i]|changed[js])
 for j in js[possible]:
  if np.any(f[i][:,None]==f[j][None,:]):continue
  tests+=1;hit=intersection(T1[i],T1[j])
  if hit is None:continue
  old=intersection(T0[i],T0[j]);hit.update(triangles=[int(i),int(j)],centroid_mm=np.vstack((T1[i],T1[j])).mean(0).tolist(),present_in_v7=old is not None);hits.append(hit)
assert sha(stl)==stlsha and sha(solpath)==solsha
r={'actual_stl':str(stl),'actual_stl_sha256':stlsha,'solution_sha256':solsha,'actual_stl_facets_match_final_array_exactly':True,'before_matches_delivered_v7':True,'source_locked_max_displacement_mm':float(np.linalg.norm(delta[s['source_locked']],axis=1).max()),'locked_max_displacement_mm':float(np.linalg.norm(delta[s['locked']],axis=1).max()),'yz_max_displacement_mm':float(abs(delta[:,1:]).max()),'normal_rotation_over_90_count':int((dot<0).sum()),'degenerate_triangles':int((a1<1e-12).sum()),'minimum_normal_dot':float(dot.min()),'scope':'Both sides |X|>=17, Y -7..12, Z16..53; includes ear-root and temple source junctions. Pairs sharing any vertex are excluded; at least one triangle must change. This is a local intersection check, not a universal full-model proof.','region_triangles':len(ids),'changed_region_triangles':int((changed&region).sum()),'nonadjacent_aabb_pairs_checked':tests,'tolerance_mm':eps,'projected_polygon_rejection':True,'pairs':hits,'new_strict_intersections_vs_v7':sum(not h['present_in_v7'] and h['kind'] in ('transverse_crossing','coplanar_overlap') for h in hits),'new_ambiguous_contacts_vs_v7':sum(not h['present_in_v7'] and h['kind'] not in ('transverse_crossing','coplanar_overlap') for h in hits),'source_files_unchanged_during_check':True,'duration_seconds':time.time()-start}
(R/'local-junction-intersection-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
