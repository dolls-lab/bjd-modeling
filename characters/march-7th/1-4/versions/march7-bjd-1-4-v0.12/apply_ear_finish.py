"""Reproduce the reviewed final PRINT-only ear finish after build_head.py.

Run with Blender -b -t4 --python apply_ear_finish.py. The current head must
match the recorded pre-finish coordinates/topology; no guessed remapping.
The unchanged mother remains the pre-hollow reference; PRINT is final.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import bpy,bmesh
from mathutils import Vector
R=Path(__file__).resolve().parent;D=R/'ear-postprocess'
BLEND=R/'march7-bjd-head-v0.12-draft.blend';HEAD=R/'march7-head-shell-v0.12-draft.stl';CAP=R/'march7-head-cap-v0.12-draft.stl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
solution=D/'print-solution.npz';s=np.load(solution);solver=json.loads((D/'print-solution-report.json').read_text())
cross=json.loads((D/'print-local-intersections.json').read_text());thick=json.loads((D/'print-local-thickness.json').read_text())
for report in (solver,cross,thick):assert report['solution_sha256']==sha(solution)
assert cross['new_strict_intersections']==0 and cross['new_ambiguous_contacts']==0
assert solver['normal_over_90_count']==0 and thick['new_below_0p4_count']==0
assert solver['selected']['max_mm']<=.30 and solver['selected']['rim_max_mm']<=.17
old_blend_hash=sha(BLEND);old_head_hash=sha(HEAD);cap_hash=sha(CAP)
bpy.ops.wm.open_mainfile(filepath=str(BLEND));h=bpy.data.objects['PRINT_01_Head_Shell'];h.data.calc_loop_triangles()
before=np.array([h.matrix_world@p.co for p in h.data.vertices]);faces=np.array([t.vertices[:] for t in h.data.loop_triangles],np.int32)
assert np.array_equal(faces,s['triangles']),'Current head topology differs from recorded pre-ear baseline'
assert np.array_equal(before,s['before']),'Rebuild the matching pre-ear model before applying; current vertices differ'
other={name:np.array([o.matrix_world@p.co for p in o.data.vertices]) for name,o in bpy.data.objects.items() if o.type=='MESH' and name!='PRINT_01_Head_Shell'}
inv=h.matrix_world.inverted();after_coordinates=s['after'];free_indices=np.flatnonzero(s['free'])
for i in free_indices:h.data.vertices[int(i)].co=inv@Vector(after_coordinates[i])
h.data.update();actual=np.array([h.matrix_world@p.co for p in h.data.vertices])
assert np.array_equal(actual[s['locked']],before[s['locked']])
assert np.max(np.linalg.norm(actual-s['after'],axis=1))<.00002
for name,v in other.items():assert np.array_equal(v,np.array([bpy.data.objects[name].matrix_world@p.co for p in bpy.data.objects[name].data.vertices]))
h['ear_surface_finishing']='Final PRINT geometry: rear-ear, attachment groove and narrow rim micro-fairing after voxel reconstruction; see ear-postprocess reports.'
h['ear_finish_solution_sha256']=sha(solution)
h['final_editable_surface']='PRINT_01_Head_Shell; pre-hollow mother does not include this ear-only print finish.'
bpy.ops.object.select_all(action='DESELECT');h.select_set(True);bpy.context.view_layer.objects.active=h
bpy.ops.wm.stl_export(filepath=str(HEAD),export_selected_objects=True,apply_modifiers=True,global_scale=1.0,use_scene_unit=False)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
assert sha(CAP)==cap_hash
report=json.loads((R/'build-report.json').read_text())
for name in ('PRINT_01_Head_Shell','PRINT_02_Removable_Cap'):
 ob=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(ob.data)
 vv=np.array([ob.matrix_world@p.co for p in ob.data.vertices]);rr=report['parts'][name]
 rr.update(vertices=len(ob.data.vertices),faces=len(ob.data.polygons),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),volume_mm3=float(abs(bm.calc_volume(signed=True))),bounds_mm=(vv.max(0)-vv.min(0)).tolist());bm.free()
actual_delta=np.linalg.norm(actual-before,axis=1)
finish={'method':solver['method'],'performed_after_voxel_reconstruction':True,
 'mother_unchanged_by_ear_finish':True,'editable_final_object':'PRINT_01_Head_Shell',
 'pre_ear_blend_sha256':old_blend_hash,'pre_ear_head_stl_sha256':old_head_hash,
 'solution_file':'ear-postprocess/print-solution.npz','solution_sha256':sha(solution),
 'moved_vertices':int(np.count_nonzero(actual_delta)),'free_vertices':int(s['free'].sum()),
 'maximum_actual_displacement_mm':float(actual_delta.max()),
 'maximum_rim_actual_displacement_mm':float(actual_delta[s['rim_weight']>.5].max()),
 'outside_support_exactly_unchanged':True,'all_other_mesh_objects_exactly_unchanged':True,
 'cap_stl_bytes_unchanged':True,'normal_rotation_over_90_triangles':0,
 'local_nonadjacent_new_intersections':0,'local_new_ambiguous_contacts':0,
 'thickness_sampling':thick,'solver_report':'ear-postprocess/print-solution-report.json',
 'local_intersection_report':'ear-postprocess/print-local-intersections.json',
 'visual_review':'Same two close views of actual geometry before/after, no raster retouching. Narrow natural attachment groove retained; original beaded rim explicitly released for micro-fairing.',
 'preservation_note':'Eye/nose/mouth/major face and ear concha/lobe beyond local support are unchanged by this step. Rear ear and narrow rim intentionally move; do not claim all original ear vertices remain fixed.'}
report['ear_postprocess']=finish
(R/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
finish.update(final_blend_sha256=sha(BLEND),final_head_stl_sha256=sha(HEAD),final_cap_stl_sha256=sha(CAP),build_report_sha256=sha(R/'build-report.json'))
(D/'ear-finish-provenance.json').write_text(json.dumps(finish,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(finish,ensure_ascii=False,indent=2),flush=True)
