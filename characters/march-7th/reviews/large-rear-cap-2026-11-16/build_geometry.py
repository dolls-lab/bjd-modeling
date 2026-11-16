"""Rejoin the former narrow rear seam and resplit into face and crown/rear cap.
Source triangles retained outside old seam/internal support work and new cut.
"""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/private/tmp/bjd-hook-groove-deps')
import numpy as np,trimesh,manifold3d as mf
HERE=Path(__file__).resolve().parent
CHAR=HERE.parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(t):
 s=mf.Manifold(mf.Mesh64(np.asarray(t.vertices,dtype=float),np.asarray(t.faces,dtype=np.uint64)))
 assert s.status()==mf.Error.NoError,s.status()
 return s

def mesh(s):
 m=s.to_mesh64();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)

def cylinder(r,depth,center,axis):
 axis=np.asarray(axis,float);axis/=np.linalg.norm(axis)
 u=np.array([1.,0,0]);v=np.cross(axis,u)
 return mf.Manifold.cylinder(depth,r,r,160,False).transform(np.column_stack([u,v,axis,np.asarray(center)]))

def boundary_loops(t):
 t.remove_unreferenced_vertices();e=t.edges;es=np.sort(e,axis=1);_,inv,counts=np.unique(es,axis=0,return_inverse=True,return_counts=True)
 be=e[counts[inv]==1];mapping={int(a):int(b) for a,b in be}
 assert len(mapping)==len(be),('branched boundary',len(be),len(mapping))
 loops=[]
 while mapping:
  start=next(iter(mapping));loop=[start];cur=mapping.pop(start)
  while cur!=start:loop.append(cur);cur=mapping.pop(cur)
  loops.append(np.asarray(loop))
 return loops

def join_old_seam(head,cap,p):
 s=p['source_uniform_scale'];n=np.array([0,1.,.3]);n/=np.linalg.norm(n);o=np.array([0,14.5,50])*s
 R=np.column_stack([[1.,0,0],np.cross(n,[1.,0,0]),n]);gap=.25*s
 oldp=p['inherited_source_parameters'];centers=oldp['magnet_centers_mm']
 from smooth_old_magnet_cleanup import make_old_magnet_cutters
 cuts,cleanup=make_old_magnet_cutters(head,cap,s,source_parameters=p['inherited_source_parameters'])
 filled=[]
 for tag,obj in [('head',head),('cap',cap)]:
  so=solid(obj)
  for center in centers:
   c=np.asarray(center,float)
   d=oldp['magnet_hole_depth_mm'];r=oldp['magnet_hole_diameter_mm']/2
   a= -d-.01 if tag=='head' else gap
   # Coplanar hole cover is removed with the whole former end-face.
   so=so+cylinder(r+.03,d+.01,c+n*a,n)
  for cutter in cuts:so=so-cutter
  level=-.1*s if tag=='head' else gap+.1*s
  so=so.trim_by_plane(-n,-float(np.dot(o,n))-level) if tag=='head' else so.trim_by_plane(n,float(np.dot(o,n))+level)
  tm=mesh(so);q=np.einsum('ij,j->i',tm.vertices-o,n)
  remove=(np.max(np.abs(q[tm.faces]-level),axis=1)<1e-8)&(np.abs(np.einsum('ij,j->i',tm.face_normals,n))>1-1e-8)
  tm=trimesh.Trimesh(tm.vertices,tm.faces[~remove],process=False)
  loops=boundary_loops(tm)
  assert len(loops)==2,[(len(l),tm.vertices[l].mean(0)) for l in loops]
  loops.sort(key=lambda l:np.ptp(np.einsum('ij,jk->ik',tm.vertices[l],R[:,:2]),axis=0).prod(),reverse=True)
  filled.append((tm,loops))
 a,la=filled[0];b,lb=filled[1];verts=np.vstack([a.vertices,b.vertices]);faces=list(a.faces)+list(b.faces+len(a.vertices));bridge=[]
 for outer,ia,ib in zip([True,False],la,lb):
  # Preserve actual boundary adjacency, then orient CCW and align the origins.
  ia=np.asarray(ia);ib=np.asarray(ib)+len(a.vertices)
  center=np.mean(np.einsum('ij,jk->ik',np.vstack([verts[ia],verts[ib]]),R[:,:2]),axis=0)
  def ordered(ids):
   q=np.einsum('ij,jk->ik',verts[ids],R[:,:2])-center
   if np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))<0:ids=ids[::-1];q=q[::-1]
   theta=np.mod(np.arctan2(q[:,1],q[:,0]),2*np.pi)
   ids=np.roll(ids,-int(np.argmin(theta)))
   lengths=np.linalg.norm(verts[np.roll(ids,-1)]-verts[ids],axis=1)
   param=np.r_[0,np.cumsum(lengths[:-1])]/lengths.sum()*2*np.pi
   return ids,param
  ia,ta=ordered(ia);ib,tb=ordered(ib)
  # Choose an origin before both first vertices; walk the two closed rings.
  na=len(ia);nb=len(ib);i=j=0
  while i<na or j<nb:
   nexta=ta[(i+1)%na]+(2*np.pi if i+1>=na else 0) if i<na else np.inf
   nextb=tb[(j+1)%nb]+(2*np.pi if j+1>=nb else 0) if j<nb else np.inf
   if nexta<nextb:
    f=[ia[i%na],ia[(i+1)%na],ib[j%nb]];i+=1
   else:
    f=[ia[i%na],ib[(j+1)%nb],ib[j%nb]];j+=1
   if not outer:f=f[::-1]
   bridge.append(f)
 faces.extend(bridge)
 tm=trimesh.Trimesh(verts,np.asarray(faces),process=False)
 assert tm.is_watertight and tm.is_winding_consistent,(tm.is_watertight,tm.is_winding_consistent)
 assert tm.volume>0
 print('REJOINED',len(tm.faces),flush=True)
 return tm,{'old_gap_mm':gap,'seam_reconstruction_band_mm':gap+.2*s,'bridge_triangles':len(bridge),'old_magnet_cleanup':cleanup,'method':'Remove former cut end-faces after filling blind magnet holes; stitch exact outer and inner boundary vertices across old gap with boundary-order arclength annular triangulation.'}

if __name__=='__main__':
 d=Path(sys.argv[1]);p=json.loads((d/'parameters.json').read_text());src=CHAR/p['source_directory']
 for k,f in p['source_files'].items():assert sha(src/f)==p['source_sha256'][k]
 old={k:trimesh.load_mesh(src/p['source_files'][k],process=True,validate=False) for k in ['head','cap']}
 tm,report=join_old_seam(old['head'],old['cap'],p)
 np.savez_compressed(d/'rejoined-stage.npz',vertices=tm.vertices,faces=tm.faces)
 (d/'rejoined-stage.json').write_text(json.dumps(report,indent=2)+'\n')

 # Repartition the rejoined hollow head; seam remains planar and opens outward.
 s=p['source_uniform_scale'];n=np.asarray(p['cap_plane_normal'],float);norm=np.linalg.norm(n);n/=norm
 offset=p['cap_plane_intercept_mm']/norm;gap=p['cap_gap_mm']
 joined=solid(tm)
 parts={'head':joined.trim_by_plane(-n,-offset),'cap':joined.trim_by_plane(n,offset+gap)}
 hp=p['inherited_source_parameters'];radius=hp['magnet_hole_diameter_mm']/2;depth=hp['magnet_hole_depth_mm'];wall=1.25*s;bossr=radius+wall
 centers=[np.array([sign*22.1,3.2,42.])*s for sign in [-1,1]]
 p['magnet_centers_mm']=[c.tolist() for c in centers];p['magnet_axis']=n.tolist();p['magnet_diameter_mm']=hp['magnet_diameter_mm'];p['magnet_thickness_mm']=hp['magnet_thickness_mm'];p['magnet_hole_diameter_mm']=2*radius;p['magnet_hole_depth_mm']=depth;p['magnet_boss_radius_mm']=bossr;p['magnet_pocket_floor_mm']=wall;p['magnet_count_per_part']=2
 p['old_seam_reconstruction_band_mm']=[-.1*s,.35*s]
 def rounded_support(center,tag):
  h=depth+wall;f=.6*s
  profile=[[0,-h],[bossr-f,-h]]
  for th in np.linspace(-np.pi/2,0,17)[1:]:profile.append([bossr-f+f*np.cos(th),-h+f+f*np.sin(th)])
  profile.extend([[bossr,0],[0,0]])
  so=mf.Manifold.revolve(mf.CrossSection([np.array(profile)]),160)
  # local z rises to the mating plane for head; cap is mirrored to face it.
  axis=n if tag=='head' else -n
  R=np.column_stack([[1.,0,0],np.cross(axis,[1.,0,0]),axis])
  origin=center if tag=='head' else center+n*gap
  return so.transform(np.column_stack([R,origin]))
 for tag in parts:
  for c in centers:
   parts[tag]=parts[tag]+rounded_support(c,tag)
   low=-depth if tag=='head' else gap-.02
   cutter_depth=depth+.02
   parts[tag]=parts[tag]-cylinder(radius,cutter_depth,c+n*low,n)
  assert parts[tag].status()==mf.Error.NoError
  q=mesh(parts[tag]);labels=trimesh.graph.connected_component_labels(q.face_adjacency,node_count=len(q.faces))
  assert q.is_watertight and q.is_winding_consistent and len(np.unique(labels))==1
  np.savez_compressed(d/(tag+'-stage.npz'),vertices=q.vertices,faces=q.faces)
  print('NEW_PART',tag,len(q.faces),flush=True)
 report.update({'new_cap_plane_normal':n.tolist(),'new_cap_plane_offset_mm':offset,'new_gap_mm':gap,'new_magnets':p['magnet_centers_mm'],'prior_neck_geometry_untouched':True})
 (d/'geometry-stage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (d/'parameters.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
 for k,f in p['source_files'].items():assert sha(src/f)==p['source_sha256'][k]
 print('GEOMETRY_READY',p['version'],flush=True)
