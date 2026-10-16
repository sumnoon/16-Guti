"""Project the generated neutral portrait onto a shaped static head."""
import math
import numpy as np
from PIL import Image,ImageFilter
from build_models import Mesh,ellipsoid,tube
R=None

def uv_face(v):
    # Landmarks measured in the generated source: chin, lips, nose, eyes, hairline.
    z=np.asarray(v)[:,2]
    vv=np.interp(z,[1.47,1.49,1.55,1.585,1.625,1.68,1.745],[.92,.88,.74,.63,.49,.26,.03])
    return np.column_stack([np.clip(.5+np.asarray(v)[:,0]*3.67,.23,.77),vv])

def head(o,pose):
    start=len(o.parts);tmp=Mesh('head');v=[];f=[];n=32
    rings=[(1.47,.026,.031,-.022),(1.49,.049,.045,-.019),(1.515,.063,.057,-.012),(1.55,.075,.067,-.005),(1.585,.082,.076,0),(1.61,.083,.076,.003),(1.635,.081,.074,.006),(1.66,.080,.077,.010),(1.69,.077,.075,.014),(1.72,.062,.061,.017),(1.74,.035,.036,.018),(1.745,0,0,.018)]
    for z,rx,ry,cy in rings:
        for i in range(n+1):
            a=math.tau*i/n;x=rx*math.cos(a);y=cy+ry*math.sin(a)
            if math.sin(a)<0:
                # Broader cheek plane, eye sockets, nasal bridge, muzzle and chin.
                y=cy-ry*(max(0,1-(x/max(rx,1e-6))**2)**.32)
                y+=.009*math.exp(-((abs(x)-.030)/.015)**2-((z-1.625)/.015)**2)
                y-=.012*math.exp(-(x/.031)**2-((z-1.55)/.024)**2)
            v.append([x,y,z])
    v=np.array(v)
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*(n+1)+i;f.extend([[a,a+1,a+n+2],[a,a+n+2,a+n+1]])
    f=np.array(f);front=v[f].mean(1)[:,1]<0
    o.add(v,f[front],'face',uv_face(v))
    o.add(v,f[~front],'skin',np.column_stack([v[:,0]*3,v[:,2]*3]))
    # Nose surface is textured from the same portrait and aligned to its landmarks.
    nv=np.array([[-.010,-.073,1.65],[.010,-.073,1.65],[0,-.097,1.61],[-.019,-.082,1.587],[.019,-.082,1.587],[0,-.109,1.589],[0,-.087,1.576]])
    o.add(nv,[[0,1,2],[0,2,3],[1,4,2],[2,4,5],[2,5,3],[3,5,6],[5,4,6]],'face',uv_face(nv))
    for x in [-.083,.083]:ellipsoid(o,(x,.012,1.598),(.012,.016,.027),'skin',8,5)
    # Textured hair cap follows the cranial surface with a subtly irregular hairline.
    hv=[];hf=[];hu=[]
    for j in range(6):
        for i in range(33):
            a=math.tau*i/32;p=(j/5)*(1.79+.34*math.sin(a)+.025*math.sin(5*a))
            hv.append([.085*math.sin(p)*math.cos(a),.015+.081*math.sin(p)*math.sin(a),1.683+.064*math.cos(p)]);hu.append([i/32,j/5])
    for j in range(5):
        for i in range(32):
            a=j*33+i;hf.extend([[a,a+33,a+1],[a+1,a+33,a+34]])
    o.add(hv,hf,'hair',hu)
    if pose in ['cheer','fire']:
        # A small mouth aperture retains the action pose; surrounding lips use the source.
        mv=np.array([[-.017,-.083,1.550],[.017,-.083,1.550],[.013,-.085,1.536],[-.013,-.085,1.536]])
        o.add(mv,[[0,1,2],[0,2,3]],'mouth')
    pitch={'hold':-.03,'point':-.18,'cheer':-.12,'fire':-.40}[pose];yaw={'hold':.10,'point':-.18,'cheer':.16,'fire':0}[pose]
    rx=np.array([[1,0,0],[0,math.cos(pitch),-math.sin(pitch)],[0,math.sin(pitch),math.cos(pitch)]]);rz=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
    pivot=np.array([0,0,1.46])
    for part in o.parts[start:]:part[0]=(part[0]-pivot)@(rz@rx).T+pivot

def apply(module):
    global R
    R=module
    import rooftop_refinements
    src=Image.open(R.ROOT/'production/rooftop_source/textures/support_rooftop_face.png').convert('RGB')
    src.save(R.ROOT/'textures/support_rooftop_face.png')
    w,h=src.size
    hair=src.crop((int(w*.31),int(h*.09),int(w*.67),int(h*.24))).resize((512,512),Image.Resampling.LANCZOS)
    hair.save(R.ROOT/'textures/support_rooftop_hair.png')
    # Match the body material to the cheeks, keeping its high-frequency skin detail.
    cheek=np.asarray(src.crop((int(w*.31),int(h*.56),int(w*.39),int(h*.64))),float).mean((0,1))
    skin_path=R.ROOT/'textures/support_rooftop_skin.png';skin=np.asarray(Image.open(skin_path),float)
    skin=skin/skin.mean((0,1));skin=np.clip((1+(skin-1)*.22)*cheek,0,255);Image.fromarray(skin.astype('uint8')).save(skin_path)
    R.M['skin']['color']=[.73]*3
    R.M['skinlight']['color']=[.77]*3
    R.material('face',[1,1,1],'support_rooftop_face',.78)
    R.material('hair',[1,1,1],'support_rooftop_hair',.93)
    rooftop_refinements.head=head
