import numpy as np
from types import SimpleNamespace

class RawSurface:
 """Ray intersections against an open master, without filling or changing it."""
 def __init__(self,vertices,faces):
  self.triangles=np.asarray(vertices)[np.asarray(faces)]
  self.lo=self.triangles.min(1);self.hi=self.triangles.max(1)
 def ray_cast(self,origin,endpoint):
  origin=np.array(origin,float);d=np.array(endpoint,float)-origin
  mask=np.ones(len(self.triangles),bool)
  for axis in range(3):
   if abs(d[axis])<1e-12:mask&=(self.lo[:,axis]<=origin[axis]+1e-10)&(self.hi[:,axis]>=origin[axis]-1e-10)
  tri=self.triangles[mask]
  if not len(tri):return []
  e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];q=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,q)
  valid=abs(det)>1e-12;inv=np.zeros(len(tri));inv[valid]=1/det[valid]
  a=origin-tri[:,0];u=np.einsum('ij,ij->i',a,q)*inv;cross=np.cross(a,e1)
  v=np.einsum('j,ij->i',d,cross)*inv;t=np.einsum('ij,ij->i',e2,cross)*inv
  valid&=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>=0)&(t<=1)
  return [SimpleNamespace(position=origin+x*d) for x in sorted(t[valid])]

