"""Package the visually reviewed preview and full-resolution pictures only."""
from pathlib import Path
import json,hashlib,zipfile,os
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
model='march7-v14-makeup-preview.blend'
build=json.loads((R/'preview-build-report.json').read_text())
render=json.loads((R/'render-provenance.json').read_text())
assert build['print_geometry_exactly_unchanged'] and build['original_file_unchanged']
assert build['preview_blend_sha256']==render['model_sha256']==sha(R/model)
assert render['input_model_modified'] is False and len(render['views'])==9
assert json.loads((R/'visual-review.json').read_text())['accepted_final_preview_sha256']==sha(R/model)
names=[model,'README.md','source-usage-rules.txt','preview-build-report.json','render-provenance.json','board-provenance.json','visual-review.json','unpainted-baseline-integrity.json','makeup-multiview.png','hair-multiview.png','character-comparison.png']
names+=['previews/'+q['file'] for q in render['views']]
names+=['uv-transfer/uv-transfer-report.json','uv-transfer/uv-mask-review.json','uv-transfer/loop-uv-conflict-review.json']
manifest={n:{'sha256':sha(R/n),'bytes':(R/n).stat().st_size} for n in names}
raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
tmp=R/'.preview-package.tmp';dest=R/'march7-v14-makeup-preview.zip'
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for n in names:z.write(R/n,n)
    z.writestr('checksums.json',raw)
with zipfile.ZipFile(tmp) as z:
    assert z.testzip() is None
    for n,d in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==d['sha256']==sha(R/n)
os.replace(tmp,dest);(R/'checksums.json').write_bytes(raw)
print(json.dumps({'file':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'verified':True,'files':len(names)},ensure_ascii=False))
