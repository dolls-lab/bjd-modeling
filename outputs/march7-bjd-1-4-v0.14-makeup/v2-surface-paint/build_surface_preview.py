"""Paint only local pigment on unchanged v14 and add independent half-ball eyes."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import bpy
from mathutils import Vector

R = Path(__file__).resolve().parent
BASE = R.parent.parent / 'march7-bjd-1-4-v0.14'
OUT = R / 'march7-v14-local-makeup-v2.blend'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry(ob):
    ob.data.calc_loop_triangles()
    v = np.asarray([ob.matrix_world @ p.co for p in ob.data.vertices], np.float32)
    t = np.asarray([p.vertices[:] for p in ob.data.loop_triangles], np.int32)
    return v, t, hashlib.sha256(v.tobytes() + t.tobytes()).hexdigest()
def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

basefile = BASE / 'march7-bjd-head-v0.14-draft.blend'
basehash = sha(basefile)
assert basehash == 'cdb0839449d64a6867cae512fef653a1221315ab97c70b1a8e554a4aa232f96a'
bpy.ops.wm.open_mainfile(filepath=str(basefile))
scene = bpy.context.scene
head = bpy.data.objects['PRINT_01_Head_Shell']
cap = bpy.data.objects['PRINT_02_Removable_Cap']
before = {o.name: geometry(o)[2] for o in (head, cap)}
for ob in list(bpy.data.objects):
    if ob not in {head, cap}:
        bpy.data.objects.remove(ob, do_unlink=True)
skincol = collection('01_V14_Head_Local_Paint')
eyecol = collection('02_Two_Hemisphere_Eyes_PREVIEW_ONLY')
studio = collection('03_Studio')
for ob in (head, cap):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    skincol.objects.link(ob)
    ob.hide_render = ob.hide_viewport = False
    ob.hide_set(False)
    ob['v14_geometry_unchanged'] = True
for c in list(bpy.data.collections):
    if c not in {skincol, eyecol, studio}:
        bpy.data.collections.remove(c)

# Paint UV is a frontal projection. Existing exterior-face gating prevents the
# pigment from also appearing on internal walls or at the back of the head.
config = json.loads((R / 'paint-assets/local-paint-mapping.json').read_text())
xmin, xmax = config['world_x_range_mm']
zmin, zmax = config['world_z_range_mm']
v, t, _ = geometry(head)
with np.load(R.parent / 'uv-transfer/face-uv-transfer.npz') as u:
    assert np.array_equal(v, u['head_vertices'].astype(np.float32))
    assert np.array_equal(t, u['head_triangles'])
    vertexweight = u['head_vertex_makeup_weight'].astype(np.float32)
loopvertex = np.empty(len(head.data.loops), np.int32)
head.data.loops.foreach_get('vertex_index', loopvertex)
loopv = v[loopvertex]
loopuv = np.column_stack(((loopv[:, 0] - xmin) / (xmax - xmin),
                          (loopv[:, 2] - zmin) / (zmax - zmin))).astype(np.float32)
uv = head.data.uv_layers.new(name='Local_Eye_Lip_Paint')
uv.data.foreach_set('uv', loopuv.ravel())
weight = head.data.attributes.new(name='Exterior_Paint_Only', type='FLOAT', domain='CORNER')
weight.data.foreach_set('value', vertexweight[loopvertex])
head.data.uv_layers.active_index = head.data.uv_layers.find('Local_Eye_Lip_Paint')
head.data.uv_layers['Local_Eye_Lip_Paint'].active_render = True
base_mat = head.data.materials[0]
paint_mat = base_mat.copy()
paint_mat.name = 'V14_Resin_With_Local_Painted_Brows_Eyeliner_Lips'
head.data.materials.clear()
head.data.materials.append(paint_mat)
n = paint_mat.node_tree.nodes
l = paint_mat.node_tree.links
bs = next(q for q in n if q.type == 'BSDF_PRINCIPLED')
basecolor = tuple(bs.inputs['Base Color'].default_value)
tex = n.new('ShaderNodeTexImage')
tex.name = 'LOCAL_PIGMENT_RGBA_ONLY'
tex.label = 'Transparent elsewhere; no full-face skin image'
tex.image = bpy.data.images.load(str(R / 'paint-assets/local-paint.png'), check_existing=True)
tex.image.colorspace_settings.name = 'sRGB'
tex.image.pack()
tex.extension = 'CLIP'
un = n.new('ShaderNodeUVMap')
# Creating another mesh attribute can invalidate a cached UV-layer RNA handle.
un.uv_map = 'Local_Eye_Lip_Paint'
l.new(un.outputs['UV'], tex.inputs['Vector'])
attr = n.new('ShaderNodeAttribute')
attr.attribute_name = weight.name
mul = n.new('ShaderNodeMath')
mul.operation = 'MULTIPLY'
l.new(attr.outputs['Fac'], mul.inputs[0])
l.new(tex.outputs['Alpha'], mul.inputs[1])
enabled = n.new('ShaderNodeValue')
enabled.name = 'LOCAL_MAKEUP_ON'
enabled.label = '1 = local makeup; 0 = original bare resin'
enabled.outputs[0].default_value = 1
on = n.new('ShaderNodeMath')
on.operation = 'MULTIPLY'
l.new(mul.outputs[0], on.inputs[0])
l.new(enabled.outputs[0], on.inputs[1])
mix = n.new('ShaderNodeMixRGB')
mix.inputs[1].default_value = basecolor
l.new(on.outputs[0], mix.inputs[0])
l.new(tex.outputs['Color'], mix.inputs[2])
l.new(mix.outputs[0], bs.inputs['Base Color'])
head['makeup_method'] = 'Local RGBA pigment on this exact surface; no overlay mesh, displacement, or whole-face skin texture.'

eye_assets = R / 'eye-assets'
if '--candidate-eyes' in sys.argv:
    eye_assets = eye_assets / 'candidate-fit'
for arg in sys.argv:
    if arg.startswith('--eye-assets='):
        eye_assets = R / arg.split('=', 1)[1]
sys.path.insert(0, str(eye_assets))
from build_hemisphere_eyes import build_eyes
eye_objects, eye_report = build_eyes(eyecol)
assert len(eye_objects) == 2

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new('Local makeup neutral studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.17, .20, .25, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
scene.view_settings.view_transform = 'AgX'
for name, loc, power, size in [
    ('Key', (-90, -100, 150), 220000, 65),
    ('Fill', (100, -40, 75), 120000, 65),
    ('Front Softbox', (0, -170, 44), 100000, 85),
    ('Rim', (10, 90, 130), 200000, 50),
]:
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = power
    ld.shape = 'DISK'
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    studio.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 35)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
cd = bpy.data.cameras.new('Review Camera')
cam = bpy.data.objects.new('Review Camera', cd)
studio.objects.link(cam)
scene.camera = cam
cd.type = 'ORTHO'
cd.clip_start = .1
cd.clip_end = 3000
cd.ortho_scale = 88
cam.location = (0, -200, 35)
cam.rotation_euler = (Vector((0, 0, 35)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene['preview_note'] = 'v14 geometry and bare resin shader preserved. Only locally painted eye/brow/lip pigment and two separate hemisphere eyes. This is an appearance preview.'
scene['switch_makeup_off'] = 'Set LOCAL_MAKEUP_ON to 0 on the head material.'
scene['see_inside'] = 'Hide PRINT_02_Removable_Cap and rotate to rear; hemisphere eye cups are separate objects.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.shading.type = 'MATERIAL'
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True)
bpy.context.view_layer.objects.active = head
assert before == {o.name: geometry(o)[2] for o in (head, cap)}
assert len([o for o in scene.objects if o.type == 'MESH']) == 4
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT))
after = {name: geometry(bpy.data.objects[name])[2] for name in before}
assert before == after and sha(basefile) == basehash
report = {
    'base_blend_sha256': basehash,
    'preview_blend_sha256': sha(OUT),
    'print_geometry_before': before,
    'print_geometry_after_saved_reload': after,
    'print_geometry_exactly_unchanged': before == after,
    'original_blend_unchanged': sha(basefile) == basehash,
    'material_base_linear_rgba': basecolor,
    'base_principled_settings_unchanged': True,
    'only_base_color_mixed_with_local_pigment': True,
    'paint_uv_map': 'Local_Eye_Lip_Paint',
    'visible_mesh_objects': [o.name for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render],
    'no_face_or_makeup_overlay_meshes': True,
    'paint_mapping': config,
    'eyes': eye_report,
    'packed_images': [im.name for im in bpy.data.images if im.packed_file],
}
(R / 'preview-build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('LOCAL_MAKEUP_PREVIEW_SAVED ' + report['preview_blend_sha256'], flush=True)
