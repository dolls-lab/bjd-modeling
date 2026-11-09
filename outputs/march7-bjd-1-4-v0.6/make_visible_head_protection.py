"""Refine v5 print protection to visible source sculpt plus raw feature ROIs.
Does not change the archived original protection mask or any model.
Run with Blender -b --python make_visible_head_protection.py.
"""
from pathlib import Path
import hashlib, heapq, json
import numpy as np
ROOT=Path(__file__).resolve().parent
with np.load(ROOT/'v6-side-protection.npz') as arc:p={k:arc[k] for k in arc.files}
with np.load(ROOT/'head-source-surface-diagnostics.npz') as arc:diag={k:arc[k] for k in arc.files}
LIMIT=.65;RADIUS=5.
points=p['head_baseline_vertices'];edges=p['head_baseline_edges'];n=len(points)
classes=p['master_triangle_source_class'][p['head_nearest_master_triangle']]
source_mapped=(classes!=3)|p['head_shared_boundary_lock']
visible=source_mapped&(p['head_nearest_master_distance_mm']<=LIMIT)
features=('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
feature_union=np.logical_or.reduce([p['head_raw_feature_'+name] for name in features])
locked=visible|feature_union
released=p['head_locked']&~locked
assert not np.any(locked&~p['head_locked'])
lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]];lengths=np.r_[lengths,lengths]
order=np.argsort(rows,kind='stable');rows=rows[order];cols=cols[order];lengths=lengths[order]
starts=np.r_[0,np.cumsum(np.bincount(rows,minlength=n))]
distance=np.full(n,np.inf);distance[locked]=0.;queue=[]
crossing=locked[rows]&~locked[cols]&(lengths<RADIUS)
for j,w in zip(cols[crossing],lengths[crossing]):
 if w<distance[j]:distance[j]=w;heapq.heappush(queue,(float(w),int(j)))
while queue:
 d,i=heapq.heappop(queue)
 if d>distance[i]+1e-12:continue
 for k in range(starts[i],starts[i+1]):
  j=int(cols[k]);nd=d+lengths[k]
  if nd<RADIUS and nd<distance[j]:distance[j]=nd;heapq.heappush(queue,(float(nd),j))
t=np.minimum(distance/RADIUS,1.);weight=t*t*t*(t*(t*6-15)+10);weight[locked]=0.
arrays={'head_locked':locked,'head_feather_weight':weight,'head_visible_source_locked':visible,
        'head_raw_feature_locked':feature_union,'head_old_source_locked_informational':p['head_locked'],
        'head_released_from_old_lock':released,'head_inner_wall_source_class':np.where(source_mapped&~visible,classes,-1).astype(np.int8),
        'head_nearest_master_source_class':classes,'head_distance_to_source_locked_mm_capped_at_5':np.minimum(distance,RADIUS),
        'head_baseline_vertices':points,'head_baseline_triangles':p['head_baseline_triangles'],
        'head_topology_sha256':p['head_topology_sha256'],'baseline_blend_sha256':p['baseline_blend_sha256'],
        'visible_distance_limit_mm':np.array(LIMIT),'feather_radius_mm':np.array(RADIUS)}
for label,name in [(0,'face'),(1,'ear'),(2,'closure')]:arrays['head_visible_source_'+name]=visible&(classes==label)
arrays['head_visible_source_shared_boundary']=visible&p['head_shared_boundary_lock']
for name in features:arrays['head_raw_feature_'+name]=p['head_raw_feature_'+name]
counts={name:int(np.sum(released&(classes==label))) for label,name in [(0,'face'),(1,'ear'),(2,'closure'),(3,'added_boundary')]}
surface_stats={}
for label,name in [(0,'face'),(1,'ear'),(2,'closure')]:
 region=(classes==label)&(diag['normal_alignment']>.3)&(diag['signed_normal_distance_mm']>-1)
 dd=p['head_nearest_master_distance_mm'][region]
 surface_stats[name]={'vertices':int(region.sum()),'max_distance_mm':float(dd.max()),'p99_distance_mm':float(np.percentile(dd,99)),'all_covered_by_visible_threshold':bool(np.all(dd<=LIMIT))}
report={'units':'mm','baseline_blend_sha256':str(p['baseline_blend_sha256']),
        'archived_mask_sha256':hashlib.sha256((ROOT/'v6-side-protection.npz').read_bytes()).hexdigest(),
        'visible_rule':'Nearest v5 master triangle class is original face/ear/closure or shared source boundary, and closest-master distance <=0.65 mm.',
        'actual_head_lock':'head_visible_source_locked OR independent established raw eye/mouth/nose/cheek/chin ROI union. Master mask remains unchanged.',
        'distance_evidence':surface_stats,
        'exterior_ray_evidence_file':'head-source-surface-diagnostics.json',
        'counts':{'original_head_locked':int(p['head_locked'].sum()),'head_visible_source_locked':int(visible.sum()),'head_raw_feature_locked':int(feature_union.sum()),'head_locked':int(locked.sum()),'released_old_lock':int(released.sum()),'released_by_nearest_master_source_class':counts},
        'all_raw_feature_rois_locked':all(not np.any(p['head_raw_feature_'+name]&~locked) for name in features),
        'released_region_semantics':'These are source-mapped points farther than 0.65 mm from the exterior master and outside independently protected feature ROIs. They are mostly inner cavity walls, but distance alone is not an exact topological inner/outer label. head_inner_wall_source_class uses -1 for other points; labels 0/1/2/3 follow original provenance.',
        'audit_requirement':'Strict zero only for visible source sculpt and raw feature ROI union. Old full head source lock regions remain informational and may move to preserve wall thickness.',
        'feather_method':'5 mm shortest path along actual head mesh edges; smootherstep. Consumers may use the field differently to preserve inner/outer wall translation; hard locks are independent.'}
np.savez_compressed(ROOT/'head-visible-source-protection.npz',**arrays)
(ROOT/'head-visible-source-protection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
