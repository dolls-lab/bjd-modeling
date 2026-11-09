"""Package the reviewed v8 geometry, unchanged prior delivery and validation evidence."""
from pathlib import Path
import json,hashlib,zipfile
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=R.parent/'march7-bjd-1-4-v0.7'
for name,entry in json.loads((old/'checksums.json').read_text()).items():
    assert sha(old/name)==entry['sha256'],'Prior v7 delivery changed: '+name
validation=json.loads((R/'validation.json').read_text());audit=json.loads((R/'source-preservation-review.json').read_text())
assert validation['pass'] and audit['all_checks_pass']
for part,fn in [('head_shell','march7-head-shell-v0.8-draft.stl'),('head_cap','march7-head-cap-v0.8-draft.stl')]:assert validation['parts'][part]['sha256']==sha(R/fn)
for key in ['current_head_stl','current_cap_stl','current_blend']:
    e=audit['files'][key];assert e['sha256']==sha(Path(e['path']))
for relative in ['side-views/render-provenance.json','comparison-renders/v8-render-provenance.json']:
    assert json.loads((R/relative).read_text())['model_sha256']==sha(R/'march7-bjd-head-v0.8-draft.blend')
names=['march7-bjd-head-v0.8-draft.blend','march7-head-shell-v0.8-draft.stl','march7-head-cap-v0.8-draft.stl','README.md','parameters.json','source-usage-rules.txt','build-report.json','local-fairing-report.json','validation.json','source-preservation-review.json','local-quality-review.json','roundness-comparison.png','surface-comparison.png']
files=[R/n for n in names]
files+=sorted((R/'side-views').glob('v8-*.png'))+sorted((R/'comparison-renders').glob('*.png'))
files+=sorted((R/'comparison-renders').glob('*-render-provenance.json'))
if (R/'side-views/render-provenance.json').exists():files.append(R/'side-views/render-provenance.json')
for n in ['horizontal-roundness-review.json','horizontal-roundness-review.png','top-silhouette-review.json','top-silhouette-review.png','side-shell-review.json','local-junction-intersection-check.json','eye-insertion-check.json','face-opening-comparison.json','eye-aperture-comparison.png']:
    if (R/n).exists():files.append(R/n)
manifest={str(p.relative_to(R)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}
(R/'checksums.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
dest=R/'march7-bjd-head-v0.8-draft.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[R/'checksums.json']:z.write(p,arcname=str(p.relative_to(R)))
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for name,e in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==e['sha256']
print(json.dumps({'file':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'manifested_files':len(files),'verified':True}))
