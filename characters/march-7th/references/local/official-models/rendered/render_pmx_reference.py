from pathlib import Path
import struct,json,math
import numpy as np
from PIL import Image, ImageDraw
base=Path('/Users/mmj/Projects/mihoyo/character-doll-workshop/projects/honkai-star-rail/march-7th-preservation-bjd-1-4/references/local/official-models')
p=base/'extracted/星穹铁道—三月七/三月七 1.0.pmx'; b=p.read_bytes();pos=4

def read(fmt):
 global pos
 n=struct.calcsize('<'+fmt);out=struct.unpack_from('<'+fmt,b,pos);pos+=n
 return out[0] if len(out)==1 else out

def skip(n):
 global pos;pos+=n
version=read('f');hs=read('B');h=list(b[pos:pos+hs]);skip(hs);enc='utf-16-le' if h[0]==0 else 'utf-8'
def txt():
 global pos
 n=read('i');s=b[pos:pos+n].decode(enc);skip(n);return s
def idx(size):return read({1:'b',2:'h',4:'i'}[size])
for _ in range(4):txt()
v=[];uv=[];normals=[]
for _ in range(read('i')):
 v.append(read('3f'));normals.append(read('3f'));uv.append(read('2f'));skip(16*h[1]);typ=read('B')
 skip({0:h[5],1:2*h[5]+4,2:4*h[5]+16,3:2*h[5]+4+36,4:4*h[5]+16}[typ]);skip(4)
v=np.array(v);uv=np.array(uv);normals=np.array(normals)
ni=read('i');fmt={1:'B',2:'H',4:'I'}[h[2]];faces=np.array(read(str(ni)+fmt),dtype=np.int32).reshape(-1,3)
textures=[txt() for _ in range(read('i'))]; imgs={}
for i,name in enumerate(textures):imgs[i]=np.array(Image.open(p.parent/name).convert('RGBA'))
mats=[];start=0
for _ in range(read('i')):
 name=txt();txt();diffuse=np.array(read('4f'));skip(12+4+12);flags=read('B');skip(16+4);ti=idx(h[3]);idx(h[3]);read('B');tf=read('B');skip(1 if tf else h[3]);txt();count=read('i')//3
 mats.append((start,start+count,name,ti,diffuse));start+=count
out=base/'rendered';out.mkdir(exist_ok=True)
views=[('front',0),('back',math.pi),('left',-math.pi/2),('right',math.pi/2)]
for name,angle in views:
 cs,sn=math.cos(angle),math.sin(angle);xyz=np.column_stack([v[:,0]*cs+v[:,2]*sn,v[:,1],-v[:,0]*sn+v[:,2]*cs])
 W,H=760,1080;scale=46
 xy=np.column_stack([W/2+xyz[:,0]*scale,H-55-xyz[:,1]*scale]);depth=xyz[:,2]
 canvas=np.full((H,W,3),247,dtype=np.uint8);zbuf=np.full((H,W),np.inf)
 for st,en,mname,ti,diff in mats:
  if mname=='表情':continue
  img=imgs.get(ti);th,tw=img.shape[:2] if img is not None else (0,0)
  for ids in faces[st:en]:
   tri=xy[ids];lo=np.maximum(np.floor(tri.min(axis=0)).astype(int),[0,0]);hi=np.minimum(np.ceil(tri.max(axis=0)).astype(int),[W-1,H-1])
   if (hi<lo).any():continue
   a,c,d=tri;den=(c[1]-d[1])*(a[0]-d[0])+(d[0]-c[0])*(a[1]-d[1])
   if abs(den)<1e-8:continue
   xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
   w0=((c[1]-d[1])*(xx-d[0])+(d[0]-c[0])*(yy-d[1]))/den
   w1=((d[1]-a[1])*(xx-d[0])+(a[0]-d[0])*(yy-d[1]))/den;w2=1-w0-w1
   dep=w0*depth[ids[0]]+w1*depth[ids[1]]+w2*depth[ids[2]]
   z=zbuf[lo[1]:hi[1]+1,lo[0]:hi[0]+1];mask=(w0>=0)&(w1>=0)&(w2>=0)&(dep<z)
   if not mask.any():continue
   if img is not None:
    u=w0*uv[ids[0],0]+w1*uv[ids[1],0]+w2*uv[ids[2],0];vv=w0*uv[ids[0],1]+w1*uv[ids[1],1]+w2*uv[ids[2],1]
    sample=img[(vv*th).astype(int)%th,(u*tw).astype(int)%tw]
   else:
    sample=np.zeros((*w0.shape,4));sample[:]=255
   alpha=sample[:,:,3]/255*diff[3];mask&=alpha>.5
   rgb=np.clip(sample[:,:,:3]*diff[:3],0,255).astype(np.uint8)
   canvas[lo[1]:hi[1]+1,lo[0]:hi[0]+1][mask]=rgb[mask];z[mask]=dep[mask]
 im=Image.fromarray(canvas);dr=ImageDraw.Draw(im);dr.text((20,18),f'March 7th | {name} | official PMX 1.0',fill=(35,40,55));dr.text((20,H-28),'Local observation render / unlit texture / model units, not doll measurements',fill=(55,60,70));im.save(out/f'{name}.png');print(name,flush=True)
board=Image.new('RGB',(4*W,H),'white')
for i,(name,_) in enumerate(views):board.paste(Image.open(out/f'{name}.png'),(W*i,0))
board.save(out/'four-views.png')
print(out/'four-views.png')
