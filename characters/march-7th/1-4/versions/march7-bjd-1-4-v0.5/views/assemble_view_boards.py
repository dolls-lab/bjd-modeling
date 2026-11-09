"""Compose labeled sheets from actual Blender renders, preserving image geometry."""
from pathlib import Path
import json,hashlib,zipfile
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def font(size):return ImageFont.truetype(FONT,size)
BG=(76,84,96);INK='#f2eeea';MUTED='#cdd4de'
def paste(board,path,xy,size):
    im=Image.open(R/path).convert('RGB')
    board.paste(im.resize((size,size),Image.Resampling.LANCZOS),xy)
def centered(draw,text,cx,y,size=28,fill=INK):
    f=font(size);box=draw.textbbox((0,0),text,font=f)
    draw.text((cx-(box[2]-box[0])/2,y),text,font=f,fill=fill)

items=[('front','正面'),('left-quarter','左前斜侧'),('right-quarter','右前斜侧'),('back','背面'),
       ('left-side','左侧'),('right-side','右侧'),('top','俯视'),('rear-quarter','后方斜侧')]
tile=550;row=600;W=2200;H=1360
board=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(board)
d.text((34,22),'三月七四分 BJD · v5 多角度',font=font(46),fill=INK)
d.text((35,79),'真实模型渲染  /  同一版本、相同尺寸比例',font=font(25),fill=MUTED)
for i,(name,label) in enumerate(items):
    x=(i%4)*tile;y=125+(i//4)*row
    paste(board,'v5-'+name+'.png',(x,y),tile)
    centered(d,label,x+tile/2,y+tile+8)
d.text((35,1330),'另附仰视及每个角度的 1200 × 1200 原图。',font=font(23),fill=MUTED)
board.save(R/'v5-eight-views.png')

columns=[('character-texture-','原人物 · 原贴图预览'),('raw-face-','原 PMX 裸脸 · 统一灰材质'),('v5-clay-','v5 娃头 · 统一灰材质')]
for view,viewlabel in [('front','正面'),('quarter','斜前方'),('side','侧面')]:
    b=Image.new('RGB',(2400,1050),BG);dd=ImageDraw.Draw(b)
    dd.text((35,22),'三月七原模型与娃头 · '+viewlabel+'对照',font=font(46),fill=INK)
    for j,(prefix,label) in enumerate(columns):
        centered(dd,label,j*800+400,91,30)
        paste(b,prefix+view+'.png',(j*800,140),800)
    dd.text((35,965),'同一相机、相同模型比例；中间与右侧使用相同材质和灯光。',font=font(28),fill=INK)
    dd.text((35,1010),'原裸脸本身没有完整后脑；左列为本地 PMX 贴图预览，非游戏截图。',font=font(24),fill=MUTED)
    b.save(R/('source-comparison-'+view+'.png'))

# Compact two-view overview: one column definition, two correctly aligned rows.
overview=Image.new('RGB',(2100,1660),BG);od=ImageDraw.Draw(overview)
od.text((35,22),'原三月七人物模型 → 原裸脸 → v5 娃头',font=font(42),fill=INK)
for j,(_,label) in enumerate(columns):centered(od,label,j*700+350,88,27)
for row,(view,label) in enumerate([('front','正面'),('quarter','斜前方')]):
    y=135+row*735
    for j,(prefix,_) in enumerate(columns):paste(overview,prefix+view+'.png',(j*700,y),700)
    centered(od,label,1050,y+700,26)
od.text((32,1615),'相同相机与比例；中、右列统一灰材质。左列为原贴图预览，非游戏截图。',font=font(23),fill=MUTED)
overview.save(R/'source-comparison-overview.png')

note='''# v5 多角度与原三月七模型对照

本文件夹仅新增预览图，未修改 v5 Blender、STL 或尺寸。

- v5-eight-views.png：八视图总览；v5-low-front.png 另提供仰视。
- source-comparison-overview.png：正面与斜前方，三列依次为原人物贴图、原裸脸、v5 娃头。
- source-comparison-front/quarter/side.png：三个方向的大图对照。
- v5-*.png、raw-face-*.png、character-*.png：各角度原图。

原脸使用本地 PMX 的原始“脸”网格、法线及同一尺度，不做新雕刻或细分。原脸是开放动画网格，没有完整皮肤后脑；眼白、瞳孔、睫毛和头发属于另外的网格，因此裸脸与完整人物的观感不同。中间原裸脸与右侧娃头使用完全相同的材质、灯光、相机及比例，便于观察五官和打印化差异。

原人物贴图列采用无光照贴图预览，使原纹理颜色清楚可见；另保留统一物理照明的 character-original-*.png。两者都是 Blender 对本地 PMX 的渲染，不是游戏画面，也未复刻游戏或 MMD toon 着色器。斜前方为水平约32.6°并略俯视。

模型仍为待实物打印与试装的打样版。原模型来源与使用规则继承 v5 模型包说明。每张原图为1200×1200，拼图只排版缩放，没有修形。
'''
(R/'README.md').write_text(note)
include=sorted(p for p in R.iterdir() if p.suffix in {'.png','.py','.json','.md'} and p.name!='view-checksums.json')
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in include}
(R/'view-checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
archive=R/'march7-v5-view-comparisons.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in include+[R/'view-checksums.json']:z.write(p,'march7-v5-views/'+p.name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'archive':str(archive),'files':len(include),'bytes':archive.stat().st_size}))
