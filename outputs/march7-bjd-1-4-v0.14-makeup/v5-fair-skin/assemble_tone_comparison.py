"""Arrange old/new/source renders without retouching any image."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont
R = Path(__file__).resolve().parent
OLD = R.parent/'v4-hair-preview'
REF = OLD/'original-comparison'
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
font = lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',n)
new_prov = json.loads((R/'render-provenance.json').read_text())
old_prov = json.loads((OLD/'render-provenance.json').read_text())
ref_prov = json.loads((REF/'comparison-provenance.json').read_text())
assert new_prov['model_sha256']==sha(R/'march7-v14-fair-skin-original-hair.blend')
assert old_prov['model_sha256']==ref_prov['bjd_model_sha256']==sha(OLD/'march7-v14-pale-skin-original-hair.blend')
for prov,folder in [(new_prov,R/'previews'),(old_prov,OLD/'previews')]:
    for v in prov['views']:
        assert sha(folder/v['file'])==v['sha256']
for v in ref_prov['views']:
    assert sha(REF/v['original_file'])==v['original_image_sha256']
records = []
def board(filename,title,subtitle,rows,columns,size):
    pad,gap,top = 24,18,122
    im = Image.new('RGB',(pad*2+columns*size+(columns-1)*gap,top+len(rows)*(size+58)+44),'#29333e')
    draw = ImageDraw.Draw(im)
    draw.text((pad,20),title,font=font(32),fill='white')
    draw.text((pad,74),subtitle,font=font(21),fill='#d9dfe7')
    inputs = []
    for row,cells in enumerate(rows):
        for col,(path,label) in enumerate(cells):
            x=pad+col*(size+gap);y=top+row*(size+58)
            im.paste(Image.open(path).convert('RGB').resize((size,size),Image.Resampling.LANCZOS),(x,y))
            draw.text((x+8,y+size+12),label,font=font(23),fill='white')
            inputs.append({'file':str(path.resolve()),'sha256':sha(path)})
    draw.text((pad,im.height-33),'同角度、同灯光 · 仅调整头壳底色 · 原角色为本地 PMX 的 Blender 重渲染',font=font(18),fill='#c4cdd9')
    im.save(R/filename)
    records.append({'file':filename,'sha256':sha(R/filename),'inputs':inputs,'operations':'Resize and arrange only; no recoloring or retouching.'})
rows=[]
for key,label in [('face-front','正面'),('face-quarter','斜侧')]:
    rows.append([(OLD/'previews'/(key+'.png'),'上一版 · '+label),
                 (R/'previews'/(key+'.png'),'本次调白 · '+label),
                 (REF/('original-'+key+'.png'),'原角色模型 · '+label)])
board('skin-tone-comparison.png','三月七 · 肤色进一步调白','左：上一版　　中：本次调白　　右：原角色模型',rows,3,550)
rows=[]
for key,label in [('front','正面'),('quarter-left','左前斜侧')]:
    rows.append([(R/'previews'/(key+'.png'),'本次调白 BJD · '+label),
                 (REF/('original-'+key+'.png'),'原角色模型 · '+label)])
board('new-original-overall.png','调白后 · 与原模型对照','左：本次 BJD　　右：原三月七 PMX 模型',rows,2,620)
(R/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('FAIR_SKIN_COMPARISON_DONE')
