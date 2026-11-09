"""Package final v9 geometry and hash-bound reviews; do not include old candidates."""
from pathlib import Path
import hashlib
import json
import zipfile

R = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda n: json.loads((R/n).read_text())

old = R.parent/'march7-bjd-1-4-v0.8'
for name, entry in json.loads((old/'checksums.json').read_text()).items():
    assert sha(old/name) == entry['sha256'], 'Prior v8 delivery changed: '+name

validation = read('validation.json')
source = read('source-surface-review.json')
eyes = read('eye-insertion-check.json')
crossings = read('print-intersection-check.json')
correspondence = read('blend-stl-consistency.json')
assert validation['pass'] and source['all_integrity_checks_pass'] and eyes['pass']
assert crossings['no_strict_nonadjacent_self_intersections'] and crossings['all_inputs_unchanged']
assert correspondence['all_unordered_triangles_bitwise_equal'] and correspondence['all_input_files_unchanged']
assert correspondence['blend_sha256_after'] == sha(R/'march7-bjd-head-v0.9-draft.blend')
for part, name in [('head_shell', 'march7-head-shell-v0.9-draft.stl'), ('head_cap', 'march7-head-cap-v0.9-draft.stl')]:
    assert validation['parts'][part]['sha256'] == sha(R/name)
for entry in source['files'].values():
    assert sha(Path(entry['path'])) == entry['sha256']
assert eyes['head_shell_sha256'] == sha(R/'march7-head-shell-v0.9-draft.stl')
for entry in crossings['parts'].values():
    assert sha(Path(entry['file'])) == entry['sha256']
for name, version in [('march7-bjd-head-v0.9-draft.blend', 'v9'), ('baseline-v0.8.blend', 'v8')]:
    assert read(f'comparison-renders/{version}-render-provenance.json')['model_sha256'] == sha(R/name)

required = ['march7-bjd-head-v0.9-draft.blend', 'march7-head-shell-v0.9-draft.stl', 'march7-head-cap-v0.9-draft.stl',
            'README.md', 'parameters.json', 'source-usage-rules.txt', 'mother-surface.npz', 'central-source-protection.npz',
            'back-top-comparison.png', 'side-comparison.png', 'blend-stl-consistency.json']
files = [R/n for n in required]
files += [p for p in R.glob('*.json') if p.name not in {'parameters.json', 'checksums.json', 'baseline-build-report.json', 'blend-stl-consistency.json'}]
files += [p for p in R.glob('*.py') if p.name != 'render_mother.py']
files += [R/n for n in ['eye-aperture-comparison.png', 'side-shell-review.png', 'upper-forehead-profile-review.png', 'mother-sections.png']]
for folder in ['comparison-renders', 'earback-review']:
    files += sorted(p for p in (R/folder).iterdir() if p.suffix in {'.png', '.json', '.py'})
files = sorted(set(files))
assert all(p.is_file() for p in files), 'Missing delivery artifact'
manifest = {str(p.relative_to(R)): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in files}
(R/'checksums.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
dest = R/'march7-bjd-head-v0.9-draft.zip'
with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files+[R/'checksums.json']:
        z.write(p, arcname=str(p.relative_to(R)))
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    for name, entry in manifest.items():
        assert hashlib.sha256(z.read(name)).hexdigest() == entry['sha256']
print(json.dumps({'file': str(dest), 'bytes': dest.stat().st_size, 'sha256': sha(dest), 'manifested_files': len(files),
                  'prior_v8_delivery_unchanged': True, 'zip_readback_verified': True}))
