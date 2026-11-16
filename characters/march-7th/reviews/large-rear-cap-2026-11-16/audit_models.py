"""Independent final STL audit of crown/rear split and inherited reference assembly.
No geometry-builder imports; all tests read immutable source/final files.
"""
from pathlib import Path
import sys,json,hashlib,time
sys.path.insert(0,'/private/tmp/bjd-hook-groove-deps')
import numpy as np,trimesh,manifold3d as mf
from scipy.spatial import ConvexHull,cKDTree
HERE=Path(__file__).resolve().parent
TOL=1e-5

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(t):
 o=mf.Manifold(mf.Mesh64(np.asarray(t.vertices,float),np.asarray(t.faces,np.uint64)))
 assert o.status()==mf.Error.NoError,o.status()
 return o.as_original()
def mesh(o):
 a=o.to_mesh64();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=False)
def vol(a,b):return max(0.,float((a^b).volume()))
def box(lo,hi):return mf.Manifold.cube(tuple(np.asarray(hi)-lo)).translate(lo)
def union(objs):
 result=objs[0]
 for obj in objs[1:]:result=result+obj
 return result

def audit(folder):
 start=time.monotonic();d=Path(folder).resolve();p=json.loads((d/'parameters.json').read_text());s=p['source_uniform_scale'];char=d.parents[2];src=char/p['source_directory']
 paths={'parameters':d/'parameters.json','head':d/p['output_files']['head'],'cap':d/p['output_files']['cap'],'source_head':src/p['source_files']['head'],'source_cap':src/p['source_files']['cap'],'source_reference':src/'geometry-stage.npz','source_motion':src/'assembly-final.json','source_parameters':src/'parameters.json','blend':d/p['output_files']['blend'],'blend_audit':HERE/f"audit-blend-{p['version']}.json"}
 hashes={k:sha(v) for k,v in paths.items()};sp=json.loads(paths['source_parameters'].read_text());ba=json.loads(paths['blend_audit'].read_text())
 assert all(hashes['source_'+k]==p['source_sha256'][k] for k in ['head','cap'])
 assert ba['input_hashes']['blend']==hashes['blend'] and ba['pass']
 geometry={k:trimesh.load_mesh(paths[k],process=True,validate=False) for k in ['head','cap','source_head','source_cap']};sol={k:solid(tm) for k,tm in geometry.items()}
 report={'version':p['version'],'audit_script_sha256':sha(Path(__file__)),'input_hashes':hashes,'mesh':{}}
 for k in ['head','cap']:
  tm=geometry[k];labels=trimesh.graph.connected_component_labels(tm.face_adjacency,node_count=len(tm.faces))
  report['mesh'][k]={'watertight':bool(tm.is_watertight),'winding_consistent':bool(tm.is_winding_consistent),'components':len(np.unique(labels)),'minimum_triangle_area_mm2':float(tm.area_faces.min()),'volume_mm3':float(tm.volume)}
 old=sol['source_head']+sol['source_cap'];new=sol['head']+sol['cap'];n=np.array([0.,1.,.9]);n/=np.linalg.norm(n);offset=41*s/np.sqrt(1+.9**2);gap=.25*s
 hd=np.einsum('ij,j->i',geometry['head'].vertices,n);cd=np.einsum('ij,j->i',geometry['cap'].vertices,n)
 report['split']={'normal':n.tolist(),'approved_offset_mm':offset,'head_max_dot_mm':float(hd.max()),'cap_min_dot_mm':float(cd.min()),'actual_plane_gap_mm':float(cd.min()-hd.max()),'head_cap_overlap_mm3':vol(sol['head'],sol['cap']),'plane_separation_guarantees_linear_cap_head_disassembly':bool(hd.max()<cd.min()),'cap_contains_entire_crown_above_mm':65*s,'front_vertices_above_crown_threshold':int(np.count_nonzero(geometry['head'].vertices[:,2]>65*s))}
 report['split']['pass']=bool(abs(hd.max()-offset)<3e-5 and abs(cd.min()-(offset+gap))<3e-5 and report['split']['head_cap_overlap_mm3']<TOL and report['split']['front_vertices_above_crown_threshold']==0)
 # Protect the entire lower head including neck, three-groove boss, ball cup and passage.
 region=box(np.array([-60.,-60.,-15.])*s,np.array([60.,60.,25.])*s)
 neck_added=max(0.,float(((sol['head']-sol['source_head'])^region).volume()));neck_removed=max(0.,float(((sol['source_head']-sol['head'])^region).volume()))
 # The plane cuts the rear shell below25; restrict to the actual integral neck footprint.
 yc=p['neck_center_y_mm'];r=14.1*s
 neckregion=mf.Manifold.cylinder(50*s,r,r,256).translate((0,yc,-25*s))
 neck_added=max(0.,float(((sol['head']-sol['source_head'])^neckregion).volume()));neck_removed=max(0.,float(((sol['source_head']-sol['head'])^neckregion).volume()))
 old_neck=geometry['source_head'].vertices;mask=(np.hypot(old_neck[:,0],old_neck[:,1]-yc)<r)&(old_neck[:,2]<25*s)
 tree=cKDTree(geometry['head'].vertices);distance=tree.query(old_neck[mask])[0]
 report['neck']={'protected_radius_mm':r,'protected_top_z_mm':25*s,'added_mm3':neck_added,'removed_mm3':neck_removed,'protected_source_vertices':int(mask.sum()),'maximum_nearest_vertex_error_mm':float(distance.max()),'pass':bool(max(neck_added,neck_removed)<TOL and distance.max()<1e-5)}
 # Direct preservation check for facial features and both ears, away from all split/hardware work.
 sv=geometry['source_head'].vertices
 face=(sv[:,1]<-7*s)&(sv[:,2]<42*s)&(np.abs(sv[:,0])<23*s)
 ear_box=(np.abs(sv[:,0])>24*s)&(sv[:,2]<38*s)&(sv[:,1]<6*s)
 ear_outward=np.einsum('ij,ij->i',geometry['source_head'].vertex_normals,sv-np.array([0.,0.,35.])*s)>0
 ears=ear_box&ear_outward
 fm=face|ears;fd=tree.query(sv[fm])[0]
 report['protected_face_ears']={'method':'Facial feature region plus outward-facing ear-box vertices; inward cranial wall inside this box is allowed to join new magnetic supports. Exterior ray checks separately inspect the side surface.', 'inner_sidewall_vertices_excluded':int(np.count_nonzero(ear_box&~ear_outward)), 'source_vertices_checked':int(fm.sum()),'maximum_vertex_error_mm':float(fd.max()),'pass':bool(fd.max()<1e-5)}
 # Source exterior radial intersections are measured directly, excluding only the two seam bands.
 oldn=np.array([0.,1.,.3]);oldn/=np.linalg.norm(oldn);oldoff=29.5*s/np.sqrt(1+.3**2)
 center=np.array([0.,0.,35.])*s;errors=[];seam_skipped=0;missing=0;cap_hits=oldcap_hits=0;area_weights=[]
 for elev in np.linspace(-1.25,1.5,37):
  for az in np.linspace(0,2*np.pi,96,endpoint=False):
   direction=np.array([np.cos(elev)*np.cos(az),np.cos(elev)*np.sin(az),np.sin(elev)])
   origin=center+100*s*direction;end=center
   oh=old.ray_cast(tuple(origin),tuple(end));nh=new.ray_cast(tuple(origin),tuple(end))
   if not oh:continue
   op=np.array(oh[0].position,float)
   if not nh:missing+=1;continue
   npnt=np.array(nh[0].position,float)
   if -.12*s < np.dot(op,oldn)-oldoff < .37*s or abs(np.dot(op,n)-offset)<gap+.04*s:seam_skipped+=1;continue
   errors.append(float(np.linalg.norm(op-npnt)))
 report['exterior_samples']={'method':'Outermost surface hit from same 3552 radial rays toward a common cranial center; old and new seam bands excluded. Not every surface patch is visible radially.','tested':len(errors),'seam_excluded':seam_skipped,'missing_hits':missing,'maximum_error_mm':max(errors),'pass':bool(missing==0 and max(errors)<.005*s)}
 # Quantify cap footprint with the same normal/radial classifier for old/new; approximate surface area, not volume.
 fractions={}
 for label,keys in [('old',['source_head','source_cap']),('new',['head','cap'])]:
  areas=[]
  for k in keys:
   tm=geometry[k];rad=tm.triangles_center-center
   exterior=np.einsum('ij,ij->i',tm.face_normals,rad)>0
   areas.append(float(tm.area_faces[exterior].sum()))
  fractions[label]={'classified_outer_areas_mm2':areas,'cap_fraction':areas[1]/sum(areas)}
 fractions['method']='Normal points away from common cranial center; approximate exterior-area classification includes some holes/edges.'
 fractions['pass']=bool(fractions['new']['cap_fraction']>.35 and fractions['new']['cap_fraction']>1.8*fractions['old']['cap_fraction'])
 report['cap_coverage']=fractions
 # Measure the main access opening on a section just inside each head seam; magnet bores excluded.
 openings={}
 for label,obj,normal,off in [('old',sol['source_head'],oldn,oldoff),('new',sol['head'],n,offset)]:
  frame=np.array([[1.,0.,0.],np.cross(normal,[1.,0.,0.]),normal])
  local=obj.transform(np.column_stack([frame,np.zeros(3)]));polys=local.slice(off-.02*s).to_polygons()
  signed=[float(.5*np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))) for poly in polys]
  openings[label]={'outer_section_area_mm2':max(signed),'main_access_opening_area_mm2':-min(signed),'signed_contour_areas_mm2':signed}
 openings['area_ratio']=openings['new']['main_access_opening_area_mm2']/openings['old']['main_access_opening_area_mm2']
 openings['pass']=bool(openings['area_ratio']>1.5);report['access_opening']=openings
 # Independently measure both blind bores on both new seam faces.
 u=np.array([1.,0.,0.]);v=np.cross(n,u);bore=p['magnet_hole_diameter_mm']/2;depth=p['magnet_hole_depth_mm'];pockets=[]
 for tag,into,axial in [('head',-n,0.),('cap',n,gap)]:
  obj=sol[tag]
  for center0 in p['magnet_centers_mm']:
   center=np.asarray(center0,float)+n*axial
   startp=center-into*.1;hits=obj.ray_cast(tuple(startp),tuple(center+into*12*s))
   ds=[float(np.dot(np.asarray(h.position)-center,into)) for h in hits]
   bottom=ds[0] if ds else float('inf');floor=ds[1]-ds[0] if len(ds)>1 else 12*s-bottom
   radii=[];walls=[]
   for angle in np.linspace(0,2*np.pi,32,endpoint=False):
    radial=np.cos(angle)*u+np.sin(angle)*v;c=center+into*(depth/2)
    hs=obj.ray_cast(tuple(c),tuple(c+radial*12*s));rr=[float(np.linalg.norm(np.asarray(h.position)-c)) for h in hs]
    radii.append(rr[0] if rr else float('inf'))
    if len(rr)>1:walls.append(rr[1]-rr[0])
   pockets.append({'part':tag,'center_mm':center.tolist(),'measured_depth_mm':bottom,'maximum_radius_error_mm':max(abs(np.array(radii)-bore)),'minimum_sampled_radial_sidewall_mm':min(walls,default=float('inf')),'axial_floor_mm':floor})
 report['magnets']={'pockets':pockets,'nominal_magnet_diameter_thickness_mm':[p['magnet_diameter_mm'],p['magnet_thickness_mm']],'nominal_pocket_diameter_depth_mm':[2*bore,depth],'pass':bool(all(abs(q['measured_depth_mm']-depth)<.01 and q['maximum_radius_error_mm']<.01 and q['minimum_sampled_radial_sidewall_mm']>.8*s and q['axial_floor_mm']>.8*s for q in pockets)),'limits':'Measured along32 radial bore sections and central axis; not a global minimum-wall or load certification.'}
 # Rerun approved motion on the NEW final obstacles with the unchanged source reference.
 a=np.load(paths['source_reference']);motion=json.loads(paths['source_motion'].read_text());settled=motion['settled_delta_z_mm'];lift=motion['lift_before_rotation_mm']
 hook=solid(trimesh.Trimesh(a['hook_vertices'],a['hook_faces'],process=False)).translate((0,0,settled));cord=solid(trimesh.Trimesh(a['cord_vertices'],a['cord_faces'],process=False)).translate((0,0,settled))
 eyes=[mf.Manifold.sphere(p['inherited_source_parameters']['nominal_eye_diameter_mm']/2,128).translate((sign*13.663962920147602*s,-13.289332231246028*s,27.67311677124019*s)) for sign in [-1,1]]
 obstacles=union([sol['head']]+eyes)
 def turn(o,angle):return o.translate((0,-yc,0)).rotate((0,0,angle)).translate((0,yc,0))
 raised=(hook+cord).translate((0,0,lift));entry=turn(raised,90);v=mesh(entry).vertices;xy=np.unique(v[:,:2],axis=0);hull=xy[ConvexHull(xy).vertices]
 prism=mf.Manifold.extrude(mf.CrossSection([hull]),v[:,2].max()+80).translate((0,0,-80))
 insertion={'overlap_mm3':vol(prism,obstacles),'min_gap_mm':float(prism.min_gap(obstacles,2))}
 radius=max(np.linalg.norm(mesh(raised).vertices[:,:2]-[0,yc],axis=1));bound=2*radius*np.sin(np.deg2rad(1)/2)
 rot=[]
 for angle in np.r_[0.,np.arange(1.,90.,2.),90.]:
  obj=turn(raised,float(angle));rot.append({'angle':float(angle),'gap_mm':float(obj.min_gap(obstacles,2)),'overlap_mm3':vol(obj,obstacles)})
 descent=[]
 for label,obj in [('hook',hook),('cord',cord)]:
  hull3=mf.Manifold.batch_hull([obj,obj.translate((0,0,lift))]);descent.append({'part':label,'overlap_mm3':vol(hull3,obstacles),'gap_mm':float(hull3.min_gap(obstacles,2))})
 close={k:vol(o,sol['cap']) for k,o in [('hook',hook),('cord',cord),('left_eye',eyes[0]),('right_eye',eyes[1])]}
 # Continuous cap removal against interior fixtures: gap at 1-mm samples exceeds half-step bound.
 fixtures=union([hook,cord]+eyes);step=.5*s;caps=[]
 for dist in np.arange(0,60*s+step/2,step):
  moved=sol['cap'].translate(tuple(n*dist));caps.append({'distance_mm':float(dist),'gap_mm':float(moved.min_gap(fixtures,2))})
 capmove={'sample_step_mm':step,'lipschitz_half_step_mm':step/2,'minimum_sample_gap_mm':min(c['gap_mm'] for c in caps),'end_offset_mm':caps[-1]['distance_mm'],'continuous_clear':min(c['gap_mm'] for c in caps)>step/2+.005,'initial_closed_overlap_mm3':close}
 aftercap=sol['cap'].translate(tuple(n*60*s));capmove['separated_at_path_end']=bool(np.min(np.einsum('ij,j->i',mesh(aftercap).vertices,n))>np.max(np.einsum('ij,j->i',mesh(fixtures).vertices,n)))
 probes=[]
 for dz in [.08,.1,.5,1.,2.]:probes.append({'down_mm':dz,'overlap_mm3':vol(sol['head'],hook.translate((0,0,-dz)))})
 contacts=[]
 for sign in [-1,1]:
  part=box(np.array([0 if sign>0 else -30,yc-20,-10]),np.array([30 if sign>0 else 0,yc+20,70]));vpart=(sol['head']^hook.translate((0,0,-.08)))^part
  contacts.append({'side':sign,'contact_volume_mm3':max(0.,float(vpart.volume()))})
 report['assembly']={'source_reference_dimensions_mm':np.ptp(a['hook_vertices'],axis=0).tolist(),'source_pose_delta_mm':settled,'insertion':insertion,'rotation_minimum_gap_mm':min(q['gap_mm'] for q in rot),'rotation_continuous_displacement_bound_mm':float(bound),'rotation_maximum_overlap_mm3':max(q['overlap_mm3'] for q in rot),'descent':descent,'both_support_contacts':contacts,'downward_obstruction':probes,'cap_removal':capmove}
 report['assembly']['pass']=bool(insertion['overlap_mm3']<TOL and insertion['min_gap_mm']>.05 and min(q['gap_mm'] for q in rot)>bound+.005 and max(q['overlap_mm3'] for q in rot)<TOL and all(q['overlap_mm3']<TOL for q in descent) and max(close.values())<TOL and min(q['contact_volume_mm3'] for q in contacts)>1e-4 and min(q['overlap_mm3'] for q in probes)>1e-4 and capmove['continuous_clear'] and capmove['separated_at_path_end'])
 snapshot=json.loads((HERE/'audit-source-integrity-before.json').read_text());report['source_snapshot_unchanged']=all(sha(char/k)==h for k,h in snapshot.items())
 report['inputs_unchanged']=all(sha(paths[k])==h for k,h in hashes.items());report['elapsed_seconds']=time.monotonic()-start
 report['limits']=['Geometry verification uses the previously approved approximate reference hook and rigid cord; real hardware/body fit, loads, glue and printer tolerances remain untested.','Cap coverage is approximate surface classification; do not describe as literal equal-volume halves.']
 report['pass']=bool(report['inputs_unchanged'] and report['source_snapshot_unchanged'] and all(q['watertight'] and q['winding_consistent'] and q['components']==1 and q['minimum_triangle_area_mm2']>0 for q in report['mesh'].values()) and all(report[k]['pass'] for k in ['split','neck','protected_face_ears','exterior_samples','cap_coverage','access_opening','magnets','assembly']))
 (HERE/f"audit-final-{p['version']}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('FINAL_AUDIT',p['version'],report['pass'],flush=True)
 return report
if __name__=='__main__':
 for f in sys.argv[1:]:assert audit(f)['pass']
