"""Lower v9's upper forehead and crown smoothly, preserving all skin below Z40."""
from pathlib import Path
import hashlib, json
import numpy as np

R = Path(__file__).resolve().parent
SOURCE = R.parent/'march7-bjd-1-4-v0.9/mother-surface.npz'
with np.load(SOURCE) as arc:
    data = {k: arc[k] for k in arc.files}
before = data['after'].copy()
z0 = 40.0
top = float(before[:, 2].max())
lowering = 3.0
t = np.clip((before[:, 2]-z0)/(top-z0), 0, 1)
w = t**3*(10-15*t+6*t*t)
after = before.copy()
after[:, 2] -= lowering*w
assert np.array_equal(after[data['core_locked']], before[data['core_locked']])
assert np.array_equal(after[data['ear_body_locked']], before[data['ear_body_locked']])
assert np.array_equal(after[before[:,2] <= z0], before[before[:,2] <= z0])
# The vertical map is strictly monotonic, with positive lower bound on its
# derivative. It is C2 at Z40 and at the crown; X/Y are never modified.
minimum_vertical_derivative = 1-lowering*1.875/(top-z0)
assert minimum_vertical_derivative > 0
f = data['triangles']
n0 = np.cross(before[f[:,1]]-before[f[:,0]], before[f[:,2]]-before[f[:,0]])
n1 = np.cross(after[f[:,1]]-after[f[:,0]], after[f[:,2]]-after[f[:,0]])
areas = np.linalg.norm(n1, axis=1)
dot = (n0*n1).sum(1)/np.maximum(np.linalg.norm(n0,axis=1)*areas, 1e-20)
assert np.all(areas > 1e-12) and np.all(dot > 0)
data['historical_v5_baseline'] = data['baseline']
data.update(baseline=before, before=before, after=after, vertices=after,
            crown_lowering_weight=w, crown_lowering_mm=np.array(lowering))
np.savez_compressed(R/'mother-surface.npz', **data)
report = {
    'version': 'v0.10', 'units': 'mm',
    'method': 'C2 quintic-smoothstep vertical lowering of the entire continuous v9 upper forehead and crown; then regenerate shell and cap.',
    'baseline_file': str(SOURCE), 'baseline_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'mother_surface_sha256': hashlib.sha256((R/'mother-surface.npz').read_bytes()).hexdigest(),
    'formula': 'z_new = z_old - 3 * smoothstep5(clamp((z_old-40)/(z_top-40),0,1)); X,Y unchanged',
    'lowering_start_z_mm': z0, 'maximum_lowering_mm': lowering,
    'crown_before_z_mm': top, 'crown_after_z_mm': float(after[:,2].max()),
    'minimum_vertical_map_derivative': minimum_vertical_derivative,
    'central_core_points': int(data['core_locked'].sum()),
    'central_core_maximum_displacement_mm': float(np.linalg.norm(after-before,axis=1)[data['core_locked']].max()),
    'ear_body_maximum_displacement_mm': float(np.linalg.norm(after-before,axis=1)[data['ear_body_locked']].max()),
    'all_vertices_below_z40_unchanged': True,
    'triangles_normal_rotation_over_90': int((dot<0).sum()),
    'degenerate_triangles': int((areas<1e-12).sum()),
    'mother_topology_unchanged': True,
    'print_geometry_note': 'Print parts require regenerated inward shell and new round mechanical holes; mother preservation does not imply remeshed print vertices match one-to-one.',
}
(R/'mother-surface-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
