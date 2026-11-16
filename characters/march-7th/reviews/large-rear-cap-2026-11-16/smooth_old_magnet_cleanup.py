"""Optional read-only source-derived cutters to erase old seam's filled magnet bosses.
No old mesh/files are written. Work in quarter-size old seam coordinates. API:
cutters, report = make_old_magnet_cutters(source_head_tm, source_cap_tm, scale)
Returns 2 manifold cutters in world mm. Apply to closed rejoined head.
"""
import sys
sys.path.insert(0,'/private/tmp/bjd-hook-groove-deps')
import numpy as np, trimesh, manifold3d as mf
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d

def make_old_magnet_cutters(head,cap,scale=1.,source_parameters=None):
    normal=np.array([0.,1.,.3]);normal/=np.linalg.norm(normal)
    R=np.column_stack([np.array([1.,0,0]),np.cross(normal,[1.,0,0]),normal]);O=np.array([0.,14.5,50.])*scale
    solids=[]
    for tm in [head,cap]:
        vv=np.einsum('ij,kj->ki',R.T,(np.asarray(tm.vertices)-O)/scale)
        solids.append(mf.Manifold(mf.Mesh64(vv,np.asarray(tm.faces,np.uint64))))
    # Close old blind holes only in the sampling solid; caller performs final hole fill.
    if source_parameters is None:
        raise ValueError('Pass source_parameters=p["inherited_source_parameters"] for exact old magnet pockets')
    filled=[]
    rp=source_parameters['magnet_hole_diameter_mm']/2/scale+.03/scale
    dep=source_parameters['magnet_hole_depth_mm']/scale
    for index,so in enumerate(solids):
        for center in source_parameters['magnet_centers_mm']:
            z0=-dep-.01/scale if index==0 else .25
            cy=mf.Manifold.cylinder(dep+.01/scale,rp,rp,192,False).translate((center[0]/scale,0.,z0))
            so=so+cy
        filled.append(so)
    ws=np.r_[np.linspace(-7.0,-.035,140),np.linspace(.285,7.0,135)]
    vs=np.r_[np.linspace(-8.,-5.1,21),np.linspace(5.1,8.,21)]
    cutters=[];reports=[]
    for sign in [-1.,1.]:
        coeff=[];residual=[]
        for w in ws:
            vv=[];uu=[]
            ob=solids[0 if w<0 else 1]
            for v in vs:
                hits=ob.ray_cast((0.,float(v),float(w)),(sign*40.,float(v),float(w)))
                inner=[h for h in hits if h.normal[0]*sign<-.04]
                if inner:
                    vv.append(v);uu.append(min(h.position[0]*sign for h in inner))
            vv=np.array(vv);uu=np.array(uu)
            assert len(vv)>=12
            des=np.column_stack([np.ones(len(vv)),vv,vv**2,vv**3])
            co=np.linalg.lstsq(des,uu**2,rcond=None)[0]
            coeff.append(co);residual.append(float(np.max(np.abs(np.sqrt(np.maximum(des@co,0))-uu))))
        # Gentle axial fit regularization avoids following voxel-scale ray noise.
        co=np.asarray(coeff)
        co=np.vstack([gaussian_filter1d(co[:140],1.5,axis=0),gaussian_filter1d(co[140:],1.5,axis=0)])
        spline=CubicSpline(ws,co,axis=0)
        gv=np.linspace(-5.1,5.1,205);gw=np.linspace(-6.5,6.5,261)
        V,W=np.meshgrid(gv,gw,indexing='ij');C=spline(W)
        U=np.sqrt(np.maximum(0,C[:,:,0]+C[:,:,1]*V+C[:,:,2]*V**2+C[:,:,3]*V**3))-.22
        U=np.maximum(.1,U)
        def sample_inner_u(v,w):
            def get(q):
                ob=filled[0 if q<0 else 1]
                hits=ob.ray_cast((0.,float(v),float(q)),(sign*40.,float(v),float(q)))
                inner=[h.position[0]*sign for h in hits if h.normal[0]*sign<0]
                assert inner, (v,q)
                return min(inner)
            if w<-.035 or w>.285:return get(w)
            t=(w+.035)/.32
            return (1-t)*get(-.035)+t*get(.285)
        def smstep(t):
            t=np.clip(t,0.,1.);return t*t*t*(10-15*t+6*t*t)
        def blend_target(src,fit,v,w):
            k=.6
            h=np.maximum(0.,1-np.abs(src-fit)/k)
            rounded=np.maximum(src,fit)+k*h**3/6
            weight=(1-smstep((np.abs(v)-4.6)/.5))*(1-smstep((np.abs(w)-6.3)/.2))
            return src+weight*(rounded-src)-.002
        SRC=np.array([[sample_inner_u(v,w) for w in gw] for v in gv])
        U=blend_target(SRC,U,V,W)
        verts=[]
        for lower in [True,False]:
            xx=np.zeros_like(U) if lower else sign*U
            verts.extend(np.stack([xx,V,W],axis=-1).reshape(-1,3))
        nv,nw=V.shape;N=nv*nw;faces=[]
        for i in range(nv-1):
            for j in range(nw-1):
                a=i*nw+j;b=(i+1)*nw+j
                faces.extend([(a,a+1,b+1),(a,b+1,b),(a+N,b+N,b+1+N),(a+N,b+1+N,a+1+N)])
        for i in range(nv-1):
            for j in [0,nw-1]:
                a=i*nw+j;b=(i+1)*nw+j
                faces.extend([(a,b,b+N),(a,b+N,a+N)] if j==0 else [(a,a+N,b+N),(a,b+N,b)])
        for j in range(nw-1):
            for i in [0,nv-1]:
                a=i*nw+j;b=a+1
                faces.extend([(a,a+N,b+N),(a,b+N,b)] if i==0 else [(a,b,b+N),(a,b+N,a+N)])
        tm=trimesh.Trimesh(np.asarray(verts),np.asarray(faces),process=False)
        if tm.volume<0:tm.invert()
        assert tm.is_watertight and tm.is_winding_consistent
        tm.vertices=np.einsum('ij,kj->ki',R,np.asarray(tm.vertices)*scale)+O
        cutter=mf.Manifold(mf.Mesh64(np.asarray(tm.vertices),np.asarray(tm.faces,np.uint64)))
        assert cutter.status()==mf.Error.NoError
        cutters.append(cutter)
        # Wall chord along local u: fitted boundary remains safely inside actual outer wall.
        chords=[];boundary_overcut=[];sampled=0
        for w in np.r_[np.linspace(-6.5,-.035,66),np.linspace(.285,6.5,64)]:
            ob=solids[0 if w<0 else 1];c=spline(w)
            for v in np.linspace(-5.1,5.1,103):
                hits=ob.ray_cast((0.,float(v),float(w)),(sign*40.,float(v),float(w)))
                enter=[h.position[0]*sign for h in hits if h.normal[0]*sign<0]
                leave=[h.position[0]*sign for h in hits if h.normal[0]*sign>0]
                if not enter or not leave:continue
                source_u=min(enter);fit=max(.1,np.sqrt(max(0,c@[1.,v,v*v,v**3]))-.22);target=float(blend_target(sample_inner_u(v,w),fit,v,w))
                if target>source_u:
                    chords.append(max(leave)-target);sampled+=1
                if abs(v)>5.09 or w< -6.49 or w>6.49:
                    boundary_overcut.append(max(0,target-source_u))
        reports.append({'sign':sign,'fit':'cubic u-squared fit minus .22 mm; C2 smooth maximum with actual filled source inner X, blend radius .6mm, compact taper v4.6..5.1 w6.3..6.5; .002mm sampling inset',
          'quarter_bounds':{'v':[-5.1,5.1],'w':[-6.5,6.5]},'max_fit_ray_residual_q_mm':max(residual),'minimum_sampled_radial_wall_chord_q_mm':min(chords) if chords else None,
          'max_boundary_cut_q_mm':max(boundary_overcut),'removed_surface_ray_samples':sampled})
    return cutters, reports
