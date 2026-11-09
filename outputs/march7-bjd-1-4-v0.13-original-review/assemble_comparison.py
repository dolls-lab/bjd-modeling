from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent
font=lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',n)
cell,pad,gap,top,row=530,24,20,155,590
out=Image.new('RGB',(3*cell+2*pad+2*gap,top+3*row+65),'#252e39');d=ImageDraw.Draw(out)
d.text((pad,18),'三月七原模型与 v13 · 相同坐标、尺度、相机',font=font(34),fill='white')
cols=[('original-textured','原模型 · 含原贴图和头发'),('original-face','原模型 · 脸部网格'),('bjd-v13','v13 · 当前头壳')]
for j,(v,label) in enumerate(cols):d.text((pad+j*(cell+gap),92),label,font=font(27),fill='#c6cdd7')
for i,(view,label) in enumerate([('front','正面'),('quarter','斜侧面'),('side','侧面')]):
 for j,(v,_) in enumerate(cols):
  x,y=pad+j*(cell+gap),top+i*row
  pic=Image.open(R/f'{v}-{view}.png').convert('RGB');out.paste(pic.resize((cell,cell),Image.Resampling.LANCZOS),(x,y));d.text((x+12,y+cell+12),label,font=font(25),fill='white')
d.text((pad,out.height-62),'原模型未补后脑；含发列为本地原贴图的 Blender 渲染，并非游戏截图。',font=font(22),fill='#c6cdd7')
d.text((pad,out.height-32),'灰模两列使用同一材质和灯光；无模型改动，仅图像缩放排版。',font=font(22),fill='#c6cdd7')
out.save(R/'original-comparison-grid.png')
