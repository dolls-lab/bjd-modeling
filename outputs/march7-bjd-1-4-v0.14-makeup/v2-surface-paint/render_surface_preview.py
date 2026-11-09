"""Render the saved preview without editing any saved geometry or retouching images."""
from pathlib import Path
import bpy, hashlib, json, sys
from mathutils import Vector
R = Path(__file__).resolve().parent
D = R / 'previews'
D.mkdir(exist_ok=True)
P = R / 'march7-v14-local-makeup-v2.blend'
digest = hashlib.sha256(P.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P))
s = bpy.context.scene
cam = s.camera
cap = bpy.data.objects['PRINT_02_Removable_Cap']
head = bpy.data.objects['PRINT_01_Head_Shell']
eyes = bpy.data.collections['02_Two_Hemisphere_Eyes_PREVIEW_ONLY']
enabled = head.data.materials[0].node_tree.nodes['LOCAL_MAKEUP_ON']
views = [
    ('makeup-front', (0, -200, 35), (0, 0, 35), 88, 'paint'),
    ('makeup-quarter-left', (-130, -190, 55), (0, 0, 35), 88, 'paint'),
    ('makeup-quarter-right', (130, -190, 55), (0, 0, 35), 88, 'paint'),
    ('makeup-side', (-220, 0, 35), (0, 0, 35), 88, 'paint'),
    ('makeup-closeup', (-40, -200, 38), (0, -20, 25), 53, 'paint'),
    ('bare-front', (0, -200, 35), (0, 0, 35), 88, 'bare'),
    ('bare-quarter-left', (-130, -190, 55), (0, 0, 35), 88, 'bare'),
    ('inside-back-open', (0, 200, 75), (0, -3, 31), 88, 'inside'),
    ('hemisphere-cups', (-65, 170, 80), (0, -13, 28), 54, 'eyes'),
]
quick = '--quick' in sys.argv
if quick:
    views = views[:2] + views[-2:]
    s.render.resolution_percentage = 70
    s.cycles.samples = 24
provenance = []
for name, loc, target, scale, mode in views:
    head.hide_render = mode == 'eyes'
    cap.hide_render = mode in {'inside', 'eyes'}
    eyes.hide_render = mode == 'bare'
    eyes.hide_viewport = eyes.hide_render
    enabled.outputs[0].default_value = 0 if mode == 'bare' else 1
    cam.location = loc
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = scale
    s.render.filepath = str(D / (('quick-' if quick else '') + name + '.png'))
    bpy.ops.render.render(write_still=True)
    provenance.append({'file':Path(s.render.filepath).name, 'camera_mm':loc, 'target_mm':target,
                       'ortho_width_mm':scale, 'mode':mode})
assert hashlib.sha256(P.read_bytes()).hexdigest() == digest
(R / ('quick-render-provenance.json' if quick else 'render-provenance.json')).write_text(json.dumps({
    'model_file':str(P), 'model_sha256':digest, 'input_model_modified':False,
    'image_method':'Actual Blender renders, no raster retouching.',
    'views':provenance,
}, indent=2) + '\n')
print('SURFACE_PREVIEW_RENDERS_DONE', flush=True)
