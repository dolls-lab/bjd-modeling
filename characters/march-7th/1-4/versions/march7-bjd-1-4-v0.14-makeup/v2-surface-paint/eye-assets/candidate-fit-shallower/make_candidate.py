from pathlib import Path
import numpy as np,json,hashlib,shutil
P=Path(__file__).resolve().parent;B=P.parent/'baseline-r8';d=np.load(B/'hemisphere-eye-geometry.npz');a={k:d[k].copy() for k in d.files}
for side,sign in [('negative',-1),('positive',1)]:
 old=a['center_'+side].copy();center=old+np.array([-sign*1.5,-1.,0.]);v=a['vertices_'+side];q=v-old;r=np.linalg.norm(q,axis=1);newr=np.where(r>7.7,9.,8.4);after=center+q*(newr/r)[:,None]
 a['vertices_'+side]=after;a['center_'+side]=center
 # Retain iris position/size in world XZ, independent of the adapted sphere center.
 a['uv_'+side]=np.c_[.5+(after[:,0]-old[0])/16,.5+(after[:,2]-old[2])/16].astype(np.float32)
 shutil.copy2(B/f'march7-hemisphere-eye-{side}.png',P/f'march7-hemisphere-eye-{side}.png')
np.savez_compressed(P/'hemisphere-eye-geometry.npz',**a)
r=json.loads((B/'eye-assets-report.json').read_text());r['outer_radius_mm']=9.;r['inner_radius_mm']=8.4;r['eye_centers_mm']={s:a['center_'+s].tolist() for s in ['negative','positive']};r['candidate_only']=True;r['fit_adjustment']={'nasal_shift_mm':1.5,'forward_shift_mm':1.,'old_radius_mm':8.,'new_radius_mm':9.,'purpose':'Fill actual ±34.4-degree eye windows; head remains untouched. Potential hidden socket overlap requires final render review.'};r['geometry_npz_sha256']=hashlib.sha256((P/'hemisphere-eye-geometry.npz').read_bytes()).hexdigest();(P/'eye-assets-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
s=(B/'build_hemisphere_eyes.py').read_text().replace("ob['outer_radius_mm']=8.;ob['inner_radius_mm']=7.4", "ob['outer_radius_mm']=9.;ob['inner_radius_mm']=8.4").replace("'outer_radius_mm':8.,'inner_radius_mm':7.4", "'outer_radius_mm':9.,'inner_radius_mm':8.4")
(P/'build_hemisphere_eyes.py').write_text(s)
print(r['geometry_npz_sha256'])
