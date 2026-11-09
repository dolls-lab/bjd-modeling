"""Lay out unchanged, identically lit Blender model renders for review."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parent
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

def board(filename, title, views):
    width, cell, pad, top, row = 1600, 750, 35, 130, 810
    out = Image.new('RGB', (width, top + len(views)*row + 55), '#252e39')
    draw = ImageDraw.Draw(out)
    font = lambda n: ImageFont.truetype(FONT, n)
    draw.text((pad, 22), title, fill='white', font=font(36))
    draw.text((pad, 78), '左：v9　　右：v10　｜　相同相机、比例与灯光', fill='#c6cdd7', font=font(26))
    for i, (suffix, label) in enumerate(views):
        for j, version in enumerate(('v9', 'v10')):
            x, y = pad + j*(cell+30), top+i*row
            im = Image.open(R/'comparison-renders'/f'{version}-{suffix}.png').convert('RGB')
            out.paste(im.resize((cell, cell), Image.Resampling.LANCZOS), (x, y))
            draw.text((x+12, y+cell+12), label+' · '+version, fill='white', font=font(28))
    draw.text((pad, out.height-40), '实际头壳与后盖网格渲染；仅缩放排版，未修形或磨皮。', fill='#c6cdd7', font=font(22))
    out.save(R/filename)

board('forehead-height-comparison.png', '三月七四分 BJD · 额头顶部降低约 3 mm', [('front', '正面'), ('side', '侧面')])
print('COMPARISONS_DONE')
