"""Side-by-side identical-camera comparisons; layout only, no visual retouching."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont
R = Path(__file__).resolve().parent
font = lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', n)
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
provenance = json.loads((R/'comparison-provenance.json').read_text())
views = {v['view']:v for v in provenance['views']}
records = []
def board(filename, title, keys, size=620):
    pad, gap, top, rowh = 26, 22, 130, size+57
    im = Image.new('RGB',(pad*2+size*2+gap,top+len(keys)*rowh+52),'#29333e')
    draw = ImageDraw.Draw(im)
    draw.text((pad,22),title,font=font(31),fill='white')
    draw.text((pad,78),'左：当前 BJD　　右：原三月七 PMX 模型',font=font(22),fill='#d9dfe7')
    inputs = []
    for row,key in enumerate(keys):
        v = views[key]
        files = [Path(v['bjd_file']), R/v['original_file']]
        expected = [v['bjd_image_sha256'],v['original_image_sha256']]
        for col,(p,digest) in enumerate(zip(files,expected)):
            assert sha(p) == digest
            x = pad+col*(size+gap)
            y = top+row*rowh
            im.paste(Image.open(p).convert('RGB').resize((size,size),Image.Resampling.LANCZOS),(x,y))
            label = ('当前 BJD' if col==0 else '原角色模型')+' · '+v['label']
            draw.text((x+9,y+size+12),label,font=font(23),fill='white')
            inputs.append({'file':str(p.resolve()),'sha256':digest})
    draw.text((pad,im.height-35),'同角度、同尺度、同灯光 · 原模型为 Blender 重渲染，非游戏实机画面',font=font(18),fill='#c4cdd9')
    im.save(R/filename)
    records.append({'file':filename,'sha256':sha(R/filename),'inputs':inputs,'operations':'Resize and arrange only; no geometry, proportion or color retouching.'})
board('overall-comparison.png','三月七 · 娃头与原模型对照',['front','quarter-left'])
board('face-comparison.png','三月七 · 面部近景对照',['face-front','face-quarter'],size=680)
board('profile-comparison.png','三月七 · 侧面对照',['side'])
(R/'board-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('COMPARISON_BOARDS_DONE')
