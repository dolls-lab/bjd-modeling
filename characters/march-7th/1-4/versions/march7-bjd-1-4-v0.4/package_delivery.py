"""Create a labeled contact sheet and local delivery archive after validation."""
from pathlib import Path
import json, zipfile, hashlib
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
report=json.loads((root/'validation.json').read_text())
assert report['pass'], 'Do not package an unverified mesh'
for part in report['parts'].values():
    assert hashlib.sha256((root/part['file']).read_bytes()).hexdigest()==part['sha256'], 'Validation is stale'
eyes=json.loads((root/'eye-insertion-check.json').read_text())
assert eyes['pass'], 'No verified eye insertion path'
assert hashlib.sha256((root/eyes['head_shell_file']).read_bytes()).hexdigest()==eyes['head_shell_sha256'], 'Eye check is stale'
front=Image.open(root/'preview-quarter.png').convert('RGB')
opened=Image.open(root/'preview-exploded.png').convert('RGB')
bg=front.getpixel((0,0))
board=Image.new('RGB',(1600,1000),bg)
draw=ImageDraw.Draw(board)
font_path='/System/Library/Fonts/STHeiti Medium.ttc'
title=ImageFont.truetype(font_path,38)
body=ImageFont.truetype(font_path,23)
small=ImageFont.truetype(font_path,20)
draw.text((38,25),'三月七 · 四分 BJD 额颞部圆顺',font=title,fill='#f8f1eb')
draw.text((1240,40),'v0.4  /  打样版',font=body,fill='#dbd7d6')
board.paste(front.resize((760,760),Image.Resampling.LANCZOS),(20,105))
board.paste(opened.resize((760,760),Image.Resampling.LANCZOS),(820,105))
draw.text((210,856),'面部与脑壳过渡',font=body,fill='#f8f1eb')
draw.text((1110,856),'向后开盖 / 内部结构',font=body,fill='#f8f1eb')
g=report['girth_check']['measured_mm']
draw.line((38,906,1560,906),fill='#8b929a',width=1)
draw.text((38,924),f'头围 {g:.2f} mm  ·  16 mm 眼珠  ·  磁吸后脑盖  ·  囡囡体颈座试版',font=body,fill='#f8f1eb')
draw.text((38,962),'基于本地三月七 PMX 脸形重建；数字检查通过，尚待实物打印与试装。',font=small,fill='#d5d8dc')
board.save(root/'preview-overview.png')
# Same-camera, same-material, same-light comparison of actual mesh renders.
before=Image.open(root/'preview-before-v0.3-quarter.png').convert('RGB')
after=Image.open(root/'preview-quarter.png').convert('RGB')
comparison=Image.new('RGB',(1600,1000),bg);cd=ImageDraw.Draw(comparison)
cd.text((38,25),'三月七 · 面部与脑壳过渡对比',font=title,fill='#f8f1eb')
comparison.paste(before.resize((760,760),Image.Resampling.LANCZOS),(20,90))
comparison.paste(after.resize((760,760),Image.Resampling.LANCZOS),(820,90))
cd.text((260,855),'修改前 · v0.3',font=body,fill='#f8f1eb')
cd.text((1060,855),'修改后 · v0.4',font=body,fill='#f8f1eb')
cd.line((38,906,1560,906),fill='#8b929a',width=1)
cd.text((38,925),'前额与太阳穴重塑为连续圆弧，保留五官与后脑开盖。',font=body,fill='#f8f1eb')
cd.text((38,966),'相同相机、灯光与材质的真实模型渲染。仍需实物打印与试装。',font=small,fill='#d5d8dc')
comparison.save(root/'preview-comparison.png')
# Side silhouettes show the forehead-to-cranium rounding most directly.
side_comparison=Image.new('RGB',(1600,1000),bg);sd=ImageDraw.Draw(side_comparison)
sd.text((38,25),'额头到脑壳 · 圆顺过渡',font=title,fill='#f8f1eb')
old_side=Image.open(root/'preview-before-v0.3-side.png').convert('RGB')
new_side=Image.open(root/'preview-side.png').convert('RGB')
side_comparison.paste(old_side.resize((760,760),Image.Resampling.LANCZOS),(20,90))
side_comparison.paste(new_side.resize((760,760),Image.Resampling.LANCZOS),(820,90))
sd.text((260,855),'修改前 · v0.3',font=body,fill='#f8f1eb')
sd.text((1060,855),'修改后 · v0.4',font=body,fill='#f8f1eb')
sd.line((38,906,1560,906),fill='#8b929a',width=1)
sd.text((38,925),'重塑额头与太阳穴连接区；五官、颈座与后脑盖保留。',font=body,fill='#f8f1eb')
sd.text((38,966),'同相机、同材质、同灯光的模型渲染。尚待实物打印与试装。',font=small,fill='#d5d8dc')
side_comparison.save(root/'preview-side-comparison.png')



include=['README.md','parameters.json','build_head.py','parse_pmx.py','validate_mesh.py',
         'package_delivery.py','build-report.json','validation.json','source-usage-rules.txt',
         'source-face-reference.png','design-reference-notes.md','baseline-v0.3.blend','baseline-build-report.json','baseline-cap.stl','march7-bjd-head-v0.4-draft.blend',
         'march7-head-shell-v0.4-draft.stl','march7-head-cap-v0.4-draft.stl']
include += [p.name for p in sorted(root.glob('preview-*.png'))]
include += ['eye-insertion-check.json','check_eye_insertion.py','face-opening-comparison.json','compare_eye_apertures.py','eye-aperture-comparison.png']
include += ['cranium-profile-review.json','cranium-profile-comparison.png','review_cranium_profiles.py']
checks={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in include}
(root/'checksums.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
archive=root/'march7-bjd-head-v0.4-draft.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in include+['checksums.json']:z.write(root/name,'march7-bjd-head-v0.4/'+name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive,archive.stat().st_size)
