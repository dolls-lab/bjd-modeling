"""V11 protection proposal on actual v10 mother; no model modifications."""
from pathlib import Path
import hashlib,heapq,json
import numpy as np
R=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.10')
OUT=Path(__file__).resolve().parent
with np.load(R/'mother-surface.npz') as a:mother={k:a[k] for k in a.files}
with np.load(R/'central-source-protection.npz') as a:old={k:a[k] for k in a.files}
v=mother['after'];f=mother['triangles'];z=v[:,2]
old_core=old['master_core_locked'];features=old['master_feature_locked'];closures=old['master_source_closure_locked'];lower=old['master_lower_front_locked']
release=old_core&~features&~closures&~lower&(z>=35)
core=old_core&~release;ear=old['master_source_ear_incident'];locked=core|ear
edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
def distance(seed):
 n=len(v);lens=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
 rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]];ls=np.r_[lens,lens]
 order=np.argsort(rows,kind='stable');rows=rows[order];cols=cols[order];ls=ls[order]
 starts=np.r_[0,np.cumsum(np.bincount(rows,minlength=n))]
 dist=np.full(n,np.inf);dist[seed]=0.;queue=[]
 crossing=seed[rows]&~seed[cols]
 for j,w in zip(cols[crossing],ls[crossing]):
  if w<dist[j]:dist[j]=w;heapq.heappush(queue,(float(w),int(j)))
 while queue:
  di,i=heapq.heappop(queue)
  if di>dist[i]+1e-12:continue
  for k in range(starts[i],starts[i+1]):
   j=int(cols[k]);nd=di+ls[k]
   if nd<dist[j]:dist[j]=nd;heapq.heappush(queue,(float(nd),j))
 return dist
def ss(t):
 t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))
dc=distance(core);de=distance(ear)
arrays={'master_baseline_vertices':v,'master_baseline_triangles':f,'master_baseline_edges':edges,
 'master_old_core_locked':old_core,'master_nonfeature_forehead_release':release,
 'master_core_locked':core,'master_ear_locked':ear,'master_locked':locked,
 'master_feature_locked':features,'master_closure_locked':closures,'master_lower_front_locked':lower,
 'master_distance_to_core_mm':dc,'master_distance_to_ear_mm':de,
 'master_top_reference_z_ge_60':z>=60,'master_back_reference_y_ge_0':v[:,1]>=0,
 'baseline_v10_mother_sha256':np.array(hashlib.sha256((R/'mother-surface.npz').read_bytes()).hexdigest())}
for radius in (3,5,8):
 arrays[f'master_core_weight_{radius}mm']=ss(dc/radius)
 arrays[f'master_combined_weight_{radius}mm']=np.minimum(ss(dc/radius),ss(de/3))
for k in old:
 if k.startswith('master_raw_feature_'):arrays[k]=old[k]
assert np.all(core[features|closures|lower])
assert not np.any(release&ear)
def info(m):return {'count':int(m.sum()),'bounds_mm':[v[m].min(0).tolist(),v[m].max(0).tolist()]}
report={
 'baseline':'Actual v10 mother after array, same 45548-vertex topology.',
 'baseline_v10_mother_sha256':str(arrays['baseline_v10_mother_sha256']),
 'old_core':info(old_core),'new_core':info(core),'released_nonfeature_forehead':info(release),'all_ear_locked':info(ear),
 'release_rule':'Old core, not any established eye2mm/nose/mouth2mm/cheek/chin feature, not mouth/eyelid closure, not lower front face, and Z>=35mm. This only releases the upper nonfeature portion of the former |X|<=16,Z<=39 rectangular central-forehead hard lock.',
 'all_feature_and_closure_vertices_retained':True,
 'transition':'True v10 triangulated-mesh edge geodesic; 3/5/8mm quintic smootherstep from revised core; ear all exact, optional3mm collar. Weights are continuous displacement amplitudes, not anatomical source classes or hard caps.',
 'shape_scope':'Solver must additionally keep actual back/top fixed and restrict deformation to the requested frontal slope. This file is protection only, not a second skull-shape target. Prefer smooth broad YZ curvature reference; do not copy v8 XZ/XY contour or resurrect its lateral square corners.',
 'optional_top_back_reference_masks':'Z>=60 and Y>=0 masks are offered as reference indicators; root/geometry agent chooses the precise unchanged crown/posterior domain and its smooth boundary.',
 'expected_exact_regions':'Every eye/nose/mouth/cheek/chin feature, every closure, and whole original ear including root. Revised core and ear are also exact. Released forehead displacement must be reported separately.',
}
np.savez_compressed(OUT/'v11-forehead-protection.npz',**arrays)
(OUT/'v11-forehead-protection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
