"""Further lip-only retraction, with transition weights tied to source depth."""
from pathlib import Path
import hashlib,json,shutil
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'v18-lip-only'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
params=json.loads((HERE/'parameters.json').read_text());p=params['lip_adjustment']
source=SOURCE/'march7-bjd-head-1-4-v18.blend'
source_sha=sha(source)
assert source_sha=='28197c2f02555c02885a5d8e065e844d2f1b842b940fd9c73e4a40f720a41066'
assert sha(SOURCE/'march7-head-shell-1-4-v18.stl')=='3399309ae690b1a8cfa022442971c9480ea0d427d51a3e8a8f6e58a7bf4af062'
bpy.ops.wm.open_mainfile(filepath=str(source))
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
for obj in [head,cap]:
    obj.hide_set(False);obj.hide_viewport=False;obj.hide_render=False
    assert obj.matrix_world==Matrix.Identity(4)
before=np.array([v.co[:] for v in head.data.vertices],dtype=np.float64)
cap_before=np.array([v.co[:] for v in cap.data.vertices],dtype=np.float64)
head.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in head.data.loop_triangles])
x,y,z=before.T;line=p['seam_center_z_mm']+p['seam_curve_per_mm']*x*x;rz=z-line
allowed=(np.abs(x)<p['x_zero_weight_half_width_mm'])&(rz>p['min_relative_z_mm'])&(rz<p['max_relative_z_mm'])&(y<p['zero_weight_y_above_mm'])
indices=np.flatnonzero(allowed)
def smoothstep(t):
    t=np.clip(t,0.,1.)
    return t**3*(10.-15.*t+6.*t*t)

field=np.load(HERE/'lip-field.npz')
field_report=json.loads((HERE/'lip-field-report.json').read_text())
assert sha(HERE/'lip-field.npz')==field_report['field_sha256']
assert sha(SOURCE/'march7-head-shell-1-4-v18.stl')==field_report['source_head_sha256']
gx,gu=field['x'],field['u'];grid=field['dy']
ix=np.clip(np.searchsorted(gx,x[indices])-1,0,len(gx)-2)
iu=np.clip(np.searchsorted(gu,rz[indices])-1,0,len(gu)-2)
fx=np.clip((x[indices]-gx[ix])/(gx[ix+1]-gx[ix]),0,1)
fu=np.clip((rz[indices]-gu[iu])/(gu[iu+1]-gu[iu]),0,1)
raw=(1-fu)*((1-fx)*grid[iu,ix]+fx*grid[iu,ix+1])+fu*((1-fx)*grid[iu+1,ix]+fx*grid[iu+1,ix+1])

fade=smoothstep((p['zero_weight_y_above_mm']-y[indices])/(p['zero_weight_y_above_mm']-p['full_weight_y_below_mm']))
dy=raw*fade
for index,d in zip(indices,dy):
    if d:head.data.vertices[int(index)].co.y+=float(d)
head.data.update();after=np.array([v.co[:] for v in head.data.vertices],dtype=np.float64)
head.data.calc_loop_triangles()
assert np.array_equal(faces,np.array([t.vertices[:] for t in head.data.loop_triangles]))
assert np.array_equal(before[:,[0,2]],after[:,[0,2]])
assert np.array_equal(before[~allowed],after[~allowed])
assert np.array_equal(cap_before,np.array([v.co[:] for v in cap.data.vertices]))
change=after-before;changed=np.any(change!=0,axis=1)
assert change[:,1].min()>=0 and 0<change[:,1].max()<p['maximum_displacement_mm']
head['mouth_adjustment']='v19: additional inward-only lip refinement from v18; source-depth transitions; cheeks/chin/corners fixed.'
bpy.context.scene['model_version']=params['version']
bpy.context.scene['notes']='Quarter v19. Exact source v18 retained; all non-lip geometry locked.'
head_path=HERE/'march7-head-shell-1-4-v19.stl';cap_path=HERE/'march7-head-cap-1-4-v19.stl'
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.wm.stl_export(filepath=str(head_path),export_selected_objects=True,apply_modifiers=True,global_scale=1.,use_scene_unit=False)
shutil.copyfile(SOURCE/'march7-head-cap-1-4-v18.stl',cap_path)
bpy.context.preferences.filepaths.save_version=0;blend=HERE/'march7-bjd-head-1-4-v19.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
assert np.array_equal(after,np.array([v.co[:] for v in bpy.data.objects['PRINT_01_Head_Shell'].data.vertices]))
assert np.array_equal(cap_before,np.array([v.co[:] for v in bpy.data.objects['PRINT_02_Removable_Cap'].data.vertices]))
assert sha(source)==source_sha
np.savez_compressed(HERE/'lip-displacements.npz',vertex_indices=np.flatnonzero(changed),original_vertices=before[changed],delta=change[changed])
report={'version':params['version'],'source_blend_sha256':source_sha,'source_unchanged':True,'saved_reopened_meshes_identical':True,'blend':blend.name,'blend_sha256':sha(blend),'head_stl_sha256':sha(head_path),'cap_stl_sha256':sha(cap_path),'vertices':len(before),'triangles':len(faces),'topology_unchanged':True,'xz_unchanged':True,'outside_declared_lip_support_unchanged':True,'mouth_corners_unchanged':True,'cap_unchanged':True,'changed_vertices':int(changed.sum()),'max_displacement_mm':float(change[:,1].max()),'dy_range_mm':[float(change[:,1].min()),float(change[:,1].max())],'changed_bounds_mm':[before[changed].min(0).tolist(),before[changed].max(0).tolist()],'field_provenance':field_report,'deformation':'Additional compact lip-only inward offset relative to v18. Transition coordinates use original outer-surface depth; only retraction amplitude is smoothed across X and capped by source depth bounds before compact tapering. All X/Z and outside-lip vertices fixed; inner/outer wall share the field.'}
(HERE/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('BUILD_COMPLETE',json.dumps(report),flush=True)
