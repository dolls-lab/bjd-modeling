"""Read-only v8 -> rebuilt v9 face/ear surface measurements.

Run after the final model exists:
  Blender -b -t 4 --python review_source_surface.py
No vertex-order correspondence between the two PRINT meshes is assumed.
Writes source-surface-review.json; never changes or saves a model.
"""
from pathlib import Path
import hashlib, json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'march7-bjd-1-4-v0.8'
PATHS={
 'baseline_blend':ROOT/'baseline-v0.8.blend',
 'current_blend':ROOT/'march7-bjd-head-v0.9-draft.blend',
 'current_head_stl':ROOT/'march7-head-shell-v0.9-draft.stl',
 'mother_surface':ROOT/'mother-surface.npz',
 'central_protection':ROOT/'central-source-protection.npz',
 'raw_source_masks':OLD/'source-protection-masks.npz',
 'baseline_provenance':OLD/'v6-side-protection.npz',
 'baseline_visible_masks':OLD/'head-visible-source-protection.npz',
 'baseline_print_earback':OLD/'preserved-v7-earback-mask.npz',
}
EXPECTED_V8_SHA='4ea04ae429876fe0a2ed0a750b74453d054c089777ecf9ad1c22d89585bf6034'
FEATURES=('eye_geodesic_2mm_band','mouth_geodesic_2mm_band','nose_roi','cheek_roi','chin_roi')
NAMES={'head':'PRINT_01_Head_Shell','master':'EDITABLE_Outer_Surface_Before_Hollowing'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def arc(p):
 with np.load(p) as a:return {k:a[k] for k in a.files}
for path in PATHS.values():
 if not path.is_file():raise FileNotFoundError(path)
hashes={k:sha(p) for k,p in PATHS.items()}
if hashes['baseline_blend']!=EXPECTED_V8_SHA:raise ValueError('Unexpected delivered-v8 baseline hash')
raw=arc(PATHS['raw_source_masks']);prov=arc(PATHS['baseline_provenance'])
vis=arc(PATHS['baseline_visible_masks']);earback=arc(PATHS['baseline_print_earback'])
core=arc(PATHS['central_protection']);mother=arc(PATHS['mother_surface'])

def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for key,name in NAMES.items():
  ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles()
  nm=ob.matrix_world.to_3x3().inverted().transposed()
  nn=np.array([nm@v.normal for v in me.vertices],float)
  nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-15)
  out[key]={'v':np.array([ob.matrix_world@v.co for v in me.vertices],float),
            'n':nn,'f':np.array([t.vertices[:] for t in me.loop_triangles],np.int32),
            'loops':np.array([l.vertex_index for l in me.loops],np.int32),
            'polygon_sizes':np.array([len(p.vertices) for p in me.polygons],np.int32)}
 return out
base=snapshot(PATHS['baseline_blend']);cur=snapshot(PATHS['current_blend'])
for field in ('loops','polygon_sizes'):
 if not np.array_equal(base['head'][field],prov['head_baseline_'+field]):
  raise ValueError('Historical mask does not match actual v8 baseline '+field)
if len(base['head']['v'])!=len(vis['head_visible_source_locked']):raise ValueError('Baseline mask count mismatch')

def tree(obj):return BVHTree.FromPolygons(obj['v'].tolist(),obj['f'].tolist(),all_triangles=True)
trees={key:{'v8':tree(base[key]),'v9':tree(cur[key])} for key in NAMES}
def stats(vals):
 a=np.asarray(vals,float);a=a[np.isfinite(a)]
 if not len(a):return {'count':0}
 return {'count':len(a),'mean_mm':float(a.mean()),'rms_mm':float(np.sqrt(np.mean(a*a))),
         'median_mm':float(np.median(a)),'p95_mm':float(np.percentile(a,95)),
         'max_mm':float(a.max()),'min_mm':float(a.min())}
# Baseline region assignment uses v8 positions and old *baseline-only* provenance.
# It is never applied by index to the newly remeshed print.
mf=prov['master_baseline_triangles'][prov['head_nearest_master_triangle']]
bc=prov['head_nearest_master_barycentric']
core_support=np.einsum('ij,ij->i',bc,core['master_core_locked'][mf])
earroot_support=np.einsum('ij,ij->i',bc,core['master_ear_root_transition'][mf])
outer=vis['head_visible_source_locked']
regions={'central_visible_sculpt':outer&(core_support>=.5),
         'visible_original_ear':vis['head_visible_source_ear'],
         'visible_ear_root':vis['head_visible_source_ear']&(earroot_support>=.5),
         'visible_ear_body':vis['head_visible_source_ear']&(earroot_support<.5),
         'v7_finished_print_earback_442':earback['mask']}
for name in FEATURES:regions[name]=outer&vis['head_raw_feature_'+name]
selected=np.logical_or.reduce(list(regions.values()));ids=np.flatnonzero(selected)
points=base['head']['v'];normals=base['head']['n']
dist=np.full(len(points),np.nan);signed=np.full(len(points),np.nan);matched=np.full_like(points,np.nan);normal_dot=np.full(len(points),np.nan)
for i in ids:
 q,n,ti,dd=trees['head']['v9'].find_nearest(Vector(points[i]))
 if q is not None:
  dist[i]=dd;signed[i]=np.dot(np.array(q)-points[i],normals[i]);matched[i]=q;normal_dot[i]=np.dot(n,normals[i])
forward={}
for name,mask in regions.items():
 used=np.flatnonzero(mask&np.isfinite(dist));bad=np.flatnonzero(mask&~np.isfinite(dist))
 worst=used[np.argsort(dist[used])[-5:][::-1]]
 forward[name]={'baseline_vertices':int(mask.sum()),'nearest_match_failures':len(bad),
   'nearest_surface_distance':stats(dist[mask]),
   'nearest_surface_normal_dot_below_0p25':int(np.sum(normal_dot[mask]<.25)),
   'nearest_surface_normal_dot_below_zero':int(np.sum(normal_dot[mask]<0)),
   'signed_offset_along_v8_normal':stats(signed[mask]),
   'worst_samples':[{'v8_vertex_id':int(i),'v8_point_mm':points[i].tolist(),
      'v9_matched_point_mm':matched[i].tolist(),'distance_mm':float(dist[i])} for i in worst]}
 print('SURFACE_FORWARD',name,forward[name]['nearest_surface_distance'],flush=True)

# Reverse direction: classify current exterior samples by their matched v8
# surface, with barycentric region membership. Dense current vertex samples
# are used; means are vertex-weighted, not area-weighted Hausdorff estimates.
def barycentric(p,tri):
 a,b,c=tri;ab=b-a;ac=c-a;ap=p-a;aa=ab@ab;bb=ab@ac;cc=ac@ac;qa=ap@ab;qc=ap@ac;den=aa*cc-bb*bb
 if abs(den)<1e-18:return np.array([1.,0.,0.])
 beta=(cc*qa-bb*qc)/den;gamma=(aa*qc-bb*qa)/den
 w=np.maximum([1-beta-gamma,beta,gamma],0);return w/w.sum()
bounds=np.array([points[selected].min(0)-2,points[selected].max(0)+2])
cv=cur['head']['v'];cn=cur['head']['n'];bf=base['head']['f']
mother_tree=BVHTree.FromPolygons(mother['after'].tolist(),mother['triangles'].tolist(),all_triangles=True)
reverse={name:[] for name in regions};reverse_points={name:[] for name in regions};reverse_low_normal_dot=0;reverse_mother_rejected=0
for i in np.flatnonzero(((cv>=bounds[0])&(cv<=bounds[1])).all(1)):
 mq,mn,mi,md=mother_tree.find_nearest(Vector(cv[i]))
 if mi is None or md>.65 or float(np.dot(mn,cn[i]))<.25:
  reverse_mother_rejected+=1;continue
 mj=mother['triangles'][mi];mw=barycentric(np.array(mq),mother['after'][mj])
 current_core=float(mw@mother['core_locked'][mj])>=.5
 current_ear=bool(prov['master_triangle_source_class'][mi]==1 or float(mw@core['master_source_ear_incident'][mj])>=1-1e-6)
 if not(current_core or current_ear):continue
 q,n,ti,dd=trees['head']['v8'].find_nearest(Vector(cv[i]))
 if ti is None or dd>2:continue
 jj=bf[ti];w=barycentric(np.array(q),points[jj])
 membership=[name for name,m in regions.items() if float(w@m[jj])>=.5 and
   (current_ear if name.startswith('visible_ear') or name in ('visible_original_ear','v7_finished_print_earback_442') else current_core)]
 if not membership:continue
 if float(np.dot(n,cn[i]))<.25:reverse_low_normal_dot+=1
 for name in membership:
  reverse[name].append(float(dd));reverse_points[name].append((float(dd),int(i),cv[i].tolist(),list(q)))

# Raw PMX samples quantify historical modeling error as well as new error.
# They are not pointwise preservation proofs and do not constrain upper scalp.
raw_errors={}
for key in NAMES:
 values={ver:np.array([tt.find_nearest(Vector(p))[3] for p in raw['vertices_mm']]) for ver,tt in trees[key].items()}
 raw_errors[key]={name:{'v8':stats(values['v8'][raw[name]]),'v9':stats(values['v9'][raw[name]]),
   'max_absolute_change_in_nearest_distance_mm':float(np.max(np.abs(values['v9'][raw[name]]-values['v8'][raw[name]])))} for name in FEATURES}

before=mother.get('baseline',mother['before']);after=mother['after']
delta=np.linalg.norm(after-before,axis=1)
mother_regions={name:stats(delta[mask]) for name,mask in {
 'central_hard':mother['core_locked'],'ear_body_hard':mother['ear_body_locked'],
 'source_noncore_transition':mother['source_transition'],'ear_root_transition':mother['ear_root_transition']}.items()}
checks={
 'baseline_sha_matches_final_v8':hashes['baseline_blend']==EXPECTED_V8_SHA,
 'mother_core_mask_matches_reviewed_mask':np.array_equal(mother['core_locked'],core['master_core_locked']),
 'mother_triangle_provenance_order_matches':np.array_equal(mother['triangles'],prov['master_baseline_triangles']),
 'mother_central_hard_exactly_zero':bool(np.count_nonzero(delta[mother['core_locked']])==0),
 'mother_ear_body_hard_exactly_zero':bool(np.count_nonzero(delta[mother['ear_body_locked']])==0),
 'print_head_coordinates_finite':bool(np.isfinite(cv).all()),
 'mother_coordinates_finite':bool(np.isfinite(after).all()),
 'each_forward_region_has_samples':all(item['baseline_vertices']>0 for item in forward.values()),
}
report={'baseline_version':'v0.8','current_version':'v0.9','units':'mm',
 'files':{k:{'path':str(p),'sha256':hashes[k]} for k,p in PATHS.items()},
 'methods':{
  'mother':'Only unchanged-topology mother NPZ central/ear-body arrays receive exact corresponding-vertex checks.',
  'print':'Independent topology. Actual v8 visible exterior vertex samples to nearest v9 surface, with normal disagreement reported separately. No ray fallback is substituted for a nearest-distance value: this can jump to a distant ear fold. Reverse samples must be within0.65mm of current mother with aligned normal (dot>=0.25), belong to its actual central/ear source region, then receive barycentric v8 region membership within2mm; this prevents adjacent newly modeled cranium being mislabeled as ear.',
  'statistics':'Full selected baseline vertices; reverse current vertices within regional bounds. Means/percentiles are vertex-sampling weighted. Maxima are sampled distances, not certified continuous Hausdorff bounds.',
  'raw':'Original PMX ROI vertices to full mother/print surfaces, v8 and v9. Nearest-distance change is distinct from a corresponding-vertex displacement.',
  'ear_442':'The 442-point v7 finished PRINT ear-back patch is tracked separately from the coincidentally 442-point v5 MOTHER ear-root strip. Different meshes, masks and meanings.',
  'upper_cranium':'Source-origin high forehead and added cranium are intentionally reconstructable; no blanket original-material zero constraint or upper-forehead displacement cap is added by this audit.'},
 'mesh_counts':{ver:{key:{'vertices':len(o['v']),'triangles':len(o['f'])} for key,o in objects.items()} for ver,objects in [('v8',base),('v9',cur)]},
 'mother_corresponding_vertex_displacement':mother_regions,
 'v8_outer_surface_to_v9':forward,
 'v9_outer_surface_to_v8':{name:stats(vals) for name,vals in reverse.items()},
 'reverse_worst_samples':{name:[{'distance_mm':a,'v9_vertex_id':b,'v9_point_mm':c,'v8_matched_point_mm':d} for a,b,c,d in sorted(vals,reverse=True)[:5]] for name,vals in reverse_points.items()},
 'reverse_nearest_baseline_normal_dot_below_0p25':reverse_low_normal_dot,
 'reverse_current_mother_outer_filter_rejected':reverse_mother_rejected,
 'raw_pmx_nearest_surface_error':raw_errors,'integrity_checks':checks,
 'all_integrity_checks_pass':all(checks.values()),
 'scope':'Measurement report, not a zero-change claim for remeshed PRINT, a dimensional acceptance threshold, eye-aperture contour test, thickness test or physical fit certification. STL hash is bound to this report; exact STL correspondence is handled by the independent structure/export validation.'}
report['input_files_unchanged_during_audit']=all(sha(p)==hashes[k] for k,p in PATHS.items())
if not report['input_files_unchanged_during_audit']:raise RuntimeError('Input changed during audit; refuse mixed-version report')
out=ROOT/'source-surface-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'all_integrity_checks_pass':report['all_integrity_checks_pass'],
 'current_blend_sha256':hashes['current_blend']},indent=2),flush=True)
