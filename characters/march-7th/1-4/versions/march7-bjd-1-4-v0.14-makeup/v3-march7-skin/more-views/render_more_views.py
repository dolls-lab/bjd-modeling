"""Read-only additional views of the current lighter-skin preview."""
from pathlib import Path
import json, hashlib
import bpy
from mathutils import Vector
R = Path(__file__).resolve().parent
MODEL = R.parent / 'march7-v14-local-makeup-v3-skin.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
model_hash = sha(MODEL)
assert model_hash == 'bd1d320897bbc25f3a002c5bc8458e7c0fea7747b8a7ad2b677680b97af39f4d'
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
s = bpy.context.scene
cam = s.camera
views = [
    ('face-front-close', '面部正面近景', (0,-220,28), (0,-18,26), 55, 1200),
    ('face-quarter-close', '面部斜侧近景', (-125,-200,60), (0,-18,27), 59, 1200),
    ('front-high', '前斜侧俯视', (-90,-180,145), (0,0,35), 88, 1100),
    ('front-low', '前斜侧仰视', (-80,-200,-28), (0,-3,32), 88, 1100),
    ('right-profile', '右侧面', (220,0,35), (0,0,35), 88, 1100),
    ('rear-quarter', '后斜侧', (-145,170,75), (0,0,35), 88, 1100),
    ('rear', '正后方', (0,220,40), (0,0,35), 88, 1100),
    ('top', '头顶俯视', (0,-15,240), (0,0,35), 88, 1100),
]
rows = []
for name, label, loc, target, scale, pixels in views:
    cam.location = loc
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = scale
    s.render.resolution_x = s.render.resolution_y = pixels
    s.render.resolution_percentage = 100
    s.render.filepath = str(R / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    rows.append({'file':name+'.png', 'label':label, 'camera_mm':loc, 'target_mm':target,
                 'ortho_width_mm':scale, 'resolution':[pixels,pixels],
                 'image_sha256':sha(R/(name+'.png'))})
assert sha(MODEL) == model_hash
(R / 'render-provenance.json').write_text(json.dumps({
    'model_file':str(MODEL), 'model_sha256':model_hash, 'saved_model_unchanged':True,
    'image_method':'Actual Blender renders. Only camera framing and render resolution changed in unsaved memory; no material, geometry, lighting or image edits.',
    'views':rows,
}, ensure_ascii=False, indent=2)+'\n')
print('EIGHT_EXTRA_SKIN_VIEWS_DONE', flush=True)
