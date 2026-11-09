"""Independent, read-only v5 -> v6 provenance and exported-STL audit.

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
 'baseline_blend':ROOT/'baseline-v0.5.blend',
 'current_blend':ROOT/'march7-bjd-head-v0.6-draft.blend',
 'baseline_head_stl':ROOT/'baseline-head.stl',
 'current_head_stl':ROOT/'march7-head-shell-v0.6-draft.stl',
 'baseline_cap_stl':ROOT/'baseline-cap.stl',
 'current_cap_stl':ROOT/'march7-head-cap-v0.6-draft.stl',
 'protection':ROOT/'v6-side-protection.npz',
 'visible_head_protection':ROOT/'head-visible-source-protection.npz',
 'visible_head_protection_report':ROOT/'head-visible-source-protection.json',
 'source_provenance':ROOT/'v5-master-source-provenance.npz',
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
with np.load(PATHS['source_provenance']) as arc:provenance={k:arc[k] for k in arc.files}
with np.load(PATHS['source_masks']) as arc:source={k:arc[k] for k in arc.files}
mechanics=json.loads(PATHS['baseline_report'].read_text())
build_meta=json.loads(PATHS['build_report'].read_text())
checks={}
checks['baseline_blend_matches_protection_sha256']=initial_hashes['baseline_blend']==str(protect['baseline_blend_sha256'])
checks['baseline_blend_matches_visible_head_protection_sha256']=initial_hashes['baseline_blend']==str(visible_head['baseline_blend_sha256'])

def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for key,name in NAMES.items():
  ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
  out[key]={'vertices':np.array([ob.matrix_world@v.co for v in me.vertices],dtype='<f8'),
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
  m['visible_source_shared_boundary']=visible_head['head_visible_source_shared_boundary']
  m['informational_old_full_source_lock']=protect['head_locked']
  m['informational_released_from_old_source_lock']=visible_head['head_released_from_old_lock']
  m['informational_old_mapped_shared_boundary']=protect['head_shared_boundary_lock']
 x,y,z=vertices.T
 m['neck_mechanical_cylinder']=((x*x+(y-mechanics['neck_center_y_mm'])**2)<=15.0**2)&(z<=mechanics['neck_platform_top_mm'])
 for i,c in enumerate(mechanics['magnet_centers_mm']):m[f'magnet_{i+1}_within_7mm']=np.linalg.norm(vertices-np.array(c),axis=1)<=7.0
 return m

baseline=snapshot(PATHS['baseline_blend']);current=snapshot(PATHS['current_blend'])
report={'baseline_version':'v0.5','current_version':'v0.6','units':'mm',
        'numeric_zero_tolerance_mm':EPS,'strict_zero_requirement':'Protected vertex coordinate differences must be exactly zero, not merely below tolerance.',
        'files':{k:{'path':str(p),'sha256':initial_hashes[k]} for k,p in PATHS.items()},
        'build_method':build_meta.get('side_skull_retraction',{}).get('method'),
        'methods':{
          'index_correspondence':'Vertex count, polygon loop-index array and polygon sizes must match. Edge and triangulation index equality are reported separately. Geometry-dependent quad tessellation is not itself a change to polygon topology.',
          'source_provenance':'Master retains every original PMX face/ear/closure incident vertex. Print-head strict sculpt protection is source/shared-boundary mapping within 0.65 mm of the actual v5 master, plus the independent raw feature ROI union. The previous full head source-class regions include inner cavity and are informational only.',
          'mechanics':'On baseline coordinates: neck cylinder radius <=15 mm around (0, neck_center_y), z <= neck_platform_top; each magnet center sphere radius <=7 mm.',
          'stl':'Verify each baseline/current STL independently against its Blender mesh, including exact float32 vertex positions and the oriented triangle multiset. Then attribute exported corner samples to the verified same vertex indices; no nearest-point displacement approximation.',
          'raw_pmx_error':'Nearest target-surface distance from original source vertices is separate from corresponding-vertex displacement, and is not used as an exact-zero proof.'},
        'same_index_displacement':{},'exported_stl_correspondence':{},'raw_pmx_nearest_surface_error':{},
        'limits':['No z<30 blanket protection is asserted for v6; the added side cranium is intentionally changed.',
                  'Source preservation means no further v5-to-v6 change, not pointwise equality of the final print mesh to raw PMX.',
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
  for name,array in a.items():checks[key+'_mask_baseline_'+name+'_matches']=np.array_equal(array,protect[key+'_baseline_'+name])
  topology_sha=hashlib.sha256(a['loops'].tobytes()+a['polygon_sizes'].tobytes()+a['triangles'].tobytes()).hexdigest()
  checks[key+'_mask_topology_hash_matches']=topology_sha==str(protect[key+'_topology_sha256'])
  if key=='head':
   checks['head_visible_mask_baseline_vertices_match']=np.array_equal(a['vertices'],visible_head['head_baseline_vertices'])
   checks['head_visible_mask_topology_hash_matches']=topology_sha==str(visible_head['head_topology_sha256'])
   checks['head_visible_mask_contains_all_raw_feature_rois']=all(not np.any(protect['head_raw_feature_'+name]&~visible_head['head_locked']) for name in ('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi'))
 if topology:
  delta=np.linalg.norm(b['vertices']-a['vertices'],axis=1);masks=regions(key,a['vertices'])
  delta_cache[key]=delta;mask_cache[key]=masks
  item['regions']={name:stats(delta[m]) for name,m in masks.items()}
  for name,m in masks.items():
   if key in ('master','head') and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   checks[key+'_'+name+'_exactly_unchanged']=bool(m.any() and np.count_nonzero(delta[m])==0)
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
 for version,objects,prefix in [('v05',baseline,'baseline'),('v06',current,'current')]:
  result[version],indices[version]=verify_stl(PATHS[prefix+'_'+part+'_stl'],objects[part])
  checks[part+'_'+version+'_stl_correspondence_verified']=result[version]['verified']
 if all(result[v]['verified'] for v in result) and checks[part+'_index_correspondence']:
  corner_ids=indices['v06'].ravel()
  actual_delta=np.linalg.norm(current[part]['vertices'].astype(np.float32).astype(float)-baseline[part]['vertices'].astype(np.float32).astype(float),axis=1)
  result['v5_to_v6_exported_corner_displacements']={name:stats(actual_delta[corner_ids[m[corner_ids]]]) for name,m in mask_cache[part].items()}
  for name,rr in result['v5_to_v6_exported_corner_displacements'].items():
   if part=='head' and name=='all_vertices':continue
   if name.startswith('informational_'):continue
   checks[part+'_stl_'+name+'_exactly_unchanged']=bool(rr.get('count',0)>0 and rr['moved_exactly_nonzero']==0)
 report['exported_stl_correspondence'][part]=result
checks['cap_stl_bytes_unchanged']=initial_hashes['baseline_cap_stl']==initial_hashes['current_cap_stl']

sv=source['vertices_mm']
raw_masks={name:m for name,m in source.items() if m.dtype==bool and m.shape==(len(sv),)}
for key in ('master','head'):
 errors={}
 for version,objects in [('v05',baseline),('v06',current)]:
  ob=objects[key];tree=BVHTree.FromPolygons(ob['vertices'].tolist(),ob['triangles'].tolist(),all_triangles=True)
  errors[version]=np.array([tree.find_nearest(Vector(p))[3] for p in sv])
 report['raw_pmx_nearest_surface_error'][key]={name:{'v05':stats(errors['v05'][m]),'v06':stats(errors['v06'][m]),
  'max_absolute_change_in_nearest_distance_mm':float(np.max(np.abs(errors['v06'][m]-errors['v05'][m])))} for name,m in raw_masks.items() if m.any()}

report['checks']=checks;report['all_checks_pass']=all(checks.values())
report['input_files_unchanged_during_audit']=all(digest(p)==initial_hashes[k] for k,p in PATHS.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit; refusing mixed-version report')
out=ROOT/'source-preservation-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'all_checks_pass':report['all_checks_pass'],
                  'failed_checks':[k for k,v in checks.items() if not v],
                  'current_head_stl_sha256':initial_hashes['current_head_stl']},indent=2),flush=True)
