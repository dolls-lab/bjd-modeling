"""Independent, read-only v7 -> v8 provenance and exported-STL audit.

Run: Blender -b -t 4 --python audit_source_preservation.py
Writes source-preservation-review.json. Never saves or edits a model.
All paths required for mesh/mask checks are relative to this file.
"""
from pathlib import Path
import hashlib, json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
EPS=1e-6
PATHS={
 'baseline_blend':ROOT/'baseline-v0.7.blend',
 'current_blend':ROOT/'march7-bjd-head-v0.8-draft.blend',
 'baseline_head_stl':ROOT/'baseline-head.stl',
 'current_head_stl':ROOT/'march7-head-shell-v0.8-draft.stl',
 'baseline_cap_stl':ROOT/'baseline-cap.stl',
 'current_cap_stl':ROOT/'march7-head-cap-v0.8-draft.stl',
 'protection':ROOT/'v6-side-protection.npz',
 'visible_head_protection':ROOT/'head-visible-source-protection.npz',
 'visible_head_protection_report':ROOT/'head-visible-source-protection.json',
 'head_solution':ROOT/'head-solution.npz',
 'local_fairing_report':ROOT/'local-fairing-report.json',
 'preserved_v7_earback':ROOT/'preserved-v7-earback-mask.npz',
 'source_masks':ROOT/'source-protection-masks.npz',
 'build_report':ROOT/'build-report.json',
 'baseline_report':ROOT/'baseline-build-report.json',
 'parameters':ROOT/'parameters.json',
}
NAMES={'master':'EDITABLE_Outer_Surface_Before_Hollowing','head':'PRINT_01_Head_Shell',
       'cap':'PRINT_02_Removable_Cap','source_reference':'SOURCE_Original_March7_Face_DoNotPrint'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ahash(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
for path in PATHS.values():
 if not path.is_file():raise FileNotFoundError(path)
initial_hashes={k:digest(p) for k,p in PATHS.items()}
with np.load(PATHS['protection']) as arc:protect={k:arc[k] for k in arc.files}
with np.load(PATHS['visible_head_protection']) as arc:visible_head={k:arc[k] for k in arc.files}
with np.load(PATHS['head_solution']) as arc:solution={k:arc[k] for k in arc.files}
with np.load(PATHS['preserved_v7_earback']) as arc:earback={k:arc[k] for k in arc.files}
with np.load(PATHS['source_masks']) as arc:source={k:arc[k] for k in arc.files}
mechanics=json.loads(PATHS['baseline_report'].read_text())
build_meta=json.loads(PATHS['build_report'].read_text())
checks={}
checks['baseline_blend_is_delivered_v7']=initial_hashes['baseline_blend']==str(earback['baseline_blend_sha256'])
checks['build_report_baseline_sha_matches_v07']=build_meta.get('v8_local_fairing',{}).get('baseline_sha256')==initial_hashes['baseline_blend']
checks['build_report_head_solution_sha_matches']=build_meta.get('v8_local_fairing',{}).get('objects',{}).get('head',{}).get('solution_sha256')==initial_hashes['head_solution']

def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for key,name in NAMES.items():
  ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
  normal_matrix=ob.matrix_world.to_3x3().inverted().transposed()
  out[key]={'vertices':np.array([ob.matrix_world@v.co for v in me.vertices],dtype='<f8'),
            'local_vertices':np.array([v.co[:] for v in me.vertices],dtype='<f8'),
            'vertex_normals':np.array([normal_matrix@v.normal for v in me.vertices],dtype='<f8'),
            'edges':np.array([e.vertices[:] for e in me.edges],dtype='<i4'),
            'loops':np.array([l.vertex_index for l in me.loops],dtype='<i4'),
            'polygon_sizes':np.array([len(p.vertices) for p in me.polygons],dtype='<i4'),
            'triangles':np.array([t.vertices[:] for t in me.loop_triangles],dtype='<i4'),
            'triangle_polygon_index':np.array([t.polygon_index for t in me.loop_triangles],dtype='<i4')}
 return out
def stats(d):
 return {'count':len(d),'max_mm':float(d.max()),'mean_mm':float(d.mean()),
         'median_mm':float(np.median(d)),'p95_mm':float(np.percentile(d,95)),
         'moved_exactly_nonzero':int(np.count_nonzero(d)),'moved_over_1e_6mm':int(np.sum(d>EPS))} if len(d) else {'count':0}
def regions(key,vertices):
 n=len(vertices);m={'all_vertices':np.ones(n,bool)}
 if key not in ('master','head'):return m
 m['all_protected_source_and_feature_vertices']=protect[key+'_locked'] if key=='master' else visible_head['head_locked']
 for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi'):
  m['raw_pmx_roi_'+name]=protect[key+'_raw_feature_'+name]
 if key=='master':
  for name in ('source_any_incident','source_face_incident','source_ear_incident','source_closure_incident'):
   m[name]=protect['master_'+name]
  added=np.zeros(n,bool)
  added[protect['master_baseline_triangles'][protect['master_triangle_source_class']==3].ravel()]=True
  m['shared_original_source_added_shell_boundary']=added&protect['master_source_any_incident']
 else:
  cls=protect['master_triangle_source_class'][protect['head_nearest_master_triangle']]
  m['visible_source_sculpt']=visible_head['head_visible_source_locked']
  for label,name in [(0,'source_face'),(1,'source_ear'),(2,'source_closure')]:
   m['visible_'+name]=visible_head['head_visible_'+name]
   m['informational_old_mapped_'+name]=cls==label
  m['visible_source_shared_boundary']=visible_head['head_visible_source_shared_boundary']&(cls==3)
  m['v7_microfinished_earback_preserved_exactly']=earback['mask']
  m['informational_old_full_source_lock']=protect['head_locked']
  m['informational_released_from_old_source_lock']=visible_head['head_released_from_old_lock']
  m['informational_old_mapped_shared_boundary']=protect['head_shared_boundary_lock']&(cls==3)
 x,y,z=vertices.T
 m['neck_mechanical_cylinder']=((x*x+(y-mechanics['neck_center_y_mm'])**2)<=15.0**2)&(z<=mechanics['neck_platform_top_mm'])
 for i,c in enumerate(mechanics['magnet_centers_mm']):m[f'magnet_{i+1}_within_7mm']=np.linalg.norm(vertices-np.array(c),axis=1)<=7.0
 return m

baseline=snapshot(PATHS['baseline_blend']);current=snapshot(PATHS['current_blend'])
checks['head_solution_before_matches_v07_baseline']=np.array_equal(solution['before'],baseline['head']['local_vertices'])
checks['head_solution_after_is_finite']=bool(np.isfinite(solution['after']).all())
checks['head_solution_after_matches_v08_blend_float32']=np.array_equal(solution['after'].astype(np.float32).astype(float),current['head']['local_vertices'])
checks['v7_microfinished_earback_reference_positions_match']=np.array_equal(baseline['head']['vertices'][earback['mask']],earback['baseline_positions_mm'])
checks['v7_earback_442_vertices_inside_current_strict_mask']=int(earback['mask'].sum())==442 and not np.any(earback['mask']&~visible_head['head_locked'])
solution_checks={'before_shape':list(solution['before'].shape),'after_shape':list(solution['after'].shape),
                 'before_matches_delivered_v7':checks['head_solution_before_matches_v07_baseline'],
                 'after_matches_final_blender_float32':checks['head_solution_after_matches_v08_blend_float32']}
if 'locked' in solution:
 declared=np.asarray(solution['locked'],bool)
 checks['head_solution_declared_lock_shape_valid']=declared.shape==(len(baseline['head']['vertices']),)
 if checks['head_solution_declared_lock_shape_valid']:
  delta=np.linalg.norm(current['head']['vertices']-baseline['head']['vertices'],axis=1)
  checks['head_solution_declared_locks_exactly_unchanged']=bool(np.count_nonzero(delta[declared])==0)
  solution_checks['declared_locked_vertices']=int(declared.sum())
report={'baseline_version':'v0.7','current_version':'v0.8','units':'mm',
        'numeric_zero_tolerance_mm':EPS,'strict_zero_requirement':'Protected vertex coordinate differences must be exactly zero, not merely below tolerance.',
        'files':{k:{'path':str(p),'sha256':initial_hashes[k]} for k,p in PATHS.items()},
        'build_method':'Restore rounded cranial curvature and smooth surface continuity while preserving every visible source face/ear point of delivered v7.',
        'head_solution_correspondence':solution_checks,
        'mask_origin_baseline_sha256_informational':str(protect['baseline_blend_sha256']),
        'methods':{
          'index_correspondence':'Vertex count, polygon loop-index array and polygon sizes must match. Edge and triangulation index equality are reported separately. Geometry-dependent quad tessellation is not itself a change to polygon topology.',
          'source_provenance':'The complete pre-hollow master reference is unchanged. All delivered-v7 visible source face/ear/closure points, including all 442 previously microfinished ear-back vertices, are strictly fixed. Historical masks are reused only after matching vertex/polygon indices; their old v5 position arrays/hash are not v8 baselines.',
          'editable_final_mesh':'PRINT_01_Head_Shell is the final editable v8 surface. EDITABLE_Outer_Surface_Before_Hollowing remains the unchanged v6 pre-hollowing reference.',
          'normal_changes':'Smooth vertex normals can change when adjacent added cranial faces move, even with protected coordinates fixed. These angular changes are informational.',
          'mechanics':'On baseline coordinates: neck cylinder radius <=15 mm around (0, neck_center_y), z <= neck_platform_top; each magnet center sphere radius <=7 mm.',
          'stl':'Verify each baseline/current STL independently against its Blender mesh, including exact float32 vertex positions and the oriented triangle multiset. Then attribute exported corner samples to the verified same vertex indices; no nearest-point displacement approximation.',
          'raw_pmx_error':'Nearest target-surface distance from original source vertices is separate from corresponding-vertex displacement, and is not used as an exact-zero proof.'},
        'same_index_displacement':{},'exported_stl_correspondence':{},'raw_pmx_nearest_surface_error':{},'informational_vertex_normal_changes':{},
        'limits':['No z<30 blanket protection is asserted; added cranium curvature is intentionally adjusted.',
                  'Source preservation means no further v7-to-v8 change, not pointwise equality of the final print mesh to raw PMX.',
                  'The v7 allowance for ear-back micro-fairing is historical only. V8 permits no additional motion of those 442 vertices.',
                  'Head source labels are nearest-v5-master mappings after voxelization, not original print-vertex construction history.',
                  'Old source-mapped inner cavity walls may move with the new exterior field to preserve thickness. Their motion is reported, not claimed to be zero.',
                  'This audit does not certify visual appearance, shell thickness, physical body fit or hardware assembly.']}
mask_cache={};delta_cache={}
for key in NAMES:
 a,b=baseline[key],current[key]
 topology=len(a['vertices'])==len(b['vertices']) and np.array_equal(a['loops'],b['loops']) and np.array_equal(a['polygon_sizes'],b['polygon_sizes'])
 item={'polygon_topology_and_vertex_order_identical':bool(topology),
       'edge_index_order_identical':bool(np.array_equal(a['edges'],b['edges'])),
       'triangle_index_order_identical':bool(np.array_equal(a['triangles'],b['triangles'])),
       'baseline_vertices':len(a['vertices']),'current_vertices':len(b['vertices'])}
 checks[key+'_index_correspondence']=bool(topology)
 if key in ('master','head'):
  # Historical V5 mask positions are intentionally not compared to the V7
  # baseline: V7 already refined 442 ear-back points which V8 must now freeze.
  for name in ('edges','loops','polygon_sizes'):
   checks[key+'_inherited_mask_'+name+'_indices_match_v07']=np.array_equal(a[name],protect[key+'_baseline_'+name])
  checks[key+'_inherited_mask_vertex_count_matches']=len(a['vertices'])==len(protect[key+'_baseline_vertices'])
  if key=='head':
   checks['head_visible_mask_contains_all_raw_feature_rois']=all(not np.any(protect['head_raw_feature_'+name]&~visible_head['head_locked']) for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi'))
 if topology:
  delta=np.linalg.norm(b['vertices']-a['vertices'],axis=1);masks=regions(key,a['vertices'])
  delta_cache[key]=delta;mask_cache[key]=masks
  item['regions']={name:stats(delta[m]) for name,m in masks.items()}
  for name,m in masks.items():
   if key=='head' and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   checks[key+'_'+name+'_exactly_unchanged']=bool(m.any() and np.count_nonzero(delta[m])==0)
  if key=='head':
   na=a['vertex_normals'];nb=b['vertex_normals']
   na=na/np.maximum(np.linalg.norm(na,axis=1,keepdims=True),1e-15)
   nb=nb/np.maximum(np.linalg.norm(nb,axis=1,keepdims=True),1e-15)
   angle=np.degrees(np.arctan2(np.linalg.norm(np.cross(na,nb),axis=1),np.einsum('ij,ij->i',na,nb)))
   for name in ('visible_source_sculpt','visible_source_face','visible_source_ear','v7_microfinished_earback_preserved_exactly'):
    aa=angle[masks[name]]
    report['informational_vertex_normal_changes'][name]={'count':len(aa),'max_degrees':float(aa.max()),'p95_degrees':float(np.percentile(aa,95)),'over_1_degree':int((aa>1).sum())}
 report['same_index_displacement'][key]=item
 print('INDEX_AUDIT',key,topology,flush=True)

def read_stl(path):
 data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
 if len(data)!=84+50*count:raise ValueError('Not exact binary STL layout: '+str(path))
 dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
 return np.frombuffer(data,offset=84,dtype=dtype,count=count)['vertices'].astype(float)
def sorted_oriented(tri):
 # Normalize cyclic starting corner but retain orientation.
 rotated=tri[np.arange(len(tri))[:,None],(np.argmin(tri,axis=1)[:,None]+np.arange(3))%3]
 return rotated[np.lexsort((rotated[:,2],rotated[:,1],rotated[:,0]))]
def verify_stl(path,obj):
 stl=read_stl(path);flat=stl.reshape(-1,3);uv,inverse=np.unique(flat,axis=0,return_inverse=True)
 bv=obj['vertices'].astype(np.float32).astype(float)
 lookup={tuple(p):i for i,p in enumerate(bv)}
 unique_blend=len(lookup)==len(bv)
 ids=np.array([lookup.get(tuple(p),-1) for p in uv],int)
 result={'facets':len(stl),'unique_stl_positions':len(uv),'blend_positions_unique':unique_blend,
         'all_stl_positions_match_blend_float32_exactly':bool(np.all(ids>=0)),
         'oriented_triangle_multiset_matches':False}
 corner_ids=None
 if np.all(ids>=0) and unique_blend:
  corner_ids=ids[inverse].reshape(-1,3)
  result['oriented_triangle_multiset_matches']=bool(np.array_equal(sorted_oriented(corner_ids),sorted_oriented(obj['triangles'])))
 result['verified']=all([result['blend_positions_unique'],result['all_stl_positions_match_blend_float32_exactly'],result['oriented_triangle_multiset_matches']])
 return result,corner_ids
for part in ('head','cap'):
 result={};indices={}
 for version,objects,prefix in [('v07',baseline,'baseline'),('v08',current,'current')]:
  result[version],indices[version]=verify_stl(PATHS[prefix+'_'+part+'_stl'],objects[part])
  checks[part+'_'+version+'_stl_correspondence_verified']=result[version]['verified']
 if all(result[v]['verified'] for v in result) and checks[part+'_index_correspondence']:
  corner_ids=indices['v08'].ravel()
  actual_delta=np.linalg.norm(current[part]['vertices'].astype(np.float32).astype(float)-baseline[part]['vertices'].astype(np.float32).astype(float),axis=1)
  result['v7_to_v8_exported_corner_displacements']={name:stats(actual_delta[corner_ids[m[corner_ids]]]) for name,m in mask_cache[part].items()}
  for name,rr in result['v7_to_v8_exported_corner_displacements'].items():
   if part=='head' and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   checks[part+'_stl_'+name+'_exactly_unchanged']=bool(rr.get('count',0)>0 and rr['moved_exactly_nonzero']==0)
 report['exported_stl_correspondence'][part]=result
checks['cap_stl_bytes_unchanged']=initial_hashes['baseline_cap_stl']==initial_hashes['current_cap_stl']

sv=source['vertices_mm']
raw_masks={name:m for name,m in source.items() if m.dtype==bool and m.shape==(len(sv),)}
for key in ('master','head'):
 errors={}
 for version,objects in [('v07',baseline),('v08',current)]:
  ob=objects[key];tree=BVHTree.FromPolygons(ob['vertices'].tolist(),ob['triangles'].tolist(),all_triangles=True)
  errors[version]=np.array([tree.find_nearest(Vector(p))[3] for p in sv])
 report['raw_pmx_nearest_surface_error'][key]={name:{'v07':stats(errors['v07'][m]),'v08':stats(errors['v08'][m]),
  'max_absolute_change_in_nearest_distance_mm':float(np.max(np.abs(errors['v08'][m]-errors['v07'][m])))} for name,m in raw_masks.items() if m.any()}

report['checks']=checks;report['all_checks_pass']=all(checks.values())
report['input_files_unchanged_during_audit']=all(digest(p)==initial_hashes[k] for k,p in PATHS.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit; refusing mixed-version report')
out=ROOT/'source-preservation-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'all_checks_pass':report['all_checks_pass'],
                  'failed_checks':[k for k,v in checks.items() if not v],
                  'current_head_stl_sha256':initial_hashes['current_head_stl']},indent=2),flush=True)
