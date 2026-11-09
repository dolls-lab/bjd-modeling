from pathlib import Path
import importlib.util,json,hashlib,time
import numpy as np
R=Path(__file__).resolve().parent
P=R.parent/'march7-head-shell-v0.14-draft.stl'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from final_eye_inputs import expected_head
h=sha(P);assert h==expected_head()
script=R/'check_eye_insertion.py'
spec=importlib.util.spec_from_file_location('readonly_eye_geometry',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
report=json.loads((R.parent/'build-report.json').read_text())
solid=m.load_solid(P);ball,info=m.enclosing_ball(8.)
rows=[]
for c in report['eye_centers_mm']:
 placed=ball.translate(c);overlap=solid^placed;volume=float(overlap.volume())
 row={'center_mm':c,'overlap_volume_mm3':volume,'overlap_empty':overlap.is_empty(),'overlap_status':str(overlap.status()),'minimum_gap_mm_search_limit1':float(solid.min_gap(placed,1.)),'pass':abs(volume)<=1e-5}
 rows.append(row);print(json.dumps(row),flush=True)
after=sha(P);assert after==h
out={'head_sha256':h,'sha256_after':after,'input_unchanged':True,'ball_enclosure':info,'eyes':rows,'pass':all(q['pass'] for q in rows),'scope':'Stationary conservative16mm eye-sphere enclosure at each existing seat center. This is not an insertion-path sweep or physical eye fitting.'}
(R/'eye-endpoint-check.json').write_text(json.dumps(out,indent=2)+'\n')
