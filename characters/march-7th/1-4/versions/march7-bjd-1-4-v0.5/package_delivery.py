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
sculpt=json.loads((root/'source-faithfulness-review.json').read_text())
assert sculpt['all_listed_protected_checks_pass'] and sculpt['input_files_unchanged_during_audit']
for key in ('current_blend','current_stl'):
    record=sculpt['files'][key]
    assert hashlib.sha256((root/Path(record['path']).name).read_bytes()).hexdigest()==record['sha256'], 'Sculpt audit is stale'
profiles=json.loads((root/'transition-profile-review.json').read_text())
record=profiles['sources']['v0.5']
assert hashlib.sha256((root/Path(record['file']).name).read_bytes()).hexdigest()==record['sha256'], 'Profile review is stale'
front=Image.open(root/'preview-quarter.png').convert('RGB')
opened=Image.open(root/'preview-exploded.png').convert('RGB')
bg=front.getpixel((0,0))
board=Image.new('RGB',(1600,1000),bg)
draw=ImageDraw.Draw(board)
font_path='/System/Library/Fonts/STHeiti Medium.ttc'
title=ImageFont.truetype(font_path,38)
body=ImageFont.truetype(font_path,23)
small=ImageFont.truetype(font_path,20)
draw.text((38,25),'三月七 · 原角色面雕与脑壳衔接',font=title,fill='#f8f1eb')
draw.text((1240,40),'v0.5  /  打样版',font=body,fill='#dbd7d6')
board.paste(front.resize((760,760),Image.Resampling.LANCZOS),(20,105))
board.paste(opened.resize((760,760),Image.Resampling.LANCZOS),(820,105))
draw.text((210,856),'保留角色面雕 · 修整接面',font=body,fill='#f8f1eb')
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
cd.text((38,25),'三月七 · v3 基础上修整衔接',font=title,fill='#f8f1eb')
comparison.paste(before.resize((760,760),Image.Resampling.LANCZOS),(20,90))
comparison.paste(after.resize((760,760),Image.Resampling.LANCZOS),(820,90))
cd.text((260,855),'修改前 · v0.3',font=body,fill='#f8f1eb')
cd.text((1060,855),'修改后 · v0.5',font=body,fill='#f8f1eb')
cd.line((38,906,1560,906),fill='#8b929a',width=1)
cd.text((38,925),'面雕以三月七原模型为依据，修整额头与耳周的脑壳衔接。',font=body,fill='#f8f1eb')
cd.text((38,966),'相同相机、灯光与材质的真实模型渲染。仍需实物打印与试装。',font=small,fill='#d5d8dc')
comparison.save(root/'preview-comparison.png')

for detail,label in [('ear-detail','耳侧与太阳穴'),('forehead-detail','额头到脑壳')]:
    panel=Image.new('RGB',(1600,1000),bg);pd=ImageDraw.Draw(panel)
    pd.text((38,25),'三月七 · '+label+'衔接对照',font=title,fill='#f8f1eb')
    for x,filename in [(20,'preview-before-v0.3-'+detail+'.png'),(820,'preview-'+detail+'.png')]:
        panel.paste(Image.open(root/filename).convert('RGB').resize((760,760),Image.Resampling.LANCZOS),(x,90))
    pd.text((260,855),'修改前 · v0.3',font=body,fill='#f8f1eb')
    pd.text((1060,855),'修改后 · v0.5',font=body,fill='#f8f1eb')
    pd.text((38,927),'相同镜头、灯光与材质；真实模型渲染，未对图片修形。',font=body,fill='#f8f1eb')
    panel.save(root/('preview-'+detail+'-comparison.png'))


include=['README.md','parameters.json','build_head.py','parse_pmx.py','validate_mesh.py',
         'package_delivery.py','build-report.json','validation.json','source-usage-rules.txt',
         'source-face-reference.png','design-reference-notes.md','baseline-v0.3.blend','baseline-build-report.json','baseline-cap.stl','source-protection-masks.npz','baseline-source-audit.json','march7-bjd-head-v0.5-draft.blend',
         'march7-head-shell-v0.5-draft.stl','march7-head-cap-v0.5-draft.stl']
include += [p.name for p in sorted(root.glob('preview-*.png'))]
include += ['eye-insertion-check.json','check_eye_insertion.py','face-opening-comparison.json','compare_eye_apertures.py','eye-aperture-comparison.png']
include += ['solve_junction.py','fairing-problem.npz','fairing-solution.npz','fairing-solver-report.json',
            'make_head_protection.py','head-protection-weights.npz','head-protection-weights.json',
            'audit_source_faithfulness.py','source-faithfulness-review.json',
            'review_transition_profiles.py','transition-profile-review.json','transition-profile-comparison.png','ear-back-profile-comparison.png',
            'render_detail_comparison.py']
checks={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in include}
(root/'checksums.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
archive=root/'march7-bjd-head-v0.5-draft.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in include+['checksums.json']:z.write(root/name,'march7-bjd-head-v0.5/'+name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive,archive.stat().st_size)
