"""Bake original iris/highlight color onto real hemispherical preview-eye surfaces.
Source eye triangles are used only for offline texture lookup, never output as visible geometry.
Run with external Python + numpy/Pillow.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
P=Path(__file__).resolve().parent;R=next(x for x in P.parents if x.name=='march7-bjd-1-4-v0.14-makeup')/'source-reference'
S=R/'source-head-geometry.npz';T=R/'textures'/'脸.png';HEAD=next(x for x in P.parents if x.name=='outputs')/'march7-bjd-1-4-v0.14'/'march7-head-shell-v0.14-draft.stl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p):sha(p) for p in [S,T,HEAD]}
src=np.load(S);name='SOURCE_04_IRIS_AND_HIGHLIGHT';v=src[name+'_vertices'];f=src[name+'_triangles'];uv=src[name+'_original_uv']
image=np.asarray(Image.open(T).convert('RGBA'),dtype=np.float64)/255
W=1024;SS=2;N=W*SS;RADIUS=8.;INNER=7.4
centers={'negative':[-13.663962920147602,-13.289332231246028,27.67311677124019],'positive':[13.663962920147602,-13.289332231246028,27.67311677124019]}
def sample(texuv):
 # PMX's V is top-origin. Sample original PNG directly, using bilinear filtering.
 x=np.clip(texuv[...,0]*image.shape[1]-.5,0,image.shape[1]-1);y=np.clip(texuv[...,1]*image.shape[0]-.5,0,image.shape[0]-1)
 ix=np.floor(x).astype(int);iy=np.floor(y).astype(int);jx=np.minimum(ix+1,image.shape[1]-1);jy=np.minimum(iy+1,image.shape[0]-1);ax=(x-ix)[...,None];ay=(y-iy)[...,None]
 return (image[iy,ix]*(1-ax)+image[iy,jx]*ax)*(1-ay)+(image[jy,ix]*(1-ax)+image[jy,jx]*ax)*ay

def bake(side,center):
 faceids=np.flatnonzero(np.all(v[f,:,][...,0]<0,axis=1) if side=='negative' else np.all(v[f,:,][...,0]>0,axis=1))
 # Output top-left origin, covering full projected diameter16mm.
 canvas=np.ones((N,N,4),np.float32);depth=np.full((N,N),np.inf,np.float32);covered=np.zeros((N,N),bool)
 for fi in faceids:
  xyz=v[f[fi]];q=np.c_[(xyz[:,0]-center[0]+RADIUS)/(2*RADIUS)*N,(RADIUS-(xyz[:,2]-center[2]))/(2*RADIUS)*N]
  lower=np.maximum(np.floor(q.min(0)-.5).astype(int),0);upper=np.minimum(np.ceil(q.max(0)-.5).astype(int),N-1)
  if np.any(upper<lower):continue
  xs,ys=np.meshgrid(np.arange(lower[0],upper[0]+1)+.5,np.arange(lower[1],upper[1]+1)+.5)
  a=q[1]-q[0];b=q[2]-q[0];den=a[0]*b[1]-a[1]*b[0]
  if abs(den)<1e-10:continue
  px=xs-q[0,0];py=ys-q[0,1];wb=(px*b[1]-py*b[0])/den;wc=(a[0]*py-a[1]*px)/den;wa=1-wb-wc
  bary=np.stack([wa,wb,wc],axis=-1);inside=np.min(bary,axis=-1)>=-1e-8
  dep=bary@xyz[:,1];dview=depth[lower[1]:upper[1]+1,lower[0]:upper[0]+1];active=inside&(dep<dview)
  color=sample(bary@uv[f[fi]]);active &= color[...,3]>.001
  out=canvas[lower[1]:upper[1]+1,lower[0]:upper[0]+1]
  # Original atlas alpha over opaque white sclera; no cutout plane remains.
  rgb=color[...,:3]*color[...,3:4]+1-color[...,3:4]
  out[active,:3]=rgb[active];out[active,3]=1;dview[active]=dep[active]
  covered[lower[1]:upper[1]+1,lower[0]:upper[0]+1]|=active
 dest=P/f'march7-hemisphere-eye-{side}.png'
 Image.fromarray(np.clip(canvas*255+.5,0,255).astype(np.uint8),'RGBA').resize((W,W),Image.Resampling.LANCZOS).save(dest)
 return {'side':side,'file':dest.name,'sha256':sha(dest),'source_iris_triangles':len(faceids),'baked_iris_projected_area_mm2':float(covered.sum()*(2*RADIUS/N)**2),'source_projected_bbox_xz_mm':[v[np.unique(f[faceids])][:,[0,2]].min(0).tolist(),v[np.unique(f[faceids])][:,[0,2]].max(0).tolist()]}

def hemisphere_cup(center,n_theta=64,n_phi=192):
 # Polar direction is -Y, theta0 at front pole, theta pi/2 at open back rim.
 vv=[];uvs=[];ff=[];mi=[]
 for radius in [RADIUS,INNER]:
  vv.append([0,-radius,0]);uvs.append([.5,.5])
  for j in range(1,n_theta+1):
   theta=np.pi/2*j/n_theta
   for k in range(n_phi):
    phi=2*np.pi*k/n_phi;x=radius*np.sin(theta)*np.cos(phi);zz=radius*np.sin(theta)*np.sin(phi)
    vv.append([x,-radius*np.cos(theta),zz]);uvs.append([.5+x/(2*RADIUS),.5+zz/(2*RADIUS)])
 layer=1+n_theta*n_phi
 for shell in [0,1]:
  offset=shell*layer
  for k in range(n_phi):
   tri=[offset,offset+1+k,offset+1+(k+1)%n_phi];ff.append(tri if shell==0 else tri[::-1]);mi.append(shell)
  for j in range(n_theta-1):
   for k in range(n_phi):
    a=offset+1+j*n_phi+k;b=offset+1+(j+1)*n_phi+k;c=offset+1+(j+1)*n_phi+(k+1)%n_phi;d=offset+1+j*n_phi+(k+1)%n_phi
    tris=[[a,b,c],[a,c,d]]
    for tri in tris:ff.append(tri if shell==0 else tri[::-1]);mi.append(shell)
 for k in range(n_phi):
  a=1+(n_theta-1)*n_phi+k;b=a+layer;c=1+(n_theta-1)*n_phi+(k+1)%n_phi+layer;d=c-layer
  ff.extend([[a,b,c],[a,c,d]]);mi.extend([1,1])
 return np.asarray(vv)+center,np.asarray(ff,np.int32),np.asarray(uvs,np.float32),np.asarray(mi,np.int32)
arrays={};textures=[]
for side,cc in centers.items():
 center=np.array(cc);textures.append(bake(side,center));vv,ff,uvs,mi=hemisphere_cup(center)
 arrays['vertices_'+side]=vv;arrays['faces_'+side]=ff;arrays['uv_'+side]=uvs;arrays['material_index_'+side]=mi;arrays['center_'+side]=center
np.savez_compressed(P/'hemisphere-eye-geometry.npz',**arrays)
report={'inputs':hashes,'inputs_unchanged':all(sha(Path(p))==h for p,h in hashes.items()),'eye_centers_mm':centers,'outer_radius_mm':RADIUS,'inner_radius_mm':INNER,'nominal_cup_wall_mm':RADIUS-INNER,'orientation':'front hemisphere toward -Y, open rear at center Y, annular rim only; no closing disk','meshing':{'theta_segments':64,'phi_segments':192,'outer_vertices_on_analytic_sphere':True,'note':'Triangles inscribe the analytic spherical surfaces. Closed cup solid encloses the shell material, not a closed eyeball globe.'},'texture_bake':{'method':'Orthographic -Y view of original iris/highlight material only, depth-tested original triangles, barycentric original PMX UV lookup, over pure white sclera. Result attached to actual spherical exterior by planar XZ UV coordinates. No original eye triangle is a visible output object.','png_resolution':[W,W],'supersampling':SS,'includes':'Original iris, pupil and white highlight pieces in one surface texture; no separate highlight card/mesh.','not_included':'Original sclera/upper-shadow geometry; physical/scene lighting supplies shading.','frontal_source_scale_preserved':True,'textures':textures},'geometry_npz_sha256':sha(P/'hemisphere-eye-geometry.npz'),'preview_only':True,'limitations':['Not a manufactured eyeball specification.','Original stylized iris/highlights are projected into spherical surface coordinates; oblique views correctly foreshorten with the sphere.','Texture is an offline bake of source colors, not the official game shader.']}
(P/'eye-assets-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
