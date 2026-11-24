"""Arrange actual size-normalized model renders; no retouching."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
font=lambda s:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',s)
provenance=json.loads((HERE/'render-provenance.json').read_text())
for row in provenance['views']:assert sha(HERE/row['file'])==row['sha256']
labels=[('quarter-v19','四分 v19 · 头围约18 cm'),('third-v3','三分 v3 · 头围约22.5 cm'),('special-six-v4','特六 v4 · 头围约16 cm')]
records=[]
def board(filename,title,views):
 size=440;gap=16;margin=24;top=120;caption=46
 out=Image.new('RGB',(margin*2+size*3+gap*2,top+len(views)*(size+caption)+55),'#29333e');d=ImageDraw.Draw(out)
 d.text((margin,18),title,font=font(32),fill='white')
 d.text((margin,64),'画面统一头部大小以核对脸型；实际尺寸见各列头围标注',font=font(22),fill='#d4dce5')
 inputs=[]
 for row,(view,view_label) in enumerate(views):
  for col,(label,caption_label) in enumerate(labels):
   path=HERE/'previews'/f'{label}-{view}.png';im=Image.open(path).convert('RGB').resize((size,size),Image.Resampling.LANCZOS)
   x=margin+col*(size+gap);y=top+row*(size+caption);out.paste(im,(x,y))
   d.text((x+6,y+size+10),caption_label+' · '+view_label,font=font(20),fill='white')
   inputs.append({'file':str(path.relative_to(HERE)),'sha256':sha(path)})
 d.text((margin,out.height-36),'保存后的真实模型；等比调整面部与头型，颈部接口单独处理。',font=font(20),fill='#d4dce5')
 path=HERE/filename;out.save(path);records.append({'file':filename,'sha256':sha(path),'inputs':inputs,'operations':'Resize and layout only; no retouching.'})
board('three-sizes-overview.png','三月七 · v19 三尺寸外观核对',[('front','正面'),('quarter','斜侧')])
board('face-and-side-comparison.png','三月七 · 面雕与侧面核对',[('mouth-quarter','嘴部'),('side','正侧面')])
(HERE/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('BOARDS_COMPLETE')
