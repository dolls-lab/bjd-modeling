import sys
from pathlib import Path
review=Path(__file__).resolve().parent
root=review.parents[3]
sys.path.insert(0,str(review));from old_magnet_cleanup import *
import json,hashlib
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=[]
for sf,v in [('1-4','v30'),('1-3','v14'),('1-6-special','v15')]:
    folder=root/f'characters/march-7th/{sf}/versions/{v}-pass-turn-seat'
    p=json.loads((folder/'parameters.json').read_text());paths=[folder/p['output_files'][k] for k in ['head','cap']]
    hashes={str(x.relative_to(root)):sha(x) for x in paths}
    a=[trimesh.load_mesh(path,process=True) for path in paths]
    cut,rep=make_old_magnet_cutters(*a,p['source_uniform_scale'])
    removed=[]
    for cutter in cut:
        removed.append([float((mf.Manifold(mf.Mesh64(m.vertices,np.asarray(m.faces,np.uint64)))^cutter).volume()) for m in a])
    checks={'two_valid_cutters':len(cut)==2 and all(c.status()==mf.Error.NoError for c in cut),
            'no_sampled_support_boundary_cut':all(r['max_boundary_cut_q_mm']<1e-5 for r in rep),
            'minimum_sampled_radial_chord_over_3qmm':all(r['minimum_sampled_radial_wall_chord_q_mm']>3 for r in rep),
            'source_files_unchanged':all(sha(root/k)==v for k,v in hashes.items())}
    entries.append({'source_directory':str(folder.relative_to(root)),'source_sha256':hashes,'scale':p['source_uniform_scale'],'fits':rep,'removed_volume_by_left_right_then_head_cap_before_hole_fill_mm3':removed,'checks':checks,'pass':all(checks.values())})
    print(sf,checks,flush=True)
report={'method':'Prototype source-derived local old-magnet-pad cutter checked against immutable latest source meshes, before main builder hole fill and old seam restoration. This is cutter preflight, not final-output validation.','script_sha256':sha(review/'old_magnet_cleanup.py'),'results':entries,'pass':all(r['pass'] for r in entries),'limitations':['Ray chord measured along old local X is not global minimum wall thickness.','Source samples around removed pad interpolate intended inner-wall shape; no claim to recover a unique historical precut mesh.','Final builder must independently check actual output, exterior preservation, wall integrity and part connectivity.','Cutters must be applied after filling obsolete blind magnet pockets.']}
(review/'old-magnet-cleanup-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
