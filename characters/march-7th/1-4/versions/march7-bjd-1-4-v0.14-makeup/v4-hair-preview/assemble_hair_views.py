"""Arrange original, unretouched Blender renders for review."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont
R = Path(__file__).resolve().parent
D = R/'previews'
font = lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', n)
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records = []
def board(filename, title, cells, columns=2, size=620):
    rows = (len(cells)+columns-1)//columns
    pad, gap, top = 26, 20, 122
    image = Image.new('RGB', (pad*2+columns*size+(columns-1)*gap, top+rows*(size+56)+42), '#29333e')
    draw = ImageDraw.Draw(image)
    draw.text((pad,20), title, font=font(32), fill='white')
    draw.text((pad,74), '当前浅肤色头壳＋局部妆面＋原三月七发型与发饰', font=font(20), fill='#d9dfe7')
    for i,(file,label) in enumerate(cells):
        x = pad+(i%columns)*(size+gap)
        y = top+(i//columns)*(size+56)
        image.paste(Image.open(D/file).convert('RGB').resize((size,size),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+10,y+size+12),label,font=font(24),fill='white')
    draw.text((pad,image.height-32),'实际三维模型渲染 · 头壳、眼杯、肤色与局部妆面保持原样',font=font(17),fill='#c4cdd9')
    image.save(R/filename)
    records.append({'file':filename,'sha256':sha(R/filename),'inputs':[{'file':f,'sha256':sha(D/f)} for f,_ in cells],
                    'operations':'Resize and layout only; no retouching or recoloring.'})
board('original-hair-multiview.png','三月七 · 原发型预览',[
    ('front.png','正面'),('quarter-left.png','左前斜侧'),
    ('quarter-right.png','右前斜侧'),('side.png','侧面'),
])
board('original-hair-face-closeups.png','三月七 · 加发型后的面部近景',[
    ('face-front.png','正面近景'),('face-quarter.png','斜侧近景'),
],size=680)
(R/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('HAIR_BOARDS_DONE')
