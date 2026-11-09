from pathlib import Path
import bpy,numpy as np,json,hashlib
P=Path(__file__).resolve().parent;B=P.parent.parent/'march7-bjd-1-4-v0.14'/'march7-bjd-head-v0.14-draft.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p):sha(p) for p in [B,P/'face-uv-transfer.npz']}
bpy.ops.wm.open_mainfile(filepath=str(B));o=bpy.data.objects['PRINT_01_Head_Shell'];m=o.data;m.calc_loop_triangles();u=np.load(P/'face-uv-transfer.npz');f=np.array([t.vertices[:] for t in m.loop_triangles]);assert np.array_equal(f,u['head_triangles'])
loops=np.array([t.loops[:] for t in m.loop_triangles]);flat=loops.ravel();v=u['head_uv_blender'].reshape(-1,2);w=u['head_makeup_weight'].ravel();n=len(m.loops)
counts=np.bincount(flat,minlength=n);minuv=np.full((n,2),np.inf);maxuv=np.full((n,2),-np.inf);minw=np.full(n,np.inf);maxw=np.full(n,-np.inf)
np.minimum.at(minuv,flat,v);np.maximum.at(maxuv,flat,v);np.minimum.at(minw,flat,w);np.maximum.at(maxw,flat,w)
duv=np.linalg.norm(maxuv-minuv,axis=1);dw=maxw-minw
uvconf=np.flatnonzero(duv>1e-6);wconf=np.flatnonzero(dw>1e-6);positive=np.flatnonzero((duv>1e-6)&(maxw>.01))
records=[]
for li in positive[:50]:
 pairs=np.argwhere(loops==li);polyids=[int(m.loop_triangles[int(ti)].polygon_index) for ti,k in pairs];records.append({'loop':int(li),'vertex':int(m.loops[li].vertex_index),'position_mm':list(m.vertices[m.loops[li].vertex_index].co),'triangle_corner_pairs':pairs.tolist(),'polygon_ids':polyids,'uvs':[u['head_uv_blender'][ti,k].tolist() for ti,k in pairs],'weights':[float(u['head_makeup_weight'][ti,k]) for ti,k in pairs],'uv_difference':float(duv[li]),'weight_difference':float(dw[li])})
r={'inputs':hashes,'input_hashes_unchanged':all(sha(Path(p))==h for p,h in hashes.items()),'polygons':len(m.polygons),'loop_triangles':len(m.loop_triangles),'corners':n,'duplicate_loop_indices_count':int((counts>1).sum()),'triangle_order_matches_transfer':True,'uv_conflicts_gt1e_6':len(uvconf),'positive_weight_uv_conflicts_gt1e_6':len(positive),'weight_conflicts_gt1e_6':len(wconf),'maximum_uv_difference':float(duv.max()),'maximum_weight_difference':float(dw.max()),'positive_conflicts':records,'pass_no_positive_uv_conflict':len(positive)==0,'note':'Read-only actual v14 mesh loop-triangle audit. Repeat loop values on non-triangular polygons are compared before assigning each polygon loop. No UV data or models are changed.'}
(P/'loop-uv-conflict-review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['inputs','positive_conflicts']},ensure_ascii=False),flush=True)
