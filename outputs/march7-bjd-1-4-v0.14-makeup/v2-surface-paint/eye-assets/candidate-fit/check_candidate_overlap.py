from pathlib import Path
import hashlib,json
import numpy as np
import trimesh
import manifold3d as md
P=Path(__file__).resolve().parent
G=P/'hemisphere-eye-geometry.npz'
H=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.14/march7-head-shell-v0.14-draft.stl')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hg,hh=sha(G),sha(H)
assert hg=='66095c9290d198d613b03cc4e41cd7aa167a060ee96c3aacf30d7769c4e7729c'
assert hh=='d3ac436defacb1db2a9aca6da84b8e6f4fe3ee995591e095e5ac43b9624b7ada'
def solid(v,f):return md.Manifold(md.Mesh64(np.ascontiguousarray(v,dtype=np.float64),np.ascontiguousarray(f,dtype=np.uint64)))
m=trimesh.load_mesh(H,process=True);head=solid(m.vertices,m.faces);data=np.load(G)
rows=[]
for side in ['negative','positive']:
 c=solid(data['vertices_'+side],data['faces_'+side]);inter=head^c;mesh=inter.to_mesh64();v=np.array(mesh.vert_properties)[:,:3]
 r={'eye':side,'center_mm':data['center_'+side].tolist(),'cup_status':str(c.status()),'cup_volume_mm3':float(c.volume()),'intersection_status':str(inter.status()),'intersection_empty':bool(inter.is_empty()),'intersection_volume_mm3':float(inter.volume()),'intersection_bbox_min_mm':None if not len(v) else v.min(0).tolist(),'intersection_bbox_max_mm':None if not len(v) else v.max(0).tolist(),'intersection_vertex_count':len(v),'intersection_triangle_count':len(mesh.tri_verts),'intersection_components':[]}
 for part in inter.decompose():
  pm=part.to_mesh64();pv=np.array(pm.vert_properties)[:,:3]
  r['intersection_components'].append({'volume_mm3':float(part.volume()),'bbox_min_mm':pv.min(0).tolist(),'bbox_max_mm':pv.max(0).tolist()})
 rows.append(r);print(side,json.dumps(r),flush=True)
assert sha(G)==hg and sha(H)==hh
out={'head_sha256':hh,'eye_npz_sha256':hg,'all_inputs_unchanged':True,'units':'mm','candidate':'R9, nasal center shift 1.5 mm, forward center shift 2 mm','parts':rows,'scope':'Actual closed cup material versus actual head Boolean intersection only. Bounding boxes and overlap volume cannot by themselves prove that overlap is hidden inside the socket; external protrusion must be checked in the rendered scene or by a separate visibility test. No model was modified.'}
(P/'candidate-head-overlap.json').write_text(json.dumps(out,indent=2)+'\n')
