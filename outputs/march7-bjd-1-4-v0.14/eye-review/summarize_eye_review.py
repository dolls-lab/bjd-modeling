"""Collect the one final eye-QA report set; never reruns geometry checks."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;M=R.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'head':'d3ac436defacb1db2a9aca6da84b8e6f4fe3ee995591e095e5ac43b9624b7ada','cap':'83ee07951213b490a5203cd0a5663a4033c98d5f24131bd720559543a4cf824a','blend':'cdb0839449d64a6867cae512fef653a1221315ab97c70b1a8e554a4aa232f96a','solution':'95277810376106c2bb776efa342233719024690e8a24278554ad2945c936aa92'}
paths={'head':M/'march7-head-shell-v0.14-draft.stl','cap':M/'march7-head-cap-v0.14-draft.stl','blend':M/'march7-bjd-head-v0.14-draft.blend','solution':M/'final-change-solution.npz'}
files={k:{'path':str(p),'sha256':sha(p)} for k,p in paths.items()}
assert all(files[k]['sha256']==expected[k] for k in files)
names=['eye-original-comparison.json','eye-section-and-residual-review.json','eye-endpoint-check.json','eye-insertion-check.json','eye-local-intersection-check.json','eye-wall-chord-review.json']
a,s,e,p,i,w=[json.loads((R/name).read_text()) for name in names]
assert a['sources']['print_stl']['sha256']==expected['head'] and a['sources']['print_stl']['unchanged_during_check']
assert s['input_integrity']['head_sha256']==expected['head'] and s['input_unchanged']
assert e['head_sha256']==expected['head'] and e['input_unchanged']
assert p['head_shell_sha256']==expected['head'] and p['input_integrity']['unchanged']
assert i['actual_stl_sha256']==expected['head'] and i['input_unchanged']
assert w['actual_stl_sha256']==expected['head'] and w['input_unchanged']
summary={'version':'v0.14-draft','scope':'Final combined actual head eye-region review. Cap/Blend hashes identify the matching artifact set; cap assembly and Blend/STL equivalence are checked separately by other reviewers.','files':files,'all_eye_reports_bind_final_combined_head':True}
summary['raw_pmx_source']=a['sources']['raw_pmx']
summary['eye_projection']={'pitch_mm':a['sample_pitch_mm'],'fixed_transform':a['fixed_transform'],'eyes':[{'eye_id':q['eye_id'],'metrics':q['metrics'],'changes':q['changes_print_minus_raw'],'boundary_nearest_distances':q['projected_boundary_nearest_distances']} for q in a['eyes']],'pair_spacing':a['pair_spacing'],'distance_definition':a['eye_distance_definition']}
summary['rim_sections']=[{k:q[k] for k in ['name','raw_rim_to_v14_nearest','baseline_raw_rim_nearest']} for q in s['sections'][:3]]
summary['largest_remaining_radial_deficits']=[q['worst_deficits'][0] for q in s['eyes']]
summary['intersection']={k:i[k] for k in ['changed_vertices','changed_triangles','candidate_region_triangles','nonadjacent_aabb_pairs','new_strict_intersections','new_ambiguous_contacts','degenerate_triangles']}
summary['intersection']['normal_over90_count']=len(i['normal_over90'])
summary['intersection']['scope']=i['scope']
summary['intersection']['shared_vertex_limitation']='General scan excludes pairs sharing any exact vertex. Normal-rotation faces receive supplemental shared-one-vertex/shared-edge checks; final normal-rotation count is0.'
summary['stationary_eye_spheres']={'pass':e['pass'],'eyes':e['eyes'],'enclosure':e['ball_enclosure']}
summary['continuous_insertion']={'pass':p['pass'],'selected_paths':[q['selected_path'] for q in p['eyes']],'limitations':p['limitations']}
summary['paired_local_wall_chords']={k:{field:value for field,value in q.items() if field not in ('worst_reductions','smallest_candidate_chords')} for k,q in w['groups'].items()}
summary['thin_edge_witness']=next(q for q in w['groups']['outer_corner']['smallest_candidate_chords'] if q['vertex_id']==205441)
summary['wall_measurement_limitations']=w['limitations']
summary['assessment']='Final projected main apertures closely follow raw PMX, with 0.05mm raster boundary discrepancy and maximum sampled continuous radial deficit0.0623mm; this is not exact identity. Eye-sphere seat and tested continuous paths pass; no new local nonadjacent intersections or normal rotations beyond90 degrees. Outer corner normal-ray chords include values around0.5mm and reductions versus v13; those observations are retained without claiming physical print strength or global wall-thickness certification.'
summary['artifacts']={name:{'path':str(R/name),'sha256':sha(R/name)} for name in names+['eye-original-comparison.png','eye-section-comparison.png']}
(R/'eye-review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'reports':names,'summary':str(R/'eye-review-summary.json'),'head_sha256':expected['head'],'insertion_pass':p['pass'],'endpoint_pass':e['pass'],'new_intersections':i['new_strict_intersections'],'normal_rotations_over90':len(i['normal_over90'])},indent=2))
