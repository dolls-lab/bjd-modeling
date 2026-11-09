"""Change uniform skin color only, preserve the accepted local makeup and meshes."""
from pathlib import Path
import hashlib, json
import numpy as np
import bpy
from mathutils import Vector
R = Path(__file__).resolve().parent
SOURCE = R.parent / 'v2-surface-paint/march7-v14-local-makeup-v2.blend'
OUT = R / 'march7-v14-local-makeup-v3-skin.blend'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def mesh_state(ob):
    me = ob.data
    me.calc_loop_triangles()
    v = np.asarray([ob.matrix_world @ p.co for p in me.vertices], np.float32)
    t = np.asarray([p.vertices[:] for p in me.loop_triangles], np.int32)
    uv_hashes = {}
    for uv in me.uv_layers:
        a = np.empty(len(me.loops) * 2, np.float32)
        uv.data.foreach_get('uv', a)
        uv_hashes[uv.name] = hashlib.sha256(a.tobytes()).hexdigest()
    return {'geometry':hashlib.sha256(v.tobytes()+t.tobytes()).hexdigest(), 'uv_layers':uv_hashes}
def mesh_states():
    return {o.name:mesh_state(o) for o in bpy.context.scene.objects if o.type == 'MESH'}
def image_states():
    return {im.name:hashlib.sha256(im.packed_file.data).hexdigest() for im in bpy.data.images if im.packed_file}
def lighting_state():
    s = bpy.context.scene
    return {'lights':[(o.name, list(o.location), list(o.rotation_euler), o.data.energy, list(o.data.color), o.data.size)
                      for o in s.objects if o.type == 'LIGHT'],
            'world_color':list(s.world.node_tree.nodes['Background'].inputs[0].default_value),
            'world_strength':s.world.node_tree.nodes['Background'].inputs[1].default_value,
            'view_transform':s.view_settings.view_transform, 'exposure':s.view_settings.exposure}
source_sha = sha(SOURCE)
assert source_sha == 'a0cd63f6956b78f98251cfa1256b87c4145d1a4d74c0ed5c14eabe4b9cbbc5d8'
reference = json.loads((R / 'skin-color-reference.json').read_text())
assert sha(Path(reference['source_texture'])) == reference['source_texture_sha256']
rgba = (*reference['shader_linear_rgb'], 1.)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.context.scene
before = mesh_states()
images_before = image_states()
lighting_before = lighting_state()
head = bpy.data.objects['PRINT_01_Head_Shell']
cap = bpy.data.objects['PRINT_02_Removable_Cap']
mat = head.data.materials[0]
bs = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
mix = bs.inputs['Base Color'].links[0].from_node
assert mix.type == 'MIX_RGB' and not mix.inputs[1].is_linked
old_rgba = tuple(mix.inputs[1].default_value)
mix.inputs[1].default_value = rgba
bs.inputs['Base Color'].default_value = rgba
mat.diffuse_color = rgba
mat.node_tree.nodes['LOCAL_MAKEUP_ON'].label = '1 = local makeup; 0 = plain March7 skin tone'
capmat = cap.data.materials[0]
capbs = next(n for n in capmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert not capbs.inputs['Base Color'].is_linked
assert np.allclose(tuple(capbs.inputs['Base Color'].default_value), old_rgba)
capbs.inputs['Base Color'].default_value = rgba
capmat.diffuse_color = rgba
s['preview_note'] = 'v14 shape and v2 local makeup/eye cups unchanged. Uniform skin base sampled from the original March7 face texture. No full-face texture overlay.'
s['skin_reference_srgb'] = reference['sample_hex']
assert before == mesh_states() and images_before == image_states() and lighting_before == lighting_state()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT))
after = mesh_states()
assert before == after and images_before == image_states() and lighting_before == lighting_state()
assert sha(SOURCE) == source_sha
report = {'source_blend_sha256':source_sha, 'preview_blend_sha256':sha(OUT),
          'source_blend_unchanged':True, 'all_meshes_and_uv_unchanged':True,
          'geometry_and_uv_before':before, 'geometry_and_uv_after_reload':after,
          'all_packed_textures_unchanged':True, 'packed_texture_hashes':images_before,
          'lighting_and_color_management_unchanged':True,
          'previous_skin_linear_rgba':old_rgba, 'new_skin_linear_rgba':rgba,
          'reference_skin_srgb':reference['sample_hex'],
          'changed':'Uniform head/cap base color only; local painted marks and eye colors preserved.'}
(R / 'skin-change-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('SKIN_PREVIEW_SAVED ' + report['preview_blend_sha256'], flush=True)

# Identical cameras and studio to the already-reviewed v2 renders.
s = bpy.context.scene
cam = s.camera
D = R / 'previews'
D.mkdir(exist_ok=True)
views = [
    ('front', (0,-200,35), (0,0,35)),
    ('quarter-left', (-130,-190,55), (0,0,35)),
    ('quarter-right', (130,-190,55), (0,0,35)),
    ('side', (-220,0,35), (0,0,35)),
]
rows = []
for name, loc, target in views:
    cam.location = loc
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale = 88
    s.render.filepath = str(D / ('skin-' + name + '.png'))
    bpy.ops.render.render(write_still=True)
    rows.append({'file':Path(s.render.filepath).name, 'camera_mm':loc, 'target_mm':target, 'ortho_width_mm':88})
assert sha(OUT) == report['preview_blend_sha256'] and sha(SOURCE) == source_sha
(R / 'render-provenance.json').write_text(json.dumps({
    'model_sha256':report['preview_blend_sha256'], 'source_model_unchanged':True,
    'image_method':'Actual Blender renders with unchanged v2 studio and camera settings; no retouching.',
    'views':rows,
}, indent=2) + '\n')
print('SKIN_RENDER_DONE', flush=True)
