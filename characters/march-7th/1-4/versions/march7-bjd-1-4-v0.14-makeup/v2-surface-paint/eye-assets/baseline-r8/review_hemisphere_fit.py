"""Read-only QA of two genuine hollow front-hemisphere eye cups on actual v14."""
from pathlib import Path
import argparse,hashlib,json,time,math
import numpy as np
from scipy import ndimage
import trimesh
import manifold3d as md

R=Path(__file__).resolve().parent
HEAD_ROOT=next(x for x in R.parents if x.name=='outputs')/'march7-bjd-1-4-v0.14'
HEAD=HEAD_ROOT/'march7-head-shell-v0.14-draft.stl'
GEOMETRY=R/'hemisphere-eye-geometry.npz'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def manifold(mesh):
    return md.Manifold(md.Mesh64(np.ascontiguousarray(mesh.vertices,dtype=np.float64),np.ascontiguousarray(mesh.faces,dtype=np.uint64)))

def find_aperture(head,center,pitch):
    n=int(np.ceil(24/pitch));off=(np.arange(n)+.5-n/2)*pitch
    xs,zs=center[0]+off,center[2]+off;clear=np.zeros((n,n),bool)
    for j,z in enumerate(zs):
        for i,x in enumerate(xs):
            clear[j,i]=not head.ray_cast((float(x),-45.,float(z)),(float(x),float(center[1]),float(z)))
    labels,count=ndimage.label(clear,ndimage.generate_binary_structure(2,1))
    index=int(labels[np.argmin(abs(zs-center[2])),np.argmin(abs(xs-center[0]))])
    if index==0:raise RuntimeError('Eye-center aperture is blocked by head')
    mask=labels==index
    if mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any():raise RuntimeError('Selected aperture reaches exterior ROI')
    j,i=np.nonzero(mask);return xs[i],zs[j],dict(sample_count=int(mask.sum()),area_mm2=float(mask.sum()*pitch*pitch),width_mm=float((i.max()-i.min()+1)*pitch),height_mm=float((j.max()-j.min()+1)*pitch),clear_components=int(count))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expected-eye-sha256',required=True)
    ap.add_argument('--expected-head-sha256',default='d3ac436defacb1db2a9aca6da84b8e6f4fe3ee995591e095e5ac43b9624b7ada')
    ap.add_argument('--pitch-mm',type=float,default=.05)
    a=ap.parse_args();started=time.time()
    hhead,heye=sha(HEAD),sha(GEOMETRY)
    if hhead!=a.expected_head_sha256 or heye!=a.expected_eye_sha256:raise RuntimeError('Input SHA mismatch')
    report_path=HEAD_ROOT/'build-report.json';hb=sha(report_path)
    build=json.loads(report_path.read_text());centers=sorted(build['eye_centers_mm'],key=lambda c:c[0])
    head_mesh=trimesh.load_mesh(HEAD,process=True,validate=False);head=manifold(head_mesh)
    if head.status()!=md.Error.NoError:raise RuntimeError('Final actual head is not usable for Boolean/rays')
    data=np.load(GEOMETRY)
    cups=[];parts=[]
    for label,center in zip(('negative','positive'),centers):
        center=np.array(center,dtype=float)
        v=np.asarray(data['vertices_'+label],dtype=float);f=np.asarray(data['faces_'+label],dtype=int)
        mesh=trimesh.Trimesh(v,f,process=False);cup=manifold(mesh);cups.append(cup)
        q=v-center;rad=np.linalg.norm(q,axis=1)
        tol=1e-4;outer=np.abs(rad-8.)<=tol;inner=np.abs(rad-7.4)<=tol
        edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
        labels_mesh=trimesh.graph.connected_component_labels(mesh.face_adjacency,node_count=len(f))
        components=int(len(np.unique(labels_mesh)))
        topology={'vertices':len(v),'triangles':len(f),'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),'positive_volume':bool(mesh.volume>0),'volume_mm3':float(mesh.volume),'analytic_hemisphere_wall_volume_mm3':float(2*math.pi/3*(8.**3-7.4**3)),'face_components':components,'boundary_edges':int((counts==1).sum()),'nonmanifold_edges':int((counts>2).sum()),'euler_number':int(mesh.euler_number),'manifold_status':str(cup.status())}
        domain={'center_mm':center.tolist(),'front_direction':[0,-1,0],'outer_design_radius_mm':8.,'inner_design_radius_mm':7.4,'nominal_radial_wall_mm':.6,'vertex_radius_tolerance_mm':tol,'outer_radius_vertex_count':int(outer.sum()),'inner_radius_vertex_count':int(inner.sum()),'vertices_on_neither_design_radius':int((~(outer|inner)).sum()),'maximum_outer_radius_error_mm':None if not outer.any() else float(abs(rad[outer]-8).max()),'maximum_inner_radius_error_mm':None if not inner.any() else float(abs(rad[inner]-7.4).max()),'relative_y_min_max_mm':[float(q[:,1].min()),float(q[:,1].max())],'back_plane_domain_excess_mm':float(max(0,q[:,1].max())),'rim_vertex_count':int((abs(q[:,1])<=tol).sum())}
        geometry_pass=(topology['watertight'] and topology['winding_consistent'] and topology['positive_volume'] and components==1 and cup.status()==md.Error.NoError and domain['vertices_on_neither_design_radius']==0 and outer.any() and inner.any() and domain['back_plane_domain_excess_mm']<=tol)
        if cup.status()!=md.Error.NoError:
            parts.append({'eye':label,'topology':topology,'domain':domain,'pass':False,'reason':'Invalid cup solid; remaining solid checks not meaningful'})
            continue
        intersection=head^cup;ivol=float(intersection.volume());clearance=float(head.min_gap(cup,1.)) if abs(ivol)<=1e-5 else 0
        fit={'head_intersection_volume_mm3':ivol,'head_intersection_empty':bool(intersection.is_empty()),'head_intersection_status':str(intersection.status()),'minimum_head_clearance_mm_search_limit1':clearance,'pass':intersection.status()==md.Error.NoError and abs(ivol)<=1e-5}
        # A real open-back cup has no disc closing the cavity at its equator.
        rear_tests=[]
        for radius in (0.,3.7,7.0):
            start=center+np.array([radius,1.,0]);end=center+np.array([radius,-.05,0]);hh=cup.ray_cast(start.tolist(),end.tolist())
            rear_tests.append({'offset_radius_mm':radius,'hit_count':len(hh),'clear':not hh})
        rear_open=all(t['clear'] for t in rear_tests)
        xx,zz,aperture=find_aperture(head,center,a.pitch_mm)
        rho2=(xx-center[0])**2+(zz-center[2])**2;rho=np.sqrt(rho2);analytic_ok=rho2<=64.
        analytic_y=center[1]-np.sqrt(np.maximum(0,64-rho2));missing=[];depth_errors=[];normals=[];radial_errors=[]
        for k,(x,z) in enumerate(zip(xx,zz)):
            hh=cup.ray_cast((float(x),-45.,float(z)),(float(x),float(center[1]),float(z)))
            if not hh:
                missing.append([float(x),float(z)])
                continue
            first=hh[0];point=np.array(first.position)
            depth_errors.append(float(point[1]-analytic_y[k]));normals.append(first.normal[1]);radial_errors.append(float(abs(np.linalg.norm(point-center)-8.)))
        coverage={'sample_pitch_mm':a.pitch_mm,'head_aperture':aperture,'analytic_front_hemisphere_missed_rays':int((~analytic_ok).sum()),'analytic_maximum_radial_deficit_mm':float(max(0,rho.max()-8)),'analytic_minimum_radial_margin_mm':float(8-rho.max()),'actual_cup_missing_rays':len(missing),'actual_cup_missing_area_mm2':float(len(missing)*a.pitch_mm*a.pitch_mm),'actual_cup_missing_xz_mm':missing[:100],'actual_first_hit_front_facing_count':int((np.array(normals)<0).sum()),'actual_first_hit_count':len(normals),'actual_vs_analytic_front_y_error_mm':None if not depth_errors else {'min':float(np.min(depth_errors)),'mean':float(np.mean(depth_errors)),'max':float(np.max(depth_errors))},'actual_outer_surface_radial_error_max_mm':None if not radial_errors else float(max(radial_errors)),'pass':not missing and bool(analytic_ok.all()) and bool(np.all(np.array(normals)<0))}
        parts.append({'eye':label,'topology':topology,'domain':domain,'head_fit':fit,'back_cavity_tests':rear_tests,'back_open':rear_open,'frontal_aperture_coverage':coverage,'pass':bool(geometry_pass and fit['pass'] and rear_open and coverage['pass'])})
        print('EYE_DONE',label,json.dumps({'pass':parts[-1]['pass'],'volume':topology['volume_mm3'],'intersection_mm3':ivol,'clearance_mm':clearance,'missing_rays':len(missing),'aperture_samples':aperture['sample_count']}),flush=True)
    pair_volume=None
    if len(cups)==2 and all(c.status()==md.Error.NoError for c in cups):pair_volume=float((cups[0]^cups[1]).volume())
    assert sha(HEAD)==hhead and sha(GEOMETRY)==heye and sha(report_path)==hb
    result={'units':'mm','sources':{'head_stl':{'path':str(HEAD),'sha256':hhead},'hemisphere_eye_geometry':{'path':str(GEOMETRY),'sha256':heye},'build_report':{'path':str(report_path),'sha256':hb}},'all_inputs_unchanged':True,'parts':parts,'left_right_cup_intersection_volume_mm3':pair_volume,'pass':all(p['pass'] for p in parts) and pair_volume is not None and abs(pair_volume)<=1e-5,'method':'Actual independent solid hemisphere-cup meshes versus the actual unchanged v14 head. Original flat eye meshes are not used. Head-clear frontal +Y rays on0.05mm XZ grid are tested against both the analytic R8 front hemisphere and the actual cup mesh.','limitations':['Coverage applies to the sampled frontal orthographic view, not every viewing angle or subpixel location.','Analytic R8 comparison describes nominal spherical geometry; triangulated surfaces have small faceting deviations.','Closed positive wall volume describes the cup material. The rear cavity is intentionally open and tested independently.','No insertion path, full-head structural test, physical print tolerance or strength certification was performed.'],'duration_seconds':time.time()-started}
    (R/'hemisphere-eye-fit-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('FINAL',json.dumps({'pass':result['pass'],'report':str(R/'hemisphere-eye-fit-review.json'),'sha256':heye}),flush=True)

if __name__=='__main__':main()
