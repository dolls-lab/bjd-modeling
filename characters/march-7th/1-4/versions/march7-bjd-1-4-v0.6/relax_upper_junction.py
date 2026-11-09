#!/usr/bin/env python3
"""Source-locked scalar-X fairing of the upper ear/temple junction.

Reads candidate master arrays and writes a proposed array solution only. It never
opens Blender or changes the master input, STL, source face or builder.
"""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.signal import savgol_filter
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def ramp(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t**3*(t*(t*6-15)+10)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def cotangent(v,f):
    a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    area2=np.linalg.norm(np.cross(b-a,c-a),axis=1)
    cots=np.column_stack([np.einsum('ij,ij->i',b-a,c-a),np.einsum('ij,ij->i',c-b,a-b),np.einsum('ij,ij->i',a-c,b-c)])/np.maximum(area2[:,None],1e-12)
    i=np.concatenate([f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,2],f[:,0],f[:,1]])
    data=.5*np.concatenate([cots[:,0],cots[:,1],cots[:,2]])
    W=sparse.coo_matrix((np.r_[data,data],(np.r_[i,j],np.r_[j,i])),shape=(len(v),len(v))).tocsr()
    L=sparse.diags(np.asarray(W.sum(1)).ravel())-W
    mass=np.maximum(np.bincount(f.ravel(),weights=np.repeat(area2/6,3),minlength=len(v)),1e-9)
    return L,mass
class SideRaySurface:
    def __init__(self,v,f):
        self.t=v[f];self.lo=self.t[:,:,1:].min(1);self.hi=self.t[:,:,1:].max(1)
    def x(self,y,z,sign):
        t=self.t[(self.lo[:,0]<=y+1e-10)&(self.hi[:,0]>=y-1e-10)&(self.lo[:,1]<=z+1e-10)&(self.hi[:,1]>=z-1e-10)]
        if not len(t):return np.nan
        yz=t[:,:,1:];e1=yz[:,1]-yz[:,0];e2=yz[:,2]-yz[:,0];q=np.array([y,z])-yz[:,0]
        det=e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0];valid=abs(det)>1e-12
        inv=np.zeros(len(det));inv[valid]=1/det[valid]
        u=(q[:,0]*e2[:,1]-q[:,1]*e2[:,0])*inv;w=(e1[:,0]*q[:,1]-e1[:,1]*q[:,0])*inv
        valid&=(u>=-1e-9)&(w>=-1e-9)&(u+w<=1+1e-9)
        xx=t[:,0,0]+u*(t[:,1,0]-t[:,0,0])+w*(t[:,2,0]-t[:,0,0]);xx=sign*xx[valid];xx=xx[xx>=0]
        return xx.max() if len(xx) else np.nan

def profiles(v,f):
    surface=SideRaySurface(v,f);ys=np.arange(-6,8.001,.1);rows=[]
    for sign in [-1,1]:
        for z in [36,38,40,42,44,46,48,50]:
            xx=np.array([surface.x(y,z,sign) for y in ys])
            if not np.isfinite(xx).all():raise ValueError('Missing profile sample')
            smooth=savgol_filter(xx,11,3);d=np.gradient(smooth,.1);k=np.gradient(d,.1)/(1+d*d)**1.5
            core=(ys>=-4)&(ys<=4)
            rows.append({'side':sign,'z_mm':z,'y_mm':ys.tolist(),'x_mm':xx.tolist(),
                         'curvature_per_mm':k.tolist(),'core_peak_abs_curvature_per_mm':float(abs(k[core]).max()),
                         'core_p95_abs_curvature_per_mm':float(np.quantile(abs(k[core]),.95))})
    peaks=np.array([r['core_peak_abs_curvature_per_mm'] for r in rows if 38<=r['z_mm']<=48])
    return rows,{'peak_curvature_max_per_mm':float(peaks.max()),'peak_curvature_mean_per_mm':float(peaks.mean())}

def main():
    frozen_input=ROOT/'upper-junction-input.npz'
    input_master=frozen_input if frozen_input.exists() else ROOT/'master-deformation.npz'
    inputs=[input_master,ROOT/'v6-side-protection.npz',ROOT/'parameters.json']
    hashes={p.name:digest(p) for p in inputs}
    data=np.load(inputs[0]);protection=np.load(inputs[1]);v=data['after'].copy();f=protection['master_baseline_triangles'].copy()
    source_locked=protection['master_locked'];x,y,z=v.T
    # Five-mm vertical collars and four-mm posterior collar prevent a new
    # transition line at the rectangular ROI. Original source stays exact.
    weights=ramp(32,37,z)*(1-ramp(48,53,z))*ramp(-5,-3,y)*(1-ramp(6,10,y))*ramp(20,22,abs(x))
    weights*=ramp(4,7,29.5-y-.3*z)
    report0=json.loads((ROOT/'build-report.json').read_text())
    for center in report0['magnet_centers_mm']:
        weights*=ramp(7,12,np.linalg.norm(v-np.array(center),axis=1))
    weights[source_locked]=0
    free=np.flatnonzero(weights>1e-5);fixed=np.flatnonzero(weights<=1e-5)
    L,mass=cotangent(v,f);C=(L.T@sparse.diags(1/mass)@L).tocsr()
    Cff=C[free][:,free].tocsc();rhs=-(C[free][:,fixed]@x[fixed])
    baseline_profiles,base_profile_stats=profiles(v,f)
    curvature0=L@x;energy0=float(np.sum(curvature0[free]**2/mass[free]))
    core=(abs(x)>20)&(y>-4)&(y<5)&(z>=38)&(z<=48)&(~source_locked)
    baseline_cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    baseline_len=np.linalg.norm(baseline_cross,axis=1)
    trials=[];solutions=[]
    for alpha in [.1,.3,1.]:
        prior=alpha*mass[free]/np.maximum(weights[free],.01)**2
        xx=spsolve(Cff+sparse.diags(prior),rhs+prior*x[free]);after=v.copy();after[free,0]=xx
        delta=after[:,0]-x;curvature=L@after[:,0]
        cross=np.cross(after[f[:,1]]-after[f[:,0]],after[f[:,2]]-after[f[:,0]]);lens=np.linalg.norm(cross,axis=1)
        dots=np.einsum('ij,ij->i',baseline_cross,cross)/np.maximum(baseline_len*lens,1e-30)
        ps,pstats=profiles(after,f)
        eligible=bool(abs(delta).max()<=.6 and np.array_equal(after[source_locked],v[source_locked]) and np.array_equal(after[z<=32],v[z<=32]) and np.array_equal(after[:,1:],v[:,1:]) and (lens>1e-12).all())
        rec={'alpha':alpha,'maximum_displacement_mm':float(abs(delta).max()),'p95_free_displacement_mm':float(np.quantile(abs(delta[free]),.95)),
             'signed_displacement_range_mm':[float(delta.min()),float(delta.max())],
             'local_x_bending_energy':float(np.sum(curvature[free]**2/mass[free])),
             'core_x_bending_energy':float(np.sum(curvature[core]**2/mass[core])),
             'maximum_triangle_normal_rotation_degrees':float(np.degrees(np.arccos(np.clip(dots.min(),-1,1)))),
             'triangles_over_90deg':int((dots<0).sum()),'degenerate_triangles':int((lens<=1e-12).sum()),
             'source_locked_max_displacement_mm':float(abs(delta[source_locked]).max()),
             'below_z32_max_displacement_mm':float(abs(delta[z<=32]).max()),'profile_stats':pstats,'eligible':eligible}
        print(json.dumps(rec),flush=True);trials.append(rec);solutions.append((after,ps))
    candidates=[i for i,r in enumerate(trials) if r['eligible'] and r['profile_stats']['peak_curvature_max_per_mm']<=base_profile_stats['peak_curvature_max_per_mm']*1.02]
    if not candidates:raise RuntimeError('No bounded trial without peak profile regression')
    choice=min(candidates,key=lambda i:trials[i]['profile_stats']['peak_curvature_mean_per_mm'])
    after,after_profiles=solutions[choice];chosen=trials[choice]
    for path in inputs:
        if digest(path)!=hashes[path.name]:raise RuntimeError('Input changed during solve')
    np.savez_compressed(ROOT/'upper-junction-solution.npz',vertices_before=v,vertices_after=after,triangles=f,free=free,fixed=fixed,weights=weights,source_locked=source_locked,field=after-v,selected_alpha=np.array(chosen['alpha']),input_master_npz_sha256=np.array(hashes[inputs[0].name]))
    report={'method':'Constrained scalar-X cotangent bi-Laplacian fairing with mass-weighted candidate-position prior; Y/Z, original source and lower ear root exact fixed; no pointwise clipping.',
            'inputs_sha256':hashes,'free_vertices':int(len(free)),'fixed_vertices':int(len(fixed)),
            'region':{'z_support_mm':[32,53],'z_full_mm':[37,48],'y_support_mm':[-5,10],'y_full_mm':[-3,6],'abs_x_support_mm':20,'cap_margin_support_mm':4,'mechanical_magnet_guard_mm':[7,12]},
            'baseline_x_bending_energy':energy0,'baseline_core_x_bending_energy':float(np.sum(curvature0[core]**2/mass[core])),
            'baseline_profile_stats':base_profile_stats,'trials':trials,'selected':chosen,
            'selection':'Among bounded trials and no >2% maximum-profile-curvature regression, lowest average maximum curvature across +/-X sections at Z38..48.',
            'before_profiles':baseline_profiles,'after_profiles':after_profiles,
            'limitations':['Only an array proposal; not a modified Blender model or STL.','Selected 1mm-filtered section curvature is not an exhaustive aesthetic or C2 continuity proof.','Final shared-wall transfer, collision, thickness and identical-light render still require verification.']}
    (ROOT/'upper-junction-report.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axs=plt.subplots(2,3,figsize=(12,7))
    for col,zz in enumerate([40,44,48]):
        for label,rows,color in [('candidate4',baseline_profiles,'#b95f4b'),('local fair',after_profiles,'#087e8b')]:
            rr=next(r for r in rows if r['side']==1 and r['z_mm']==zz)
            axs[0,col].plot(rr['y_mm'],rr['x_mm'],label=label,color=color)
            axs[1,col].plot(rr['y_mm'],rr['curvature_per_mm'],label=label,color=color)
        axs[0,col].set(title=f'Z={zz} mm',xlabel='Y (mm)',ylabel='X (mm)');axs[1,col].set(xlabel='Y (mm)',ylabel='Curvature (1/mm)')
        for ax in axs[:,col]:ax.grid(alpha=.3);ax.legend(fontsize=8)
    fig.suptitle(f'Upper junction only: alpha={chosen["alpha"]}, max move={chosen["maximum_displacement_mm"]:.3f} mm')
    fig.tight_layout();fig.savefig(ROOT/'upper-junction-profiles.png',dpi=160)
    print(json.dumps({'selected':chosen,'baseline_profiles':base_profile_stats,'solution_sha256':digest(ROOT/'upper-junction-solution.npz')},indent=2))
if __name__=='__main__':main()
