"""Render the original local PMX head under the current BJD studio; never save models."""
from pathlib import Path
import bpy, numpy as np, json, hashlib
from mathutils import Vector
R = Path(__file__).resolve().parent
CURRENT = R.parent/'march7-v14-pale-skin-original-hair.blend'
SOURCE = R.parent.parent/'source-reference/source-reference.blend'
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
current_hash, source_hash = sha(CURRENT), sha(SOURCE)
assert current_hash == '3fe03f533575cd2d50ff53c75d278d28c69f0390286718e7db1e57931acf6dd8'
assert source_hash == '446cc1013de352866632d84f9614d6dcd938a368e360fdbcbd6c197fe57cf844'
old = json.loads((R.parent/'render-provenance.json').read_text())
assert old['model_sha256'] == current_hash
chosen = ['front','quarter-left','side','face-front','face-quarter']
views = [v for v in old['views'] if Path(v['file']).stem in chosen]
assert len(views) == 5
for v in views:
    assert sha(R.parent/'previews'/v['file']) == v['sha256']
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
s = bpy.context.scene
head = bpy.data.objects['PRINT_01_Head_Shell']
eye = bpy.data.objects['PREVIEW_EYE_HEMISPHERE_NEGATIVE']
skin_bs = next(n for n in head.data.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
eye_bs = next(n for n in eye.data.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
shader_keys = ['Roughness','IOR','Specular IOR Level','Coat Weight','Coat Roughness','Subsurface Weight']
skin_values = {k:skin_bs.inputs[k].default_value for k in shader_keys}
eye_values = {k:eye_bs.inputs[k].default_value for k in shader_keys}
# Reuse the exact original hair already in the BJD scene for both sides.
for ob in s.objects:
    if ob.type == 'MESH' and not ob.name.startswith('LOOK_Original_March7_Hair'):
        ob.hide_render = ob.hide_viewport = True
        ob.hide_set(True)
collection = bpy.data.collections.new('TEMP_Original_PMX_Comparison_Only')
s.collection.children.link(collection)
names = ['SOURCE_00_MOUTH_INTERIOR','SOURCE_01_TEETH','SOURCE_02_BROWS_LASHES',
         'SOURCE_03_SCLERA','SOURCE_04_IRIS_AND_HIGHLIGHT','SOURCE_05_EYE_SHADOW','SOURCE_06_FACE']
with bpy.data.libraries.load(str(SOURCE), link=False) as (a,b):
    assert all(name in a.objects for name in names)
    b.objects = names
def geometry_hash(ob):
    ob.data.calc_loop_triangles()
    v = np.asarray([ob.matrix_world @ q.co for q in ob.data.vertices],np.float32)
    f = np.asarray([q.vertices[:] for q in ob.data.loop_triangles],np.int32)
    return hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest()
original_meshes = {}
material_notes = []
for ob in b.objects:
    collection.objects.link(ob)
    ob.hide_render = ob.hide_viewport = False
    ob.hide_set(False)
    original_meshes[ob.name] = geometry_hash(ob)
    mi = int(ob['source_material_index'])
    values = eye_values if mi in {3,4} else skin_values
    for mat in ob.data.materials:
        mat.node_tree.nodes['SOURCE_TexturePreviewWeight'].outputs[0].default_value = 0.
        # Keep the original texture × diffuse color and outer alpha/Transparent
        # mix. Only normalize surface response to the BJD studio materials.
        bs = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        for k,value in values.items():
            bs.inputs[k].default_value = value
        material_notes.append({'object':ob.name,'material':mat.name,'texture_emission_mix':0,
                               'surface_response':values,'original_texture_diffuse_alpha_preserved':True})
    assert original_meshes[ob.name] == geometry_hash(ob)
visible = [o.name for o in s.objects if o.type=='MESH' and not o.hide_render]
assert len(visible) == 9
assert not any(name.startswith(('PRINT_','PREVIEW_EYE_')) for name in visible)
cam = s.camera
rows = []
for v in views:
    name = Path(v['file']).stem
    cam.location = v['camera_mm']
    cam.rotation_euler = (Vector(v['target_mm'])-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale = v['ortho_width_mm']
    s.render.resolution_x = s.render.resolution_y = 1100
    s.render.resolution_percentage = 100
    file = R/('original-'+name+'.png')
    s.render.filepath = str(file)
    bpy.ops.render.render(write_still=True)
    rows.append({'view':name,'label':v['label'],'bjd_file':str((R.parent/'previews'/v['file']).resolve()),
                 'bjd_image_sha256':v['sha256'],'original_file':file.name,'original_image_sha256':sha(file),
                 'camera_mm':v['camera_mm'],'target_mm':v['target_mm'],'ortho_width_mm':v['ortho_width_mm']})
assert current_hash == sha(CURRENT) and source_hash == sha(SOURCE)
assert original_meshes == {name:geometry_hash(bpy.data.objects[name]) for name in original_meshes}
report = {'bjd_model_sha256':current_hash,'original_helper_sha256':source_hash,'model_files_unchanged':True,
          'original_pmx_mesh_geometry_unchanged':True,'original_geometry_fingerprints':original_meshes,
          'same_camera_lights_background_color_management_and_original_hair':True,
          'original_uv_textures_diffuse_and_alpha_preserved':True,'original_upper_eye_shadow_included':True,
          'original_expression_overlay_excluded':True,'temporary_visible_objects':visible,
          'original_surface_material_settings':material_notes,'views':rows,
          'comparison_note':'Original local PMX geometry/UV/textures re-rendered in Blender with matched studio surface response. Not an in-game screenshot or recreation of the game toon shader. Existing BJD renders reused only after model/image hash and camera verification. No retouching.'}
(R/'comparison-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FIVE_ORIGINAL_COMPARISON_VIEWS_DONE', flush=True)
