"""Lay out unretouched Blender renders for review; no generative retouching."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;D=R/'previews'
font=lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',n)
rows=[]
def board(filename,title,subtitle,cells,ncols,size=640):
    nr=(len(cells)+ncols-1)//ncols;pad=28;gap=24;top=126;row=size+62
    canvas=Image.new('RGB',(pad*2+ncols*size+(ncols-1)*gap,top+nr*row+44),'#29333e');draw=ImageDraw.Draw(canvas)
    draw.text((pad,21),title,font=font(34),fill='white');draw.text((pad,76),subtitle,font=font(22),fill='#d9dfe7')
    for i,(file,label) in enumerate(cells):
        x=pad+(i%ncols)*(size+gap);y=top+(i//ncols)*row
        canvas.paste(Image.open(D/file).convert('RGB').resize((size,size),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+9,y+size+14),label,font=font(25),fill='white')
    draw.text((pad,canvas.height-36),'实际三维模型渲染；素头形状未改。眼睛、眉睫与头发为观感参考。',font=font(18),fill='#c4cdd9')
    canvas.save(R/filename);rows.append({'file':filename,'inputs':[x[0] for x in cells],'sha256':hashlib.sha256((R/filename).read_bytes()).hexdigest(),'operations':'Resize and arrange only; no reshaping, retouching or recoloring.'})
board('makeup-multiview.png','三月七 · v14 妆面预览','原角色眼睛、眉睫、腮红与唇色；四个角度',[
 ('makeup-front.png','正面'),('makeup-quarter-left.png','左前斜侧'),('makeup-quarter-right.png','右前斜侧'),('makeup-side.png','纯侧面')],2)
board('hair-multiview.png','三月七 · 加入原发型参考','发型为可切换的原模型参考附件',[
 ('hair-quarter-left.png','左前斜侧'),('hair-front.png','正面'),('hair-quarter-right.png','右前斜侧')],3,560)
board('character-comparison.png','三月七 · 与原角色模型对照','左：v14 妆面＋发型参考　　右：原角色模型；相同相机、尺度与灯光',[
 ('hair-front.png','v14 · 正面'),('original-front.png','原角色 · 正面'),('hair-quarter-left.png','v14 · 左前斜侧'),('original-quarter-left.png','原角色 · 左前斜侧')],2)
(R/'board-provenance.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('PREVIEW_BOARDS_DONE')
