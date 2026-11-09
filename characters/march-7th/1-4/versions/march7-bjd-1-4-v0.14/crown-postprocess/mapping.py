"""v14 crown: smooth global outer X map, actual internal hardware protected."""
import numpy as np
ORIGIN=np.array([0.,14.5,50.]);N=np.array([0.,1.,.3]);N=N/np.linalg.norm(N);V=np.array([0.,N[2],-N[1]])
MAGNET_X=16.63362693786621
PIN=np.array([0.,11.274858474731445,60.75047302246094]);MAGNETS=[np.array([-MAGNET_X,14.5,50.]),np.array([MAGNET_X,14.5,50.])]
START=48.;FULL=67.;GAIN=.08

def smoother(t):
 t=np.clip(t,0.,1.);return t*t*t*(10+t*(-15+6*t))
def mapping(p,outer_distance,return_weights=False):
 p=np.asarray(p,dtype=float);u=p[:,0];z=p[:,2]
 weights=smoother((z-START)/(FULL-START))
 dm=np.minimum(np.linalg.norm(p-MAGNETS[0],axis=1),np.linalg.norm(p-MAGNETS[1],axis=1));dp=np.linalg.norm(p-PIN,axis=1)
 hardware=np.minimum(smoother((dm-5.5)/3),smoother((dp-4.8)/3.5))
 # Skin stays on one smooth curve. Fade hardware locks through shell thickness,
 # protecting real internal bore/pin surfaces instead of projecting pillars onto scalp.
 interior=smoother((np.asarray(outer_distance)-.65)/.9)
 weights*=1-interior*(1-hardware)
 q=p-ORIGIN;v=q[:,1]*V[1]+q[:,2]*V[2];normal=q[:,1]*N[1]+q[:,2]*N[2];pv=np.sum((PIN-ORIGIN)*V)
 rm=np.minimum(np.hypot(u-MAGNET_X,v),np.hypot(u+MAGNET_X,v));rp=np.hypot(u,v-pv)
 # Analytic bore/pin core, independent of distance to outer skin: thin blind
 # bottoms must retain their exact original mating diameter and depth.
 exact=((rm<=2.30)&(np.abs(normal)<=2.65))|((rp<=2.40)&(normal>=-1.10)&(normal<=4.20))
 mechanical=((interior>=1)&((dm<=5.5)|(dp<=4.8)))|exact
 weights[mechanical]=0.
 out=p.copy();out[:,0]=u*(1+GAIN*weights)
 if return_weights:return out,weights,mechanical,{'outer_distance_mm':np.asarray(outer_distance),'interior_weight':interior,'magnet_distance':dm,'pin_distance':dp}
 return out
