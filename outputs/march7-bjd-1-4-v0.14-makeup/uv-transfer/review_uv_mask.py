"""Read-only numerical review of the final v14 preview UV/mask transfer."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image

R=Path(__file__).resolve().parent;P=R/'face-uv-transfer.npz'
BASE=R.parent.parent/'march7-bjd-1-4-v0.14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected='bdeb5b17f846945917660562ced8edf81c90b5fb90388a846e0989513694cb0b'
initial=sha(P);assert initial==expected
source_report=R/'uv-transfer-report.json';report_hash=sha(source_report)
meta=json.loads(source_report.read_text());d=np.load(P);final=np.load(BASE/'final-change-solution.npz')
v=d['head_vertices'];f=d['head_triangles'];w=d['head_vertex_makeup_weight'];cw=d['head_makeup_weight']
dist=d['head_source_distance_mm'];nd=d['head_source_normal_dot'];visible=d['head_source_outward_visible'];error=d['head_first_hit_error_mm']
old_ids=np.array([3504,48076,58806,67521,72735,73752,75481,75593,75751,77124,78413,79282,79284,79396,81983,82005,83776,86151,137444,138022,174795,176255,176812,179677,185966,186188,186192,186966,187199,190327,192253,192438,192630,194753,204663,205298,205429,205609,212380,212500])
# Same integer pixels as Blender's bottom-origin Image.pixels sampling.
texture=Path(meta['texture_path']);pixels=np.asarray(Image.open(texture).convert('RGBA'));H,W=pixels.shape[:2]
coords=[(int(u*(W-1)),H-1-int(vv*(H-1))) for u in np.linspace(.43,.57,17) for vv in np.linspace(.77,.82,11)]
samples=np.array([pixels[y,x,:3] for x,y in coords])/255.
srgb=np.median(samples,axis=0);linear=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
color={'texture_file':str(texture),'texture_sha256':sha(texture),'image_dimensions_px':[W,H],
       'sample_count':len(coords),'PIL_top_origin_pixel_bbox':[np.min(coords,axis=0).tolist(),np.max(coords,axis=0).tolist()],
       'original_forehead_srgb_8bit_median':(srgb*255).tolist(),'PIL_encoded_srgb_median':srgb.tolist(),
       'PIL_explicit_srgb_decode_linear':linear.tolist(),'final_npz_srgb':d['skin_base_srgb_rgb'].tolist(),
       'final_npz_linear':d['skin_base_linear_rgb'].tolist(),
       'max_srgb_error':float(np.max(np.abs(d['skin_base_srgb_rgb']-srgb))),
       'max_linear_error':float(np.max(np.abs(d['skin_base_linear_rgb']-linear))),
       'sample_region_review':'The sample rectangle lies on the large face atlas forehead skin, away from separate ear/eye/mouth texture islands.',
       'buffer_interpretation':'For this loaded 8-bit PNG, observed Blender Image.pixels values matched the encoded PIL sRGB samples, not linear values. The final NPZ explicitly decodes them before supplying a linear shader socket.'}
roi=(dist<.7)&(v[:,1]<-15)&(np.abs(v[:,0])<22)&(w<.9)
remaining={'definition':'source distance<0.7mm, worldY<-15mm, |X|<22mm, vertex mask<0.9; this includes sloping eye rims and some cavity-facing points, not only exterior cheeks.',
           'count':int(roi.sum()),'normal_dot_le0p05':int((roi&(nd<=.05)).sum()),
           'normal_dot_0p05_to_0p4':int((roi&(nd>.05)&(nd<.4)).sum()),
           'normal_dot_ge0p4':int((roi&(nd>=.4)).sum()),
           'normal_ge0p4_but_invisible':int((roi&(nd>=.4)&~visible).sum())}
recovered={'baseline_issue':'40 central face points had weight0 despite distance<0.7mm and normal agreement>=0.4, with NaN first_hit_error: exact-vertex ray misses rather than rejection at the0.12mm error threshold.',
           'previous_ids':old_ids.tolist(),'count':len(old_ids),'now_visible_count':int(visible[old_ids].sum()),
           'now_weight_exactly1_count':int((w[old_ids]==1).sum()),'largest_retried_hit_error_mm':float(error[old_ids].max()),
           'all_are_in_reported_recovered_ids':bool(set(old_ids).issubset(meta['ray_retry']['recovered_ids'])),
           'total_reported_recovered':meta['ray_retry']['recovered_vertices'],
           'samples':[{'vertex_id':int(i),'position_mm':v[i].tolist(),'weight':float(w[i]),'normal_dot':float(nd[i]),'source_distance_mm':float(dist[i]),'first_hit_error_mm':float(error[i])} for i in old_ids]}
normal=np.zeros_like(v);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
for k in range(3):np.add.at(normal,f[:,k],fn)
normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-30)
sv=d['source_vertices'];sf=d['source_triangles'];sn=np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]])
sn/=np.maximum(np.linalg.norm(sn,axis=1,keepdims=True),1e-30)
geom_dot=np.einsum('ij,ij->i',normal,sn[d['head_vertex_source_triangle']])
positive=w>0;rear=positive&(v[:,1]>4)
policy={'positive_vertices':int(positive.sum()),'weight_above0p99':int((w>.99).sum()),
        'positive_backfacing_by_source_smooth_normal_dot_le0p05':int((positive&(nd<=.05)).sum()),
        'positive_stored_occluded_vertices':int((positive&~visible).sum()),
        'positive_source_distance_ge4mm':int((positive&(dist>=4)).sum()),
        'positive_source_geometric_normal_dot_below_minus0p2':int((positive&(geom_dot<-.2)).sum()),
        'positive_source_geometric_normal_dot_below0':int((positive&(geom_dot<0)).sum()),
        'corner_weight_exceeds_original_vertex_weight':int((cw>w[f]+1e-7).sum()),
        'corner_weights_finite_and_in_0_1':bool(np.isfinite(cw).all() and cw.min()>=0 and cw.max()<=1),
        'corner_uvs_finite':bool(np.isfinite(d['head_uv_blender']).all()),
        'rear_y_above4_positive_count':int(rear.sum()),'rear_y_above4_maximum_weight':float(w[rear].max()) if rear.any() else 0,
        'rear_positive_bounds_mm':[v[rear].min(0).tolist(),v[rear].max(0).tolist()] if rear.any() else None,
        'interpretation':'No violation of the existing distance, normal and directional-visibility exclusion rules. Independent source-triangle geometric normals also reveal no strongly backfacing positive samples. The small rear-positive region is a weak ear-side fade, not central occipital projection. This is not an exhaustive global anatomical inner-wall classification.'}
geom={'head_vertices_exactly_equal_final_unpainted_solution':bool(np.array_equal(v,final['head_after'])),
      'head_triangles_exactly_equal_final_unpainted_solution':bool(np.array_equal(f,final['head_triangles'])),
      'maximum_coordinate_difference_mm':float(np.max(np.abs(v-final['head_after']))),
      'unpainted_solution_sha256':sha(BASE/'final-change-solution.npz'),
      'all_input_hashes_match_transfer_report':all(sha(Path(p))==h for p,h in meta['inputs'].items())}
assert sha(P)==initial and sha(source_report)==report_hash
result={'uv_npz_sha256':initial,'uv_npz_unchanged_during_review':True,'transfer_report_sha256':report_hash,
        'color_sampling':color,'previous_exact_vertex_ray_misses':recovered,'remaining_central_low_mask':remaining,
        'mask_exclusion_review':policy,'geometry_integrity':geom,
        'assessment':'Corrected linear skin base agrees with the same PIL samples; all40 diagnosed central exact-vertex ray misses recovered to weight1; no high-normal unexplained holes remain in the tested central ROI. Normal/distance/visibility exclusions remain in force. Preview geometry is exactly unchanged.',
        'limitations':['No structure, print-fit or wall-thickness QA was repeated for this material-only preview.',
                       'Eyebrow/eyelash source geometry is separate from face skin UV; remaining eye-rim normal fades were deliberately not widened or filled.',
                       'This numeric mask review does not certify reproduction of game lighting/shading or physical makeup/printing colors.']}
(R/'uv-mask-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'npz_sha256':initial,'all40_recovered':recovered['now_weight_exactly1_count']==40,'remaining_central_high_normal_holes':remaining['normal_dot_ge0p4'],'policy':policy,'geometry':geom,'color_error':color['max_linear_error'],'report':str(R/'uv-mask-review.json')},indent=2))
