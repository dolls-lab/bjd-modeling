"""Arrange actual before/after Blender renders without retouching."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def board(name,views,title):
    cell,pad,gap,top,row=700,30,30,130,765
    out=Image.new('RGB',(2*cell+2*pad+gap,top+len(views)*row+50),'#252e39')
    d=ImageDraw.Draw(out);font=lambda n:ImageFont.truetype(FONT,n)
    d.text((pad,20),title,font=font(35),fill='white')
    d.text((pad,78),'左：v13　　右：v14　｜　相同相机、尺度与灯光',font=font(26),fill='#c6cdd7')
    for i,(suffix,label) in enumerate(views):
        for j,version in enumerate(['v13','v14']):
            x,y=pad+j*(cell+gap),top+i*row
            pic=Image.open(R/'comparison-renders'/f'{version}-{suffix}.png').convert('RGB')
            out.paste(pic.resize((cell,cell),Image.Resampling.LANCZOS),(x,y))
            d.text((x+12,y+cell+13),label+' · '+version,font=font(27),fill='white')
    d.text((pad,out.height-38),'实际打印模型网格渲染；仅缩放排版，未修形或磨皮。',font=font(21),fill='#c6cdd7')
    out.save(R/name)
board('shape-and-eyes-comparison.png',[('front','正面'),('crown-front','正顶弧线'),('eye-front','眼洞正面')],'三月七四分 BJD · 眼洞还原与正顶加宽')
board('whole-head-comparison.png',[('quarter','前斜侧'),('side','侧面'),('top','俯视')],'三月七四分 BJD · 整体轮廓核对')
board('front-comparison.png',[('front','正面')],'三月七四分 BJD · v14 正面比较')
print('COMPARISONS_DONE')
