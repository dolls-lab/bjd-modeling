"""Arrange actual Blender renders; no retouching or geometry illustration."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PREVIEWS = ROOT / 'previews'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
font = lambda size: ImageFont.truetype(FONT, size)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
records = []
provenance = json.loads((ROOT / 'render-provenance.json').read_text())
for item in provenance['views']:
    assert sha(ROOT / item['file']) == item['sha256']


def board(filename, title, subtitle, rows, size, footnote):
    columns = len(rows[0])
    margin, gap, top, caption = 24, 16, 112, 48
    width = 2 * margin + columns * size + (columns - 1) * gap
    height = top + len(rows) * (size + caption) + 48
    canvas = Image.new('RGB', (width, height), '#29333e')
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), title, font=font(32), fill='white')
    draw.text((margin, 65), subtitle, font=font(20), fill='#d4dce5')
    inputs = []
    for row, cells in enumerate(rows):
        for col, (name, label) in enumerate(cells):
            path = PREVIEWS / (name + '.png')
            image = Image.open(path).convert('RGB').resize((size, size), Image.Resampling.LANCZOS)
            x = margin + col * (size + gap)
            y = top + row * (size + caption)
            canvas.paste(image, (x, y))
            draw.text((x + 8, y + size + 10), label, font=font(21), fill='white')
            inputs.append({'file': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    draw.text((margin, height - 35), footnote, font=font(18), fill='#c3cdd9')
    canvas.save(ROOT / filename)
    records.append({'file': filename, 'sha256': sha(ROOT / filename), 'inputs': inputs,
                    'operations': 'Resize and layout only; actual model renders, no retouching.'})


board('whole-head-comparison.png','四分 v16 与 v18 · 唇部微调',
      '左：v16 基准　右：v18 仅唇缘内收 · 同机位与灯光',[
       [('v16-front','v16 · 正面'),('v18-front','v18 · 正面')],
       [('v16-quarter','v16 · 斜侧'),('v18-quarter','v18 · 斜侧')],
       [('v16-side','v16 · 正侧面'),('v18-side','v18 · 正侧面')],
      ],500,'实际保存模型的渲染；原 v16、v18 文件未修改。')
board('mouth-closeup-comparison.png','四分 v16 与 v18 · 嘴周近景',
      '左：v16 基准　右：v18 · 相同倍率与光照', [
       [('v16-mouth-front','v16 · 正面'),('v18-mouth-front','v18 · 正面')],
       [('v16-mouth-quarter','v16 · 斜侧'),('v18-mouth-quarter','v18 · 斜侧')],
      ],500,'只拼版显示真实模型；没有修图或修改模型几何。')
board('side-light-comparison.png','四分 v16 与 v18 · 侧面与侧光',
      '左：v16 基准　右：v18 · 检查唇部凸起 · 周围脸颊坐标锁定', [
       [('v16-mouth-side','v16 · 正侧面'),('v18-mouth-side','v18 · 正侧面')],
       [('v16-mouth-grazing','v16 · 侧光'),('v18-mouth-grazing','v18 · 侧光')],
      ],500,'同相机、同灯光、同材质；仅供形状对比。')
(ROOT/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Comparison boards ready')
