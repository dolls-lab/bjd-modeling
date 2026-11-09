"""Apply the reviewed v13 local skin finish to the exact immutable v12 baseline."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np
import bpy,bmesh
from mathutils import Vector
R=Path(__file__).resolve().parent;D=R/'surface-postprocess';OLD=R.parent/'march7-bjd-1-4-v0.12'
BASE=OLD/'march7-bjd-head-v0.12-draft.blend';BLEND=R/'march7-bjd-head-v0.13-draft.blend';HEAD=R/'march7-head-shell-v0.13-draft.stl';CAP=R/'march7-head-cap-v0.13-draft.stl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
solution=D/'print-solution.npz'
with np.load(solution) as z:s={k:z[k] for k in z.files}
solver=json.loads((D/'print-solution-report.json').read_text());cross=json.loads((D/'print-local-intersections.json').read_text());thick=json.loads((D/'print-local-thickness.json').read_text())
for proof in (solver,cross,thick):assert proof['solution_sha256']==sha(solution)
assert cross['new_strict_intersections']==0 and cross['new_ambiguous_contacts']==0 and solver['normal_over_90_count']==0 and thick['new_below_0p4_count']==0
assert solver['maximum_displacement_mm']<=.45
oldhash=sha(BASE);assert oldhash==str(s['baseline_blend_sha256']);oldheadhash=sha(OLD/'march7-head-shell-v0.12-draft.stl');capsha=sha(OLD/'march7-head-cap-v0.12-draft.stl')
bpy.ops.wm.open_mainfile(filepath=str(BASE));h=bpy.data.objects['PRINT_01_Head_Shell'];h.data.calc_loop_triangles()
v=np.array([h.matrix_world@p.co for p in h.data.vertices]);f=np.array([t.vertices[:] for t in h.data.loop_triangles],np.int32)
assert np.array_equal(v,s['before']) and np.array_equal(f,s['triangles'])
other={name:np.array([o.matrix_world@p.co for p in o.data.vertices]) for name,o in bpy.data.objects.items() if o.type=='MESH' and name!=h.name}
inv=h.matrix_world.inverted()
for i in np.flatnonzero(s['free']):h.data.vertices[int(i)].co=inv@Vector(s['after'][i])
h.data.update();actual=np.array([h.matrix_world@p.co for p in h.data.vertices]);delta=np.linalg.norm(actual-v,axis=1)
assert np.array_equal(actual[s['locked']],v[s['locked']]);assert np.max(np.linalg.norm(actual-s['after'],axis=1))<.00002
for key in ('inner_wall_locked','major_features_locked','ear_locked','eye_guard'):assert np.array_equal(actual[s[key]],v[s[key]])
for name,coords in other.items():assert np.array_equal(coords,np.array([bpy.data.objects[name].matrix_world@p.co for p in bpy.data.objects[name].data.vertices]))
h['surface_finish_version']='v0.13-draft: local temple and ear-front exterior skin fairing only; no global remesh or head-shape reconstruction.'
h['surface_finish_solution_sha256']=sha(solution);h['editable_final_object']='PRINT_01_Head_Shell; mother remains inherited pre-hollow reference, not the final print surface.'
bpy.context.scene['model_version']='v0.13-draft'
bpy.ops.object.select_all(action='DESELECT');h.select_set(True);bpy.context.view_layer.objects.active=h
bpy.ops.wm.stl_export(filepath=str(HEAD),export_selected_objects=True,apply_modifiers=True,global_scale=1.0,use_scene_unit=False)
shutil.copy2(OLD/'march7-head-cap-v0.12-draft.stl',CAP)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
report=json.loads((OLD/'build-report.json').read_text());report['version']='v0.13-draft'
report['inherited_v12_processing']={'note':'Historical processing of the immutable v12 baseline. v13 only performs the separate actual-print skin finish below.','ear_postprocess':report.pop('ear_postprocess'),'unified_mother_surface':report.pop('unified_mother_surface')}
for name in ('PRINT_01_Head_Shell','PRINT_02_Removable_Cap'):
 ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data);vv=np.array([ob.matrix_world@p.co for p in ob.data.vertices])
 report['parts'][name].update(vertices=len(ob.data.vertices),faces=len(ob.data.polygons),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),volume_mm3=float(abs(bm.calc_volume(signed=True))),bounds_mm=np.ptp(vv,axis=0).tolist());bm.free()
finish={'method':solver['method'],'baseline_version':'v0.12-draft','baseline_blend_sha256':oldhash,'baseline_head_stl_sha256':oldheadhash,'solution_file':'surface-postprocess/print-solution.npz','solution_sha256':sha(solution),'performed_on_actual_print_only':True,'topology_unchanged':True,'mother_cap_reference_unchanged':True,'all_other_mesh_objects_exactly_unchanged':True,'cap_stl_bytes_unchanged':sha(CAP)==capsha,'moved_vertices':int(np.count_nonzero(delta)),'free_vertices':int(s['free'].sum()),'maximum_actual_displacement_mm':float(delta.max()),'outside_support_exactly_unchanged':True,'eye_guard_ears_inner_wall_major_features_exactly_unchanged':True,'selected_alpha':solver['selected']['alpha'],'maximum_1368_direction_support_change_mm':solver['maximum_global_support_change_mm'],'global_xyz_bounds_unchanged':bool(np.array_equal(np.ptp(actual,axis=0),np.ptp(v,axis=0))),'local_nonadjacent_new_intersections':0,'normal_rotation_over_90_triangles':0,'local_thickness_sampling':thick,'visual_review':'Same-angle actual geometry closeups accepted: short temple grooves reduced, natural upper-ear attachment concavity retained; source ear shape and earlier rear-ear finishing preserved.','preservation_note':'Only local exterior skin points intentionally move. Overall shape is inherited from v12; no remeshing, hollowing, cap recut or mechanical changes.'}
report['surface_postprocess']=finish;(R/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(BASE)==oldhash and sha(OLD/'march7-head-shell-v0.12-draft.stl')==oldheadhash and sha(OLD/'march7-head-cap-v0.12-draft.stl')==capsha
finish.update(final_blend_sha256=sha(BLEND),final_head_stl_sha256=sha(HEAD),final_cap_stl_sha256=sha(CAP),build_report_sha256=sha(R/'build-report.json'))
(D/'surface-finish-provenance.json').write_text(json.dumps(finish,ensure_ascii=False,indent=2)+'\n');print(json.dumps(finish,ensure_ascii=False,indent=2),flush=True)
