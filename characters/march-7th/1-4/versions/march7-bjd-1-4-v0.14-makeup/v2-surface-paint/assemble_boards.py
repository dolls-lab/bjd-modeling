"""Arrange actual rendered views; no painting, reshaping, or image recoloring."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont
R = Path(__file__).resolve().parent
D = R / 'previews'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
font = lambda n: ImageFont.truetype(FONT, n)
records = []
def board(filename, title, subtitle, cells, ncols, size=600):
    rows = (len(cells) + ncols - 1) // ncols
    pad, gap, top, rowh = 28, 20, 124, size + 58
    canvas = Image.new('RGB', (pad * 2 + ncols * size + (ncols - 1) * gap,
                                top + rows * rowh + 44), '#29333e')
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 20), title, font=font(32), fill='white')
    draw.text((pad, 74), subtitle, font=font(20), fill='#d9dfe7')
    for i, (file, label) in enumerate(cells):
        x = pad + (i % ncols) * (size + gap)
        y = top + (i // ncols) * rowh
        canvas.paste(Image.open(D / file).convert('RGB').resize((size, size), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 10, y + size + 12), label, font=font(23), fill='white')
    draw.text((pad, canvas.height - 34), '实际三维渲染 · 头壳形状未改 · 只有局部妆面与独立半球眼球', font=font(17), fill='#c4cdd9')
    canvas.save(R / filename)
    records.append({'file':filename, 'sha256':hashlib.sha256((R / filename).read_bytes()).hexdigest(),
                    'inputs':[x[0] for x in cells], 'operations':'Resize and arrange only; no retouching.'})
board('local-makeup-multiview.png', '三月七 v14 · 局部妆面与半球眼',
      '眉眼、唇色画在原头壳上；眼洞内为独立半球', [
          ('makeup-front.png', '正面'),
          ('makeup-quarter-left.png', '左前斜侧'),
          ('makeup-quarter-right.png', '右前斜侧'),
          ('makeup-side.png', '侧面'),
      ], 2)
board('surface-and-interior.png', '局部妆面与内部结构',
      '上排：同一头壳素头／局部妆面　下排：打开后盖与独立半球眼', [
          ('bare-quarter-left.png', 'v14 原素头 · 同一相机和灯光'),
          ('makeup-quarter-left.png', '原头壳表面局部上色'),
          ('inside-back-open.png', '隐藏后盖 · 头壳内部'),
          ('hemisphere-cups.png', '独立半球眼 · 从背面看开口'),
      ], 2)
(R / 'board-provenance.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
print('BOARDS_ASSEMBLED')
