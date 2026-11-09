"""Independent, read-only v6 -> v7 provenance and exported-STL audit.

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
 'baseline_blend':ROOT/'baseline-v0.6.blend',
 'current_blend':ROOT/'march7-bjd-head-v0.7-draft.blend',
 'baseline_head_stl':ROOT/'baseline-head.stl',
 'current_head_stl':ROOT/'march7-head-shell-v0.7-draft.stl',
 'baseline_cap_stl':ROOT/'baseline-cap.stl',
 'current_cap_stl':ROOT/'march7-head-cap-v0.7-draft.stl',
 'protection':ROOT/'v6-side-protection.npz',
 'visible_head_protection':ROOT/'head-visible-source-protection.npz',
 'visible_head_protection_report':ROOT/'head-visible-source-protection.json',
 'head_solution':ROOT/'head-solution.npz',
 'earback_release':ROOT/'earback-micro-release.npz',
 'local_fairing_report':ROOT/'local-fairing-report.json',
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
with np.load(PATHS['earback_release']) as arc:earback={k:arc[k] for k in arc.files}
with np.load(PATHS['source_masks']) as arc:source={k:arc[k] for k in arc.files}
mechanics=json.loads(PATHS['baseline_report'].read_text())
build_meta=json.loads(PATHS['build_report'].read_text())
checks={}
ear_release=np.asarray(earback['head_earback_release'],bool)
EAR_LIMIT=.15
checks['earback_release_mask_matches_solution']=np.array_equal(ear_release,solution['earback_release_mask'])
checks['earback_release_count_442']=int(ear_release.sum())==442
checks['earback_release_only_original_visible_ear']=not np.any(ear_release&~visible_head['head_visible_source_ear'])
checks['earback_release_excludes_raw_feature_rois']=not np.any(ear_release&visible_head['head_raw_feature_locked'])
checks['earback_release_at_least_half_mm_from_original_rear_edge']=bool(np.all(earback['head_raw_earback_boundary_distance_mm'][ear_release]>=.5))
checks['build_report_baseline_sha_matches_v06']=build_meta.get('v7_local_fairing',{}).get('baseline_sha256')==initial_hashes['baseline_blend']
checks['build_report_head_solution_sha_matches']=build_meta.get('v7_local_fairing',{}).get('objects',{}).get('head',{}).get('solution_sha256')==initial_hashes['head_solution']

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
 m['all_protected_source_and_feature_vertices']=protect[key+'_locked'] if key=='master' else (visible_head['head_locked']&~ear_release)
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
  m['visible_source_sculpt_fixed']=visible_head['head_visible_source_locked']&~ear_release
  m['informational_visible_source_sculpt_including_earback']=visible_head['head_visible_source_locked']
  for label,name in [(0,'source_face'),(1,'source_ear'),(2,'source_closure')]:
   m['visible_'+name+'_fixed']=visible_head['head_visible_'+name]&~ear_release
   m['informational_old_mapped_'+name]=cls==label
  m['permitted_earback_microfinish']=ear_release
  m['ear_outline_half_mm_band_fixed']=visible_head['head_visible_source_ear']&(earback['head_raw_earback_boundary_distance_mm']<=.5)
  m['visible_source_shared_boundary']=visible_head['head_visible_source_shared_boundary']&(cls==3)
  m['informational_old_full_source_lock']=protect['head_locked']
  m['informational_released_from_old_source_lock']=visible_head['head_released_from_old_lock']
  m['informational_old_mapped_shared_boundary']=protect['head_shared_boundary_lock']&(cls==3)
 x,y,z=vertices.T
 m['neck_mechanical_cylinder']=((x*x+(y-mechanics['neck_center_y_mm'])**2)<=15.0**2)&(z<=mechanics['neck_platform_top_mm'])
 for i,c in enumerate(mechanics['magnet_centers_mm']):m[f'magnet_{i+1}_within_7mm']=np.linalg.norm(vertices-np.array(c),axis=1)<=7.0
 return m

baseline=snapshot(PATHS['baseline_blend']);current=snapshot(PATHS['current_blend'])
checks['head_solution_before_matches_v06_baseline']=np.array_equal(solution['before'],baseline['head']['local_vertices'])
checks['head_solution_after_is_finite']=bool(np.isfinite(solution['after']).all())
checks['head_solution_after_matches_v07_blend_float32']=np.array_equal(solution['after'].astype(np.float32).astype(float),current['head']['local_vertices'])
checks['earback_release_baseline_is_delivered_v6']=np.array_equal(earback['head_baseline_v6_vertices'],baseline['head']['local_vertices'])
candidate2=solution['candidate2_after'].astype(np.float32).astype(float)
extra_delta=np.linalg.norm(current['head']['local_vertices']-candidate2,axis=1)
checks['earback_stage_nonreleased_vertices_unchanged_from_candidate2']=bool(np.count_nonzero(extra_delta[~ear_release])==0)
checks['earback_stage_released_vertices_within_0_15mm']=bool(extra_delta[ear_release].max()<=EAR_LIMIT+EPS)
checks['candidate2_original_earback_was_fixed_to_v6']=np.array_equal(candidate2[ear_release],baseline['head']['local_vertices'][ear_release])
checks['earback_correction_field_matches_after_minus_candidate2']=bool(np.max(np.abs((solution['after']-solution['candidate2_after'])-solution['earback_correction']))<=1e-10)
solution_checks={'before_vs_v06_shape':list(solution['before'].shape),'after_shape':list(solution['after'].shape),
                 'before_matches_delivered_v6':checks['head_solution_before_matches_v06_baseline'],
                 'after_matches_final_blender_float32':checks['head_solution_after_matches_v07_blend_float32']}
if 'locked' in solution:
 declared=np.asarray(solution['locked'],bool)
 checks['head_solution_declared_lock_shape_valid']=declared.shape==(len(baseline['head']['vertices']),)
 if checks['head_solution_declared_lock_shape_valid']:
  delta=np.linalg.norm(current['head']['vertices']-baseline['head']['vertices'],axis=1)
  checks['head_solution_declared_locks_exactly_unchanged']=bool(np.count_nonzero(delta[declared])==0)
  solution_checks['declared_locked_vertices']=int(declared.sum())
report={'baseline_version':'v0.6','current_version':'v0.7','units':'mm',
        'numeric_zero_tolerance_mm':EPS,'strict_zero_requirement':'Protected vertex coordinate differences must be exactly zero, not merely below tolerance.',
        'files':{k:{'path':str(p),'sha256':initial_hashes[k]} for k,p in PATHS.items()},
        'build_method':'Direct local finishing of added postauricular print surface, followed by <=0.15 mm micro-fairing on 442 original ear-back interior vertices; complete v6 pre-hollow master reference unchanged.',
        'head_solution_correspondence':solution_checks,
        'permitted_earback_microfinish':{'released_vertices':int(ear_release.sum()),'limit_mm':EAR_LIMIT,
          'minimum_original_earback_boundary_clearance_mm':float(earback['head_raw_earback_boundary_distance_mm'][ear_release].min()),
          'extra_from_candidate2':stats(extra_delta[ear_release]),'nonreleased_extra_from_candidate2':stats(extra_delta[~ear_release]),
          'scope':'Original posterior ear interior only. Original face, ear front and >=0.5 mm original-ear boundary band remain fixed. Do not describe the entire source ear as zero-displacement.'},
        'mask_origin_baseline_sha256_informational':str(protect['baseline_blend_sha256']),
        'methods':{
          'index_correspondence':'Vertex count, polygon loop-index array and polygon sizes must match. Edge and triangulation index equality are reported separately. Geometry-dependent quad tessellation is not itself a change to polygon topology.',
          'source_provenance':'Complete v6 pre-hollow master unchanged. Print-head original face/front ear/closure and raw feature ROIs fixed; the explicitly recorded 442-point ear-back interior subset is permitted <=0.15 mm refinement. Source maps are inherited by verified indices and protected baseline coordinates, without an obsolete v5 whole-file hash assertion.',
          'editable_final_mesh':'PRINT_01_Head_Shell is the final editable v7 surface. EDITABLE_Outer_Surface_Before_Hollowing is retained only as the v6 pre-hollowing reference.',
          'normal_changes':'Visible protected coordinates are strictly fixed. Smooth vertex normals may change when adjacent added-cranium faces are finished; angular changes are informational and are not equated with sculpt displacement.',
          'mechanics':'On baseline coordinates: neck cylinder radius <=15 mm around (0, neck_center_y), z <= neck_platform_top; each magnet center sphere radius <=7 mm.',
          'stl':'Verify each baseline/current STL independently against its Blender mesh, including exact float32 vertex positions and the oriented triangle multiset. Then attribute exported corner samples to the verified same vertex indices; no nearest-point displacement approximation.',
          'raw_pmx_error':'Nearest target-surface distance from original source vertices is separate from corresponding-vertex displacement, and is not used as an exact-zero proof.'},
        'same_index_displacement':{},'exported_stl_correspondence':{},'raw_pmx_nearest_surface_error':{},'informational_vertex_normal_changes':{},
        'limits':['No z<30 blanket protection is asserted; the added postauricular surface is the finishing region.',
                  'Source preservation means no further v6-to-v7 change, not pointwise equality of the final print mesh to raw PMX.',
                  'Head source labels are nearest-v5-master mappings after voxelization, not original print-vertex construction history.',
                  'The old full source-mapped print regions include inner cavity walls. These remain informational, while every current visible source lock and raw feature ROI is strict.',
                  'The 442 authorized ear-back interior vertices are a documented exception to the earlier whole-ear lock; each must remain within 0.15 mm of delivered v6, and all other source-ear vertices remain fixed.',
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
  # V6 changes the added shell, so the inherited V5 coordinates and a hash
  # containing its geometry-dependent quad tessellation are not the baseline.
  for name in ('edges','loops','polygon_sizes'):
   checks[key+'_inherited_mask_'+name+'_indices_match_v06']=np.array_equal(a[name],protect[key+'_baseline_'+name])
  strict=protect['master_locked'] if key=='master' else visible_head['head_locked']
  checks[key+'_inherited_protected_positions_match_v06']=np.array_equal(a['vertices'][strict],protect[key+'_baseline_vertices'][strict])
  if key=='head':
   checks['head_visible_mask_protected_positions_match_v06']=np.array_equal(a['vertices'][strict],visible_head['head_baseline_vertices'][strict])
   checks['head_visible_mask_contains_all_raw_feature_rois']=all(not np.any(protect['head_raw_feature_'+name]&~visible_head['head_locked']) for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi'))
 if topology:
  delta=np.linalg.norm(b['vertices']-a['vertices'],axis=1);masks=regions(key,a['vertices'])
  delta_cache[key]=delta;mask_cache[key]=masks
  item['regions']={name:stats(delta[m]) for name,m in masks.items()}
  for name,m in masks.items():
   if key=='head' and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   if name=='permitted_earback_microfinish':
    checks[key+'_earback_microfinish_within_0_15mm']=bool(m.any() and delta[m].max()<=EAR_LIMIT+EPS)
   else:checks[key+'_'+name+'_exactly_unchanged']=bool(m.any() and np.count_nonzero(delta[m])==0)
  if key=='head':
   na=a['vertex_normals'];nb=b['vertex_normals']
   na=na/np.maximum(np.linalg.norm(na,axis=1,keepdims=True),1e-15)
   nb=nb/np.maximum(np.linalg.norm(nb,axis=1,keepdims=True),1e-15)
   angle=np.degrees(np.arctan2(np.linalg.norm(np.cross(na,nb),axis=1),np.einsum('ij,ij->i',na,nb)))
   for name in ('visible_source_sculpt_fixed','visible_source_face_fixed','visible_source_ear_fixed','permitted_earback_microfinish'):
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
 for version,objects,prefix in [('v06',baseline,'baseline'),('v07',current,'current')]:
  result[version],indices[version]=verify_stl(PATHS[prefix+'_'+part+'_stl'],objects[part])
  checks[part+'_'+version+'_stl_correspondence_verified']=result[version]['verified']
 if all(result[v]['verified'] for v in result) and checks[part+'_index_correspondence']:
  corner_ids=indices['v07'].ravel()
  actual_delta=np.linalg.norm(current[part]['vertices'].astype(np.float32).astype(float)-baseline[part]['vertices'].astype(np.float32).astype(float),axis=1)
  result['v6_to_v7_exported_corner_displacements']={name:stats(actual_delta[corner_ids[m[corner_ids]]]) for name,m in mask_cache[part].items()}
  for name,rr in result['v6_to_v7_exported_corner_displacements'].items():
   if part=='head' and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   if name=='permitted_earback_microfinish':
    checks[part+'_stl_earback_microfinish_within_0_15mm']=bool(rr.get('count',0)>0 and rr['max_mm']<=EAR_LIMIT+EPS)
   else:checks[part+'_stl_'+name+'_exactly_unchanged']=bool(rr.get('count',0)>0 and rr['moved_exactly_nonzero']==0)
 report['exported_stl_correspondence'][part]=result
checks['cap_stl_bytes_unchanged']=initial_hashes['baseline_cap_stl']==initial_hashes['current_cap_stl']

sv=source['vertices_mm']
raw_masks={name:m for name,m in source.items() if m.dtype==bool and m.shape==(len(sv),)}
for key in ('master','head'):
 errors={}
 for version,objects in [('v06',baseline),('v07',current)]:
  ob=objects[key];tree=BVHTree.FromPolygons(ob['vertices'].tolist(),ob['triangles'].tolist(),all_triangles=True)
  errors[version]=np.array([tree.find_nearest(Vector(p))[3] for p in sv])
 report['raw_pmx_nearest_surface_error'][key]={name:{'v06':stats(errors['v06'][m]),'v07':stats(errors['v07'][m]),
  'max_absolute_change_in_nearest_distance_mm':float(np.max(np.abs(errors['v07'][m]-errors['v06'][m])))} for name,m in raw_masks.items() if m.any()}

report['checks']=checks;report['all_checks_pass']=all(checks.values())
report['input_files_unchanged_during_audit']=all(digest(p)==initial_hashes[k] for k,p in PATHS.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit; refusing mixed-version report')
out=ROOT/'source-preservation-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'all_checks_pass':report['all_checks_pass'],
                  'failed_checks':[k for k,v in checks.items() if not v],
                  'current_head_stl_sha256':initial_hashes['current_head_stl']},indent=2),flush=True)
