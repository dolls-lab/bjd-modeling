"""Rasterize original local March7 eyebrow/eyeliner and visible mouth onto RGBA.
No full-face skin, visible source geometry, image generation, or geometry edits.
"""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parent;SRC=R.parents[1]/'source-reference'
D=np.load(SRC/'source-head-geometry.npz');tex=np.array(Image.open(SRC/'textures'/'脸.png').convert('RGBA'))/255.
W,H=2048,1536;XR=(-32.,32.);ZR=(0.,48.);background=np.zeros((H,W,4));manifest={}
def project(v):return np.column_stack([(v[:,0]-XR[0])/(XR[1]-XR[0])*W-.5,(ZR[1]-v[:,2])/(ZR[1]-ZR[0])*H-.5])
def sample(uv):
 x=np.clip(uv[...,0]*(tex.shape[1]-1),0,tex.shape[1]-1);y=np.clip(uv[...,1]*(tex.shape[0]-1),0,tex.shape[0]-1)
 x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,tex.shape[1]-1);y1=np.minimum(y0+1,tex.shape[0]-1);a=(x-x0)[...,None];b=(y-y0)[...,None]
 return (1-b)*((1-a)*tex[y0,x0]+a*tex[y0,x1])+b*((1-a)*tex[y1,x0]+a*tex[y1,x1])
def raster(name,roi=None):
 v=D[name+'_vertices'];f=D[name+'_triangles'];uv=D[name+'_original_uv'];p=project(v);depth=np.full((H,W),np.inf);rgba=np.zeros((H,W,4))
 for tri in f:
  pt=p[tri];vv=v[tri];tt=uv[tri]
  if roi and (vv[:,0].max()<roi[0] or vv[:,0].min()>roi[1] or vv[:,2].max()<roi[2] or vv[:,2].min()>roi[3]):continue
  x0=max(0,int(np.floor(pt[:,0].min())));x1=min(W-1,int(np.ceil(pt[:,0].max())));y0=max(0,int(np.floor(pt[:,1].min())));y1=min(H-1,int(np.ceil(pt[:,1].max())))
  if x0>x1 or y0>y1:continue
  xx,yy=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1));a,b,c=pt;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-12:continue
  l0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;l1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;l2=1-l0-l1;inside=(l0>=-1e-8)&(l1>=-1e-8)&(l2>=-1e-8)
  yyworld=l0*vv[0,1]+l1*vv[1,1]+l2*vv[2,1];old=depth[y0:y1+1,x0:x1+1];keep=inside&(yyworld<old)
  if not keep.any():continue
  uu=l0[...,None]*tt[0]+l1[...,None]*tt[1]+l2[...,None]*tt[2];col=sample(uu);old[keep]=yyworld[keep];rgba[y0:y1+1,x0:x1+1][keep]=col[keep]
 return depth,rgba
ed,ec=raster('SOURCE_02_BROWS_LASHES');brow_lash_mask=ec[:,:,3]>0;background=ec.copy()
# Only mouth pixels actually visible through the original face's tiny mouth
# opening are retained. The face atlas is used for depth occlusion only.
roi=(-8.,8.,7.5,13.5);fd,_=raster('SOURCE_06_FACE',roi);md,mc=raster('SOURCE_00_MOUTH_INTERIOR',roi)
x=XR[0]+(np.arange(W)+.5)/W*(XR[1]-XR[0]);z=ZR[1]-(np.arange(H)+.5)/H*(ZR[1]-ZR[0]);inroi=(x[None,:]>=roi[0])&(x[None,:]<=roi[1])&(z[:,None]>=roi[2])&(z[:,None]<=roi[3])
visible=inroi&np.isfinite(md)&(md<fd-1e-5);background[visible]=mc[visible]
# RGB remains texture-sRGB; straight alpha leaves the resin material intact.
rgba=np.round(np.clip(background,0,1)*255).astype(np.uint8);rgba[rgba[:,:,3]==0,:3]=0
Image.fromarray(rgba,'RGBA').save(R/'local-paint.png')
yygrid,xxgrid=np.indices((H,W));checker=np.where(((xxgrid//64+yygrid//64)%2)[:,:,None],np.array([220,220,220]),np.array([245,245,245])).astype(float)
a=rgba[:,:,3:4]/255.;preview=np.round(rgba[:,:,:3]*a+checker*(1-a)).astype(np.uint8)
Image.fromarray(preview,'RGB').save(R/'local-paint-checker-preview.png')
for label,mask in [('brows_eyeliner',brow_lash_mask),('mouth',visible)]:
 yy,xx=np.nonzero(mask)
 manifest[label]={'painted_pixels':len(xx),'world_bbox_mm':[float(x[xx].min()),float(x[xx].max()),float(z[yy].min()),float(z[yy].max())] if len(xx) else None}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'world_x_range_mm':list(XR),'world_z_range_mm':list(ZR),'resolution':[W,H],'uv_formula':'u=(worldX-xmin)/(xmax-xmin); v=(worldZ-zmin)/(zmax-zmin)','png_row_zero':'highest Z','color_space':'sRGB','alpha':'straight; zero everywhere except local eyebrow/eyeliner/mouth','source_reference_geometry_sha256':sha(SRC/'source-head-geometry.npz'),'source_face_texture_sha256':sha(SRC/'textures'/'脸.png'),'paint_sha256':sha(R/'local-paint.png'),'regions':manifest,'mouth_extraction':'Original mouth interior visible in front orthographic depth relative to original face skin; face color not copied.','material_integration':'Mix paint RGB into existing Principled Base Color by paint alpha times true exterior/front-skin weight; keep roughness, normals and all geometry unchanged.','no_full_face_atlas':True,'no_visible_source_overlay_geometry':True}
(R/'local-paint-mapping.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False,indent=2))
