"""Bind final model files, audits and real renders in a reproducible delivery manifest."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;CHAR=HERE.parents[1];REPO=CHAR.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folders=[CHAR/'1-4/versions/v31-large-rear-cap',CHAR/'1-3/versions/v15-large-rear-cap',CHAR/'1-6-special/versions/v16-large-rear-cap']
results=[]
for d in folders:
 p=json.loads((d/'parameters.json').read_text());b=json.loads((d/'build-report.json').read_text());ap=HERE/f"audit-final-{p['version']}.json";a=json.loads(ap.read_text())
 assert a['pass'] and b['source_unchanged']
 for k in ['head','cap','blend']:
  assert sha(d/p['output_files'][k])==a['input_hashes'][k]
  if k!='blend':assert sha(d/p['output_files'][k])==b['parts'][k]['sha256']
 assert sha(d/'parameters.json')==a['input_hashes']['parameters']
 src=CHAR/p['source_directory']
 for k,f in p['source_files'].items():assert sha(src/f)==p['source_sha256'][k]
 files={f.name:sha(f) for f in d.iterdir() if f.is_file() and f.name!='checksums.json'}
 (d/'checksums.json').write_text(json.dumps({'version':p['version'],'files':files},indent=2)+'\n')
 results.append({'version':p['version'],'directory':str(d.relative_to(REPO)),'files':files,'audit_file':str(ap.relative_to(REPO)),'audit_sha256':sha(ap),'checksums_sha256':sha(d/'checksums.json'),'digital_audit_pass':a['pass']})
boards=json.loads((HERE/'contact-sheet-provenance.json').read_text())
for b in boards['boards']:
 assert sha(HERE/b['image'])==b['sha256']
 for q in b['source_renders']:assert sha(HERE/q['image'])==q['sha256']
# Gather formal render metadata; previews named quick are not a delivered source.
views=[]
for f in HERE.glob('render-provenance-*.json'):
 if 'quick' in f.name:continue
 j=json.loads(f.read_text())
 for q in j['views']:
  assert sha(HERE/q['image'])==q['image_sha256']
  assert sha(REPO/q['model'])==q['model_sha256']
  views.append(q)
assert len({q['image'] for q in views})>=12
reviewfiles={f.name:sha(f) for f in HERE.iterdir() if f.is_file() and f.name!='delivery-validation.json'}
report={'digital_checks_pass':True,'models':results,'verified_render_count':len({q['image'] for q in views}),'review_files':reviewfiles,'limits':'Digital mesh and reference hardware only; physical print, magnet/adhesive and selected body fit untested.'}
(HERE/'delivery-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('DELIVERY_COMPLETE',len(results),report['verified_render_count'])
