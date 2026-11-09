#!/usr/bin/env python3
"""Compare raw PMX face triangles directly with the final v14 print eye holes.

Read-only inputs. Fixed world transform and shared rays; no fitted alignment.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import importlib.util
import json
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
import trimesh
import manifold3d as m3d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT.parent.parent
PRINT_ROOT = ROOT.parent
PARSER = PRINT_ROOT/'parse_pmx.py'
SCALE = 27.47544416498121
Z_ORIGIN = 18.16621208190918
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def metrics(mask, xs, zs, pitch):
    j, i = np.nonzero(mask)
    if not len(i):
        raise RuntimeError('Empty aperture')
    return dict(pixel_count=int(len(i)), width_mm=float((i.max()-i.min()+1)*pitch),
                height_mm=float((j.max()-j.min()+1)*pitch), area_mm2=float(len(i)*pitch*pitch),
                centroid_xz_mm=[float(xs[i].mean()),float(zs[j].mean())],
                bbox_xz_mm=[[float(xs[i.min()]-pitch/2),float(zs[j.min()]-pitch/2)],
                            [float(xs[i.max()]+pitch/2),float(zs[j.max()]+pitch/2)]])


def select_aperture(clear, xs, zs, center, pitch):
    labels, count = ndimage.label(clear, ndimage.generate_binary_structure(2, 1))
    ci, cj = np.argmin(abs(xs-center[0])), np.argmin(abs(zs-center[2]))
    selected = int(labels[cj, ci])
    if not selected:
        raise RuntimeError('Eye-center seed obstructed; no substitute component allowed')
    details = []
    for label in range(1, count+1):
        mask = labels == label
        touches = bool(mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any())
        details.append(dict(component_id=label, selected=label==selected,
                            touches_roi_boundary=touches, **metrics(mask,xs,zs,pitch)))
    if next(x for x in details if x['selected'])['touches_roi_boundary']:
        raise RuntimeError('Eye aperture connected to exterior ROI')
    return labels==selected, details


def raw_face_clear(triangles, xs, zs, y_start, y_end):
    """Exact raw triangle planes at grid samples; no skin welding/subdivision."""
    blocked = np.zeros((len(zs),len(xs)), dtype=bool)
    for tri in triangles:
        p = tri[:,[0,2]]
        ix0,ix1 = np.searchsorted(xs,[p[:,0].min(),p[:,0].max()],side='left')
        iz0,iz1 = np.searchsorted(zs,[p[:,1].min(),p[:,1].max()],side='left')
        ix1,iz1 = min(ix1+1,len(xs)),min(iz1+1,len(zs))
        if ix0>=ix1 or iz0>=iz1 or tri[:,1].min()>y_end or tri[:,1].max()<y_start:
            continue
        a,b = p[1]-p[0],p[2]-p[0]
        denom = a[0]*b[1]-a[1]*b[0]
        if abs(denom)<1e-15:  # exactly edge-on projection has zero area
            continue
        xx,zz = np.meshgrid(xs[ix0:ix1]-p[0,0],zs[iz0:iz1]-p[0,1])
        u = (xx*b[1]-zz*b[0])/denom
        v = (a[0]*zz-a[1]*xx)/denom
        y = tri[0,1]+u*(tri[1,1]-tri[0,1])+v*(tri[2,1]-tri[0,1])
        inside = (u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(y>=y_start-1e-9)&(y<=y_end+1e-9)
        blocked[iz0:iz1,ix0:ix1] |= inside
    return ~blocked


def print_clear(solid,xs,zs,y_start,y_end):
    clear = np.zeros((len(zs),len(xs)),dtype=bool)
    for j,z in enumerate(zs):
        for i,x in enumerate(xs):
            clear[j,i] = not solid.ray_cast((float(x),y_start,float(z)),(float(x),y_end,float(z)))
    return clear


def raw_boundaries(vertices,faces):
    # Exact-position reindexing is for edge topology only, never the raster input.
    vv,inv = np.unique(vertices[faces].reshape(-1,3),axis=0,return_inverse=True)
    ff = inv.reshape(-1,3)
    edges = np.sort(np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]),axis=1)
    edges,counts = np.unique(edges,axis=0,return_counts=True)
    boundary = edges[counts==1]
    adj=defaultdict(list)
    for a,b in boundary:
        adj[int(a)].append(int(b));adj[int(b)].append(int(a))
    if any(len(x)!=2 for x in adj.values()):
        raise RuntimeError('Raw face boundary has a branch; automatic loop assumption invalid')
    seen=set();loops=[]
    for seed in sorted(adj):
        if seed in seen:
            continue
        ids=[];prev=None;current=seed
        while current not in seen:
            seen.add(current);ids.append(current)
            nxt = next(x for x in adj[current] if x!=prev)
            prev,current=current,nxt
        if current!=seed:
            raise RuntimeError('Unclosed raw face boundary')
        pts=vv[ids]
        x,z=pts[:,0],pts[:,2]
        cross=x*np.roll(z,-1)-np.roll(x,-1)*z
        loops.append(dict(loop_id=len(loops),vertex_count=len(ids),vertices_xyz_mm=pts.tolist(),
                          bbox_min_mm=pts.min(0).tolist(),bbox_max_mm=pts.max(0).tolist(),
                          centroid_of_vertices_mm=pts.mean(0).tolist(),
                          perimeter_3d_mm=float(np.linalg.norm(np.roll(pts,-1,axis=0)-pts,axis=1).sum()),
                          projected_polygon_area_mm2=float(abs(cross.sum())/2),
                          projected_bbox_width_mm=float(np.ptp(x)),projected_bbox_height_mm=float(np.ptp(z))))
    return loops,dict(exact_unique_face_vertices=len(vv),triangles=len(faces),boundary_edges=len(boundary),
                      nonmanifold_edges=int((counts>2).sum()),position_welding='exact float equality for loop diagnostics only')


def boundary_comparison(raw,current,xs,zs):
    arrays=[]
    for mask in (raw,current):
        boundary=mask&~ndimage.binary_erosion(mask,structure=np.ones((3,3)))
        j,i=np.nonzero(boundary);arrays.append(np.column_stack([xs[i],zs[j]]))
    summary={}
    for key,source,target in [('raw_to_print',arrays[0],arrays[1]),('print_to_raw',arrays[1],arrays[0])]:
        dist=cKDTree(target).query(source)[0]
        summary[key]=dict(sample_count=len(dist),mean_mm=float(dist.mean()),p95_mm=float(np.percentile(dist,95)),max_mm=float(dist.max()))
    summary['symmetric_hausdorff_mm']=max(v['max_mm'] for v in summary.values())
    summary['method']='Nearest distance between boundary-pixel centers on the shared XZ grid; not indexed point displacement or a 3D surface distance.'
    return summary


def pair_metrics(measures):
    left,right=measures
    a,b=np.array(left['centroid_xz_mm']),np.array(right['centroid_xz_mm'])
    return dict(area_centroid_horizontal_separation_mm=float(b[0]-a[0]),
                area_centroid_xz_distance_mm=float(np.linalg.norm(b-a)),
                inner_bbox_gap_mm=float(right['bbox_xz_mm'][0][0]-left['bbox_xz_mm'][1][0]),
                outer_bbox_span_mm=float(right['bbox_xz_mm'][1][0]-left['bbox_xz_mm'][0][0]),
                bbox_center_horizontal_separation_mm=float((right['bbox_xz_mm'][0][0]+right['bbox_xz_mm'][1][0]-left['bbox_xz_mm'][0][0]-left['bbox_xz_mm'][1][0])/2))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pitch-mm',type=float,default=.05)
    ap.add_argument('--expected-head-sha256',required=True)
    args=ap.parse_args()
    if args.pitch_mm<=0:
        raise ValueError('Positive sample pitch required')
    started=time.time()
    params_path=PRINT_ROOT/'parameters.json';build_path=PRINT_ROOT/'build-report.json'
    params=json.loads(params_path.read_text());build=json.loads(build_path.read_text())
    pmx_path=Path(params['source_pmx']);head_path=PRINT_ROOT/'march7-head-shell-v0.14-draft.stl'
    paths=dict(raw_pmx=pmx_path,print_stl=head_path,parameters=params_path,build_report=build_path,pmx_parser=PARSER)
    sources={k:dict(file=str(p),sha256=sha(p)) for k,p in paths.items()}
    if sources['print_stl']['sha256']!=args.expected_head_sha256:
        raise RuntimeError('Final STL SHA does not match')
    if sources['raw_pmx']['sha256']!=build['source_sha256']:
        raise RuntimeError('PMX differs from build source SHA')
    if params['fixed_source_scale_mm']!=SCALE:
        raise RuntimeError('Expected fixed source scale changed')
    spec=importlib.util.spec_from_file_location('readonly_pmx_parser',PARSER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    pmx=module.load_pmx(pmx_path)
    face=next(m for m in pmx['materials'] if m['name']=='脸')
    vertices=pmx['vertices'][:,[0,2,1]].copy();vertices[:,2]-=Z_ORIGIN;vertices*=SCALE
    faces=pmx['faces'][face['start']:face['end']]
    triangles=vertices[faces]
    loops,topology=raw_boundaries(vertices,faces)
    mesh=trimesh.load_mesh(head_path,process=True,validate=False)
    solid=m3d.Manifold(m3d.Mesh64(np.ascontiguousarray(mesh.vertices,dtype=np.float64),np.ascontiguousarray(mesh.faces,dtype=np.uint64)))
    if solid.status()!=m3d.Error.NoError or solid.is_empty():
        raise RuntimeError('Print STL cannot be used as a manifold ray target')
    centers=sorted(build['eye_centers_mm'],key=lambda c:c[0])
    n=int(np.ceil(24/args.pitch_mm));offsets=(np.arange(n)+.5-n/2)*args.pitch_mm
    y_start=float(min(triangles[:,:,1].min(),mesh.bounds[0,1])-3)
    records=[];images=[]
    for center in centers:
        xs,zs=center[0]+offsets,center[2]+offsets
        y_end=float(center[1])
        print('Projecting',center[0],flush=True)
        raw,raw_components=select_aperture(raw_face_clear(triangles,xs,zs,y_start,y_end),xs,zs,center,args.pitch_mm)
        current,current_components=select_aperture(print_clear(solid,xs,zs,y_start,y_end),xs,zs,center,args.pitch_mm)
        measures=dict(raw_pmx=metrics(raw,xs,zs,args.pitch_mm),print_v14=metrics(current,xs,zs,args.pitch_mm))
        candidates=[q for q in loops if q['vertex_count']==31 and np.sign(q['centroid_of_vertices_mm'][0])==np.sign(center[0])]
        if len(candidates)!=1:
            raise RuntimeError('Raw eye loop identification is not unique')
        loop=candidates[0]
        grid_x,grid_z=np.meshgrid(xs,zs)
        polygon=PlotPath(np.asarray(loop['vertices_xyz_mm'])[:,[0,2]])
        polygon_mask=polygon.contains_points(np.column_stack([grid_x.ravel(),grid_z.ravel()])).reshape(raw.shape)
        both=raw&current;union=raw|current
        before,after=measures['raw_pmx'],measures['print_v14']
        delta=np.array(after['centroid_xz_mm'])-before['centroid_xz_mm']
        change={key:after[key]-before[key] for key in ('width_mm','height_mm','area_mm2','pixel_count')}
        change.update(area_percent=float(100*(after['area_mm2']/before['area_mm2']-1)),
                      centroid_shift_xz_mm=delta.tolist(),centroid_shift_distance_mm=float(np.linalg.norm(delta)),
                      intersection_over_union=float(both.sum()/union.sum()),
                      raw_only_area_mm2=float((raw&~current).sum()*args.pitch_mm**2),
                      print_only_area_mm2=float((current&~raw).sum()*args.pitch_mm**2),
                      symmetric_difference_area_mm2=float((raw^current).sum()*args.pitch_mm**2))
        records.append(dict(eye_id='x_negative' if center[0]<0 else 'x_positive',seed_xyz_mm=center,
                            ray_y_interval_mm=[y_start,y_end],metrics=measures,changes_print_minus_raw=change,
                            selected_raw_boundary_loop_id=loop['loop_id'],
                            raw_projection_vs_31_vertex_loop_polygon_difference_pixels=int((raw^polygon_mask).sum()),
                            clear_components=dict(raw_pmx=raw_components,print_v14=current_components),
                            projected_boundary_nearest_distances=boundary_comparison(raw,current,xs,zs)))
        images.append((xs,zs,raw,current,loop))
    pairs={key:pair_metrics([r['metrics'][key] for r in records]) for key in ('raw_pmx','print_v14')}
    pairs['changes_print_minus_raw']={k:pairs['print_v14'][k]-pairs['raw_pmx'][k] for k in pairs['raw_pmx']}
    for key,p in paths.items():
        sources[key]['sha256_after']=sha(p)
        sources[key]['unchanged_during_check']=sources[key]['sha256']==sources[key]['sha256_after']
        if not sources[key]['unchanged_during_check']:
            raise RuntimeError(f'Input changed: {key}')
    report=dict(units='mm',sources=sources,
                fixed_transform=dict(formula='world = [PMX.X, PMX.Z, PMX.Y - 18.16621208190918] * 27.47544416498121',
                                     scale_mm_per_pmx_unit=SCALE,pmx_y_origin=Z_ORIGIN,fitted_alignment=False),
                raw_skin_material=dict(name=face['name'],global_triangle_start=face['start'],global_triangle_end_exclusive=face['end'],triangle_count=len(faces)),
                excluded_pmx_materials=[m['name'] for m in pmx['materials'] if m['name']!='脸'],
                source_topology=topology,raw_face_boundary_loops=loops,sample_pitch_mm=args.pitch_mm,
                method='Two-sided raw PMX face-triangle +Y segment coverage by barycentric plane intersection, compared with actual v14 solid ray hits on the same world XZ grid and identical ray endpoints. No skin smoothing, remesh, subdivision, source-pose morph or fitted rescaling.',
                aperture_selection='4-connected clear component containing each shared eye-center seed. The two separate 8-vertex upper-eyelid slit components and exterior background are not merged into the main eye aperture. Full component inventories are retained.',
                eyes=records,pair_spacing=pairs,
                eye_distance_definition='Primary eye distance is horizontal separation of the two area centroids of the projected main apertures. Also report XZ centroid distance, inner bbox gap, outer bbox span and bbox-center separation. These are not anatomical pupil distance: eyeballs/irises are excluded.',
                geometric_correspondence='Original 31-vertex 3D boundary curves are retained in this report. The final printable shell is closed and has no topological open-boundary loop at the eye: its visible hole is a depth-dependent silhouette through a thick wall. Therefore no indexed 3D point displacement or equivalence of raw edge and print rim is claimed.',
                limitations=['Raw PMX is a zero-thickness skin surface; PRINT is a thick solid with an eye socket. Differences combine reconstruction/smoothing and front-visible occlusion through wall thickness.',
                             'Raw triangles are treated two-sided, with material textures/transparency/shaders ignored; eyebrow/eyelash/eyeball/eye-white geometry is excluded by selecting only the face material.',
                             'Raster boundary resolution is 0.05 mm at the default pitch; reported nearest-boundary distances use boundary-pixel centers, not exact continuous curve distances.',
                             'No manual geometric correspondence, best-fit transform or size normalization is used. The eye center only selects a component and sets a shared rear ray depth.',
                             'This report assesses bare geometric apertures, not full character likeness or the appearance with rendered eyes, lashes, makeup and hair.'],
                figure='eye-original-comparison.png',duration_seconds=time.time()-started)
    (ROOT/'eye-original-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    fig=plt.figure(figsize=(13,10),layout='constrained');gs=fig.add_gridspec(2,2,height_ratios=[1,0.75])
    for k,(xs,zs,raw,current,loop) in enumerate(images):
        ax=fig.add_subplot(gs[0,k]);rgb=np.ones((*raw.shape,3))*.97
        rgb[raw&current]=[.22,.25,.29];rgb[raw&~current]=[.88,.29,.45];rgb[current&~raw]=[.05,.62,.65]
        ax.imshow(rgb,origin='lower',extent=[xs[0]-.5*args.pitch_mm,xs[-1]+.5*args.pitch_mm,zs[0]-.5*args.pitch_mm,zs[-1]+.5*args.pitch_mm])
        pts=np.asarray(loop['vertices_xyz_mm']);pts=np.vstack([pts,pts[0]])
        ax.plot(pts[:,0],pts[:,2],color='#da7590',lw=.7,alpha=.75)
        center=centers[k];ax.set_xlim(center[0]-7.5,center[0]+7.5);ax.set_ylim(center[2]-6,center[2]+6)
        ax.set_title(f"{'Negative X' if k==0 else 'Positive X'} main eye aperture")
        ax.set_xlabel('World X (mm)');ax.set_ylabel('World Z (mm)');ax.set_aspect('equal')
    ax=fig.add_subplot(gs[1,:])
    for xs,zs,raw,current,loop in images:
        ax.contour(xs,zs,raw.astype(float),[.5],colors=['#df4a73'],linewidths=1.6)
        ax.contour(xs,zs,current.astype(float),[.5],colors=['#099ea6'],linewidths=1.2)
    for key,color in [('raw_pmx','#df4a73'),('print_v14','#099ea6')]:
        cc=np.array([r['metrics'][key]['centroid_xz_mm'] for r in records]);ax.scatter(cc[:,0],cc[:,1],c=color,s=28,marker='+')
    ax.set_xlim(-22,22);ax.set_ylim(21,34);ax.set_aspect('equal');ax.set_xlabel('World X (mm)');ax.set_ylabel('World Z (mm)')
    ax.set_title('Shared fixed world coordinates; no fitted alignment or scaling')
    fig.legend(handles=[Patch(color='#38404a',label='Open in both'),Patch(color='#e04a73',label='Raw PMX only'),Patch(color='#0a9ea6',label='PRINT v14 only')],loc='outside lower center',ncol=3)
    fig.suptitle('Original PMX skin eye openings vs final v14 PRINT\n0.05 mm sampling; upper-eyelid slits excluded from main openings',fontsize=15)
    fig.savefig(ROOT/'eye-original-comparison.png',dpi=160)
    plt.close(fig)
    print(json.dumps(dict(eyes=[dict(eye_id=r['eye_id'],metrics=r['metrics'],changes=r['changes_print_minus_raw'],boundary=r['projected_boundary_nearest_distances']) for r in records],pair_spacing=pairs,source_sha=sources['raw_pmx']['sha256'],print_sha=sources['print_stl']['sha256']),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
