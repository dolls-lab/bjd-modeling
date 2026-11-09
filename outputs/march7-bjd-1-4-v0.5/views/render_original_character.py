"""Render original local March 7th PMX geometry and textures, without reshaping.

Run with Blender's Python. This creates only PNGs and a provenance JSON in this
directory; it never saves a .blend file or modifies the BJD assets.
The material implementation is a Blender diffuse reconstruction, not the MMD
toon/sphere shader or a screenshot of the game.
Pass -- --unlit for texture-only Emission previews with retained transparency.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy
import numpy as np
from mathutils import Vector

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
BASE = ROOT.parent / 'march7-bjd-1-4-v0.3'
sys.path.insert(0, str(BASE))
from parse_pmx import load_pmx

parser = argparse.ArgumentParser()
parser.add_argument('--unlit', action='store_true', help='Render original textures through emission, keeping alpha and geometry.')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

SCALE = 27.47544416498121
CHIN = 18.16621208190918
SOURCE = Path(json.loads((BASE / 'parameters.json').read_text())['source_pmx'])
src = load_pmx(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'march7-bjd-head-v0.5-draft.blend'))
scene = bpy.context.scene
for ob in scene.objects:
    if ob.type == 'MESH':
        ob.hide_render = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
scene.cycles.samples = 48
scene.cycles.transparent_max_bounces = 16
if args.unlit:
    # Standard applies the sRGB display transfer without a photographic tone
    # curve; this view is explicitly an original-texture preview, not a game
    # shader reproduction or a geometry lighting comparison.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

vertices = src['vertices']
world = np.column_stack((vertices[:, 0], vertices[:, 2], vertices[:, 1] - CHIN)) * SCALE
normals = src['normals'][:, [0, 2, 1]]
images = {}
material_records = []
geometry_max_roundoff = 0.0

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for spec in src['materials']:
    faces = src['faces'][spec['start']:spec['end']]
    ids = np.unique(faces)
    mapping = np.full(len(vertices), -1, dtype=int)
    mapping[ids] = np.arange(len(ids))
    # The axis exchange is a reflection, so reverse winding to retain the
    # original outward surface orientation. Vertex positions are untouched.
    local_faces = mapping[faces][:, ::-1]
    mesh = bpy.data.meshes.new('PMX_original_' + spec['name'])
    mesh.from_pydata(world[ids].tolist(), [], local_faces.tolist())
    mesh.update()
    uv = mesh.uv_layers.new(name='Original_PMX_UV')
    for loop in mesh.loops:
        su, sv = src['uvs'][ids[loop.vertex_index]]
        uv.data[loop.index].uv = (float(su), 1.0 - float(sv))
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals[ids].tolist())
    ob = bpy.data.objects.new('PMX_original_' + spec['name'], mesh)
    scene.collection.objects.link(ob)
    geometry_max_roundoff = max(geometry_max_roundoff, float(np.max(np.abs(
        np.asarray([v.co[:] for v in mesh.vertices]) - world[ids]))))

    mat = bpy.data.materials.new('Original_Texture_' + spec['name'])
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    if args.unlit:
        bsdf = nodes.new('ShaderNodeEmission')
        bsdf.inputs['Strength'].default_value = 1.0
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        alpha_mix = nodes.new('ShaderNodeMixShader')
        links.new(transparent.outputs[0], alpha_mix.inputs[1])
        links.new(bsdf.outputs[0], alpha_mix.inputs[2])
        links.new(alpha_mix.outputs[0], output.inputs['Surface'])
        color_socket = bsdf.inputs['Color']
        alpha_socket = alpha_mix.inputs[0]
    else:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        color_socket = bsdf.inputs['Base Color']
        alpha_socket = bsdf.inputs['Alpha']
    color_socket.default_value = spec['diffuse']
    alpha_socket.default_value = spec['diffuse'][3]
    texture_path = None
    ti = spec['texture_index']
    if 0 <= ti < len(src['textures']):
        texture_path = SOURCE.parent / src['textures'][ti].replace('\\', '/')
        if not texture_path.is_file():
            raise FileNotFoundError(texture_path)
        if texture_path not in images:
            images[texture_path] = bpy.data.images.load(str(texture_path), check_existing=True)
            images[texture_path].colorspace_settings.name = 'sRGB'
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = images[texture_path]
        tex.interpolation = 'Linear'
        color = nodes.new('ShaderNodeMixRGB')
        color.blend_type = 'MULTIPLY'
        color.inputs[0].default_value = 1.0
        color.inputs[2].default_value = spec['diffuse']
        links.new(tex.outputs['Color'], color.inputs[1])
        links.new(color.outputs[0], color_socket)
        alpha = nodes.new('ShaderNodeMath')
        alpha.operation = 'MULTIPLY'
        alpha.inputs[1].default_value = spec['diffuse'][3]
        links.new(tex.outputs['Alpha'], alpha.inputs[0])
        links.new(alpha.outputs[0], alpha_socket)
    mesh.materials.append(mat)
    material_records.append({
        'original_material': spec['name'], 'triangles': len(faces),
        'diffuse_rgba': spec['diffuse'],
        'texture': str(texture_path) if texture_path else None,
        'geometry_modifiers': [],
    })

views = [
    ('front', (0, -180, 37), (0, 0, 37), 105),
    ('quarter', (115, -180, 100), (0, 0, 37), 105),
    ('side', (180, 0, 40), (0, 0, 37), 105),
    ('overview', (0, -180, 26), (0, 0, 26), 130),
]
if args.unlit:
    views = views[:3]
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.clip_start = 0.1
camera.data.clip_end = 3000
view_records = []
for name, location, target, scale in views:
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    prefix = 'character-texture' if args.unlit else 'character-original'
    path = OUT / f'{prefix}-{name}.png'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    view_records.append({'name': name, 'path': str(path), 'camera_world': location,
                         'target_world': target, 'ortho_scale_mm': scale})

notes = {
    'description_zh': ('原人物·贴图预览：本地原 PMX 几何与原贴图的无光照 Blender 渲染；不是游戏截图。' if args.unlit else '本地原 PMX 网格、原 UV 与原贴图的 Blender 渲染；不是游戏截图。'),
    'source_pmx': str(SOURCE), 'source_sha256': digest(SOURCE),
    'world_transform': '(srcX, srcZ, srcY - 18.16621208190918) * 27.47544416498121',
    'geometry': 'All PMX rest-pose vertices and triangles are imported. No morph, subdivision, smoothing modifier, remesh, reconstruction, or vertex sculpt is applied. Original per-vertex normals are transformed and retained.',
    'geometry_float32_max_coordinate_roundoff_mm': geometry_max_roundoff,
    'texture_method': ('Original sRGB texture multiplied by original PMX diffuse RGB into Emission strength 1; original texture alpha multiplied by PMX diffuse alpha mixes with Transparent BSDF. No illumination, shadows or geometry changes; Standard view transform, exposure 0, gamma 1.' if args.unlit else 'Original sRGB texture multiplied by original PMX diffuse RGBA; alpha retained; Blender diffuse Principled shader under v5 studio lighting.'),
    'shader_limitations': 'Original MMD toon ramps, sphere maps, edge outlines, material draw flags and runtime/game shading are not reproduced. Appearance is a Blender reconstruction, not an official game render.',
    'framing': 'front/quarter/side use the same 105 mm orthographic framing as the BJD comparison. Lowest hair tips may be cropped.' + ('' if args.unlit else ' Overview uses 130 mm to show the entire hair silhouette.'),
    'materials': material_records,
    'textures': [{'path': str(p), 'sha256': digest(p)} for p in images],
    'views': view_records,
    'blender_version': bpy.app.version_string,
}
notes_name = 'character-texture-notes.json' if args.unlit else 'character-render-notes.json'
(OUT / notes_name).write_text(json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
print('ORIGINAL_CHARACTER_RENDER_DONE', flush=True)
