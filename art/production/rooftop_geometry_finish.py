"""Moulded chair silhouette and smooth coincident normals for curved surfaces."""
import math
import numpy as np
from build_models import Mesh,tube

def chair(R):
    o=Mesh('prop_plastic_chair')
    # Rounded, slightly dished injection-moulded seat. Solid rim and underside.
    n=40;v=[];f=[];uv=[]
    for j in range(4):
        for i in range(n):
            a=math.tau*i/n
            x=.225*np.sign(math.cos(a))*abs(math.cos(a))**.35
            y=.225*np.sign(math.sin(a))*abs(math.sin(a))**.35
            scale=[.0,.88,1.,1.][j];z=[.438,.442,.453,.422][j]
            v.append([x*scale,y*scale,z]);uv.append([x*scale/.45+.5,y*scale/.45+.5])
    for j in range(3):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;f.extend([[a,b,b+n],[a,b+n,a+n]])
    o.add(v,f,'redplastic',uv)
    # Flared rectangular channel legs, wider at the seat and splayed at the foot.
    for side in [-1,1]:
        for back in [-1,1]:
            v=[];uv=[];f=[]
            for j,z in enumerate([0,.05,.36,.43]):
                cx=side*(.225-z*.09);cy=back*(.225-z*.10)
                w=.018+z*.025;d=.014+z*.012
                for x,y in [(-w,-d),(w,-d),(w,d),(-w,d)]:v.append([cx+x,cy+y,z]);uv.append([x*9+.5,z*2])
            for j in range(3):
                for i in range(4):
                    a=j*4+i;b=j*4+(i+1)%4;f.extend([[a,b,b+4],[a,b+4,a+4]])
            o.add(v,f,'redplastic',uv)
    # Bowed back, rounded top and integrated vertical slots.
    nx=24;ny=12;v=[];uv=[];f=[]
    for j in range(ny+1):
        t=j/ny
        for i in range(nx+1):
            s=2*i/nx-1;x=s*(.217+.018*math.sin(t*math.pi))
            z=.45+t*(.40-.055*s*s);y=.19+t*.075+.032*(1-s*s)
            v.append([x,y,z]);uv.append([i/nx,t])
    for j in range(ny):
        for i in range(nx):
            if 2<=j<9 and i in [5,6,10,11,15,16,19,20]:continue
            a=j*(nx+1)+i;b=a+nx+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,'redplastic',uv)
    for s in [-1,1]:
        tube(o,[(s*.214,.19,.45),(s*.233,.25,.67),(s*.217,.265,.795)],.010,'redplastic',6)
        # Arms sweep into the rear shell; useful for the familiar monobloc outline.
        tube(o,[(s*.217,-.12,.45),(s*.245,-.13,.61),(s*.245,.10,.64),(s*.225,.24,.67)],[.012,.017,.018,.012],'redplastic',8)
    tube(o,[(s*.217,.265+.032*(1-s*s),.85-.055*s*s) for s in np.linspace(-1,1,17)],.010,'redplastic',6)
    return o

def apply(R):
    previous=R.hand_props
    def props():
        previous()
        for i,(name,budget,objects) in enumerate(R.ASSETS):
            if name=='prop_plastic_chair':R.ASSETS[i]=(name,budget,[chair(R).fit(height=.85)])
    R.hand_props=props
    old=R.b.smooth_normals
    def normals(v,f):
        n=old(v,f);out=n.copy();groups={}
        for i,p in enumerate(v):groups.setdefault(tuple(np.round(p,7)),[]).append(i)
        for ids in groups.values():
            if len(ids)<2:continue
            a=n[ids]
            for j,idx in enumerate(ids):
                compatible=a@a[j]>.7;avg=a[compatible].sum(0);out[idx]=avg/max(np.linalg.norm(avg),1e-12)
        return out
    R.b.smooth_normals=normals
