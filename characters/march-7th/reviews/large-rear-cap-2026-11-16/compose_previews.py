"""Arrange actual renderer outputs with Chinese labels; resize only, no retouch."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=[]
def font(size):return ImageFont.truetype(FONT,size)
def board(filename,title,subtitle,tiles,cols=2,tile_width=680):
    margin=28;gap=20;top=125;caption=48;bottom=54
    rows=(len(tiles)+cols-1)//cols
    width=margin*2+cols*tile_width+(cols-1)*gap
    height=top+rows*(tile_width+caption+gap)+bottom
    im=Image.new('RGB',(width,height),'#f3f0eb');draw=ImageDraw.Draw(im)
    draw.text((margin,24),title,font=font(32),fill='#26313b')
    draw.text((margin,77),subtitle,font=font(22),fill='#53616a')
    sources=[]
    for i,(name,label) in enumerate(tiles):
        path=HERE/name;src=Image.open(path).convert('RGB')
        assert src.width==src.height,src.size
        resized=src.resize((tile_width,tile_width),Image.Resampling.LANCZOS)
        x=margin+(i%cols)*(tile_width+gap);y=top+(i//cols)*(tile_width+caption+gap)
        im.paste(resized,(x,y));draw.text((x,y+tile_width+12),label,font=font(24),fill='#26313b')
        sources.append({'image':name,'sha256':sha(path),'source_size':list(src.size),'destination_xy':[x,y],'display_size':[tile_width,tile_width]})
    draw.text((margin,height-42),'真实模型渲染；粉色仅标识后盖。展示图未对网格外观进行修图。',font=font(20),fill='#65717b')
    out=HERE/filename;im.save(out)
    records.append({'image':filename,'sha256':sha(out),'source_renders':sources,'operation':'Uniform image resize and label/layout only; no crop, repainting, filtering, shape change, or generated visual content.'})

board('large-cap-before-after.png','后盖扩大 · 四分前后对比','相同机位与比例；粉色部分为可拆后盖。',[
 ('quarter-old-side.png','原版：头顶大多留在前壳'),
 ('quarter-new-side.png','新版：头顶和后脑连成一片'),
 ('quarter-old-open.png','原版：取下后盖'),
 ('quarter-new-open.png','新版：取下后盖，开口扩大'),
])
board('large-cap-overview.png','新版分片 · 四分多角度','前壳与后盖分开展示；爆炸图仅移动零件位置。',[
 ('quarter-new-exploded.png','前壳与后盖分开展示'),
 ('quarter-new-cap-interior.png','后盖内侧'),
 ('quarter-new-front.png','合盖正面 · 统一素色'),
 ('quarter-new-top.png','合盖俯视 · 粉色标识后盖范围'),
])
board('large-cap-three-sizes.png','三种尺寸 · 新分片结构','各尺寸按相同构图展示，画面中的缩放比例不同。',[
 ('quarter-new-open.png','四分 v31 · 取下后盖'),
 ('third-new-open.png','三分 v15 · 取下后盖'),
 ('special-six-new-open.png','特六 v16 · 取下后盖'),
 ('special-six-new-exploded.png','特六 v16 · 前后壳分开'),
])
(HERE/'contact-sheet-provenance.json').write_text(json.dumps({'boards':records,'no_geometry_or_pixel_retouch':True},ensure_ascii=False,indent=2)+'\n')
print('CONTACT_SHEETS_COMPLETE',len(records))
