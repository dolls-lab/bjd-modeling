"""Independent read-only validation of a small lip-only edit against quarter v18.

Proves all source triangle corners outside the declared lip support are unchanged;
checks oriented solids and samples through-wall thickness without repairing input.
"""
from pathlib import Path
import hashlib,json,time
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'v18-lip-only'
SOURCE_FILES={'head':'march7-head-shell-1-4-v18.stl','cap':'march7-head-cap-1-4-v18.stl'}
FILES={'head':'march7-head-shell-1-4-v19.stl','cap':'march7-head-cap-1-4-v19.stl'}
SOURCE_HASHES={'head':'3399309ae690b1a8cfa022442971c9480ea0d427d51a3e8a8f6e58a7bf4af062','cap':'83ee07951213b490a5203cd0a5663a4033c98d5f24131bd720559543a4cf824a'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def quintic(t):
    t=np.clip(t,0.,1.)
    return 6*t**5-15*t**4+10*t**3


def specification(points,source_solid):
    """Independently interpolate the saved increment grid; do not import builder."""
    from scipy.interpolate import RegularGridInterpolator
    field=np.load(ROOT/'lip-field.npz')
    gx,gu=field['x'],field['u'];grid=field['dy']
    if grid.shape==(len(gu),len(gx)):grid=grid.T
    assert grid.shape==(len(gx),len(gu))
    interpolator=RegularGridInterpolator((gx,gu),grid,bounds_error=False,fill_value=0.)
    x,y,z=points.T;u=z-(9.85+.033*x*x)
    dy=interpolator(np.column_stack([x,u]))*quintic((-15.-y)/4.)
    dy[~allowed_region(points)]=0
    stats={'method':'Independent scipy RegularGridInterpolator on the source-derived, amplitude-smoothed increment field; the model builder is not imported. The source surface itself is not replaced.','field_sha256':sha(ROOT/'lip-field.npz'),'grid_shape_x_u':[len(gx),len(gu)],'maximum_grid_increment_mm':float(grid.max()),'support_edge_max_absolute_mm':float(max(np.abs(grid[[0,-1],:]).max(),np.abs(grid[:,[0,-1]]).max())),'note':'Only the amplitude curve is smoothed and globally reduced to stay below each raw amplitude on the grid. Source-depth gates are retained. The raw continuous mapping derivative bound is distinct from grid interpolation and finite-triangle geometry; actual exported profile samples are checked separately.'}
    raw_a=field['source_amplitude'];final_a=field['amplitude_final'];boundary=field['boundary_outer_y']
    width=1-quintic((np.abs(gx)-2.3)/2.2)
    span=boundary[:,0]-boundary[:,1]
    stats['amplitude_global_scale']=float(field['amplitude_global_scale'])
    stats['maximum_final_to_source_amplitude_ratio']=float(np.max(final_a/raw_a))
    stats['grid_analytic_profile_derivative_lower_bound']=float(np.min(1-1.875*final_a*width/span))
    stats['source_depth_gate_retention_error_mm']=float(np.max(np.abs(field['smoothed_unweighted_dy']-field['raw_unweighted_dy']*(final_a/raw_a)[None,:])))
    stats['pass']=bool(grid.min()>=0 and stats['maximum_grid_increment_mm']<.14 and stats['support_edge_max_absolute_mm']<1e-10 and stats['maximum_final_to_source_amplitude_ratio']<=1.000001 and stats['grid_analytic_profile_derivative_lower_bound']>=.25 and stats['source_depth_gate_retention_error_mm']<1e-10)
    return dy,stats


def allowed_region(points):
    x,y,z=np.moveaxis(points,-1,0)
    d=z-(9.85+.033*x*x)
    return (np.abs(x)<4.5)&(y<-15.)&(d>-1.4)&(d<2.)


def pair(solid,x,z):
    hits=sorted(solid.ray_cast((float(x),-55.,float(z)),(float(x),-12.,float(z))),key=lambda h:h.position[1])
    if len(hits)<2 or hits[0].normal[1]>=-1e-5 or hits[1].normal[1]<=1e-5:return None
    return tuple(float(h.position[1]) for h in hits[:2])


def run():
    start=time.monotonic()
    sp={k:SOURCE/name for k,name in SOURCE_FILES.items()};tp={k:ROOT/name for k,name in FILES.items()}
    inputs={str(p):sha(p) for p in [*sp.values(),*tp.values(),SOURCE/'march7-bjd-head-1-4-v18.blend',ROOT/'march7-bjd-head-1-4-v19.blend']}
    assert all(sha(sp[k])==SOURCE_HASHES[k] for k in sp)
    sm=trimesh.load_mesh(sp['head'],process=False,validate=False);tm=trimesh.load_mesh(tp['head'],process=False,validate=False)
    st=np.asarray(sm.triangles);tt=np.asarray(tm.triangles)
    assert st.shape==tt.shape
    delta=tt-st;changed=np.any(delta!=0,axis=-1);allowed=allowed_region(st)
    sverts,indices=np.unique(st.reshape(-1,3),axis=0,return_index=True)
    vdelta=delta.reshape(-1,3)[indices]
    positive_changed=np.any(vdelta!=0,axis=1)
    dot=np.einsum('ij,ij->i',sm.face_normals,tm.face_normals)
    x,y,z=np.moveaxis(st,-1,0);line=9.85+.033*x*x;d=z-line
    def lock(mask):
        count=int(mask.sum());bad=int(np.count_nonzero(changed&mask))
        return {'triangle_corners_checked':count,'changed_triangle_corners':bad,'pass':bool(count>100 and bad==0)}
    locks={
      'all_outside_lip_support':lock(~allowed),
      'mouth_corners_and_adjacent_cheeks':lock((np.abs(x)>=4.5)&(np.abs(x)<18)&(z>3)&(z<22)&(y<0)),
      'chin_below_lips':lock((z<8.4)&(y<0)),
      'nose_forehead_eyes_and_upper_head':lock(z>=13.),
      'rear_and_neck_side':lock(y>=-15.),
    }
    seam=(np.abs(x)<4.5)&(np.abs(d)<=.12)&(y<-15)
    locks['original_mouth_seam_xz']={'triangle_corners_checked':int(seam.sum()),'changed_xz_triangle_corners':int(np.count_nonzero(np.any(delta[...,[0,2]]!=0,axis=-1)&seam)),'maximum_y_retraction_mm':float(delta[...,1][seam].max()),'note':'The seam moves back with the rest of the lip; its original X/Z path remains exact.','pass':bool(seam.sum()>100 and np.array_equal(st[...,[0,2]][seam],tt[...,[0,2]][seam]))}
    import manifold3d as m3d
    source_processed=trimesh.load_mesh(sp['head'],process=True,validate=False)
    source_solid=m3d.Manifold(m3d.Mesh64(np.asarray(source_processed.vertices),np.asarray(source_processed.faces,dtype=np.uint64)))
    prescribed,profile_stats=specification(sverts,source_solid);error=np.abs(vdelta[:,1]-prescribed)
    scope={'source_vertices':len(sverts),'changed_vertices':int(positive_changed.sum()),'raw_triangles':len(st),'xz_exactly_identical':bool(np.array_equal(st[...,[0,2]],tt[...,[0,2]])),'outside_lip_support_changed':int(np.count_nonzero(changed&~allowed)),'all_changes_inward':bool(delta[...,1].min()>=0),'dy_range_mm':[float(delta[...,1].min()),float(delta[...,1].max())],'changed_bounds_source_xyz_mm':[sverts[positive_changed].min(0).tolist(),sverts[positive_changed].max(0).tolist()],'whole_head_bounds_exactly_identical':bool(np.array_equal(sm.bounds,tm.bounds)),'minimum_source_target_normal_dot':float(dot.min()),'minimum_face_area_ratio':float((tm.area_faces/sm.area_faces).min()),'maximum_independent_field_sampling_error_mm':float(error.max()),'cap_stl_byte_identical':sha(sp['cap'])==sha(tp['cap'])}
    scope['pass']=bool(scope['xz_exactly_identical'] and scope['outside_lip_support_changed']==0 and scope['all_changes_inward'] and 0<scope['dy_range_mm'][1]<.14001 and scope['whole_head_bounds_exactly_identical'] and dot.min()>0 and error.max()<2e-5 and scope['cap_stl_byte_identical'])
    helper=ROOT.parents[2]/'1-6-special/versions/v1/validate_model.py'
    ns={'__file__':str(helper),'__name__':'geometry_helpers'};exec(compile(helper.read_text(),str(helper),'exec'),ns)
    parts={};solids={}
    for k in tp:
      row,mesh,solid=ns['mesh_checks'](tp[k],-4 if k=='head' else 2);parts[k]=row;solids[k]=solid
    source_solid=ns['as_solid'](trimesh.load_mesh(sp['head'],process=True,validate=False))
    rows=[];invalidated=[]
    for x0 in np.arange(-4.65,4.651,.15):
      for z0 in np.arange(8.3,12.751,.15):
        a=pair(source_solid,x0,z0);b=pair(solids['head'],x0,z0)
        if a and not b:invalidated.append([float(x0),float(z0)])
        if a and b:
          ta=a[1]-a[0];tb=b[1]-b[0]
          rows.append({'x_mm':float(x0),'z_mm':float(z0),'source_y_thickness_mm':ta,'target_y_thickness_mm':tb,'thickness_change_mm':tb-ta,'outer_dy_mm':b[0]-a[0],'inner_dy_mm':b[1]-a[1]})
    thickness={'method':'Oriented first entry/exit pairs along Y in the mouth wall; projected samples, not global perpendicular minimum thickness.','valid_pairs':len(rows),'source_valid_target_invalid':invalidated,'minimum_source_sample_mm':min(r['source_y_thickness_mm'] for r in rows),'minimum_target_sample_mm':min(r['target_y_thickness_mm'] for r in rows),'maximum_thinning_mm':max(0.,max(-r['thickness_change_mm'] for r in rows)),'maximum_thickening_mm':max(0.,max(r['thickness_change_mm'] for r in rows)),'worst_thinning_samples':sorted(rows,key=lambda r:r['thickness_change_mm'])[:10]}
    thickness['pass']=bool(len(rows)>1000 and not invalidated and thickness['minimum_target_sample_mm']>2.0 and thickness['maximum_thinning_mm']<.09)
    from scipy.signal import find_peaks
    profile_rows=[]
    for x0 in [-4.,-3.,-2.,-1.,0.,1.,2.,3.,4.]:
        line=9.85+.033*x0*x0
        z_values=np.arange(line-1.7,line+2.3001,.025)
        curves=[]
        for solid in [source_solid,solids['head']]:
            curve=[]
            for z0 in z_values:
                hit=solid.ray_cast((x0,-80.,float(z0)),(x0,-10.,float(z0)))
                assert hit,'missing profile ray'
                curve.append(min(h.position[1] for h in hit))
            curves.append(np.asarray(curve))
        source_curve,target_curve=curves
        a=len(find_peaks(source_curve,prominence=.01)[0])+len(find_peaks(-source_curve,prominence=.01)[0])
        b=len(find_peaks(target_curve,prominence=.01)[0])+len(find_peaks(-target_curve,prominence=.01)[0])
        profile_rows.append({'x_mm':x0,'z_samples':len(z_values),'source_extrema_count':a,'target_extrema_count':b,'maximum_front_y_increment_mm':float((target_curve-source_curve).max()),'new_extrema_count':max(0,b-a)})
    actual_profiles={'method':'Actual source and target STL first-hit Y profiles, .025 mm Z spacing. Peaks/troughs with prominence >=.01 mm counted; unchanged counts are a finite sampling diagnostic, not a global smoothness proof.','profiles':profile_rows,'pass':all(row['new_extrema_count']==0 for row in profile_rows)}
    unchanged=all(sha(Path(path))==digest for path,digest in inputs.items())
    report={'version':'march7-quarter-v19-lip-refine','units':'mm','source_fixed_hashes_match':True,'input_sha256':inputs,'method':'Independent raw triangle-coordinate comparison; exact source preservation outside analytic lip support; oriented-solid acceptance and thickness ray samples. No repair or input writes.','change_scope':scope,'protected_geometry':locks,'increment_field_verification':profile_stats,'parts':parts,'mouth_wall_y_samples':thickness,'actual_exported_profile_samples':actual_profiles,'interfaces':{'method':'All head vertices outside the tiny anterior lip region unchanged, plus byte-identical cap. The existing eye/neck/cap interface geometry is preserved; no new fitting claim.','pass':bool(locks['all_outside_lip_support']['pass'] and scope['cap_stl_byte_identical'])},'input_files_unchanged':unchanged,'physical_fit':'NOT TESTED','limitations':['Source and target normals remain in the same hemisphere; oriented manifold acceptance is not an exhaustive all-triangle self-intersection proof.','Wall samples are Y-projected, not a global minimum wall/strength proof.','The lip geometry is intentionally modified; fixed surrounding vertices do not prove identical perceived expression.','Appearance requires same-camera renders and user confirmation.'],'duration_seconds':time.monotonic()-start}
    report['pass']=bool(unchanged and scope['pass'] and profile_stats['pass'] and all(r['pass'] for r in locks.values()) and all(r['pass'] for r in parts.values()) and thickness['pass'] and actual_profiles['pass'])
    return report

if __name__=='__main__':
    try:result=run()
    except Exception as exc:result={'pass':False,'error':f'{type(exc).__name__}: {exc}'}
    (ROOT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result.get(k) for k in ['pass','error','change_scope']},ensure_ascii=False))
    raise SystemExit(0 if result['pass'] else 1)
