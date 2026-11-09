"""Run with Blender Python. Produces only UV/masks; never opens or saves source Blend.

Mesh order is final-change-solution.npz head_after/head_triangles, matching actual v14.
No head coordinates, topology, or normals are modified. Per-corner UVs resolve raw
PMX UV islands separately. Original UV V is flipped once for Blender.
"""
from pathlib import Path
import sys,json,hashlib,time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
BASE=OUT.parent.parent/'march7-bjd-1-4-v0.14'
sys.path.insert(0,str(OUT))
from parse_pmx import load_pmx
SCALE=27.47544416498121;ORIGIN=18.16621208190918
source=Path(json.loads((BASE/'parameters.json').read_text())['source_pmx'])
inputs=[source,BASE/'final-change-solution.npz',BASE/'march7-head-shell-v0.14-draft.stl',BASE/'march7-bjd-head-v0.14-draft.blend']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial={str(p):sha(p) for p in inputs}
raw=load_pmx(source);mat=next(m for m in raw['materials'] if m['name']=='脸')
source_faces=raw['faces'][mat['start']:mat['end']][:,::-1].astype(np.int32)
source_vertices=raw['vertices'][:,[0,2,1]].copy();source_vertices[:,2]-=ORIGIN;source_vertices*=SCALE
source_normals=raw['normals'][:,[0,2,1]].copy()
source_uv=raw['uvs'].copy();source_uv[:,1]=1-source_uv[:,1]
z=np.load(BASE/'final-change-solution.npz');vertices=z['head_after'].astype(np.float64);faces=z['head_triangles'].astype(np.int32)
# UV islands use original indices, deliberately not welded positions.
parent=np.arange(len(source_vertices))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for tri in source_faces:
 a=root(int(tri[0]))
 for b in tri[1:]:parent[root(int(b))]=a
labels=np.array([root(int(f[0])) for f in source_faces]);classes=np.unique(labels);labels=np.searchsorted(classes,labels)
source_bvh=BVHTree.FromPolygons(source_vertices.tolist(),source_faces.tolist(),all_triangles=True)
head_bvh=BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True)
island_faces=[np.flatnonzero(labels==k) for k in range(len(classes))]
island_bvh=[BVHTree.FromPolygons(source_vertices.tolist(),source_faces[ids].tolist(),all_triangles=True) for ids in island_faces]
tri_xyz=source_vertices[source_faces];tri_uv=source_uv[source_faces];tri_normals=source_normals[source_faces]
head_normals=np.zeros_like(vertices)
fn=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
for k in range(3):np.add.at(head_normals,faces[:,k],fn)
head_normals/=np.maximum(np.linalg.norm(head_normals,axis=1,keepdims=True),1e-30)
def bary(p,tri):
 a,b,c=tri;e=b-a;f=c-a;q=p-a
 ee=e@e;ef=e@f;ff=f@f;eq=e@q;fq=f@q;den=ee*ff-ef*ef
 if abs(den)<1e-20:return np.array([1.,0,0])
 v=(ff*eq-ef*fq)/den;w=(ee*fq-ef*eq)/den
 x=np.clip([1-v-w,v,w],0,1);return x/np.sum(x)
def ramp(x):
 t=np.clip(x,0,1);return t*t*t*(10+t*(-15+6*t))
uv=np.zeros((len(vertices),2));dist=np.zeros(len(vertices));tri_ids=np.zeros(len(vertices),np.int32);normal_dot=np.zeros(len(vertices));visible=np.zeros(len(vertices),bool);first_hit_error=np.full(len(vertices),np.nan);weights=np.zeros(len(vertices))
t0=time.time();ray_retry_vertices=[];ray_retry_success=[]
for idx,p in enumerate(vertices):
 hit,_,ti,d=source_bvh.find_nearest(Vector(p));ti_ids=ti
 tri_ids[idx]=ti;dist[idx]=d
 bc=bary(np.asarray(hit),tri_xyz[ti]);uv[idx]=bc@tri_uv[ti]
 sn=bc@tri_normals[ti];sn/=max(np.linalg.norm(sn),1e-30)
 nd=sn@head_normals[idx];normal_dot[idx]=nd
 if d<4.0 and nd>0.05:
  # Certification that source-outward ray sees this exterior skin first.
  loc,_,_,depth=head_bvh.ray_cast(Vector(p+sn*10),Vector(-sn),10.2)
  if depth is not None:
   err=abs(depth-10.0);first_hit_error[idx]=err;visible[idx]=err<.12
  if not visible[idx]:
   # An exact vertex ray can numerically miss all incident triangles.
   # Four 1-micron tangential offsets test nearby surface interiors instead.
   ray_retry_vertices.append(idx)
   axis=np.array([0.,0.,1.]) if abs(sn[2])<.9 else np.array([1.,0.,0.])
   tangent=np.cross(sn,axis);tangent/=np.linalg.norm(tangent);tangent2=np.cross(sn,tangent)
   for offset in [tangent*.001,-tangent*.001,tangent2*.001,-tangent2*.001]:
    loc,_,_,depth2=head_bvh.ray_cast(Vector(p+sn*10+offset),Vector(-sn),10.2)
    if depth2 is not None and abs(depth2-10)<.12:
     first_hit_error[idx]=abs(depth2-10);visible[idx]=True;ray_retry_success.append(idx);break
  if visible[idx]:weights[idx]=float((1-ramp((d-.7)/3.3))*ramp((nd-.05)/.35))
 if idx%50000==0:print('MAP',idx,len(vertices),'seconds',time.time()-t0,flush=True)
# Per-loop representation prevents interpolation across separate ear/face atlas islands.
corner_uv=uv[faces].copy();corner_weight=weights[faces].copy();vertex_island=labels[tri_ids];face_island=vertex_island[faces[:,0]].copy()
mixed=np.flatnonzero(np.any(vertex_island[faces]!=vertex_island[faces[:,0]][:,None],axis=1))
for fi in mixed:
 center=vertices[faces[fi]].mean(0);_,_,ti,_=source_bvh.find_nearest(Vector(center));island=int(labels[ti]);face_island[fi]=island
 for k,vi in enumerate(faces[fi]):
  loc,_,li,d=island_bvh[island].find_nearest(Vector(vertices[vi]));ti=int(island_faces[island][li]);bc=bary(np.asarray(loc),tri_xyz[ti]);corner_uv[fi,k]=bc@tri_uv[ti]
  # If selected island is farther away, never expand an existing skin mask.
  corner_weight[fi,k]*=float(1-ramp((d-.7)/3.3))
tex_path=source.parent/raw['textures'][mat['texture_index']].replace('\\','/')
# Stable pale skin sample, away from blush/lip/eye/ear islands, in upper forehead.
import bpy
img=bpy.data.images.load(str(tex_path),check_existing=True);pixels=np.array(img.pixels[:]).reshape(img.size[1],img.size[0],4)
# This 8-bit PNG image buffer was independently checked against PIL: it exposes encoded sRGB values.
us=np.linspace(.43,.57,17);vs=np.linspace(.77,.82,11)
samples=np.array([pixels[int(v*(img.size[1]-1)),int(u*(img.size[0]-1)),:3] for u in us for v in vs]);base_srgb=np.median(samples,axis=0)
# Encode explicit linear and sRGB values; shader default socket expects linear.
base_linear=np.where(base_srgb<=.04045,base_srgb/12.92,((base_srgb+.055)/1.055)**2.4)
np.savez_compressed(OUT/'face-uv-transfer.npz',head_vertices=vertices,head_triangles=faces,head_uv_blender=corner_uv.astype(np.float32),head_makeup_weight=corner_weight.astype(np.float32),head_vertex_uv_blender=uv.astype(np.float32),head_vertex_makeup_weight=weights.astype(np.float32),head_vertex_source_triangle=tri_ids,head_vertex_source_island=vertex_island,head_face_source_island=face_island,head_source_distance_mm=dist.astype(np.float32),head_source_normal_dot=normal_dot.astype(np.float32),head_source_outward_visible=visible,head_first_hit_error_mm=first_hit_error.astype(np.float32),skin_base_linear_rgb=base_linear,skin_base_srgb_rgb=base_srgb,source_vertices=source_vertices,source_triangles=source_faces,source_uv_blender=source_uv)
assert all(sha(Path(p))==h for p,h in initial.items())
report={'inputs':initial,'input_hashes_unchanged':True,'head_vertices':len(vertices),'head_triangles':len(faces),'geometry_modified':False,'source_transform':'[PMX X, PMX Z, PMX Y - 18.16621208190918] * 27.47544416498121','source_material':mat,'texture_path':str(tex_path),'texture_sha256':sha(tex_path),'uv_convention':'Blender bottom-origin: (u, 1 - raw_pmx_v), flip already applied. Shape (triangle_count,3,2) is final head_triangles corner order.','mask_convention':'per-corner float 0..1; mix solid skin color at 0 with original texture at 1. Mask only affects material, never alpha or geometry.','method':'Nearest raw face triangle and barycentric original UV interpolation. Separate original-index connected UV islands for face/ear; mixed-island final triangles use the source island nearest their centroid and reproject their corners within it.','mask_method':'C2 distance fade 0.7..4.0 mm times source-to-head outward-normal agreement C2 0.05..0.40. Candidate point must be the first surface seen from 10 mm along interpolated source outward normal (tolerance 0.12 mm), excluding hidden inner walls/back-side projection. Failed exact-vertex rays are retried at four 0.001 mm tangential offsets to avoid vertex-hit numerical misses.','source_uv_islands':[{'island':k,'triangles':len(ids),'world_bounds_mm':[source_vertices[np.unique(source_faces[ids])].min(0).tolist(),source_vertices[np.unique(source_faces[ids])].max(0).tolist()]} for k,ids in enumerate(island_faces)],'mixed_island_head_triangles':len(mixed),'ray_retry':{'offset_mm':.001,'attempted_vertices':len(ray_retry_vertices),'recovered_vertices':len(ray_retry_success),'recovered_ids':ray_retry_success},'mask_counts':{'positive_vertices':int(np.count_nonzero(weights)),'weight_gt0p99':int(np.count_nonzero(weights>.99)),'normal_backfacing_positive':int(np.count_nonzero((normal_dot<=.05)&(weights>0))),'occluded_positive':int(np.count_nonzero((~visible)&(weights>0))),'back_y_gt4_positive':int(np.count_nonzero((vertices[:,1]>4)&(weights>0))),'distance_ge4_positive':int(np.count_nonzero((dist>=4)&(weights>0)))},'skin_base_linear_rgb':base_linear.tolist(),'skin_base_srgb_rgb':base_srgb.tolist(),'skin_sample':'Median original forehead UV u=.43..57, v_blender=.77..82, 8-bit PNG buffer independently verified equal to PIL encoded sRGB; explicitly decoded by IEC sRGB transfer function for shader socket.','limitations':['Preview-only appearance transfer, not printer color data.','Reconstructed cranial surfaces do not possess original PMX facial UV; they fade to matched skin.','Original eyebrows and eyelashes are separate source geometry and should be displayed separately, not baked into this face material.','Ray visibility is directional and a conservative material mask; it is not a global geometric visibility proof.','Original game shading is not reproduced by this UV transfer.'], 'duration_seconds':time.time()-t0}
(OUT/'uv-transfer-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('UV_TRANSFER_DONE',OUT/'face-uv-transfer.npz',report['mask_counts'],flush=True)
