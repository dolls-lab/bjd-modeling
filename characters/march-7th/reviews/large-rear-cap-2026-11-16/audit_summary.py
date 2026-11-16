"""Bind the three completed final independent audits to current files."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
CHAR=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for scale,version in [('1-4','v31-large-rear-cap'),('1-3','v15-large-rear-cap'),('1-6-special','v16-large-rear-cap')]:
 d=CHAR/scale/'versions'/version;p=json.loads((d/'parameters.json').read_text());source=CHAR/p['source_directory']
 path=HERE/f"audit-final-{p['version']}.json";a=json.loads(path.read_text());bp=HERE/f"audit-blend-{p['version']}.json";b=json.loads(bp.read_text())
 assert a['pass'] and b['pass']
 paths={'parameters':d/'parameters.json','head':d/p['output_files']['head'],'cap':d/p['output_files']['cap'],'source_head':source/p['source_files']['head'],'source_cap':source/p['source_files']['cap'],'source_reference':source/'geometry-stage.npz','source_motion':source/'assembly-final.json','source_parameters':source/'parameters.json','blend':d/p['output_files']['blend'],'blend_audit':bp}
 assert all(sha(f)==a['input_hashes'][k] for k,f in paths.items())
 assert a['audit_script_sha256']==sha(HERE/'audit_models.py') and b['audit_script_sha256']==sha(HERE/'audit_blend.py')
 for k in ['blend','head','cap','parameters']:assert b['input_hashes'][k]==sha(paths[k])
 rows.append({'version':p['version'],'model_sha256':{k:sha(paths[k]) for k in ['blend','head','cap']},'final_audit':path.name,'final_audit_sha256':sha(path),'saved_blend_audit':bp.name,'saved_blend_audit_sha256':sha(bp),'neck_max_vertex_error_mm':a['neck']['maximum_nearest_vertex_error_mm'],'face_ear_max_vertex_error_mm':a['protected_face_ears']['maximum_vertex_error_mm'],'exterior_samples_max_error_mm':a['exterior_samples']['maximum_error_mm'],'access_opening_area_ratio':a['access_opening']['area_ratio'],'main_access_opening_mm2':[a['access_opening'][k]['main_access_opening_area_mm2'] for k in ['old','new']],'old_new_cap_fraction_estimate':[a['cap_coverage'][k]['cap_fraction'] for k in ['old','new']],'head_cap_gap_mm':a['split']['actual_plane_gap_mm'],'minimum_magnet_sampled_wall_mm':min(q['minimum_sampled_radial_sidewall_mm'] for q in a['magnets']['pockets']),'minimum_magnet_axial_floor_mm':min(q['axial_floor_mm'] for q in a['magnets']['pockets']),'insertion_gap_mm':a['assembly']['insertion']['min_gap_mm'],'reference_assembly_pass':a['assembly']['pass'],'cap_removal_continuous_clear':a['assembly']['cap_removal']['continuous_clear'],'pass':True})
snapshot=json.loads((HERE/'audit-source-integrity-before.json').read_text());assert all(sha(CHAR/k)==v for k,v in snapshot.items())
report={'models':rows,'source_snapshot_file_count':len(snapshot),'source_snapshot_unchanged':True,'audit_scripts_sha256':{f:sha(HERE/f) for f in ['audit_blend.py','audit_models.py','audit_summary.py']},'pass':True,'limitations':['Digital mesh/path checks only; real magnets/glue, physical hook/body, elastic deformation, resin strength and print tolerances untested.','Exterior sampling excludes authorized old/new seam bands and does not claim every surface point was ray-tested.','Cap fraction is approximate outward-normal/radial area classification, not literal equal volume halves.']}
(HERE/'audit-final-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
