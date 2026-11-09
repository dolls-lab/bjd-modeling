from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;V=P.parent/'march7-bjd-1-4-v0.13';d=np.load(P/'face-distance-samples.npz');v=d['source_vertices'];f=d['source_faces'];raw=v[f];stl=V/'march7-head-shell-v0.13-draft.stl';b=stl.read_bytes();n=int.from_bytes(b[80:84],'little');dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')]);cur=np.frombuffer(b,dtype=dt,offset=84,count=n)['vertices'].astype(float)
def segments(tri,axis,value):
 q=tri[(tri[:,:,axis].min(1)<=value)&(tri[:,:,axis].max(1)>value)];out=[]
 for t in q:
  pts=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   if (t[i,axis]<=value<t[j,axis]) or (t[j,axis]<=value<t[i,axis]):pts.append(t[i]+(t[j]-t[i])*(value-t[i,axis])/(t[j,axis]-t[i,axis]))
  if len(pts)==2:out.append(pts)
 return np.array(out)
def front_extent(seg,ymax=-8):
 pp=[]
 for a,b in seg:
  if a[1]<=ymax:pp.append(a)
  if b[1]<=ymax:pp.append(b)
  if (a[1]-ymax)*(b[1]-ymax)<0:pp.append(a+(b-a)*(ymax-a[1])/(b[1]-a[1]))
 q=np.array(pp);return {'x_min_mm':float(q[:,0].min()),'x_max_mm':float(q[:,0].max()),'width_mm':float(np.ptp(q[:,0])),'frontmost_Y_mm':float(q[:,1].min())}
sections=[]
for z in [4.,8.,12.,16.,20.,24.,28.]:
 a=front_extent(segments(raw,2,z));b=front_extent(segments(cur,2,z));sections.append({'height_Z_mm':z,'original':a,'v13':b,'width_change_mm':b['width_mm']-a['width_mm'],'left_boundary_X_change_mm':b['x_min_mm']-a['x_min_mm'],'right_boundary_X_change_mm':b['x_max_mm']-a['x_max_mm']})
zgrid=np.arange(2,34.001,.05);profiles={}
for name,tri in [('original',raw),('v13',cur)]:
 s=segments(tri,0,1e-6);yy=[]
 for z in zgrid:
  pts=[]
  for a,b in s:
   if min(a[2],b[2])<=z<=max(a[2],b[2]) and abs(b[2]-a[2])>1e-12:pts.append(float(a[1]+(b[1]-a[1])*(z-a[2])/(b[2]-a[2])))
  yy.append(min(pts) if pts else np.nan)
 profiles[name]=np.array(yy)
r={'head_stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'fixed_transform':'[X,Z,Y-18.16621208190918]*27.47544416498121, no fit','front_face_horizontal_sections':sections,'section_definition':'Intersection with Z=constant, only points Y<=-8mm retained to exclude posterior cranium/ear bulk; reported X extrema describe this explicitly clipped anterior-face section, not a whole-head or full cheek silhouette.','midline_profile':{'plane_X_mm':1e-6,'sample_Z_mm':zgrid.tolist(),'original_frontmost_Y_mm':[None if not np.isfinite(x) else float(x) for x in profiles['original']],'v13_frontmost_Y_mm':profiles['v13'].tolist(),'note':'Original gaps are retained as missing samples, not filled. Same fixed coordinate plane; nose/lips/chin profile without claiming anatomical point correspondence.'},'limitations':'Seven clipped horizontal sections and one sagittal profile are diagnostic curves, not every viewing silhouette or visual likeness certification.'}
(P/'face-contour-comparison.json').write_text(json.dumps(r,indent=2)+'\n')
fig,axs=plt.subplots(1,3,figsize=(16,8),constrained_layout=True);pts=d['points'];dist=d['distance_mm'];m=(pts[:,1]<-6)&(pts[:,2]<=35)&(abs(pts[:,0])<=24);ax=axs[0];h=ax.scatter(pts[m,0],pts[m,2],c=dist[m],s=1,cmap='magma',vmin=0,vmax=.4);ax.set(title='Original face samples → nearest v13 skin',xlabel='X mm',ylabel='Z mm');ax.set_aspect('equal');fig.colorbar(h,ax=ax,label='distance mm (color capped at0.4)')
ax=axs[1]
for name,color in [('original','#555555'),('v13','#00a2a0')]:ax.plot(profiles[name],zgrid,color=color,label=name)
ax.set(title='Actual midline skin profile',xlabel='Y mm (front is negative)',ylabel='Z mm');ax.set_aspect('equal');ax.legend();ax.grid(alpha=.3)
ax=axs[2]
for name,color in [('original','#555555'),('v13','#00a2a0')]:
 ax.plot([a[name]['x_min_mm'] for a in sections],[a['height_Z_mm'] for a in sections],'-o',color=color,label=name);ax.plot([a[name]['x_max_mm'] for a in sections],[a['height_Z_mm'] for a in sections],'-o',color=color)
ax.set(title='Anterior-face section edges (Y≤−8mm)',xlabel='X mm',ylabel='Z mm');ax.set_aspect('equal');ax.legend();ax.grid(alpha=.3)
fig.savefig(P/'face-audit-overview.png',dpi=150);print(json.dumps(sections,indent=2))
