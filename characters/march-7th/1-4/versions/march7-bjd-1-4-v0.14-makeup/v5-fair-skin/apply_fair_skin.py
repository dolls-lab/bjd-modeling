"""Lighten only the uniform BJD skin base; preserve local makeup, hair and geometry."""
from pathlib import Path
import hashlib, json
import bpy, numpy as np
from mathutils import Vector
R = Path(__file__).resolve().parent
OLD = R.parent/'v4-hair-preview'
SOURCE = OLD/'march7-v14-pale-skin-original-hair.blend'
OUT = R/'march7-v14-fair-skin-original-hair.blend'
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def mesh_state(ob):
    me = ob.data
    me.calc_loop_triangles()
    v = np.asarray([ob.matrix_world @ q.co for q in me.vertices],np.float32)
    f = np.asarray([q.vertices[:] for q in me.loop_triangles],np.int32)
    uvs = {}
    for layer in me.uv_layers:
        values = np.empty(len(me.loops)*2,np.float32)
        layer.data.foreach_get('uv',values)
        uvs[layer.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return {'geometry':hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest(),'uv':uvs}
def meshes():
    return {o.name:mesh_state(o) for o in bpy.context.scene.objects if o.type=='MESH'}
def image_hashes():
    return {im.name:hashlib.sha256(im.packed_file.data).hexdigest() for im in bpy.data.images if im.packed_file}
source_hash = sha(SOURCE)
assert source_hash == '3fe03f533575cd2d50ff53c75d278d28c69f0390286718e7db1e57931acf6dd8'
config = json.loads((R/'skin-tone.json').read_text())
rgb = np.asarray(config['new_srgb_8bit'],np.float64)/255
linear = np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
rgba = (*linear,1.)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
before = meshes()
images_before = image_hashes()
head = bpy.data.objects['PRINT_01_Head_Shell']
cap = bpy.data.objects['PRINT_02_Removable_Cap']
mat = head.data.materials[0]
bs = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
mix = bs.inputs['Base Color'].links[0].from_node
assert mix.type=='MIX_RGB' and not mix.inputs[1].is_linked
old_color = tuple(mix.inputs[1].default_value)
mix.inputs[1].default_value = rgba
bs.inputs['Base Color'].default_value = rgba
mat.diffuse_color = rgba
capmat = cap.data.materials[0]
capbs = next(n for n in capmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert not capbs.inputs['Base Color'].is_linked
assert np.allclose(capbs.inputs['Base Color'].default_value,old_color)
capbs.inputs['Base Color'].default_value = rgba
capmat.diffuse_color = rgba
s = bpy.context.scene
s['skin_reference_srgb'] = config['new_hex']
s['preview_note'] = 'v14 geometry, local makeup, eye cups and original hair preserved. Uniform head/cap base color lightened and made less yellow for closer visual agreement with the original PMX under the same studio.'
assert before==meshes() and images_before==image_hashes()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT))
assert before==meshes() and images_before==image_hashes() and sha(SOURCE)==source_hash
report = {'source_model_sha256':source_hash,'new_model_sha256':sha(OUT),
          'source_model_unchanged':True,'all_six_meshes_and_uv_unchanged':True,
          'existing_meshes':before,'all_packed_textures_unchanged':True,'packed_textures':images_before,
          'previous_skin_linear_rgba':old_color,'new_skin_linear_rgba':rgba,
          'new_skin_srgb':config['new_hex'],'lighting_exposure_and_non_skin_materials_unchanged':True,
          'change_scope':'Only uniform head/cap skin base color; no full-face texture, no emission, no geometry change.'}
(R/'skin-change-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FAIR_SKIN_SAVED '+report['new_model_sha256'],flush=True)

old_provenance = json.loads((OLD/'render-provenance.json').read_text())
assert old_provenance['model_sha256']==source_hash
views_by_name = {Path(v['file']).stem:v for v in old_provenance['views']}
cam = bpy.context.scene.camera
s = bpy.context.scene
D = R/'previews'
D.mkdir(exist_ok=True)
rows = []
for name in ['face-front','face-quarter','front','quarter-left']:
    v = views_by_name[name]
    cam.location = v['camera_mm']
    cam.rotation_euler = (Vector(v['target_mm'])-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale = v['ortho_width_mm']
    s.render.resolution_x = s.render.resolution_y = 1100
    s.render.resolution_percentage = 100
    p = D/(name+'.png')
    s.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    rows.append({'file':p.name,'camera_mm':v['camera_mm'],'target_mm':v['target_mm'],
                 'ortho_width_mm':v['ortho_width_mm'],'sha256':sha(p)})
assert sha(OUT)==report['new_model_sha256'] and sha(SOURCE)==source_hash
(R/'render-provenance.json').write_text(json.dumps({'model_sha256':report['new_model_sha256'],
    'model_files_unchanged_by_render':True,'image_method':'Actual Blender render, same studio as v4 and original comparison, no retouching.',
    'views':rows},ensure_ascii=False,indent=2)+'\n')
print('FAIR_SKIN_RENDER_DONE',flush=True)
