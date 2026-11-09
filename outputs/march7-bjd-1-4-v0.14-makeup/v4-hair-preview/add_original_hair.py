"""Add only the original March7 hair/accessory to the unchanged pale-skin preview."""
from pathlib import Path
import bpy, numpy as np, hashlib, json
from mathutils import Vector
R = Path(__file__).resolve().parent
BASE = R.parent / 'v3-march7-skin/march7-v14-local-makeup-v3-skin.blend'
SOURCE = R.parent / 'source-reference/source-reference.blend'
OUT = R / 'march7-v14-pale-skin-original-hair.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def state(ob):
    me = ob.data
    me.calc_loop_triangles()
    v = np.asarray([ob.matrix_world @ p.co for p in me.vertices], np.float32)
    f = np.asarray([t.vertices[:] for t in me.loop_triangles], np.int32)
    uvs = {}
    for layer in me.uv_layers:
        a = np.empty(len(me.loops)*2, np.float32)
        layer.data.foreach_get('uv', a)
        uvs[layer.name] = hashlib.sha256(a.tobytes()).hexdigest()
    return {'geometry':hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest(), 'uv':uvs}
basehash = sha(BASE)
sourcehash = sha(SOURCE)
assert basehash == 'bd1d320897bbc25f3a002c5bc8458e7c0fea7747b8a7ad2b677680b97af39f4d'
assert sourcehash == '446cc1013de352866632d84f9614d6dcd938a368e360fdbcbd6c197fe57cf844'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
s = bpy.context.scene
before = {o.name:state(o) for o in s.objects if o.type == 'MESH'}
textures_before = {im.name:hashlib.sha256(im.packed_file.data).hexdigest() for im in bpy.data.images if im.packed_file}
haircol = bpy.data.collections.new('04_Original_March7_Hair_PREVIEW_ONLY')
s.collection.children.link(haircol)
names = ['SOURCE_26_HEAD_ACCESSORY', 'SOURCE_28_HAIR']
with bpy.data.libraries.load(str(SOURCE), link=False) as (a, b):
    assert all(name in a.objects for name in names)
    b.objects = names
hair_before = {}
for ob in b.objects:
    oldname = ob.name
    haircol.objects.link(ob)
    ob.name = 'LOOK_Original_March7_Hair' if ob.get('source_material_index') == 28 else 'LOOK_Original_March7_Hair_Accessory'
    ob.hide_render = ob.hide_viewport = False
    ob.hide_set(False)
    ob['preview_only'] = True
    ob['reference_source_object'] = oldname
    ob['reference_geometry_unmodified'] = True
    hair_before[ob.name] = state(ob)
    for mat in ob.data.materials:
        # Keep original image colors and alpha, with partial studio shading.
        node = mat.node_tree.nodes.get('SOURCE_TexturePreviewWeight')
        if node:
            node.outputs[0].default_value = .6
    assert hair_before[ob.name] == state(ob)
assert len([o for o in s.objects if o.type == 'MESH']) == 6
assert before == {name:state(bpy.data.objects[name]) for name in before}
for name, digest in textures_before.items():
    assert hashlib.sha256(bpy.data.images[name].packed_file.data).hexdigest() == digest
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        im.pack()
s.cycles.transparent_max_bounces = 16
cam = s.camera
cam.location = (0,-220,27)
cam.rotation_euler = (Vector((0,0,27))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale = 133
s['preview_note'] = 'Pale v3 BJD head, local makeup and eye cups preserved. Only original PMX hair and accessory added. No original face, brow, mouth or game eye geometry imported.'
s['how_to_hide_hair'] = 'Disable collection 04_Original_March7_Hair_PREVIEW_ONLY in viewport/render.'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT))
after = {name:state(bpy.data.objects[name]) for name in before}
assert before == after
assert hair_before == {name:state(bpy.data.objects[name]) for name in hair_before}
assert sha(BASE) == basehash and sha(SOURCE) == sourcehash
report = {'source_pale_preview_sha256':basehash, 'original_hair_helper_sha256':sourcehash,
          'new_preview_sha256':sha(OUT), 'pale_preview_file_unchanged':True,
          'existing_head_cap_eye_meshes_and_uv_unchanged':True, 'original_hair_geometry_unchanged':True,
          'existing_meshes':after, 'added_hair_meshes':hair_before,
          'original_face_or_eye_geometry_imported':False,
          'existing_painted_texture_hashes':textures_before,
          'packed_images':[im.name for im in bpy.data.images if im.packed_file],
          'source_hair_shader_weight':.6,
          'purpose':'Original hair appearance reference; not a manufactured wig design.'}
(R/'hair-preview-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('HAIR_PREVIEW_SAVED '+report['new_preview_sha256'], flush=True)

s = bpy.context.scene
cam = s.camera
D = R/'previews'
D.mkdir(exist_ok=True)
views = [
    ('front', '正面', (0,-220,27), (0,0,27), 133),
    ('quarter-left', '左前斜侧', (-140,-210,58), (0,0,27), 135),
    ('quarter-right', '右前斜侧', (140,-210,58), (0,0,27), 135),
    ('side', '侧面', (-240,0,30), (0,0,27), 135),
    ('face-front', '面部正面近景', (0,-220,28), (0,-18,27), 61),
    ('face-quarter', '面部斜侧近景', (-125,-200,60), (0,-18,27), 65),
]
rows = []
for name, label, loc, target, scale in views:
    cam.location = loc
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale = scale
    s.render.resolution_x = s.render.resolution_y = 1100
    s.render.resolution_percentage = 100
    s.render.filepath = str(D/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    rows.append({'file':name+'.png', 'label':label, 'camera_mm':loc, 'target_mm':target,
                 'ortho_width_mm':scale, 'sha256':sha(D/(name+'.png'))})
assert sha(OUT) == report['new_preview_sha256'] and sha(BASE) == basehash
(R/'render-provenance.json').write_text(json.dumps({'model_sha256':report['new_preview_sha256'],
    'saved_models_unchanged_by_render':True, 'image_method':'Actual Blender render; no image retouching.',
    'views':rows}, ensure_ascii=False, indent=2)+'\n')
print('SIX_ORIGINAL_HAIR_VIEWS_DONE', flush=True)
