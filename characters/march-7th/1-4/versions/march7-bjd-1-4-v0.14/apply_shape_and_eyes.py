"""Apply reviewed disjoint eye and crown changes to immutable v13 actual PRINT."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,hashlib,sys
from mathutils import Vector
R=Path(__file__).resolve().parent;OLD=R.parent/'march7-bjd-1-4-v0.13';sys.path.insert(0,str(R/'crown-postprocess'));from mapping import mapping
BASE=OLD/'march7-bjd-head-v0.13-draft.blend';BLEND=R/'march7-bjd-head-v0.14-draft.blend';HEAD=R/'march7-head-shell-v0.14-draft.stl';CAP=R/'march7-head-cap-v0.14-draft.stl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 with np.load(p) as d:return {k:d[k] for k in d.files}
eye=load(R/'eye-postprocess/eye-solution.npz');crown=load(R/'crown-postprocess/crown-solution.npz')
assert sha(R/'eye-postprocess/eye-solution.npz')=='83948585ee2ed7e622ddb6e65697361d4af750cdee07e21c34ebdbe31a305348'
assert sha(BASE)==str(crown['baseline_blend_sha256']);assert np.array_equal(eye['before'],crown['head_before']);assert np.array_equal(eye['triangles'],crown['head_triangles'])
assert not np.any(eye['free']&crown['head_free'])
target=mapping(eye['after'],crown['head_outer_distance_mm']);assert np.array_equal(target[crown['head_free']],crown['head_after'][crown['head_free']]);assert np.array_equal(target[~crown['head_free']],eye['after'][~crown['head_free']])
bpy.ops.wm.open_mainfile(filepath=str(BASE));before_other={o.name:np.array([o.matrix_world@p.co for p in o.data.vertices]) for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('PRINT_')}
sol={'head_before':eye['before'],'head_after_target':target,'head_eye_after_target':eye['after'],'head_triangles':eye['triangles'],'head_eye_free':eye['free'],'head_crown_free':crown['head_free'],'head_free':eye['free']|crown['head_free'],'head_locked':~(eye['free']|crown['head_free']),'cap_before':crown['cap_before'],'cap_after_target':crown['cap_after'],'cap_triangles':crown['cap_triangles'],'cap_crown_free':crown['cap_free'],'cap_free':crown['cap_free'],'cap_locked':~crown['cap_free'],'baseline_blend_sha256':crown['baseline_blend_sha256']}
for tag,name,path in [('head','PRINT_01_Head_Shell',HEAD),('cap','PRINT_02_Removable_Cap',CAP)]:
 o=bpy.data.objects[name];o.data.calc_loop_triangles();v=np.array([o.matrix_world@p.co for p in o.data.vertices]);f=np.array([t.vertices[:] for t in o.data.loop_triangles],np.int32);assert np.array_equal(v,sol[tag+'_before']) and np.array_equal(f,sol[tag+'_triangles'])
 inv=o.matrix_world.inverted();after=sol[tag+'_after_target']
 for i in np.flatnonzero(sol[tag+'_free']):o.data.vertices[int(i)].co=inv@Vector(after[i])
 o.data.update();sol[tag+'_after']=np.array([o.matrix_world@p.co for p in o.data.vertices]);assert np.array_equal(v[sol[tag+'_locked']],sol[tag+'_after'][sol[tag+'_locked']]);assert np.max(np.linalg.norm(sol[tag+'_after']-after,axis=1))<2e-5
 sol[tag+'_mechanical_locked']=crown[tag+'_mechanical_locked'];o['v14_editable_final_print']=True;o['v14_changes']='Original PMX eye aperture restoration (head only) + high crown X widening on assembled head/cap; see final-change-solution.npz.'
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.wm.stl_export(filepath=str(path),export_selected_objects=True,apply_modifiers=True,global_scale=1.0,use_scene_unit=False)
for name,v in before_other.items():assert np.array_equal(v,np.array([bpy.data.objects[name].matrix_world@p.co for p in bpy.data.objects[name].data.vertices]))
bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing']['historical_reference']='Inherited v12 pre-hollow mother. Does not include v12 ear finish, v13 skin finish or v14 eye/crown edits. Final editable geometry is PRINT head/cap.'
bpy.context.scene['model_version']='v0.14-draft';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
np.savez_compressed(R/'final-change-solution.npz',**sol)
report=json.loads((OLD/'build-report.json').read_text());report['version']='v0.14-draft';report['inherited_v13_processing']={'surface_postprocess':report.pop('surface_postprocess'),'baseline_blend_sha256':sha(BASE)}
for tag,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);v=sol[tag+'_after'];report['parts'][name].update(vertices=len(o.data.vertices),faces=len(o.data.polygons),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),volume_mm3=float(abs(bm.calc_volume(signed=True))),bounds_mm=np.ptp(v,axis=0).tolist());bm.free()
report['v14_eye_restoration']=json.loads((R/'eye-postprocess/eye-solution-report.json').read_text());report['v14_crown_widening']=json.loads((R/'crown-postprocess/crown-report.json').read_text());report['final_editable_geometry']='PRINT_01_Head_Shell and PRINT_02_Removable_Cap. Pre-hollow mother is historical reference.';report['v14_final_solution_sha256']=sha(R/'final-change-solution.npz')
(R/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
files={n:{'path':str(p),'sha256':sha(p)} for n,p in [('blend',BLEND),('head_stl',HEAD),('cap_stl',CAP),('solution',R/'final-change-solution.npz'),('build_report',R/'build-report.json')]};(R/'final-files-provenance.json').write_text(json.dumps(files,indent=2)+'\n');print(json.dumps(files,indent=2),flush=True)
assert sha(BASE)==str(crown['baseline_blend_sha256'])
