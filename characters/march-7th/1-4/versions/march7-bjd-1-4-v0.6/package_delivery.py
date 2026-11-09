"""Verify report hashes, compose actual-mesh comparison sheets, and package v6."""
from pathlib import Path
import json,hashlib,zipfile
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
def read(name):return json.loads((R/name).read_text())
def sha(name):return hashlib.sha256((R/name).read_bytes()).hexdigest()
v=read('validation.json');assert v['pass']
for part in v['parts'].values():assert sha(part['file'])==part['sha256']
a=read('source-preservation-review.json');assert a['all_checks_pass'] and a['input_files_unchanged_during_audit']
for key in ['current_blend','current_head_stl','current_cap_stl']:
    row=a['files'][key];assert sha(Path(row['path']).name)==row['sha256']
eyes=read('eye-insertion-check.json');assert eyes['pass'] and sha(eyes['head_shell_file'])==eyes['head_shell_sha256']
side=read('side-shell-review.json')['sources']['v0.6'];assert sha(Path(side['file']).name)==side['sha256']
F='/System/Library/Fonts/STHeiti Medium.ttc'
def font(n):return ImageFont.truetype(F,n)
bg=(78,85,97);fg='#f5f1eb';dim='#d1d8e0'
def center(draw,text,cx,y,n):
    f=font(n);box=draw.textbbox((0,0),text,font=f);draw.text((cx-(box[2]-box[0])/2,y),text,font=f,fill=fg)
for view,label in [('front','正面'),('quarter','斜前方'),('side','侧面'),('top','俯视'),('ear-detail','耳部近景')]:
    b=Image.new('RGB',(1800,1120),bg);d=ImageDraw.Draw(b)
    d.text((35,24),'三月七 · 耳后侧脑体量修整 / '+label,font=font(40),fill=fg)
    for i,name in enumerate(['preview-before-v0.5-'+view+'.png','preview-'+view+'.png']):
        im=Image.open(R/name).convert('RGB').resize((860,860),Image.Resampling.LANCZOS);b.paste(im,(20+i*900,105))
    center(d,'修改前 · v5',450,976,30);center(d,'修改后 · v6',1350,976,30)
    d.text((35,1045),'相同镜头、材质与灯光；修整新增侧脑，保留原面雕与耳廓。',font=font(26),fill=fg)
    d.text((35,1085),'真实模型渲染，未对图片修形。',font=font(22),fill=dim)
    b.save(R/('preview-'+view+'-comparison.png'))

overview=Image.new('RGB',(2100,1620),bg);d=ImageDraw.Draw(overview)
d.text((35,22),'v5 → v6 · 耳后侧脑收回',font=font(43),fill=fg)
for j,(view,label) in enumerate([('front','正面'),('side','侧面'),('top','俯视')]):
    center(d,label,j*700+350,85,30)
    for i,prefix in enumerate(['preview-before-v0.5-','preview-']):
        im=Image.open(R/(prefix+view+'.png')).convert('RGB').resize((680,680),Image.Resampling.LANCZOS)
        overview.paste(im,(j*700+10,130+i*720))
        center(d,'v5 · 修改前' if i==0 else 'v6 · 修改后',j*700+350,810+i*720,25)
d.text((35,1580),'同一比例的真实模型对照；原脸和耳廓外表面保持，内腔随侧脑调整。',font=font(25),fill=dim)
overview.save(R/'preview-comparison-overview.png')

include=sorted(p for p in R.iterdir() if p.is_file() and p.suffix in {'.blend','.stl','.npz','.json','.py','.md','.txt','.png'} and p.name!='checksums.json')
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in include}
(R/'checksums.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
archive=R/'march7-bjd-head-v0.6-draft.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in include+[R/'checksums.json']:z.write(p,'march7-bjd-head-v0.6/'+p.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read('march7-bjd-head-v0.6/'+n)).hexdigest()==h for n,h in checks.items())
print(json.dumps({'archive':str(archive),'files':len(include),'bytes':archive.stat().st_size}),flush=True)
