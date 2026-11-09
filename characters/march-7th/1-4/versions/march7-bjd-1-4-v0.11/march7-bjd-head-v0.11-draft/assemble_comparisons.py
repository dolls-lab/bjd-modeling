"""Arrange unchanged actual Blender renders; no shape edits or retouching."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'

def board(name, versions, views, title):
    cell,pad,gap,top,row=650,30,25,130,710
    im=Image.new('RGB',(pad*2+len(versions)*cell+(len(versions)-1)*gap,top+len(views)*row+52),'#252e39')
    d=ImageDraw.Draw(im);f=lambda n:ImageFont.truetype(FONT,n)
    d.text((pad,20),title,font=f(36),fill='white')
    d.text((pad,77),'　→　'.join(versions)+'　｜　相同相机、相同尺度与灯光',font=f(25),fill='#c6cdd7')
    for i,(suffix,label) in enumerate(views):
        for j,ver in enumerate(versions):
            x,y=pad+j*(cell+gap),top+i*row
            pic=Image.open(R/'comparison-renders'/f'{ver}-{suffix}.png').convert('RGB')
            im.paste(pic.resize((cell,cell),Image.Resampling.LANCZOS),(x,y))
            d.text((x+12,y+cell+12),label+' · '+ver,font=f(27),fill='white')
    d.text((pad,im.height-39),'实际头壳与后盖网格渲染；仅缩放排版，未修形或磨皮。',font=f(21),fill='#c6cdd7')
    im.save(R/name)

board('forehead-transition-comparison.png',['v10','v11'],[('right-quarter','前斜侧'),('top','俯视')],'三月七四分 BJD · 额头与眉眼两侧的过渡')
board('v8-reference-comparison.png',['v8','v10','v11'],[('side','侧面'),('top','俯视')],'三月七四分 BJD · v8 参考与本轮修整')
board('front-side-comparison.png',['v10','v11'],[('front','正面'),('side','侧面')],'三月七四分 BJD · 正面与侧面')
print('COMPARISONS_DONE')
