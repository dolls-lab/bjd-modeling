"""Retract only the existing v16 lip ridges; all surrounding face vertices fixed."""
from pathlib import Path
import hashlib,json,shutil
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'v16-surface-fairing'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
params=json.loads((HERE/'parameters.json').read_text())
p=params['lip_adjustment']
source=SOURCE/'march7-bjd-head-1-4-v16.blend'
source_sha=sha(source)
assert source_sha=='13448fe3c2018752af51c46312dbba8643ac5021e589e1f94726ca4b61f4dbe9'
assert sha(SOURCE/'march7-head-shell-1-4-v16.stl')=='ed302cfdb3dce7f763e64fcdda104ec7eaed3a846ccea3f8eaaf84bd97e92c2d'
bpy.ops.wm.open_mainfile(filepath=str(source))
head=bpy.data.objects['PRINT_01_Head_Shell']
cap=bpy.data.objects['PRINT_02_Removable_Cap']
for obj in [head,cap]:
    obj.hide_set(False);obj.hide_viewport=False;obj.hide_render=False
    assert obj.matrix_world==Matrix.Identity(4)
vertices=np.array([v.co[:] for v in head.data.vertices],dtype=np.float64)
cap_before=np.array([v.co[:] for v in cap.data.vertices],dtype=np.float64)
head.data.calc_loop_triangles()
faces_before=np.array([t.vertices[:] for t in head.data.loop_triangles])
x,y,z=vertices.T

def smoothstep(t):
    t=np.clip(t,0,1)
    return t**3*(10-15*t+6*t*t)

line=p['seam_center_z_mm']+p['seam_curve_per_mm']*x*x
relative_z=z-line
x_weight=1-smoothstep((np.abs(x)-p['x_full_weight_half_width_mm'])/(p['x_zero_weight_half_width_mm']-p['x_full_weight_half_width_mm']))
z_weight=smoothstep((relative_z-p['min_relative_z_mm'])/(p['lower_plateau_relative_z_mm']-p['min_relative_z_mm']))*smoothstep((p['max_relative_z_mm']-relative_z)/(p['max_relative_z_mm']-p['upper_plateau_relative_z_mm']))
y_weight=smoothstep((p['zero_weight_y_above_mm']-y)/(p['zero_weight_y_above_mm']-p['full_weight_y_below_mm']))
delta=p['retraction_mm']*x_weight*z_weight*y_weight
allowed=(np.abs(x)<p['x_zero_weight_half_width_mm'])&(relative_z>p['min_relative_z_mm'])&(relative_z<p['max_relative_z_mm'])&(y<p['zero_weight_y_above_mm'])
assert np.all(delta[~allowed]==0)
for index in np.flatnonzero(delta):
    head.data.vertices[int(index)].co.y+=float(delta[index])
head.data.update()
after=np.array([v.co[:] for v in head.data.vertices],dtype=np.float64)
head.data.calc_loop_triangles()
assert np.array_equal(faces_before,np.array([t.vertices[:] for t in head.data.loop_triangles]))
assert np.array_equal(vertices[:,[0,2]],after[:,[0,2]])
assert np.array_equal(vertices[~allowed],after[~allowed])
assert np.array_equal(cap_before,np.array([v.co[:] for v in cap.data.vertices]))
change=after-vertices
assert np.min(change[:,1])>=0 and np.max(change[:,1])<p['maximum_displacement_mm']
head['mouth_adjustment']='v18: existing lips retract together at most 0.12mm; cheeks/chin/corners unchanged, seam X/Z unchanged.'
bpy.context.scene['model_version']=params['version']
bpy.context.scene['notes']='Quarter v18 lip-only trial based on v16. No new perioral reconstruction. Source v16 preserved.'
head_path=HERE/'march7-head-shell-1-4-v18.stl'
cap_path=HERE/'march7-head-cap-1-4-v18.stl'
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.wm.stl_export(filepath=str(head_path),export_selected_objects=True,apply_modifiers=True,global_scale=1.0,use_scene_unit=False)
shutil.copyfile(SOURCE/'march7-head-cap-1-4-v16.stl',cap_path)
bpy.context.preferences.filepaths.save_version=0
blend=HERE/'march7-bjd-head-1-4-v18.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
assert np.array_equal(after,np.array([v.co[:] for v in bpy.data.objects['PRINT_01_Head_Shell'].data.vertices]))
assert np.array_equal(cap_before,np.array([v.co[:] for v in bpy.data.objects['PRINT_02_Removable_Cap'].data.vertices]))
assert sha(source)==source_sha
changed=np.any(change!=0,axis=1)
np.savez_compressed(HERE/'lip-displacements.npz',vertex_indices=np.flatnonzero(changed),original_vertices=vertices[changed],delta=change[changed])
report={'version':params['version'],'source_blend_sha256':source_sha,'source_unchanged':True,'saved_reopened_meshes_identical':True,'blend':blend.name,'blend_sha256':sha(blend),'head_stl_sha256':sha(head_path),'cap_stl_sha256':sha(cap_path),'vertices':len(vertices),'triangles':len(faces_before),'topology_unchanged':True,'xz_unchanged':True,'outside_declared_lip_support_unchanged':True,'mouth_corners_unchanged':True,'mouth_seam_xz_unchanged':True,'cap_unchanged':True,'changed_vertices':int(changed.sum()),'max_displacement_mm':float(change[:,1].max()),'dy_range_mm':[float(change[:,1].min()),float(change[:,1].max())],'changed_bounds_mm':[vertices[changed].min(0).tolist(),vertices[changed].max(0).tolist()],'deformation':'Single continuous C2 inward-only offset across the existing lips including their seam; entire lip wall receives the same X/Z field before depth fade. No resampling, broad face reconstruction, outside-lip smoothing or outward filling.'}
(HERE/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('BUILD_COMPLETE',json.dumps(report),flush=True)
