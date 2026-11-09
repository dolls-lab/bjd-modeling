from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont
R = Path(__file__).resolve().parent
OLD = R.parent / 'v2-surface-paint'
font = lambda n: ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', n)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_prov = json.loads((OLD / 'render-provenance.json').read_text())
new_prov = json.loads((R / 'render-provenance.json').read_text())
assert old_prov['model_sha256'] == sha(OLD / 'march7-v14-local-makeup-v2.blend')
assert new_prov['model_sha256'] == sha(R / 'march7-v14-local-makeup-v3-skin.blend')
records = []
def board(filename, title, subtitle, cells):
    size, pad, gap, top, rowh = 580, 28, 20, 122, 636
    im = Image.new('RGB', (pad*2 + 2*size + gap, top + 2*rowh + 38), '#29333e')
    d = ImageDraw.Draw(im)
    d.text((pad, 20), title, font=font(31), fill='white')
    d.text((pad, 74), subtitle, font=font(19), fill='#d9dfe7')
    for i, (path, label) in enumerate(cells):
        x = pad + (i%2)*(size+gap)
        y = top + (i//2)*rowh
        im.paste(Image.open(path).convert('RGB').resize((size, size), Image.Resampling.LANCZOS), (x,y))
        d.text((x+9, y+size+12), label, font=font(22), fill='white')
    d.text((pad, im.height-32), '实际三维渲染 · 仅调整统一肤色 · 头型、眼杯、局部妆面均保持原样', font=font(16), fill='#c4cdd9')
    im.save(R/filename)
    records.append({'file':filename,'sha256':sha(R/filename),'inputs':[{'path':str(p.resolve()),'sha256':sha(p)} for p,_ in cells],
                    'operations':'Resize and arrange only; no recoloring or retouching.'})
board('skin-before-after.png', '三月七肤色 · 调整前后', '左：上一版　右：原角色浅肤色；相同相机、灯光', [
    (OLD/'previews/makeup-front.png', '原肤色 · 正面'),
    (R/'previews/skin-front.png', '三月七浅肤色 · 正面'),
    (OLD/'previews/makeup-quarter-left.png', '原肤色 · 斜侧'),
    (R/'previews/skin-quarter-left.png', '三月七浅肤色 · 斜侧'),
])
board('skin-multiview.png', '三月七 v14 · 浅肤色妆面预览', '从原角色额头无妆区域取色，保留现有眉眼和嘴部妆面', [
    (R/'previews/skin-front.png', '正面'),
    (R/'previews/skin-quarter-left.png', '左前斜侧'),
    (R/'previews/skin-quarter-right.png', '右前斜侧'),
    (R/'previews/skin-side.png', '侧面'),
])
(R/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('SKIN_COMPARISON_BOARDS_DONE')
