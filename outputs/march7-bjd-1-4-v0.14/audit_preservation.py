"""Read-only saved-v14 actual geometry, feature/crown protection and oriented STL audit."""
from pathlib import Path
import bpy,numpy as np,json,hashlib
R=Path(__file__).resolve().parent;OLD=R.parent/'march7-bjd-1-4-v0.13';BASE=OLD/'march7-bjd-head-v0.13-draft.blend';FINAL=R/'march7-bjd-head-v0.14-draft.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files={'baseline_blend':BASE,'final_blend':FINAL,'head_stl':R/'march7-head-shell-v0.14-draft.stl','cap_stl':R/'march7-head-cap-v0.14-draft.stl','solution':R/'final-change-solution.npz','parameters':R/'parameters.json','build_report':R/'build-report.json','eye_solution':R/'eye-postprocess/eye-solution.npz','crown_solution':R/'crown-postprocess/crown-solution.npz'}
hashes={k:sha(p) for k,p in files.items()}
with np.load(files['solution']) as a:s={k:a[k] for k in a.files}
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));out={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();out[o.name]={'v':np.array([o.matrix_world@p.co for p in o.data.vertices]),'f':np.array([t.vertices[:] for t in o.data.loop_triangles],np.int32)}
 return out
b=snapshot(BASE);c=snapshot(FINAL);checks={'same_mesh_names':set(b)==set(c)};stats={};details={}
N=np.array([0.,1.,.3]);N/=np.linalg.norm(N);V=np.array([0.,N[2],-N[1]]);O=np.array([0.,14.5,50.]);P=np.array([0.,11.274858474731445,60.75047302246094]);PV=np.sum((P-O)*V)
for tag,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
 v=b[name]['v'];a=c[name]['v'];f=b[name]['f'];d=a-v;length=np.linalg.norm(d,axis=1)
 checks[tag+'_same_topology']=np.array_equal(f,c[name]['f']);checks[tag+'_solution_before_exact']=np.array_equal(v,s[tag+'_before']);checks[tag+'_solution_saved_after_exact']=np.array_equal(a,s[tag+'_after']);checks[tag+'_outside_union_support_exact']=np.array_equal(a[s[tag+'_locked']],v[s[tag+'_locked']])
 crown=s[tag+'_crown_free'];checks[tag+'_crown_YZ_exact']=np.array_equal(a[crown,1:],v[crown,1:]);checks[tag+'_maximum_Z_exact']=float(a[:,2].max())==float(v[:,2].max())
 if tag=='head':
  checks['eye_and_crown_disjoint']=not np.any(s['head_eye_free']&crown);checks['crown_stage_below_z48_exact']=np.array_equal(s['head_after_target'][v[:,2]<=48],s['head_eye_after_target'][v[:,2]<=48])
 q=v-O;normal=q[:,1]*N[1]+q[:,2]*N[2];tangent=q[:,1]*V[1]+q[:,2]*V[2];rm=np.minimum(np.hypot(v[:,0]-16.63362693786621,tangent),np.hypot(v[:,0]+16.63362693786621,tangent));rp=np.hypot(v[:,0],tangent-PV)
 masks={'actual_magnet_recess_cylinders_r2p30_depth2p65':(rm<=2.30)&(abs(normal)<=2.65),'actual_rear_pin_or_bore_r2p40_depth_minus1p10_to4p20':(rp<=2.40)&(normal>=-1.10)&(normal<=4.20),'neck_seat_platform_and_lower_mechanics':(v[:,2]<21)&(v[:,1]>-5),'non_eye_low_face_and_ears':(v[:,2]<=40)&(~s['head_eye_free'] if tag=='head' else np.ones(len(v),bool))}
 for key,m in masks.items():
  details[tag+'_'+key]={'vertices':int(m.sum()),'moved':int((length[m]>0).sum()),'max_mm':float(length[m].max()) if m.any() else 0.};checks[tag+'_'+key+'_exact']=bool(np.array_equal(a[m],v[m]))
 stats[tag]={'changed_vertices':int((length>0).sum()),'max_displacement_mm':float(length.max()),'crown_max_abs_X_mm':float(abs(d[crown,0]).max()),'bounds_before_mm':np.ptp(v,axis=0).tolist(),'bounds_after_mm':np.ptp(a,axis=0).tolist(),'minmax_Z_before_after':[float(v[:,2].min()),float(v[:,2].max()),float(a[:,2].min()),float(a[:,2].max())]}
others={}
for name in sorted(set(b)-{'PRINT_01_Head_Shell','PRINT_02_Removable_Cap'}):
 ok=np.array_equal(b[name]['v'],c[name]['v']) and np.array_equal(b[name]['f'],c[name]['f']);others[name]=ok;checks[name+'_historical_or_reference_geometry_unchanged']=ok

def sorted_tri(t):
 r=t[np.arange(len(t))[:,None],(np.argmin(t,axis=1)[:,None]+np.arange(3))%3];return r[np.lexsort((r[:,2],r[:,1],r[:,0]))]
def stl_equal(path,obj):
 data=path.read_bytes();n=int.from_bytes(data[80:84],'little');assert len(data)==84+n*50;dt=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);q=np.frombuffer(data,dtype=dt,offset=84,count=n)['vertices'].reshape(-1,3);sv,si=np.unique(q,axis=0,return_inverse=True);vv,vi=np.unique(obj['v'].astype(np.float32),axis=0,return_inverse=True);pos=np.array_equal(sv,vv);tri=pos and np.array_equal(sorted_tri(si.reshape(-1,3)),sorted_tri(vi[obj['f']]));return {'triangles':n,'unique_float32_vertices_exact':pos,'oriented_triangle_multiset_exact':tri,'pass':pos and tri}
exports={}
for tag,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
 exports[tag]=stl_equal(files[tag+'_stl'],c[name]);checks[tag+'_STL_exactly_matches_saved_Blend']=exports[tag]['pass']

def width(v,f,z,front_only=False):
 t=v[f];t=t[(t[:,:,2].min(1)<=z)&(t[:,:,2].max(1)>z)];points=[]
 for i,j in [(0,1),(1,2),(2,0)]:
  a=t[:,i];bb=t[:,j];ok=((a[:,2]<=z)&(bb[:,2]>z))|((bb[:,2]<=z)&(a[:,2]>z));a=a[ok];bb=bb[ok];p=a+(z-a[:,2])[:,None]/(bb[:,2]-a[:,2])[:,None]*(bb-a)
  if front_only:p=p[p[:,1]<=-6]
  points.append(p)
 p=np.concatenate(points);return float(np.ptp(p[:,0]))
face=[];head='PRINT_01_Head_Shell'
for z in [5,10,15,20,25,30,35,40,45]:
 w0=width(b[head]['v'],b[head]['f'],z,True);w1=width(c[head]['v'],c[head]['f'],z,True);face.append({'z_mm':z,'before_mm':w0,'after_mm':w1,'difference_mm':w1-w0})
checks['frontal_face_width_sections_unchanged']=max(abs(a['difference_mm']) for a in face)<1e-6
crown_width=[]
for z in [48,50,55,60,65,67,69]:
 w0=width(b[head]['v'],b[head]['f'],z);w1=width(c[head]['v'],c[head]['f'],z);crown_width.append({'z_mm':z,'before_mm':w0,'after_mm':w1,'per_side_gain_mm':(w1-w0)/2})
checks['all_input_hashes_unchanged']=all(sha(p)==hashes[k] for k,p in files.items())
r={'version':'v0.14-draft','files':{k:{'path':str(p),'sha256':hashes[k]} for k,p in files.items()},'checks':checks,'all_integrity_checks_pass':all(checks.values()),'parts':stats,'protected_actual_regions':details,'other_mesh_geometry':others,'stl_correspondence':exports,'face_width_sections':{'definition':'Horizontal sections of actual head surface; extrema restricted to Y<=-6 mm to exclude ear and rear skull. Eye apertures may change but external facial widths stay fixed.','measurements':face},'crown_width_sections':crown_width,'scope':'Actual saved v13/v14 world-coordinate comparison, same topology, independent oriented STL verification. Crown-only Y/Z and low-Z preservation are separate from authorized eye changes. Cap is changed by crown mapping and is NOT claimed unchanged.','limitations':'Mechanical ROIs use the actual original pin/recess center, radius and depth; this coordinate check supplements final assembly/eye-volume/mesh validation and is not a physical fit test. Former pre-hollow mother is historical reference only.'}
(R/'preservation-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'all_integrity_checks_pass':r['all_integrity_checks_pass'],'failed':[k for k,v in checks.items() if not v],'files':r['files']},indent=2),flush=True)
