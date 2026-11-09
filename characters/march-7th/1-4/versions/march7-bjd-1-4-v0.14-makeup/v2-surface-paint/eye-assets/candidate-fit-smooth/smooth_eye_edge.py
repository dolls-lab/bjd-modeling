"""Smooth only preview-eye retraction, preserving every previous skin clearance."""
from pathlib import Path
import numpy as np, json, hashlib, shutil
P = Path(__file__).resolve().parent
B = P.parent / 'candidate-fit-protected'
with np.load(B / 'hemisphere-eye-geometry.npz') as z:
    a = {k:z[k] for k in z.files}
def shift(v, di, dj):
    ids = np.clip(np.arange(v.shape[0]) + di, 0, v.shape[0] - 1)
    return np.roll(v[ids], dj, axis=1)
records = []
for side in ['negative', 'positive']:
    old = a['skin_retraction_' + side]
    q = old[1:].reshape(64, 192)
    dil = np.maximum.reduce([shift(q, i, j) for i in range(-3, 4) for j in range(-3, 4)])
    weights = np.exp(-np.arange(-5, 6)**2 / (2 * 1.5**2))
    weights /= weights.sum()
    sm = sum(w * shift(dil, i, 0) for w, i in zip(weights, range(-5, 6)))
    sm = sum(w * shift(sm, 0, j) for w, j in zip(weights, range(-5, 6)))
    use = q > 1e-6
    gain = max(1., float(np.max(q[use] / sm[use]))) + 1e-6
    smooth = np.r_[old[0], (sm * gain).ravel()]
    assert np.min(smooth - old) > -1e-6
    v = a['unadapted_vertices_' + side].copy()
    n = len(v) // 2
    v[:n, 1] += smooth
    v[n:, 1] += smooth
    a['vertices_' + side] = v
    a['skin_retraction_' + side] = smooth
    records.append({'side':side, 'gain':gain, 'largest_retraction_mm':float(smooth.max()),
                    'all_previous_skin_clearances_retained':True,
                    'method':'3-ring maximum envelope then sigma1.5-ring Gaussian smoothing, rescaled to retain every original protected sample; inner and outer cup move together.'})
np.savez_compressed(P / 'hemisphere-eye-geometry.npz', **a)
for name in ['build_hemisphere_eyes.py', 'march7-hemisphere-eye-negative.png', 'march7-hemisphere-eye-positive.png']:
    shutil.copy2(B / name, P / name)
r = json.loads((B / 'eye-assets-report.json').read_text())
r['geometry_npz_sha256'] = hashlib.sha256((P / 'hemisphere-eye-geometry.npz').read_bytes()).hexdigest()
r['eye_edge_smoothing'] = records
(P / 'eye-assets-report.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n')
print(r['geometry_npz_sha256'])
