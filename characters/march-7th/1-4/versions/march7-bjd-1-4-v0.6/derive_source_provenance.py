from pathlib import Path
import json, sys, math
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from parse_pmx import load_pmx, topology
P=json.loads((ROOT/'parameters.json').read_text());src=load_pmx(P['source_pmx'])
mat=next(m for m in src['materials'] if m['name']=='脸')
fs=src['faces'][mat['start']:mat['end']]
scale=27.47544416498121;chin=18.16621208190918
rv=src['vertices'];world=np.column_stack([rv[:,0],rv[:,2],rv[:,1]-chin])*scale
parent=np.arange(len(rv))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for f in fs:
 for a,b in zip(f,np.roll(f,-1)):
  aa,bb=root(a),root(b)
  if aa!=bb:parent[aa]=bb
groups={}
for i in np.unique(fs):groups.setdefault(root(i),[]).append(int(i))
groups=sorted(groups.values(),key=len,reverse=True)
report={'raw_components':[]}
for gi,ids in enumerate(groups):
 p=world[ids];uv=src['uvs'][ids]
 report['raw_components'].append({'index':gi,'vertices':len(ids),'bounds_mm':[p.min(0).tolist(),p.max(0).tolist()],'uv_bounds':[uv.min(0).tolist(),uv.max(0).tolist()]})
ear_raw_ids=np.concatenate([np.asarray(g) for g in groups[1:]])
ear_triangles=np.all(np.isin(fs,ear_raw_ids),axis=1)
report['raw_ear_triangles']=int(ear_triangles.sum())

# Recreate only the topology generation, with source-origin material labels.
# Labels survive subdivision; no existing model is saved or modified.
top,raw,ff=topology(src['vertices'],fs)
verts=raw.tolist();faces=ff.tolist();labels=np.where(ear_triangles,1,0).tolist()
loops=top['boundary_loops']
for loop in loops:
 if loop['vertex_count'] not in (8,44):continue
 ids=loop['vertex_ids'];center=np.array(loop['vertices']).mean(0)
 if loop['vertex_count']==44:center[2]+=.012
 ci=len(verts);verts.append(center.tolist())
 for j,a in enumerate(ids):faces.append([a,ids[(j+1)%len(ids)],ci]);labels.append(2)
outer=next(l for l in loops if l['vertex_count']==56);prev=outer['vertex_ids']
rim=np.array(outer['vertices']);angles=np.arctan2((rim[:,1]-19.35)/1.06,rim[:,0]/.95)
target=np.column_stack([1.06*np.cos(angles),19.48+np.where(np.sin(angles)>0,1.34,1.0)*np.sin(angles),np.full(len(rim),.12)])
def ring(points):
 global prev
 ids=list(range(len(verts),len(verts)+len(points)));verts.extend(points.tolist())
 for j in range(len(ids)):faces.append([prev[j],prev[(j+1)%len(ids)],ids[(j+1)%len(ids)],ids[j]]);labels.append(3)
 prev=ids
for t in (.12,.25,.4,.55,.7,.85,1.0):
 blend=math.sin(t*math.pi/2);pp=rim*(1-blend)+target*blend;pp[:,2]=rim[:,2]*(1-t)+target[:,2]*t;ring(pp)
for phi in np.linspace(0,math.pi/2,15)[1:-1]:
 pts=target.copy();pts[:,0]*=math.cos(phi);pts[:,1]=19.48+(pts[:,1]-19.48)*math.cos(phi);pts[:,2]=.12+.98*math.sin(phi);ring(pts)
pole=len(verts);verts.append([0,19.48,1.10])
for j in range(len(prev)):faces.append([prev[j],prev[(j+1)%len(prev)],pole]);labels.append(3)
v=np.array(verts);v=np.column_stack([v[:,0],v[:,2],v[:,1]-chin])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'baseline-v0.5.blend'))
master=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing']
mv=np.array([v.co[:] for v in master.data.vertices]);master.data.calc_loop_triangles()
mt=np.array([t.vertices[:] for t in master.data.loop_triangles])
mp=np.array([t.polygon_index for t in master.data.loop_triangles])
mesh=bpy.data.meshes.new('TEMP_provenance_rebuild');mesh.from_pydata(v.tolist(),[],faces);mesh.update()
for label in ['original_face','original_ear','mouth_overlay_closure','added_cranium']:
 mesh.materials.append(bpy.data.materials.new('TEMP_'+label))
for poly,label in zip(mesh.polygons,labels):poly.material_index=label
ob=bpy.data.objects.new('TEMP_provenance_rebuild',mesh);bpy.context.scene.collection.objects.link(ob)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
sub=ob.modifiers.new('Original SUBSURF2','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
me=ob.data
same=len(me.vertices)==len(master.data.vertices) and len(me.polygons)==len(master.data.polygons) and all(sorted(a.vertices)==sorted(b.vertices) for a,b in zip(me.polygons,master.data.polygons))
report['provenance_topology_matches_v5_master']=bool(same)
if not same:raise RuntimeError('Provenance topology mismatch')
poly_labels=np.array([p.material_index for p in me.polygons],np.int8)
vertex_incident=np.zeros((4,len(mv)),bool)
for p in me.polygons:vertex_incident[p.material_index,list(p.vertices)]=True
source_face,source_ear,source_fill,added=vertex_incident
source_any=source_face|source_ear|source_fill;added_only=added&~source_any
report['provenance_counts']={'source_face_incident':int(source_face.sum()),'source_ear_incident':int(source_ear.sum()),'source_closure_incident':int(source_fill.sum()),'source_any_incident':int(source_any.sum()),'added_shell_only':int(added_only.sum()),'shared_original_face_added_shell_boundary':int((added&source_any).sum())}
tree=BVHTree.FromPolygons(world.tolist(),fs.tolist(),all_triangles=True)
nearest=[tree.find_nearest(Vector(p)) for p in mv]
dist=np.array([q[3] for q in nearest]);closest_tri=np.array([q[2] for q in nearest])
x,y,z=mv.T;old_ear=(np.abs(x)>20)&(z>17)&(z<36)&(dist<1.5)
report['old_ear_box_vs_provenance']={'all_old_ear_locked':int(old_ear.sum()),'genuine_ear_incident':int((old_ear&source_ear).sum()),'main_face_incident':int((old_ear&source_face).sum()),'added_shell_only_locked_incorrectly_as_ear':int((old_ear&added_only).sum()),'genuine_ear_vertices_missed_by_old_box':int((~old_ear&source_ear).sum()),'added_shell_only_below_z30':int((added_only&(z<30)).sum())}
for name,mask in [('added_only_old_ear',old_ear&added_only),('ear_missed_old_box',~old_ear&source_ear)]:
 p=mv[mask];report[name+'_bounds_mm']=[p.min(0).tolist(),p.max(0).tolist()] if len(p) else None

def segments(v,f,z):
 tris=v[f];segs=[]
 for tri in tris[(tris[:,:,2].min(1)<z)&(tris[:,:,2].max(1)>z)]:
  ps=[]
  for a,b in zip(tri,np.roll(tri,-1,axis=0)):
   if (a[2]-z)*(b[2]-z)<0:ps.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
  if len(ps)==2:segs.append(ps)
 return np.array(segs).reshape(-1,2,3)
def segment_stats(seg):
 pts=seg.reshape(-1,3);pos=pts[pts[:,0]>0]
 out={'positive_max_x_point':pos[pos[:,0].argmax()].tolist() if len(pos) else None,'x_at_y':{}}
 for yy in [-15,-10,-5,0,2,5,10,15]:
  hits=[]
  for a,b in seg:
   if (a[1]-yy)*(b[1]-yy)<0:
    q=a+(b-a)*((yy-a[1])/(b[1]-a[1]))
    if q[0]>0:hits.append(q[0])
  out['x_at_y'][str(yy)]=float(max(hits)) if hits else None
 return out
rawmain=fs[~ear_triangles];rawe=fs[ear_triangles]
raw_world=np.column_stack([raw[:,0],raw[:,2],raw[:,1]-chin])*scale
outerids=outer['vertex_ids'];boundary_segs=np.array([[raw_world[a],raw_world[outerids[(i+1)%len(outerids)]]] for i,a in enumerate(outerids)])
report['sections']=[]
for zz in [20,22,24,26,28,30,32,34,36,38,40]:
 boundary_hits=[]
 for a,b in boundary_segs:
  if (a[2]-zz)*(b[2]-zz)<0:
   q=a+(b-a)*((zz-a[2])/(b[2]-a[2]))
   if q[0]>0:boundary_hits.append(q.tolist())
 report['sections'].append({'z_mm':zz,'raw_main_face':segment_stats(segments(world,rawmain,zz)),'raw_ear':segment_stats(segments(world,rawe,zz)),'raw_outer_boundary_positive_x':boundary_hits,'v5_added_cranium':segment_stats(segments(mv,mt[poly_labels[mp]==3],zz))})
OUT=Path(__file__).parent
np.savez_compressed(OUT/'v5-master-source-provenance.npz',master_vertices_mm=mv,master_triangles=mt,master_triangle_polygon_index=mp,master_polygon_source_class=poly_labels,source_face_incident=source_face,source_ear_incident=source_ear,source_closure_incident=source_fill,source_any_incident=source_any,added_shell_only=added_only,raw_face_ear_triangle_mask=ear_triangles,raw_face_source_triangles=fs,raw_ear_vertex_ids=ear_raw_ids)
(OUT/'ear-source-components.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
