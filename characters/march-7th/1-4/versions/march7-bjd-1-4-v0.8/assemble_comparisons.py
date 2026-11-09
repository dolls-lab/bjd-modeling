"""Arrange unretouched, identically lit v6/v7 Blender renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
old=R/'comparison-renders'
new=R/'comparison-renders'
font='/System/Library/Fonts/STHeiti Medium.ttc'
def f(n):return ImageFont.truetype(font,n)
def comparison(name,views):
    w=1800; pad=40; cell=840; top=155; row=925
    im=Image.new('RGB',(w,top+len(views)*row+55),'#252e39');d=ImageDraw.Draw(im)
    d.text((pad,24),'三月七四分 BJD · 圆润头型与顺滑表面',font=f(44),fill='white')
    d.text((pad,88),'左：v7　　右：v8　｜　相同相机、相同灯光，真实网格渲染',font=f(27),fill='#c6cdd7')
    for i,(suffix,label) in enumerate(views):
        y=top+i*row
        for j,(folder,version) in enumerate([(old,'v7'),(new,'v8')]):
            pic=Image.open(folder/(version+'-'+suffix+'.png')).convert('RGB')
            pic=pic.resize((cell,cell),Image.Resampling.LANCZOS)
            x=pad+j*(cell+40);im.paste(pic,(x,y))
            d.text((x+15,y+cell+18),label+' · '+version,font=f(32),fill='white')
    d.text((pad,im.height-42),'仅等比例缩放与排版；未对渲染图修形或磨皮。',font=f(22),fill='#c6cdd7')
    im.save(R/name)
comparison('roundness-comparison.png',[('right-quarter','前斜侧'),('top','俯视轮廓')])
comparison('surface-comparison.png',[('right-ear-rear','耳后近景'),('front','正面')])
print('COMPARISONS_DONE')
