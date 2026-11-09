"""Create strict v3 head masks and a 2 mm geodesic feather; no model writes.

Run with Blender -b --python make_head_protection.py. All arrays follow the
unchanged vertex ordering of PRINT_01_Head_Shell in baseline-v0.3.blend.
"""
from pathlib import Path
import argparse, hashlib, heapq, json, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--deep-lock-mm',type=float,default=8.0)
ARGS=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
LOCK_MM=ARGS.deep_lock_mm
BASE=ROOT/'baseline-v0.3.blend'
SOURCE=ROOT/'source-protection-masks.npz'
with np.load(SOURCE) as archive:
    source={key:archive[key] for key in archive.files}
sv=source['vertices_mm'];sf=source['faces'];geod=source['outer_boundary_geodesic_mm']
tree=BVHTree.FromPolygons(sv.tolist(),sf.tolist(),all_triangles=True)
kd=KDTree(len(sv))
for i,p in enumerate(sv):kd.insert(Vector(p),i)
kd.balance()
bpy.ops.wm.open_mainfile(filepath=str(BASE))
ob=bpy.data.objects['PRINT_01_Head_Shell'];me=ob.data
points=np.array([ob.matrix_world @ v.co for v in me.vertices],float)
edges=np.array([e.vertices[:] for e in me.edges],np.int32)
n=len(points)
features=('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
masks={k:np.zeros(n,bool) for k in features}
deep=np.zeros(n,bool);ear=np.zeros(n,bool)
interpolated_geodesic=np.zeros(n,float);source_distances=np.zeros(n,float)
for i,p in enumerate(points):
    q,normal,tri,distance=tree.find_nearest(Vector(p))
    a,b,c=sv[sf[tri]];ab=b-a;ac=c-a;aq=np.array(q)-a
    aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=aq@ab;qc=aq@ac;den=aa*cc-bb*bb
    if abs(den)>1e-15:
        beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den
        bary=np.maximum([1-beta-gamma,beta,gamma],0.);bary/=bary.sum()
        g=float(bary@geod[sf[tri]])
    else:g=float(np.mean(geod[sf[tri]]))
    interpolated_geodesic[i]=g;source_distances[i]=distance
    deep[i]=distance<2.0 and g>=LOCK_MM
    x,y,z=p
    ear[i]=abs(x)>20 and 17<z<36 and distance<1.5
    if distance<3.0:
        nearest=kd.find(q)[1]
        for key in features:masks[key][i]=bool(source[key][nearest])
masks['source_deep_face']=deep
masks['ear_surface']=ear
# Preserve the already-frozen lower face, chin base and neck mechanics as well.
masks['all_below_z21mm']=points[:,2]<21
locked=np.logical_or.reduce(list(masks.values()))

# Bounded, multi-source Dijkstra along actual manifold mesh edges. Sources
# are every locked vertex; only its immediate free neighbors need queue entries.
# Distances beyond the feather radius are irrelevant and remain +inf.
radius=2.0
lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
rows=np.concatenate([edges[:,0],edges[:,1]])
cols=np.concatenate([edges[:,1],edges[:,0]])
weights=np.concatenate([lengths,lengths])
order=np.argsort(rows,kind='stable');rows=rows[order];cols=cols[order];weights=weights[order]
starts=np.r_[0,np.cumsum(np.bincount(rows,minlength=n))]
distance=np.full(n,np.inf);distance[locked]=0.
queue=[]
crossing=locked[rows]&~locked[cols]&(weights<radius)
for a,b,w in zip(rows[crossing],cols[crossing],weights[crossing]):
    if w<distance[b]:distance[b]=w;heapq.heappush(queue,(float(w),int(b)))
while queue:
    d,i=heapq.heappop(queue)
    if d>distance[i]+1e-12:continue
    for k in range(starts[i],starts[i+1]):
        j=int(cols[k]);nd=d+weights[k]
        if nd<radius and nd<distance[j]:
            distance[j]=nd;heapq.heappush(queue,(float(nd),j))
t=np.minimum(distance/radius,1.)
feather=t*t*t*(t*(t*6-15)+10)
feather[locked]=0.
assert np.all(feather[locked]==0)
assert np.isfinite(feather).all() and np.all((feather>=0)&(feather<=1))
vertex_hash=hashlib.sha256(points.astype('<f8').tobytes()).hexdigest()
np.savez_compressed(ROOT/'head-protection-weights.npz',
    locked=locked,feather_weight=feather,
    deep_lock_mm=np.array(LOCK_MM),
    deep_lock_interpolation=np.array('barycentric_geodesic_at_closest_source_surface'),
    source_geodesic_at_closest_surface_mm=interpolated_geodesic,
    source_surface_distance_mm=source_distances,
    distance_to_locked_mm_capped_at_2=np.minimum(distance,radius),
    baseline_vertices_mm=points,
    **masks)
report={'baseline_blend':str(BASE),'baseline_blend_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
        'source_masks_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'object':'PRINT_01_Head_Shell','units':'mm','vertices':n,'edges':len(edges),
        'baseline_world_vertices_f64_sha256':vertex_hash,
        'source_deep_lock_geodesic_mm':LOCK_MM,
        'source_deep_lock_interpolation':'Barycentric interpolation of source-vertex geodesic distance at the closest source-surface point; continuous across shared source-triangle edges.',
        'locked_count':int(locked.sum()),'free_count':int((~locked).sum()),
        'feather_band_free_vertices_count':int(np.sum((feather>0)&(feather<1))),
        'full_weight_vertices_count':int(np.sum(feather==1)),
        'region_counts':{k:int(v.sum()) for k,v in masks.items()},
        'distance_method':'Multi-source Dijkstra on baseline head mesh edges weighted by world Euclidean edge length; only distances below 2 mm are traversed.',
        'feather_method':'smootherstep(clamp(geodesic_distance_to_locked/2mm,0,1)); locked vertices have exactly zero.',
        'mask_scope':'Union of continuous-geodesic original-face deep mask, ear surface, original eye/mouth/nose/cheek/chin masks, plus pre-existing z<21mm lower-face/neck lock.',
        'usage':'Require unchanged baseline vertex count and order. Multiply the proposed displacement field by feather_weight; independently enforce displacement[locked]=0. Do not treat these masks as physical fit certification.'}
(ROOT/'head-protection-weights.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
