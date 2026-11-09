from pathlib import Path
import numpy as np,json,hashlib
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
O=Path(__file__).resolve().parent;p=O/'front-solution.npz';s=np.load(p);F=s['triangles'];V=s['after'];B=s['before'];R=s['reference_v10'];h=hashlib.sha256(p.read_bytes()).hexdigest()
e,inv,c=np.unique(np.sort(np.concatenate([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]),axis=1),axis=0,return_inverse=True,return_counts=True);order=np.argsort(inv,kind='stable');start=np.r_[0,np.cumsum(c)[:-1]];ff=np.tile(np.arange(len(F)),3);interior=np.flatnonzero(c==2);fa=ff[order[start[interior]]];fb=ff[order[start[interior]+1]];ei=e[interior]
def angles(v):
 T=v[F];N=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);N/=np.maximum(np.linalg.norm(N,axis=1)[:,None],1e-30);return np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',N[fa],N[fb]),-1,1)))
angle={label:angles(v) for label,v in [('v10',R),('v11',B),('v12_front',V)]};length=np.linalg.norm(B[e[:,0]]-B[e[:,1]],axis=1);graph=coo_matrix((np.r_[length,length],(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(B),len(B))).tocsr();features=[('upper_negative',[113,17599]),('upper_positive',[1059,16397]),('outer_negative',[80,9049]),('outer_positive',[1092,3458])];results=[]
for name,pair in features:
 pair=np.sort(pair);j=np.flatnonzero(np.all(ei==pair,axis=1))[0];dist=dijkstra(graph,directed=False,indices=pair,min_only=True);row={'name':name,'vertex_ids':pair.tolist(),'v11_center_mm':B[pair].mean(0).tolist(),'v12_center_mm':V[pair].mean(0).tolist(),'dihedral_degrees':{k:float(a[j]) for k,a in angle.items()},'vertex_displacements_xyz_mm':(V[pair]-B[pair]).tolist(),'vertex_displacement_lengths_mm':np.linalg.norm(V[pair]-B[pair],axis=1).tolist(),'solver_weights':s['weights'][pair].tolist(),'current_eye_edge_geodesic_mm':s['eye_distance_mm'][pair].tolist(),'neighborhoods':[]}
 for radius in [1.5,3.0]:
  select=np.max(dist[ei],axis=1)<=radius;row['neighborhoods'].append({'radius_mm':radius,'edge_count':int(select.sum()),'method':'Same interior-edge set in each version; both endpoints within baseline-v11 graph-geodesic radius of the original feature edge vertices.','dihedral_summary_degrees':{label:{'mean':float(a[select].mean()),'p95':float(np.percentile(a[select],95)),'max':float(a[select].max())} for label,a in angle.items()}})
 results.append(row)
report={'solution':str(p),'solution_sha256':h,'input_unchanged':hashlib.sha256(p.read_bytes()).hexdigest()==h,'units':'mm','normal_dihedral_definition':'acos(dot(normal of each adjacent triangle)); smaller angle means more nearly coplanar neighboring triangles. This diagnoses mesh creases and does not by itself certify aesthetic curvature or likeness.','features':results}
(O/'front-horn-review.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(r['name'],r['dihedral_degrees'],'moves',r['vertex_displacement_lengths_mm'],'neighborhoods',r['neighborhoods'])
