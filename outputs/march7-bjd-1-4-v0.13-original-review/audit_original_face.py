"""Read-only PMX face-material vs actual final v13 STL; fixed historical transform.
Run with Blender --background --factory-startup --python THIS_FILE.
No model is opened/saved or altered. No registration/normalization/refitting.
"""
from pathlib import Path
import sys,json,hashlib,heapq
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;V=P.parent/'march7-bjd-1-4-v0.13';sys.path.insert(0,str(P))
from parse_pmx import load_pmx,topology
params=json.loads((V/'parameters.json').read_text());pmx=Path(params['source_pmx']);stl=V/'march7-head-shell-v0.13-draft.stl';blend=V/'march7-bjd-head-v0.13-draft.blend';S=27.47544416498121;CHIN=18.16621208190918
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={k:sha(v) for k,v in [('pmx',pmx),('head_stl',stl),('blend',blend)]}
assert hashes['head_stl']=='a382b257380f066a1e616298d869e88a5f6c39ffa208c962383c3db8949b6c9d'
assert hashes['blend']=='20ef80dfb192116a10e61da95f981e5b27bb7bde0f0e0cec4227258c839d4a56'
src=load_pmx(pmx);mat=next(m for m in src['materials'] if m['name']=='脸');fs=src['faces'][mat['start']:mat['end']];top,raw,f=topology(src['vertices'],fs);v=np.column_stack([raw[:,0],raw[:,2],raw[:,1]-CHIN])*S
# Swapping PMX Y/Z reverses orientation; reverse triangle corner order as in original import.
f=f[:,::-1];rt=v[f];cross=np.cross(rt[:,1]-rt[:,0],rt[:,2]-rt[:,0]);area=np.linalg.norm(cross,axis=1)/2;rn=cross/np.maximum(2*area[:,None],1e-15)
loops=top['boundary_loops'];eyeloops=[l for l in loops if l['vertex_count']==31];mouth=next(l for l in loops if l['vertex_count']==44);outer=next(l for l in loops if l['vertex_count']==56)
adj=[{} for _ in v]
for t in f:
 for a,b in zip(t,np.roll(t,-1)):
  w=float(np.linalg.norm(v[a]-v[b]));adj[a][int(b)]=w;adj[b][int(a)]=w
def geod(ids):
 d=np.full(len(v),np.inf);heap=[]
 for i in ids:d[i]=0;heapq.heappush(heap,(0,int(i)))
 while heap:
  dd,i=heapq.heappop(heap)
  if dd>d[i]+1e-10:continue
  for j,w in adj[i].items():
   q=dd+w
   if q<d[j]:d[j]=q;heapq.heappush(heap,(q,j))
 return d
ed=geod([i for l in eyeloops for i in l['vertex_ids']]);md=geod(mouth['vertex_ids']);od=geod(outer['vertex_ids'])
rawbytes=stl.read_bytes();count=int.from_bytes(rawbytes[80:84],'little');assert len(rawbytes)==84+count*50
dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);tt=np.frombuffer(rawbytes,dtype=dt,offset=84,count=count)['vertices'].astype(float);tv,ti=np.unique(tt.reshape(-1,3),axis=0,return_inverse=True);tf=ti.reshape(-1,3)
tree=BVHTree.FromPolygons(tv.tolist(),tf.tolist(),all_triangles=True);rawtree=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
def query(points,t=tree):
 near=[];dist=[];normal=[];face=[]
 for p in points:
  q,n,i,d=t.find_nearest(Vector(p));near.append(q);dist.append(d);normal.append(n);face.append(i)
 return np.array(near),np.array(dist),np.array(normal),np.array(face)
def masks(points,eye,mouth,outer):
 x,y,z=points.T;ax=abs(x)
 return {'all_original_face_material_including_ears':np.ones(len(points),bool),'principal_front_face_below_Z35':(ax<=24)&(y<-6)&(z<=35),'nose':(ax<=5)&(z>=13)&(z<=27)&(y<-12),'mouth_skin_2mm_geodesic_band':mouth<=2,'chin':(z<=8)&(y<-5),'main_cheeks':(ax>=7)&(ax<=21)&(z>=8)&(z<=25)&(y<-8),'left_cheek_negative_X':(x<=-7)&(x>=-21)&(z>=8)&(z<=25)&(y<-8),'right_cheek_positive_X':(x>=7)&(x<=21)&(z>=8)&(z<=25)&(y<-8),'original_eye_skin_2mm_band':eye<=2,'central_forehead_Z35_to45':(ax<=16)&(z>=35)&(z<=45)&(y<-12),'temple_nonfeature_skin':(ax>=18)&(z>=23)&(z<=45)&(y<-6),'high_forehead_Z45_plus':(z>=45)&(y<-6)}
def stats(a,weights=None):
 a=np.asarray(a,float)
 if not len(a):return {'count':0}
 w=np.ones(len(a)) if weights is None else np.asarray(weights,float);order=np.argsort(a);aa=a[order];ww=w[order];c=(np.cumsum(ww)-ww/2)/ww.sum();q=lambda t:float(np.interp(t,c,aa))
 return {'count':len(a),'mean_mm':float(np.average(a,weights=w)),'median_mm':q(.5),'p95_mm':q(.95),'max_mm':float(a.max()),'sample_weight_sum':float(w.sum())}
# Area-proportional deterministic stratified random samples cover face interiors,
# not just low-poly source vertices. Weights sum exactly to source triangle area.
rng=np.random.default_rng(73113);samples=[];barys=[];faceids=[];weights=[]
for i,(tri,a) in enumerate(zip(rt,area)):
 n=max(3,int(np.ceil(a/.08)));q=rng.random((n,2));sq=np.sqrt(q[:,0]);b=np.column_stack([1-sq,sq*(1-q[:,1]),sq*q[:,1]]);samples.append(b@tri);barys.append(b);faceids.extend([i]*n);weights.extend([a/n]*n)
points=np.concatenate(samples);barys=np.concatenate(barys);faceids=np.array(faceids);weights=np.array(weights);se=np.einsum('ij,ij->i',barys,ed[f[faceids]]);sm=np.einsum('ij,ij->i',barys,md[f[faceids]]);so=np.einsum('ij,ij->i',barys,od[f[faceids]])
nearest,dist,normal,which=query(points);regions=masks(points,se,sm,so);vnear,vd,vnorm,vwhich=query(v);vregions=masks(v,ed,md,od)
region_stats={}
for name,mask in regions.items():
 ids=np.flatnonzero(mask);worst=ids[np.argsort(dist[ids])[-5:][::-1]] if len(ids) else []
 region_stats[name]={'source_surface_area_weighted':stats(dist[mask],weights[mask]),'source_vertices':stats(vd[vregions[name]]),'maximum_over_source_vertices_and_surface_samples_mm':float(max(dist[mask].max(),vd[vregions[name]].max())) if mask.any() and vregions[name].any() else None,'source_samples_bounds_mm':[points[mask].min(0).tolist(),points[mask].max(0).tolist()] if mask.any() else None,'worst_surface_samples':[{'source_triangle':int(faceids[i]),'source_point_mm':points[i].tolist(),'closest_final_surface_mm':nearest[i].tolist(),'nearest_distance_mm':float(dist[i])} for i in worst]}
print('forward samples',len(points),flush=True)
# Reverse direction: area-weighted centroids of actual triangles on the front
# exterior, selected by source normal agreement, never by a distance cutoff.
tc=tt.mean(1);cross2=np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]);ta=np.linalg.norm(cross2,axis=1)/2;tn=cross2/np.maximum(2*ta[:,None],1e-15);candidate=np.flatnonzero((tc[:,1]<-6)&(tc[:,2]<=45)&(abs(tc[:,0])<=26));reverse_rows={k:[] for k in regions};reverse_weights={k:[] for k in regions};rejected=0
for i in candidate:
 # Restrict reverse audit to visible front skin in the original occupied XZ footprint.
 # This rejects inner cavity/neck returns and new material filling original openings.
 origin=Vector(tc[i]+[0.,-100.,0.]);direct=Vector((0.,1.,0.))
 hit,_,_,_=tree.ray_cast(origin,direct,100.05)
 rawhit,_,_,_=rawtree.ray_cast(origin,direct,200.)
 if hit is None or rawhit is None or np.linalg.norm(np.array(hit)-tc[i])>.01:rejected+=1;continue
 q,n,j,d=rawtree.find_nearest(Vector(tc[i]));q=np.array(q)
 if float(np.dot(n,tn[i]))<.25:rejected+=1;continue
 tr=rt[j];aa=tr[1]-tr[0];bb=tr[2]-tr[0];pp=q-tr[0];M=np.array([[aa@aa,aa@bb],[aa@bb,bb@bb]])
 if abs(np.linalg.det(M))<1e-18:b=np.array([1.,0,0])
 else:
  beta,gamma=np.linalg.solve(M,np.array([aa@pp,bb@pp]));b=np.maximum([1-beta-gamma,beta,gamma],0);b/=b.sum()
 region=masks(q[None],np.array([b@ed[f[j]]]),np.array([b@md[f[j]]]),np.array([b@od[f[j]]]))
 for name,mask in region.items():
  if mask[0]:reverse_rows[name].append(float(d));reverse_weights[name].append(float(ta[i]))
reverse={k:stats(a,reverse_weights[k]) for k,a in reverse_rows.items()}
# Original nose/chin extrema and mouth boundary queried separately; these are
# nearest-point matches, not identified semantic landmark correspondences.
landmarks={}
for name,region,axis,direction in [('nose_tip',vregions['nose'],1,-1),('chin_bottom',vregions['chin'],2,-1)]:
 ids=np.flatnonzero(region);idx=ids[np.argmin(v[ids,axis]*(-direction))];landmarks[name]={'source_vertex':int(idx),'source_mm':v[idx].tolist(),'closest_final_mm':vnear[idx].tolist(),'delta_xyz_mm':(vnear[idx]-v[idx]).tolist(),'distance_mm':float(vd[idx]),'meaning':'Closest final surface point to original extremum; not a semantically matched final landmark.'}
curves={}
for name,loop in [('original_mouth_boundary',mouth),('original_eye_negative',min(eyeloops,key=lambda l:np.mean(v[l['vertex_ids'],0]))),('original_eye_positive',max(eyeloops,key=lambda l:np.mean(v[l['vertex_ids'],0])))]:
 vv=v[loop['vertex_ids']];pp=[];ww=[]
 for a,b in zip(vv,np.roll(vv,-1,axis=0)):
  length=np.linalg.norm(a-b);n=max(1,int(np.ceil(length/.1)));pp.extend(a+(b-a)*((np.arange(n)+.5)/n)[:,None]);ww.extend([length/n]*n)
 pp=np.array(pp);q,dd,nn,jj=query(pp);curves[name]={'source_vertices':len(vv),'perimeter_mm':float(np.sum(ww)),'source_3D_boundary_to_any_final_skin':stats(dd,ww),'meaning':'Distance to nearest final skin, not to corresponding final aperture edge. Actual eye aperture outline is measured separately in eye-original-comparison.json.'}
report={'comparison':'Original PMX face material directly versus final v13 actual PRINT STL','units':'mm','files':{'pmx':{'path':str(pmx),'sha256':hashes['pmx']},'head_stl':{'path':str(stl),'sha256':hashes['head_stl']},'blend_identity_only':{'path':str(blend),'sha256':hashes['blend']}},'source_material':mat,'source_welded_vertices':len(v),'source_triangles':len(f),'current_triangles':len(tf),'fixed_transform':{'formula':'[sourceX, sourceZ, sourceY - 18.16621208190918] * 27.47544416498121','scale_mm':S,'offset_sourceY':CHIN,'fit_or_registration_performed':False},'area_samples':{'count':len(points),'maximum_mean_area_per_sample_mm2':.08,'seed':73113,'total_original_material_area_mm2':float(area.sum()),'weighting':'Each triangle contributes its exact area divided among its deterministic samples; region medians/p95 are area-weighted, maxima are sampled.'},'source_to_final_surface':region_stats,'final_front_exterior_to_original_surface':reverse,'reverse_scope':{'actual_triangle_centroids_examined':len(candidate),'normal_rejected_inner_or_back':rejected,'gate':'Current Y<-6,Z<=45,|X|<=26. Actual triangle centroid must be frontmost along+Y within0.01mm and original PMX material must occupy that XZ ray. Nearest original face normal dot current normal>=.25; source-coordinate region membership; no distance cutoff. Thus new fill in original holes and internal cavity/neck returns are excluded; their mismatches are not mislabeled facial skin.'},'source_landmark_queries':landmarks,'source_boundary_queries':curves,'region_definitions':{'nose':'|X|<=5,13<=Z<=27,Y<-12','mouth':'Original44-edge mouth boundary surface geodesic<=2mm','chin':'Z<=8,Y<-5','cheeks':'7<=|X|<=21,8<=Z<=25,Y<-8','eye_skin':'Geodesic<=2mm from original31-edge main eye loops; original small8-edge lid slits are not main-eye loops','principal_face':'|X|<=24,Y<-6,Z<=35','forehead':'Explicit geometric bands; these were intentionally remodeled and are not asserted original.'},'interpretation':'These are direct geometric differences, not a likeness score or corresponding-vertex motion. Earlier0-motion protection does not prove raw PMX agreement. Original low-poly face, mouth/eyelid closure, subdivision/fairing and print conversion can all contribute.','limitations':['Original face material is an open face-and-ear patch; no original complete skull or removable cap exists for a whole-head comparison.','Median/p95 are sampling distributions; sampled maxima are not a certified continuous Hausdorff bound.','Nearest surface can slide tangentially; it can understate an aperture-edge shift. Eye outline is compared independently by same-depth projection.','Original PMX material, UV textures, eyelashes/eyebrows/eye whites/eyeballs and hair affect perceived likeness but are excluded from this face-skin geometry comparison.','No claim of exact source identity or unchanged facial sculpt is inferred from historical version-to-version locks.']}
assert all(sha(path)==hashes[k] for k,path in [('pmx',pmx),('head_stl',stl),('blend',blend)])
report['all_input_hashes_unchanged']=True
(P/'face-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
np.savez_compressed(P/'face-distance-samples.npz',points=points,distance_mm=dist,nearest_final=nearest,weights_mm2=weights,source_vertices=v,source_faces=f,source_vertex_distance_mm=vd)
print(json.dumps({'output':str(P/'face-audit.json'),'regions':{k:v['source_surface_area_weighted'] for k,v in region_stats.items()},'reverse':reverse,'landmarks':landmarks},ensure_ascii=False,indent=2),flush=True)
