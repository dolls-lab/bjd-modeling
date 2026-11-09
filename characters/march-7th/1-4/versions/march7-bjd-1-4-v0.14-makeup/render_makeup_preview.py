"""Render actual preview geometry in several views; never save input Blend."""
from pathlib import Path
import sys,json,hashlib
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent;D=R/'previews';D.mkdir(exist_ok=True)
p=R/'march7-v14-makeup-preview.blend';sha=hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(p));s=bpy.context.scene;cam=s.camera
skin=bpy.data.collections['01_V14_Painted_Head'];eyes=bpy.data.collections['02_Character_Eyes_Brows_Mouth_PREVIEW_ONLY'];hair=bpy.data.collections['03_Optional_Original_Hair_PREVIEW_ONLY'];ref=bpy.data.collections['90_Original_March7_Reference']
views=[('front',(0,-200,35),(0,0,35)),('quarter-left',(-130,-190,55),(0,0,35)),('quarter-right',(130,-190,55),(0,0,35)),('side',(-220,0,35),(0,0,35))]
rows=[];quick='--quick' in sys.argv
for mode in ['makeup','hair','original']:
    skin.hide_render=mode=='original';eyes.hide_render=mode=='original';hair.hide_render=mode!='hair';ref.hide_render=mode!='original'
    # hide_viewport is global and can remove geometry from depsgraph, so keep in sync.
    for c in [skin,eyes,hair,ref]:c.hide_viewport=c.hide_render
    choices=views[:1] if quick else (views if mode=='makeup' else views[:3] if mode=='hair' else views[:2])
    for name,loc,target in choices:
        scale=98 if mode=='makeup' else 120
        if mode!='makeup':target=(0,0,28);loc=(loc[0],loc[1],loc[2]-7)
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
        file=f'{mode}-{name}.png';s.render.filepath=str(D/file);bpy.ops.render.render(write_still=True)
        rows.append({'file':file,'mode':mode,'camera':loc,'target':target,'ortho_width_mm':scale})
assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
name='quick-render-provenance.json' if quick else 'render-provenance.json'
(R/name).write_text(json.dumps({'model_file':str(p),'model_sha256':sha,'input_model_modified':False,'image_method':'Actual Blender render, no image retouching.','views':rows},indent=2)+'\n')
print('MAKEUP_RENDER_DONE',flush=True)
