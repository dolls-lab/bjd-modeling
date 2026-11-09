"""Read-only distance/orientation and exterior-ray audit of v5 source surfaces."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
with np.load(ROOT/'v6-side-protection.npz') as a:p={k:a[k] for k in a.files}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'baseline-v0.5.blend'))
m=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing'];h=bpy.data.objects['PRINT_01_Head_Shell']
mv=p['master_baseline_vertices'];hv=p['head_baseline_vertices'];mt=p['master_baseline_triangles'];ht=p['head_baseline_triangles']
assert np.array_equal(hv,np.array([v.co[:] for v in h.data.vertices]))
mn=np.array([v.normal[:] for v in m.data.vertices]);hn=np.array([v.normal[:] for v in h.data.vertices])
nearest=p['head_nearest_master_triangle'];bary=p['head_nearest_master_barycentric']
cls=p['master_triangle_source_class'][nearest];d=p['head_nearest_master_distance_mm']
q=np.einsum('ij,ijk->ik',bary,mv[mt[nearest]])
normal=np.einsum('ij,ijk->ik',bary,mn[mt[nearest]])
normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-15)
alignment=np.einsum('ij,ij->i',hn,normal)
signed=np.einsum('ij,ij->i',hv-q,normal)
def ds(a):return {'count':len(a),'min':float(a.min()),'median':float(np.median(a)),'p95':float(np.percentile(a,95)),'p99':float(np.percentile(a,99)),'max':float(a.max())} if len(a) else {'count':0}
report={'units':'mm','regions':{}}
for label,name in [(0,'face'),(1,'ear'),(2,'closure')]:
 base=cls==label
 rr={'all_distance':ds(d[base]),'normal_aligned_distance':ds(d[base&(alignment>.3)]),
     'normal_aligned_and_signed_gt_minus1_distance':ds(d[base&(alignment>.3)&(signed>-1)]),
     'normal_opposed_distance':ds(d[base&(alignment<-.3)])}
 ids=np.flatnonzero(base&(alignment>.3));worst=ids[np.argsort(d[ids])[-12:]]
 rr['farthest_normal_aligned']=[{'vertex':int(i),'position':hv[i].tolist(),'distance':float(d[i]),'alignment':float(alignment[i]),'signed':float(signed[i])} for i in worst]
 report['regions'][name]=rr

# Start beyond the source surface and ray inward. These rays expose faces that
# are actually first hit from outside, independently of nearest-distance size.
headtree=BVHTree.FromPolygons(hv.tolist(),ht.tolist(),all_triangles=True)
mastertree=BVHTree.FromPolygons(mv.tolist(),mt.tolist(),all_triangles=True)
ray_hits=[]
for i in np.flatnonzero(p['master_source_any_incident']):
 origin=mv[i]+mn[i]*8.;direction=-mn[i]
 hit,hitn,ti,length=headtree.ray_cast(Vector(origin),Vector(direction),16.)
 if hit is None:continue
 hit=np.array(hit);hitn=np.array(hitn)
 loc,n,mi,md=mastertree.find_nearest(Vector(hit))
 ray_hits.append((i,ti,mi,md,float(np.dot(hitn,mn[i])),float(np.linalg.norm(hit-mv[i]))))
rh=np.array(ray_hits,float)
report['exterior_ray_hits']={}
for label,name in [(0,'face'),(1,'ear'),(2,'closure')]:
 mask=(p['master_triangle_source_class'][rh[:,2].astype(int)]==label)&(rh[:,4]>.3)
 report['exterior_ray_hits'][name]={'hit_distance_to_master':ds(rh[mask,3]),'ray_hit_to_launch_source_vertex':ds(rh[mask,5]),'over_0_65mm':int(np.sum(rh[mask,3]>.65))}
report['exterior_ray_outliers_over_0_65mm']=[]
for row in rh[(rh[:,3]>.65)&(rh[:,4]>.3)&(p['master_triangle_source_class'][rh[:,2].astype(int)]!=3)]:
 ids=ht[int(row[1])]
 report['exterior_ray_outliers_over_0_65mm'].append({'launch_source_vertex':int(row[0]),'launch_position_mm':mv[int(row[0])].tolist(),
  'hit_triangle':int(row[1]),'hit_triangle_center_mm':hv[ids].mean(0).tolist(),'hit_distance_to_master_mm':float(row[3]),
  'hit_triangle_corner_distances_mm':d[ids].tolist(),'hit_triangle_corner_normal_alignment':alignment[ids].tolist(),
  'hit_triangle_corner_signed_distance_mm':signed[ids].tolist(),
  'raw_feature_roi_corners':{name:int(p['head_raw_feature_'+name][ids].sum()) for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')}})
np.savez_compressed(ROOT/'head-source-surface-diagnostics.npz',distance_to_master_mm=d,normal_alignment=alignment,signed_normal_distance_mm=signed,nearest_source_class=cls,exterior_ray_records=rh)
(ROOT/'head-source-surface-diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
