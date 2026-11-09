"""Arrange unretouched, identically lit v6/v7 Blender renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
old=R.parent/'march7-bjd-1-4-v0.6'/'side-views'
new=R/'side-views'
font='/System/Library/Fonts/STHeiti Medium.ttc'
def f(n):return ImageFont.truetype(font,n)
def comparison(name,views):
    w=1800; pad=40; cell=840; top=155; row=925
    im=Image.new('RGB',(w,top+len(views)*row+55),'#252e39');d=ImageDraw.Draw(im)
    d.text((pad,24),'三月七四分 BJD · 耳后过渡调整',font=f(44),fill='white')
    d.text((pad,88),'左：v6　　右：v7　｜　相同相机、相同灯光，真实网格渲染',font=f(27),fill='#c6cdd7')
    for i,(suffix,label) in enumerate(views):
        y=top+i*row
        for j,(folder,version) in enumerate([(old,'v6'),(new,'v7')]):
            pic=Image.open(folder/(version+'-'+suffix+'.png')).convert('RGB')
            pic=pic.resize((cell,cell),Image.Resampling.LANCZOS)
            x=pad+j*(cell+40);im.paste(pic,(x,y))
            d.text((x+15,y+cell+18),label+' · '+version,font=f(32),fill='white')
    d.text((pad,im.height-42),'仅等比例缩放与排版；未对渲染图修形或磨皮。',font=f(22),fill='#c6cdd7')
    im.save(R/name)
comparison('ear-rear-comparison.png',[('right-ear-rear','右耳后侧'),('left-ear-rear','左耳后侧')])
comparison('side-comparison.png',[('right-front-side','右前斜侧'),('right-rear-side','右后斜侧')])
comparison('ear-front-comparison.png',[('right-ear-front','右耳前侧'),('left-ear-front','左耳前侧')])
print('COMPARISONS_DONE')
