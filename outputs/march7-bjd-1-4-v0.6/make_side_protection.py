"""Source-origin protection on the immutable v5 baseline; writes only NPZ/JSON."""
from pathlib import Path
import hashlib, heapq, json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline-v0.5.blend'
PROV=OUT/'v5-master-source-provenance.npz'
RADIUS=5.0
def filehash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ahash(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
before_sha=filehash(BASE)
with np.load(PROV) as arc:prov={k:arc[k] for k in arc.files}
bpy.ops.wm.open_mainfile(filepath=str(BASE))
def snapshot(name):
 ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
 return dict(vertices=np.array([ob.matrix_world@v.co for v in me.vertices],dtype='<f8'),
             edges=np.array([e.vertices[:] for e in me.edges],dtype='<i4'),
             loops=np.array([l.vertex_index for l in me.loops],dtype='<i4'),
             polygon_sizes=np.array([len(p.vertices) for p in me.polygons],dtype='<i4'),
             triangles=np.array([t.vertices[:] for t in me.loop_triangles],dtype='<i4'),
             triangle_polygon_index=np.array([t.polygon_index for t in me.loop_triangles],dtype='<i4'))
master=snapshot('EDITABLE_Outer_Surface_Before_Hollowing')
head=snapshot('PRINT_01_Head_Shell')
assert np.array_equal(master['vertices'],prov['master_vertices_mm'])
assert np.array_equal(master['triangles'],prov['master_triangles'])
assert np.array_equal(master['triangle_polygon_index'],prov['master_triangle_polygon_index'])
master_locked=prov['source_any_incident'].copy()
source_class=prov['master_polygon_source_class']
triangle_class=source_class[master['triangle_polygon_index']]
tree=BVHTree.FromPolygons(master['vertices'].tolist(),master['triangles'].tolist(),all_triangles=True)
n=len(head['vertices'])
head_locked=np.zeros(n,bool);nearest_triangle=np.empty(n,np.int32);nearest_dist=np.empty(n)
nearest_bary=np.zeros((n,3));shared_boundary=np.zeros(n,bool)
for i,p in enumerate(head['vertices']):
 q,normal,ti,distance=tree.find_nearest(Vector(p));nearest_triangle[i]=ti;nearest_dist[i]=distance
 ids=master['triangles'][ti];a,b,c=master['vertices'][ids];ab=b-a;ac=c-a;ap=np.array(q)-a
 aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=ap@ab;qc=ap@ac;den=aa*cc-bb*bb
 if abs(den)>1e-15:
  beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den
  bary=np.maximum([1-beta-gamma,beta,gamma],0.);bary/=bary.sum()
 else:
  bary=np.zeros(3);bary[np.argmin(np.linalg.norm(master['vertices'][ids]-q,axis=1))]=1.
 nearest_bary[i]=bary
 # On the source/new-shell boundary, a tie may return an added triangle.
 # Lock projections supported entirely by original-source incident vertices.
 shared_boundary[i]=float(bary@master_locked[ids])>=1.-1e-6
 head_locked[i]=triangle_class[ti]!=3 or shared_boundary[i]

def feather(points,edges,locked):
 n=len(points);lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
 rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]];lens=np.r_[lengths,lengths]
 order=np.argsort(rows,kind='stable');rows=rows[order];cols=cols[order];lens=lens[order]
 starts=np.r_[0,np.cumsum(np.bincount(rows,minlength=n))]
 dist=np.full(n,np.inf);dist[locked]=0.;queue=[]
 crossing=locked[rows]&~locked[cols]&(lens<RADIUS)
 for b,w in zip(cols[crossing],lens[crossing]):
  if w<dist[b]:dist[b]=w;heapq.heappush(queue,(float(w),int(b)))
 while queue:
  d,i=heapq.heappop(queue)
  if d>dist[i]+1e-12:continue
  for k in range(starts[i],starts[i+1]):
   j=int(cols[k]);nd=d+lens[k]
   if nd<RADIUS and nd<dist[j]:dist[j]=nd;heapq.heappush(queue,(float(nd),j))
 t=np.minimum(dist/RADIUS,1.);weight=t*t*t*(t*(t*6-15)+10);weight[locked]=0.
 assert np.isfinite(weight).all()
 return weight,np.minimum(dist,RADIUS)

# Independently retain the established raw-PMX eye/nose/lip/cheek/chin ROI
# definition as an audit. It does not select generated cranium by a broad box.
with np.load(ROOT/'source-protection-masks.npz') as arc:raw={k:arc[k] for k in arc.files}
sv=raw['vertices_mm'];sf=raw['faces']
rawtree=BVHTree.FromPolygons(sv.tolist(),sf.tolist(),all_triangles=True)
kd=KDTree(len(sv))
for i,p in enumerate(sv):kd.insert(Vector(p),i)
kd.balance()
features=('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
feature_checks={};feature_masks={}
for key,obj,locked in [('master',master,master_locked),('head',head,head_locked)]:
 masks={name:np.zeros(len(obj['vertices']),bool) for name in features}
 for i,p in enumerate(obj['vertices']):
  q,normal,ti,d=rawtree.find_nearest(Vector(p))
  if d<3.0:
   nearest=kd.find(q)[1]
   for name in features:masks[name][i]=raw[name][nearest]
 feature_masks[key]=masks
 feature_checks[key]={name:{'vertices':int(mask.sum()),'unlocked_vertices':int((mask&~locked).sum())} for name,mask in masks.items()}

initial_feature_checks=feature_checks
extra_feature_locks={};extra_feature_info={};feature_checks={}
for key,obj,locked in [('master',master,master_locked),('head',head,head_locked)]:
 feature_union=np.logical_or.reduce(list(feature_masks[key].values()))
 extra=feature_union&~locked;extra_feature_locks[key]=extra
 pts=obj['vertices'][extra]
 extra_feature_info[key]={'vertices':int(extra.sum()),'bounds_mm':[pts.min(0).tolist(),pts.max(0).tolist()] if len(pts) else None}
 locked|=feature_union
 feature_checks[key]={name:{'vertices':int(mask.sum()),'unlocked_vertices':int((mask&~locked).sum())} for name,mask in feature_masks[key].items()}
master_feather,master_distance=feather(master['vertices'],master['edges'],master_locked)
head_feather,head_distance=feather(head['vertices'],head['edges'],head_locked)

arrays={'master_locked':master_locked,'master_feather_weight':master_feather,
        'head_locked':head_locked,'head_feather_weight':head_feather,
        'master_distance_to_source_locked_mm_capped_at_5':master_distance,
        'head_distance_to_source_locked_mm_capped_at_5':head_distance,
        'master_polygon_source_class':source_class,'master_triangle_source_class':triangle_class,
        'head_nearest_master_triangle':nearest_triangle,'head_nearest_master_barycentric':nearest_bary,
        'head_nearest_master_distance_mm':nearest_dist,'head_shared_boundary_lock':shared_boundary,
        'master_source_face_incident':prov['source_face_incident'],'master_source_ear_incident':prov['source_ear_incident'],
        'master_source_any_incident':prov['source_any_incident'],
        'master_source_closure_incident':prov['source_closure_incident'],'master_added_shell_only':prov['added_shell_only'],
        'master_conservative_feature_addition':extra_feature_locks['master'],'head_conservative_feature_addition':extra_feature_locks['head'],
        'feather_radius_mm':np.array(RADIUS),'baseline_blend_sha256':np.array(before_sha)}
info={}
for key,obj,locked,weight in [('master',master,master_locked,master_feather),('head',head,head_locked,head_feather)]:
 for name,arr in obj.items():arrays[key+'_baseline_'+name]=arr
 hashes={name:ahash(arr) for name,arr in obj.items()}
 topology_sha=hashlib.sha256(obj['loops'].tobytes()+obj['polygon_sizes'].tobytes()+obj['triangles'].tobytes()).hexdigest()
 arrays[key+'_topology_sha256']=np.array(topology_sha)
 info[key]={'vertices':len(obj['vertices']),'edges':len(obj['edges']),'triangles':len(obj['triangles']),
            'locked':int(locked.sum()),'free':int((~locked).sum()),'feather_band_free':int(((weight>0)&(weight<1)).sum()),
            'full_weight_free':int((weight==1).sum()),'array_sha256':hashes,'topology_sha256':topology_sha}
 for name,mask in feature_masks[key].items():arrays[key+'_raw_feature_'+name]=mask
report={'baseline_blend':str(BASE),'baseline_blend_sha256':before_sha,'units':'mm',
        'source_provenance_npz':str(PROV),'source_provenance_sha256':filehash(PROV),
        'source_class_labels':{'0':'original PMX main face','1':'original PMX ear front/back UV islands','2':'mouth and eyelid overlay closure','3':'added cranium'},
        'master_lock_method':'All vertices incident to original face/ear/closure polygons, including 224 vertices shared with the added cranium. Exact indexed v5 topology verified against reconstructed source-origin subdivision. Additionally lock the established feature ROI union; only near-chin added shell needs this conservative addition.',
        'head_lock_method':'Closest actual v5 master triangle has class 0/1/2, OR its closest point barycentric support is entirely on master source-locked vertices (weight >=1-1e-6). Same rule for inner and outer walls. Additionally retain the established feature ROI union; no broad ear distance box or Z lock.',
        'feather_method':'Independent master/head mesh-edge shortest paths from locked vertices, Euclidean edge weights, capped at 5 mm. smootherstep(distance/5), exact zero on locked vertices.',
        'objects':info,'raw_feature_roi_checks':feature_checks,
        'raw_feature_roi_checks_before_conservative_addition':initial_feature_checks,'conservative_feature_addition':extra_feature_info,
        'all_raw_feature_rois_locked':all(v['unlocked_vertices']==0 for group in feature_checks.values() for v in group.values()),
        'mechanical_constraints':'Not included. Root must separately exclude cap, magnets, neck socket and other hardware from displacement.',
        'nearest_surface_limit':'Head provenance is a nearest-master-surface mapping, not a historical construction label for voxelized print vertices. Ear cavity and nearby skull may be spatially close; diagnostic nearest triangles/distances/barycentrics are retained.',
        'baseline_unchanged':filehash(BASE)==before_sha}
assert report['baseline_unchanged']
np.savez_compressed(OUT/'v6-side-protection.npz',**arrays)
(OUT/'v6-side-protection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
