"""Read-only horizontal curvature/sagitta comparison for a rounded-skull candidate."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import manifold3d as m
from scipy.signal import savgol_filter,find_peaks,peak_widths
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ap=argparse.ArgumentParser();ap.add_argument('--solution',type=Path,default=Path(__file__).resolve().parent/'head-solution.npz');ap.add_argument('--out-prefix',default='horizontal-roundness-review');ap.add_argument('--label',default='v0.8')
args=ap.parse_args();out=Path(__file__).resolve().parent;path=args.solution;digest=hashlib.sha256(path.read_bytes()).hexdigest();s=np.load(path)
faces=s['triangles'];source=np.load(out/'head-visible-source-protection.npz')
earface=np.any(source['head_visible_source_ear'][faces],axis=1)
ys=np.arange(-5,18.001,.25);heights=[24,26,30,32,36,38,42,44,48];records=[]
actual_stl=out/'march7-head-shell-v0.8-draft.stl'
actual_bytes=actual_stl.read_bytes();actual_sha=hashlib.sha256(actual_bytes).hexdigest()
facet_count=int.from_bytes(actual_bytes[80:84],'little')
facet_dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
actual_facets=np.frombuffer(actual_bytes,offset=84,dtype=facet_dtype,count=facet_count)['vertices']
candidate_vertices=s['after'].astype(np.float32).astype(np.float64)
assert np.array_equal(actual_facets,candidate_vertices[faces]),'Actual STL differs from candidate solution'
versions={'v0.5':s['reference_v5'],'v0.7':s['before'],args.label:candidate_vertices}
def chunks(mask):
    ii=np.flatnonzero(mask)
    return np.split(ii,np.where(np.diff(ii)>1)[0]+1) if len(ii) else []
def metric(x):
    select=(ys>=4)&(ys<=12);xx=x[select];yy=ys[select]
    if not np.isfinite(xx).all():return None
    chord=np.interp(yy,[4,12],[xx[0],xx[-1]]);sag=xx-chord
    dx=savgol_filter(xx,9,3,deriv=1,delta=.25,mode='interp');ddx=savgol_filter(xx,9,3,deriv=2,delta=.25,mode='interp');theta=np.arctan(dx)
    mid=(yy>=5)&(yy<=11);dt=np.diff(theta[mid]);curv=ddx/(1+dx*dx)**1.5
    return {'chord_y_interval_mm':[4,12],'outward_sagitta_max_mm':float(sag.max()),'inward_sagitta_min_mm':float(sag.min()),
        'midpoint_sagitta_mm':float(sag[len(sag)//2]),'positive_reverse_turn_deg_y5to11':float(np.degrees(np.maximum(dt,0).sum())),
        'signed_tangent_turn_deg_y5to11':float(np.degrees(theta[mid][-1]-theta[mid][0])),
        'macro_signed_curvature_p10_p50_p90_per_mm':np.percentile(curv[mid],[10,50,90]).tolist()}
for ver,verts in versions.items():
    solid=m.Manifold(m.Mesh64(np.asarray(verts,dtype='f8'),np.asarray(faces,dtype='u8')))
    if solid.status()!=m.Error.NoError:raise RuntimeError(str(solid.status()))
    face_ids=solid.to_mesh64().face_id
    for z in heights:
        for sign in [-1,1]:
            x=np.full(len(ys),np.nan);ear=np.zeros(len(ys),bool);origfaces=np.full(len(ys),-1,int)
            for j,y in enumerate(ys):
                hits=solid.ray_cast([sign*60,float(y),float(z)],[0,float(y),float(z)])
                if not hits:continue
                h=hits[0];x[j]=abs(h.position[0]);fi=int(face_ids[h.face_id]);origfaces[j]=fi;ear[j]=bool(earface[fi])
            cap_margin=(29.5-ys-.3*z)/np.sqrt(1.09)
            eligible=np.isfinite(x)&~ear&(cap_margin>=.5)
            extrema=[];segment_reports=[]
            for indices in chunks(eligible):
                if len(indices)<9:continue
                xx=x[indices];smooth=savgol_filter(xx,9,3,mode='interp');peaks,props=find_peaks(smooth,prominence=.10,distance=3)
                widths=peak_widths(smooth,peaks,rel_height=.5)[0]*.25 if len(peaks) else []
                for k,j in enumerate(peaks):
                    if widths[k]<.75:continue
                    extrema.append({'y_mm':float(ys[indices[j]]),'x_abs_mm':float(smooth[j]),'prominence_mm':float(props['prominences'][k]),'half_prominence_width_mm':float(widths[k]),
                                    'eligible_segment_y_mm':[float(ys[indices[0]]),float(ys[indices[-1]])]})
                deriv=savgol_filter(xx,9,3,deriv=1,delta=.25,mode='interp');angles=np.arctan(deriv)
                if len(indices)>8:angles=angles[4:-4]
                segment_reports.append({'y_interval_mm':[float(ys[indices[0]]),float(ys[indices[-1]])],
                    'positive_reverse_turn_deg_trimmed_1mm_each_end':float(np.degrees(np.maximum(np.diff(angles),0).sum()))})
            records.append({'version':ver,'side':'negative_x_user_right' if sign<0 else 'positive_x','z_mm':z,
                'y_mm':ys.tolist(),'absolute_x_mm':[None if np.isnan(a) else float(a) for a in x],
                'original_face_ids':origfaces.tolist(),'excluded_original_ear_samples':ear.tolist(),'eligible_cranium_samples':eligible.tolist(),
                'metrics':metric(x),'non_ear_peaks_prominence_ge_0_1mm_width_ge_0_75mm':extrema,'non_ear_segments':segment_reports})
lookup={(r['version'],r['side'],r['z_mm']):r for r in records}
report={'units':'mm','solution':str(path),'solution_sha256':digest,'solution_unchanged_during_analysis':hashlib.sha256(path.read_bytes()).hexdigest()==digest,
    'actual_stl':str(actual_stl),'actual_stl_sha256':actual_sha,'actual_stl_matches_used_indexed_float32_geometry_exactly':True,
    'actual_stl_unchanged_during_analysis':hashlib.sha256(actual_stl.read_bytes()).hexdigest()==actual_sha,
    'versions':{'v0.5':'reference_v5 array in solution','v0.7':'before array in solution',args.label:'Actual v8 STL float32 coordinates, verified facet-by-facet against supplied indexed candidate geometry'},
    'measurement':'First head-shell ray hit from X=±60 toward X=0; no cap or hardware union. Exact indexed triangle provenance recovered with Manifold output face_id mapping.',
    'primary_metrics':'Signed midpoint sagitta on Y4..12; positive tangent reverse-turn on Y5..11 after a cubic Savitzky-Golay derivative on a 2 mm window.',
    'whole_profile_peak_screen':'Y−5..18, excluding any hit triangle incident to a visible original ear vertex and all samples within 0.5 mm of or behind the cap plane. Peaks use 0.10 mm prominence and 0.75 mm half-prominence width as diagnostic noise cutoffs, not design pass criteria. One broad cranium maximum is allowed; extra peaks plus reverse turns suggest a local bump.',
    'limits':['Not a circle/ellipse fitting target.','Original ear exclusions use the existing provenance mask, including the v7 rear-ear micro-refinement vertices.','A failed peak-count threshold alone does not prove a bad shape; source constraints and the plotted curves must be considered.','Surface/assembly/printing validators are not run here.'],
    'records':records}
(out/(args.out_prefix+'.json')).write_text(json.dumps(report,indent=2)+'\n')
fig,axes=plt.subplots(3,3,figsize=(15,12),sharex=True,layout='constrained')
colors={'v0.5':'#2067a5','v0.7':'#8e949c',args.label:'#da6434'}
for ax,z in zip(axes.flat,heights):
    ax.axvspan(4,12,color='#e7f0e7',alpha=.6,zorder=0)
    for ver in versions:
        for side,ls in [('negative_x_user_right','-'),('positive_x','--')]:
            rr=lookup[(ver,side,z)];xx=np.array([np.nan if p is None else p for p in rr['absolute_x_mm']]);
            xx[(29.5-ys-.3*z)<.5*np.sqrt(1.09)]=np.nan
            ax.plot(ys,xx,color=colors[ver],ls=ls,lw=1.6,alpha=1 if ls=='-' else .65,label=ver if ls=='-' else None)
    rr=lookup[(args.label,'negative_x_user_right',z)]
    for inds in chunks(np.array(rr['excluded_original_ear_samples'])):
        if len(inds):ax.axvspan(ys[inds[0]]-.125,ys[inds[-1]]+.125,color='#c6c6c6',alpha=.28,zorder=0)
    mm=rr['metrics'];ax.set_title(f'Z={z} mm | h={mm["midpoint_sagitta_mm"]:+.3f} mm | reverse={mm["positive_reverse_turn_deg_y5to11"]:.1f}°')
    ax.set_xlim(-5,18);ax.grid(alpha=.2);ax.set_ylabel('|X| (mm)');ax.set_xlabel('Y: front to rear (mm)')
handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside upper right',ncol=3)
fig.suptitle('Horizontal side-skull profiles — solid: user-right (−X), dashed: +X\nGreen: common metric span; gray: original ear exclusion; cap seam omitted',fontsize=14)
fig.savefig(out/(args.out_prefix+'.png'),dpi=160);plt.close(fig)
for z in heights:
    rr=lookup[(args.label,'negative_x_user_right',z)];m0=rr['metrics']
    print(z,'candidate sagitta',round(m0['midpoint_sagitta_mm'],5),'reverse_deg',round(m0['positive_reverse_turn_deg_y5to11'],3),'peaks',rr['non_ear_peaks_prominence_ge_0_1mm_width_ge_0_75mm'])
print('JSON',out/(args.out_prefix+'.json'));print('PLOT',out/(args.out_prefix+'.png'))
