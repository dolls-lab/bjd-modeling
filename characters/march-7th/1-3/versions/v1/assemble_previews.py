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


board('fourth-vs-third.png', '三月七 · 四分 v14 与三分打样版',
      '左：四分 v14　　右：三分 v1 · 等比 1.25 倍', [
          [('quarter-front', '四分 · 正面 · 高约 69.72 mm'), ('third-front', '三分 · 正面 · 高约 87.14 mm')],
          [('quarter-side', '四分 · 侧面'), ('third-side', '三分 · 侧面')],
      ], 570, '两列使用相同正交镜头和灯光；脸型、头型等比保留，仅颈接口局部调整。')
board('third-multiview.png', '三月七 · 三分 v1 多角度预览',
      '头围参考截面约 225 mm · 颈球座 32 mm · 拉筋槽 9 × 18 mm', [
          [('third-front', '正面'), ('third-quarter', '前斜侧'), ('third-side', '侧面')],
          [('third-rear', '后脑与后盖'), ('third-top', '顶部'), ('third-neck', '颈部接口近景')],
      ], 440, '本地实际网格渲染。当前为未指定娃体的打样版，接口需按目标娃体实测调整。')
board('neck-interface.png', '三月七 · 三分颈口与内部结构',
      '保持球座顶部位置；球座上方名义余厚 4 mm', [
          [('third-neck', '底部球座及拉筋槽'), ('third-interior', '隐藏后盖后的内部结构')],
      ], 570, '32 mm 是球座直径，不是颈围；90 mm 颈围仅为待定设计参考，尚未实装。')
(ROOT / 'board-provenance.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print('Preview boards created from verified render PNGs.')
