"""Package final v7 print files, previews and actual validation reports."""
from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parent
old=R.parent/'march7-bjd-1-4-v0.6'
old_manifest=json.loads((old/'checksums.json').read_text())
for name,sha in old_manifest.items():
    assert hashlib.sha256((old/name).read_bytes()).hexdigest()==sha,'Delivered v6 file changed: '+name
validation=json.loads((R/'validation.json').read_text())
audit=json.loads((R/'source-preservation-review.json').read_text())
assert validation['pass']
assert audit['all_checks_pass']
for key,filename in [('head_shell','march7-head-shell-v0.7-draft.stl'),('head_cap','march7-head-cap-v0.7-draft.stl')]:
    assert validation['parts'][key]['sha256']==hashlib.sha256((R/filename).read_bytes()).hexdigest()
for key in ['current_head_stl','current_cap_stl','current_blend']:
    entry=audit['files'][key]
    assert entry['sha256']==hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()
files=[R/n for n in ['march7-bjd-head-v0.7-draft.blend','march7-head-shell-v0.7-draft.stl','march7-head-cap-v0.7-draft.stl','README.md','source-usage-rules.txt','parameters.json','validation.json','source-preservation-review.json','local-fairing-report.json','ear-rear-comparison.png','side-comparison.png','ear-front-comparison.png']]
files.extend(sorted((R/'side-views').glob('v7-*.png')))
for n in ['build-report.json','local-quality-review.json','local-junction-intersection-check.json','local-earback-intersection-check.json','eye-insertion-check.json','face-opening-comparison.json','eye-aperture-comparison.png','side-shell-review.json']:
    if (R/n).exists():files.append(R/n)
for p in files:
    if not p.exists():raise FileNotFoundError(p)
manifest={str(p.relative_to(R)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files}
(R/'checksums.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
dest=R/'march7-bjd-head-v0.7-draft.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in files+[R/'checksums.json']:archive.write(p,arcname=str(p.relative_to(R)))
with zipfile.ZipFile(dest) as archive:
    assert archive.testzip() is None
    for name,entry in manifest.items():assert hashlib.sha256(archive.read(name)).hexdigest()==entry['sha256']
print(json.dumps({'archive':str(dest),'bytes':dest.stat().st_size,'files':len(files),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'verified':True}))
