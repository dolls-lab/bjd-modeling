"""Bundle the forehead-transition revision with verified geometry and reports."""
from pathlib import Path
import json, hashlib, zipfile
R = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda n: json.loads((R/n).read_text())
old = R.parent/'march7-bjd-1-4-v0.10'
for name, entry in json.loads((old/'checksums.json').read_text()).items():
    assert sha(old/name) == entry['sha256'], 'v10 changed: '+name
v = read('validation.json'); s = read('source-surface-review.json')
e = read('eye-insertion-check.json'); x = read('print-intersection-check.json')
assert v['pass'] and s['all_integrity_checks_pass'] and e['pass']
assert x['no_strict_nonadjacent_self_intersections'] and x['all_inputs_unchanged']
for p in s['files'].values():
    assert sha(Path(p['path'])) == p['sha256']
for key, name in [('head_shell','march7-head-shell-v0.11-draft.stl'), ('head_cap','march7-head-cap-v0.11-draft.stl')]:
    assert sha(R/name) == v['parts'][key]['sha256']
assert sha(R/'march7-bjd-head-v0.11-draft.blend') == read('comparison-renders/v11-render-provenance.json')['model_sha256']
assert (R/'local-quality-review.json').is_file()
files = sorted(p for p in R.iterdir() if p.is_file() and p.name not in {'baseline-v0.10.blend','checksums.json'} and p.suffix in {'.blend','.stl','.npz','.py','.json','.md','.txt','.png'})
files += sorted(p for p in (R/'comparison-renders').iterdir() if p.is_file())
manifest = {str(p.relative_to(R)): {'sha256':sha(p),'bytes':p.stat().st_size} for p in files}
(R/'checksums.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
dest = R/'march7-bjd-head-v0.11-draft.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[R/'checksums.json']: z.write(p,arcname=str(p.relative_to(R)))
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for name,item in manifest.items(): assert hashlib.sha256(z.read(name)).hexdigest() == item['sha256']
print(json.dumps({'zip':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'files':len(files),'verified':True,'v10_unchanged':True}))
