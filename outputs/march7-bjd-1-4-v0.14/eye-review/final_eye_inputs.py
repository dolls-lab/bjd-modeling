"""Read-only final combined v14 inputs and exact STL geometry verification."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
MODEL=ROOT.parent
HEAD=MODEL/'march7-head-shell-v0.14-draft.stl'
SOLUTION=MODEL/'final-change-solution.npz'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def expected_head():
    p=argparse.ArgumentParser()
    p.add_argument('--expected-head-sha256',required=True)
    return p.parse_args().expected_head_sha256

def canonical_triangles(tris):
    a=np.asarray(tris,dtype='<f4')
    order=np.lexsort((a[:,:,2],a[:,:,1],a[:,:,0]),axis=1)
    a=np.take_along_axis(a,order[:,:,None],axis=1).reshape(-1,9)
    return a[np.lexsort(tuple(a[:,i] for i in range(8,-1,-1)))]

def load_final(expected):
    h=sha(HEAD);hs=sha(SOLUTION)
    if h!=expected:raise RuntimeError('Final combined head SHA mismatch')
    build=json.loads((MODEL/'build-report.json').read_text())
    if build['v14_final_solution_sha256']!=hs:raise RuntimeError('Final solution/build-report mismatch')
    with np.load(SOLUTION) as n:
        d={k:n[k] for k in n.files}
    data={'before':d['head_before'],'after':d['head_after'],'triangles':d['head_triangles'],
          'free':d['head_eye_free'],'crown_free':d['head_crown_free']}
    if np.any(data['free']&data['crown_free']):raise RuntimeError('Eye and crown supports overlap')
    binary=HEAD.read_bytes();count=int.from_bytes(binary[80:84],'little')
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')])
    if len(binary)!=84+50*count:raise RuntimeError('Unexpected STL format')
    actual=np.frombuffer(binary,dtype=dtype,count=count,offset=84)['vertices']
    reference=data['after'][data['triangles']].astype('f4')
    ordered=bool(np.array_equal(actual,reference))
    if not ordered and not np.array_equal(canonical_triangles(actual),canonical_triangles(reference)):
        raise RuntimeError('Final actual STL and final-change-solution triangle multiset differ')
    integrity={'actual_head_stl':str(HEAD),'head_sha256':h,'final_solution':str(SOLUTION),'solution_sha256':hs,
               'actual_float32_triangle_multiset_exact':True,'actual_triangle_order_matches_solution':ordered,
               'triangle_ids_in_local_reports':'final-change-solution head_triangles indices; actual geometry is verified exact float32'}
    return data,integrity

def confirm_unchanged(integrity):
    if sha(HEAD)!=integrity['head_sha256'] or sha(SOLUTION)!=integrity['solution_sha256']:
        raise RuntimeError('Final model changed during eye QA')
