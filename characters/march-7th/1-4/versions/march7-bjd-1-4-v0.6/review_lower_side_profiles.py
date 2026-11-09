from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_side_shell import load,ROOT,BASE,OUT
paths={'v0.5':BASE/'march7-head-shell-v0.5-draft.stl','v0.6':ROOT/'march7-head-shell-v0.6-draft.stl'}
sha={v:hashlib.sha256(p.read_bytes()).hexdigest() for v,p in paths.items()}
solids={v:load(p) for v,p in paths.items()};results=[]
fig,axs=plt.subplots(1,3,figsize=(12,4))
for ax,y in zip(axs,[4,8,12]):
 profiles={}
 for ver,m in solids.items():
  rows=[]
  for z in np.arange(12,32.001,.1):
   hits=m.ray_cast([60,y,float(z)],[0,y,float(z)])
   if hits:rows.append([float(z),float(hits[0].position[0])])
  a=np.array(rows);profiles[ver]=rows;ax.plot(a[:,0],a[:,1],label=ver)
 ax.axvspan(12,24,color='gray',alpha=.10,label='lower transition region shown')
 a=np.array(profiles['v0.6']);slope=np.diff(a[:,1])/np.diff(a[:,0]);neg=slope<-.02
 results.append({'y_mm':y,'profiles_z_x_mm':profiles,'minimum_dx_dz':float(slope.min()),'descending_height_samples':a[:-1,0][neg].tolist()})
 ax.set(xlabel='Height Z (mm)',ylabel='Exterior X (mm)',title=f'Y={y} mm');ax.grid(alpha=.3);ax.legend(fontsize=8)
fig.suptitle('Lower side-skull profile: inspection for an unintended descending interval');fig.tight_layout();fig.savefig(OUT/'lower-side-profiles.png',dpi=160)
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha[v] for v,p in paths.items())
(OUT/'lower-side-profiles.json').write_text(json.dumps({'sources':{v:{'path':str(p),'sha256':sha[v]} for v,p in paths.items()},'units':'mm','method':'First positive-X surface ray intersection, step0.1mm in Z. Descending profile is descriptive, not a general anatomical error rule.','profiles':results},indent=2)+'\n')
print(json.dumps({'sha256':sha,'minimum_slopes':{r['y_mm']:r['minimum_dx_dz'] for r in results}},indent=2))
