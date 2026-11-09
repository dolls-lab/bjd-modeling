"""Blender-only read audit. Writes JSON; never saves or changes either model.

blender -b -t 4 --python audit_source_faithfulness.py -- --current-dir PATH
Reports true same-index displacements only after topology/order checks.
Raw PMX nearest-surface distances are reported separately and are NOT vertex
displacements, correspondence, likeness scores, or physical fit validation.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

parser=argparse.ArgumentParser()
parser.add_argument('--current-dir',type=Path,required=True)
parser.add_argument('--baseline-dir',type=Path,default=Path('/Users/mmj/Projects/mihoyo/hksr_database/outputs/march7-bjd-1-4-v0.3'))
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root=args.current_dir.resolve();base=args.baseline_dir.resolve()
paths={'baseline_blend':base/'march7-bjd-head-v0.3-draft.blend',
       'current_blend':root/'march7-bjd-head-v0.5-draft.blend',
       'baseline_stl':base/'march7-head-shell-v0.3-draft.stl',
       'current_stl':root/'march7-head-shell-v0.5-draft.stl'}
for path in paths.values():
    if not path.is_file():raise FileNotFoundError(path)
with np.load(root/'source-protection-masks.npz') as archive:
    source={key:archive[key] for key in archive.files}
sv=source['vertices_mm'];sf=source['faces'];geod=source['outer_boundary_geodesic_mm']
with np.load(root/'head-protection-weights.npz') as protection_archive:
    DEEP_LOCK_MM=float(protection_archive['deep_lock_mm']) if 'deep_lock_mm' in protection_archive.files else 4.0
DEEP_KEY=f'source_deep_face_barycentric_geod_ge{DEEP_LOCK_MM:g}mm_and_distance_lt2mm'
source_bvh=BVHTree.FromPolygons(sv.tolist(),sf.tolist(),all_triangles=True)
source_kd=KDTree(len(sv))
for i,p in enumerate(sv):source_kd.insert(Vector(p),i)
source_kd.balance()
OBJECTS={'master':'EDITABLE_Outer_Surface_Before_Hollowing','head':'PRINT_01_Head_Shell','cap':'PRINT_02_Removable_Cap','source_reference':'SOURCE_Original_March7_Face_DoNotPrint'}
FEATURES=('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
EPS=1e-6

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path));out={}
    for key,name in OBJECTS.items():
        ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
        out[key]={'vertices':np.array([ob.matrix_world @ v.co for v in me.vertices],float),
                  'loops':np.array([l.vertex_index for l in me.loops],int),
                  'polygon_lengths':np.array([len(p.vertices) for p in me.polygons],int),
                  'triangles':np.array([t.vertices[:] for t in me.loop_triangles],int)}
    return out

def stats(d):
    return dict(count=len(d),mean_mm=float(d.mean()),median_mm=float(np.median(d)),p95_mm=float(np.percentile(d,95)),max_mm=float(d.max()),moved_over_1e_6mm=int(np.sum(d>EPS))) if len(d) else {'count':0}

def region_masks(vertices):
    # Independent source-derived masks evaluated on BASELINE coordinates.
    # Deep mask uses continuous source geodesic distance interpolated at the
    # closest surface point. The previous all-3-corners >=4mm definition remains
    # a distinct historical diagnostic, never silently relabelled as current.
    n=len(vertices);deep=np.zeros(n,bool);old_deep=np.zeros(n,bool);features={key:np.zeros(n,bool) for key in FEATURES}
    nearest_dist=np.empty(n)
    for i,p in enumerate(vertices):
        q,normal,tri,distance=source_bvh.find_nearest(Vector(p));nearest_dist[i]=distance
        if distance<2.0:
            gmin=np.min(geod[sf[tri]])
            a,b,c=sv[sf[tri]];ab=b-a;ac=c-a;aq=np.array(q)-a
            aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=aq@ab;qc=aq@ac;den=aa*cc-bb*bb
            if abs(den)>1e-15:
                beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den
                bary=np.maximum([1-beta-gamma,beta,gamma],0.);bary/=bary.sum()
                g=float(bary@geod[sf[tri]])
            else:g=float(np.mean(geod[sf[tri]]))
            deep[i]=g>=DEEP_LOCK_MM
            old_deep[i]=gmin>=4.0
        if distance<3.0:
            k=source_kd.find(q)[1]
            for key in FEATURES:features[key][i]=bool(source[key][k])
    x,y,z=vertices.T
    return {'all_vertices':np.ones(n,bool),
            DEEP_KEY:deep,
            'historical_4mm_source_core_including_new_transition_band':old_deep,
            'all_below_z21mm':z<21,
            'all_below_z30mm':z<30,
            'ear_surface':(np.abs(x)>20)&(z>17)&(z<36)&(nearest_dist<1.5),
            **features}

def topology_match(a,b):
    return len(a['vertices'])==len(b['vertices']) and np.array_equal(a['loops'],b['loops']) and np.array_equal(a['polygon_lengths'],b['polygon_lengths']) and np.array_equal(a['triangles'],b['triangles'])

baseline=snapshot(paths['baseline_blend']);current=snapshot(paths['current_blend'])
build_meta=json.loads((root/'build-report.json').read_text())
report={'units':'mm','baseline_version':'v0.3','current_version':'v0.5','numeric_zero_tolerance_mm':EPS,
        'source_deep_face_lock_distance_mm':DEEP_LOCK_MM,
        'current_build_method':build_meta.get('junction_fairing',{}).get('method'),
        'current_build_report_sha256':digest(root/'build-report.json'),
        'current_build_max_master_displacement_mm':build_meta.get('junction_fairing',{}).get('master_max_displacement_mm'),
        'files':{k:{'path':str(v),'sha256':digest(v)} for k,v in paths.items()},
        'same_index_displacement':{},'raw_pmx_nearest_surface_error':{},
        'methods':{
           'same_index':'Compare coordinates at equal vertex indices only after exact equality of vertex count, loop vertex-index array, polygon sizes, and triangle-index array. These are actual vertex displacements.',
           'source_deep_face':f'Barycentric source geodesic at closest raw-PMX surface point >={DEEP_LOCK_MM:g} mm and nearest distance <2 mm. Historical 4 mm mask still uses ALL 3 source triangle geodesic distances >=4 mm; it stays in report but is not a current unchanged-region assertion.',
           'feature_regions':'Closest raw-source vertex to the closest source-surface point carries the original feature mask; vertex is within 3 mm of raw source. Masks are computed using baseline positions only.',
           'raw_error':'At each original welded PMX face vertex, query nearest target triangle. No correspondence is asserted. Report PMX-to-v3 and PMX-to-v5 separately.',
           'stl':'Binary STL facet/corner mapping is checked against same-index Blender head vertices before displacements are attributed to exported geometry.'},
        'limits':['No complete official skull exists in face material; added cranium is new design.',
                  'Zero v3-to-v5 protected-region motion does not imply raw PMX and v3 were identical.',
                  'Distance at original vertices does not bound every point on a surface; not a physical fit or visual likeness certification.']}
mask_cache={}
for key in OBJECTS:
    a,b=baseline[key],current[key];same=topology_match(a,b)
    entry={'topology_and_index_order_identical':bool(same),'baseline_vertices':len(a['vertices']),'current_vertices':len(b['vertices'])}
    if same:
        delta=np.linalg.norm(b['vertices']-a['vertices'],axis=1)
        masks=region_masks(a['vertices']) if key in ('master','head') else {'all_vertices':np.ones(len(delta),bool)}
        mask_cache[key]=masks;entry['regions']={name:stats(delta[m]) for name,m in masks.items()}
    else:entry['reason']='Index-correspondence checks failed; no per-index displacement claim made.'
    report['same_index_displacement'][key]=entry
    print(key,entry['topology_and_index_order_identical'],flush=True)

# Baseline errors introduced before v5 are visible and never relabelled as new
# v5 deformations. Include both master surface and exact final print mesh.
raw_masks={k:v for k,v in source.items() if v.dtype==bool and v.shape==(len(sv),)}
raw_masks[f'source_face_excluding_{DEEP_LOCK_MM:g}mm_outer_seam_band']=geod>DEEP_LOCK_MM
for key in ('master','head'):
    errors={}
    for version,objects in (('v03',baseline),('v05',current)):
        ob=objects[key];tree=BVHTree.FromPolygons(ob['vertices'].tolist(),ob['triangles'].tolist(),all_triangles=True)
        errors[version]=np.array([tree.find_nearest(Vector(p))[3] for p in sv])
    report['raw_pmx_nearest_surface_error'][key]={name:{
        'v03':stats(errors['v03'][mask]),'v05':stats(errors['v05'][mask]),
        'max_absolute_change_in_nearest_distance_mm':float(np.max(np.abs(errors['v05'][mask]-errors['v03'][mask])))} for name,mask in raw_masks.items() if mask.any()}

def read_binary_stl(path):
    data=path.read_bytes();count=int.from_bytes(data[80:84],'little')
    if len(data)!=84+count*50:raise ValueError('Expected exact binary STL layout: '+str(path))
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    return np.frombuffer(data,offset=84,dtype=dtype,count=count)['vertices'].astype(float)

at=read_binary_stl(paths['baseline_stl']);bt=read_binary_stl(paths['current_stl'])
stl={'baseline_triangles':len(at),'current_triangles':len(bt),'verified_facet_corner_correspondence':False}
if at.shape==bt.shape and report['same_index_displacement']['head']['topology_and_index_order_identical']:
    # Map unique exact float32 STL coordinates to baseline Blender vertex IDs.
    uv,inverse=np.unique(at.reshape(-1,3),axis=0,return_inverse=True)
    lookup={tuple(p):i for i,p in enumerate(baseline['head']['vertices'].astype(np.float32).astype(float))}
    ids=np.array([lookup.get(tuple(p),-1) for p in uv],int)
    stl['all_baseline_stl_vertices_match_baseline_blend_exactly']=bool(np.all(ids>=0))
    if np.all(ids>=0):
        expected=current['head']['vertices'][ids[inverse]].reshape(bt.shape)
        residual=np.linalg.norm(bt-expected,axis=2)
        stl['export_vs_corresponding_blend_max_error_mm']=float(residual.max())
        if residual.max()<=1e-5:
            stl['verified_facet_corner_correspondence']=True
            delta=np.linalg.norm(bt-at,axis=2).reshape(-1)
            stl['regions_triangle_corner_samples']={name:stats(delta[mask[ids[inverse]]]) for name,mask in mask_cache['head'].items()}
report['exported_stl_correspondence']=stl
critical=(DEEP_KEY,'all_below_z21mm','all_below_z30mm','eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi','ear_surface')
checks={}
for key in ('master','head'):
    item=report['same_index_displacement'][key]
    checks[key+'_index_correspondence']=item['topology_and_index_order_identical']
    for region in critical:
        rr=item.get('regions',{}).get(region,{})
        checks[key+'_'+region+'_unchanged']=bool(rr.get('count',0)>0 and rr.get('max_mm',1e9)<=EPS)
checks['source_reference_unchanged']=report['same_index_displacement']['source_reference'].get('regions',{}).get('all_vertices',{}).get('max_mm',1e9)<=EPS
checks['cap_unchanged']=report['same_index_displacement']['cap'].get('regions',{}).get('all_vertices',{}).get('max_mm',1e9)<=EPS
checks['export_correspondence_verified']=stl['verified_facet_corner_correspondence']
report['v3_protected_feature_preservation_checks']=checks
report['all_listed_protected_checks_pass']=all(checks.values())
report['input_files_unchanged_during_audit']=all(digest(path)==report['files'][key]['sha256'] for key,path in paths.items())
if not report['input_files_unchanged_during_audit']:
    raise RuntimeError('Model input changed during audit; refusing to write mixed-version report')
out=root/'source-faithfulness-review.json';out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'output':str(out),'all_listed_protected_checks_pass':report['all_listed_protected_checks_pass'],'checks':checks},indent=2),flush=True)
