"""Apply a verified, local v6-to-v7 geometry solution and export the print parts."""
from pathlib import Path
import hashlib,json,shutil
import bpy,bmesh
import numpy as np

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline-v0.6.blend'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='294ca014f8cb70d5fb3858fd67efedd8e3727c25b01293dc4d66fb8f17a6412e'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
head=bpy.data.objects['PRINT_01_Head_Shell']
cap=bpy.data.objects['PRINT_02_Removable_Cap']
master=bpy.data.objects['EDITABLE_Outer_Surface_Before_Hollowing']
records={}
for key,ob in [('head',head),('master',master)]:
    path=ROOT/(key+'-solution.npz')
    if not path.exists():
        records[key]={'changed':False,'note':'Retained v6 pre-hollowing reference; final editable print head contains the local finishing pass.'}
        continue
    with np.load(path) as archive:sol={k:archive[k] for k in archive.files}
    before=np.array([v.co[:] for v in ob.data.vertices])
    assert np.array_equal(before,sol['before']),key+' solution must use delivered v6 coordinates'
    assert sol['after'].shape==before.shape
    assert np.isfinite(sol['after']).all()
    for v,co in zip(ob.data.vertices,sol['after']):v.co=co
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for p in ob.data.polygons:p.use_smooth=True
    ob.data.update()
    actual=np.array([v.co[:] for v in ob.data.vertices])
    delta=np.linalg.norm(actual-before,axis=1)
    if 'locked' in sol:assert not np.any(delta[sol['locked']])
    np.savez_compressed(ROOT/(key+'-deformation.npz'),before=before,after=actual,displacement_mm=delta)
    records[key]={'changed':bool(np.any(delta)),'moved_vertices':int((delta>1e-6).sum()),'max_displacement_mm':float(delta.max()),'solution_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
bpy.context.view_layer.update()
report=json.loads((ROOT/'baseline-build-report.json').read_text())
report['version']='v0.7-draft'
report['inherited_v6_processing']={'side_skull_retraction':report.pop('side_skull_retraction')}
report['v7_surface_finishing_stages']=json.loads((ROOT/'local-fairing-report.json').read_text())
report['v7_local_fairing']={'baseline_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'objects':records,'cap_unchanged':True}
report['parts']={}
for ob in (head,cap):
    bm=bmesh.new();bm.from_mesh(ob.data)
    report['parts'][ob.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume(signed=True),'bounds_mm':list(ob.dimensions)}
    bm.free()
(ROOT/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT');head.hide_set(False);head.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.wm.stl_export(filepath=str(ROOT/'march7-head-shell-v0.7-draft.stl'),export_selected_objects=True,apply_modifiers=True,global_scale=1.,use_scene_unit=False)
shutil.copy2(ROOT/'baseline-cap.stl',ROOT/'march7-head-cap-v0.7-draft.stl')
head['revision']='v0.7: local postauricular surface finishing; see local-fairing-report.json'
master['revision_note']='v6 pre-hollowing reference; the final PRINT_01 mesh contains v7 local finishing.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'march7-bjd-head-v0.7-draft.blend'),compress=True)
print('V7_BUILD_DONE',json.dumps(records),flush=True)
