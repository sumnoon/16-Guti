"""Village Uthan procedural mesh source. Metres, Z-up internally; GLB is Y-up.
No installed modelling package required. Run with bundled Python (numpy/Pillow).
"""
import json, struct, math, random
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'models'
OUT.mkdir(exist_ok=True)
TAU=math.tau
random.seed(16016)

def mat(name,color,tex=None,rough=.85,metal=0,alpha=1):
    return dict(name=name,color=color,tex=tex,rough=rough,metal=metal,alpha=alpha)
M={
 'clay':mat('Worn terracotta',[.70,.36,.20],'uthan_tex_wall_mud'),
 'mud':mat('Hand plastered mud',[1,1,1],'uthan_tex_wall_mud'),
 'soot':mat('Soot',[.09,.075,.06],'uthan_tex_wall_mud'),
 'wood':mat('Aged wood',[.38,.26,.16],'uthan_tex_bark_banyan'),
 'bamboo':mat('Worn bamboo',[1,1,1],'uthan_tex_fence_bamboo'),
 'jute':mat('Jute weave',[1,1,1],'uthan_tex_mat_jute'),
 'straw':mat('Rice straw',[1,1,1],'uthan_tex_straw'),
 'bark':mat('Banyan bark',[1,1,1],'uthan_tex_bark_banyan'),
 'tin':mat('Weathered tin',[1,1,1],'uthan_tex_roof_tin',.64,.55),
 'dark':mat('Slate pebble',[.30,.34,.38],'support_stone',.7),
 'cream':mat('Cream pebble',[1,.96,.84],'support_stone',.75),
 'seed':mat('Tamarind shell',[.12,.048,.018],None,.22),
 'red':mat('Rust red enamel',[.65,.17,.09],'uthan_tex_roof_tin',.62,.4),
 'iron':mat('Iron',[.13,.14,.13],None,.55,.75),
 'glass':mat('Dusty glass',[.72,.78,.73],None,.15,0,.22),
 'brass':mat('Aged brass',[.58,.41,.16],None,.38,.8),
 'aluminium':mat('Dull aluminium',[.65,.68,.65],None,.42,.8),
 'leaf':mat('Leaf green',[.25,.40,.15],'support_stone',.92),
 'leaf2':mat('Sunlit leaf',[.32,.48,.20],'support_stone',.9),
 'dryleaf':mat('Dry foliage',[.48,.33,.13],'support_stone',.96),
 'clothred':mat('Faded gamcha red',[.64,.22,.16],'uthan_tex_mat_jute'),
 'clothcream':mat('Gamcha cream',[.94,.86,.66],'uthan_tex_mat_jute'),
 'clothblue':mat('Lungi indigo',[.15,.24,.30],'uthan_tex_mat_jute'),
 'feather':mat('Deshi brown plumage',[.31,.13,.045],'uthan_tex_bark_banyan'),
 'black':mat('Dark feather',[.07,.075,.05],None,.6),
 'comb':mat('Comb red',[.55,.07,.04],None,.7),
 'beak':mat('Horn and scales',[.48,.33,.13],None,.7),
 'eye':mat('Eyes',[.012,.009,.006],None,.15),
}

class Mesh:
    def __init__(self,name): self.name=name; self.parts=[]
    def add(self,v,f,m,uv=None):
        v=np.asarray(v,dtype=float); f=np.asarray(f,dtype=np.uint32)
        if uv is None: uv=np.asarray([[p[0]*2,p[2]*2+p[1]*2] for p in v])
        self.parts.append([v,f,m,np.asarray(uv,dtype=float)])
    def bounds(self):
        a=np.concatenate([p[0] for p in self.parts]); return a.min(0),a.max(0)
    def fit(self,dims=None,height=None):
        lo,hi=self.bounds(); size=hi-lo
        sc=np.array(dims)/size if dims else np.full(3,height/size[2] if height else 1.)
        for p in self.parts: p[0]=(p[0]-np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]]))*sc
        return self
    def translate(self,offset):
        for p in self.parts:p[0]+=offset
        return self

def box(o,c,s,m):
    c=np.array(c); s=np.array(s)/2
    v=[]; f=[]; uv=[]
    for axis,sign in [(0,-1),(0,1),(1,-1),(1,1),(2,-1),(2,1)]:
        other=[i for i in range(3) if i!=axis]; start=len(v)
        pts=[]
        for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:
            q=c.copy();q[axis]+=sign*s[axis];q[other[0]]+=a*s[other[0]];q[other[1]]+=b*s[other[1]];pts.append(q)
        cross=np.cross(pts[1]-pts[0],pts[2]-pts[0])
        if cross[axis]*sign<0:pts.reverse()
        v+=pts;f += [[start,start+1,start+2],[start,start+2,start+3]];uv += [[0,0],[1,0],[1,1],[0,1]]
    o.add(v,f,m,uv)

def lathe(o,profile,m,n=32,center=(0,0,0),wobble=0,start=0,arc=TAU):
    v=[];uv=[];f=[]
    for j,(r,z) in enumerate(profile):
        for i in range(n+1):
            a=start+arc*i/n; rr=r*(1+wobble*math.sin(3*a+z*13)+wobble*.5*math.cos(7*a-z*6))
            v.append([center[0]+rr*math.cos(a),center[1]+rr*math.sin(a),center[2]+z]);uv.append([i/n,j/(len(profile)-1)])
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*(n+1)+i;b=a+n+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,m,uv)

def ellipsoid(o,c,r,m,n=24,rings=12,wobble=0,flatten=0,rot=0):
    v=[];f=[];uv=[]
    for j in range(rings+1):
        p=math.pi*j/rings
        for i in range(n+1):
            a=TAU*i/n; noise=1+wobble*(math.sin(3*a+p*2)+.45*math.cos(5*a-p*3))
            x=r[0]*math.sin(p)*math.cos(a)*noise;y=r[1]*math.sin(p)*math.sin(a)*noise;z=r[2]*math.cos(p)
            if flatten:z=max(z,-r[2]*flatten)
            v.append([c[0]+x*math.cos(rot)-y*math.sin(rot),c[1]+x*math.sin(rot)+y*math.cos(rot),c[2]+z]);uv.append([i/n,j/rings])
    for j in range(rings):
        for i in range(n):
            a=j*(n+1)+i;b=a+n+1
            if j>0:f.append([a,b,a+1])
            if j<rings-1:f.append([a+1,b,b+1])
    o.add(v,f,m,uv)

def tube(o,points,radii,m,n=8,cap=True):
    p=np.asarray(points,float);v=[];f=[];uv=[]
    if np.isscalar(radii):radii=[radii]*len(p)
    for j,c in enumerate(p):
        t=p[min(j+1,len(p)-1)]-p[max(j-1,0)];t/=np.linalg.norm(t)
        ref=np.array([0.,0.,1.]) if abs(t[2])<.9 else np.array([1.,0.,0.])
        u=np.cross(t,ref);u/=np.linalg.norm(u);w=np.cross(t,u)
        for i in range(n+1):
            a=TAU*i/n;v.append(c+radii[j]*(math.cos(a)*u+math.sin(a)*w));uv.append([i/n,j/(len(p)-1)])
    for j in range(len(p)-1):
        for i in range(n):
            a=j*(n+1)+i;b=a+n+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    if cap:
        for j,rev in [(0,True),(len(p)-1,False)]:
            k=len(v);v.append(p[j]);uv.append([.5,.5]);a=j*(n+1)
            for i in range(n):f.append([k,a+i+1,a+i] if rev else [k,a+i,a+i+1])
    o.add(v,f,m,uv)

def ring(o,c,r,thick,m,n=32,vertical=False):
    pts=[]
    for i in range(n+1):
        a=TAU*i/n;pts.append([c[0]+r*math.cos(a),c[1]+(0 if vertical else r*math.sin(a)),c[2]+(r*math.sin(a) if vertical else 0)])
    tube(o,pts,thick,m,6,False)

def leaf(o,base,end,width,m,segments=6,sag=.1,torn=False):
    base=np.array(base);end=np.array(end);d=end-base;side=np.cross(d,[0,0,1.]);side/=max(np.linalg.norm(side),1e-9)
    v=[];uv=[];f=[]
    for j in range(segments+1):
        t=j/segments;c=base+d*t;c[2]+=sag*math.sin(math.pi*t)
        w=width*math.sin(math.pi*t)**.7
        for k in [-1,0,1]:
            q=c+side*w*k
            q[2]-=abs(k)*w*.15
            if torn and j%3==1 and k: q=c+side*w*k*.48
            v.append(q);uv.append([(k+1)/2,t])
    for j in range(segments):
        for k in range(2):
            a=j*3+k;b=a+3;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,m,uv)

def pot(o,h,r,m,center=(0,0,0),n=40):
    # Closed cross section, open mouth and a real inner wall.
    profile=[(0,0),(.55*r,0),(.76*r,.04*h),(.98*r,.26*h),(r,.47*h),(.84*r,.66*h),(.49*r,.79*h),(.46*r,.91*h),(.55*r,.96*h),(.55*r,h),(.43*r,h),(.38*r,.94*h),(.38*r,.82*h),(.75*r,.66*h),(.91*r,.46*h),(.88*r,.27*h),(.64*r,.09*h),(0,.09*h)]
    lathe(o,profile,m,n,center,.018)

def export(objects,name,budget):
    mats=[];indices={};texnames=[]
    for o in objects:
        for _,_,key,_ in o.parts:
            if key not in indices:indices[key]=len(mats);mats.append(M[key])
            tex=M[key]['tex']
            if tex and tex not in texnames:texnames.append(tex)
    blob=bytearray();views=[];access=[]
    def append(data,target=None):
        while len(blob)%4:blob.append(0)
        view=dict(buffer=0,byteOffset=len(blob),byteLength=len(data))
        if target:view['target']=target
        views.append(view);blob.extend(data);return len(views)-1
    def acc(a,typ,ctype,target):
        a=np.asarray(a,dtype='<f4' if ctype==5126 else '<u4');idx=append(a.tobytes(),target)
        d=dict(bufferView=idx,componentType=ctype,count=len(a),type=typ)
        if typ=='VEC3':d.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        access.append(d);return len(access)-1
    images=[]
    for tex in texnames:images.append(dict(bufferView=append((ROOT/'textures'/f'{tex}.png').read_bytes()),mimeType='image/png',name=tex))
    material=[]
    for m in mats:
        pbr=dict(baseColorFactor=m['color']+[m['alpha']],roughnessFactor=m['rough'],metallicFactor=m['metal'])
        if m['tex']:pbr['baseColorTexture']=dict(index=texnames.index(m['tex']))
        d=dict(name=m['name'],pbrMetallicRoughness=pbr,doubleSided=True)
        if m['alpha']<1:d['alphaMode']='BLEND'
        material.append(d)
    meshes=[];nodes=[];total=0
    for o in objects:
        prim=[]
        for key in indices:
            parts=[p for p in o.parts if p[2]==key]
            if not parts:continue
            vs=[];fs=[];uvs=[];offset=0
            for v,f,_,uv in parts:vs.append(v);fs.append(f+offset);uvs.append(uv);offset+=len(v)
            v=np.concatenate(vs);f=np.concatenate(fs);uv=np.concatenate(uvs)
            v=v[:,[0,2,1]];v[:,2]*=-1
            cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
            keep=np.linalg.norm(cross,axis=1)>1e-13;f=f[keep];cross=cross[keep]
            normals=np.zeros_like(v)
            for k in range(3):np.add.at(normals,f[:,k],cross)
            normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
            prim.append(dict(attributes=dict(POSITION=acc(v,'VEC3',5126,34962),NORMAL=acc(normals,'VEC3',5126,34962),TEXCOORD_0=acc(uv,'VEC2',5126,34962)),indices=acc(f.reshape(-1),'SCALAR',5125,34963),material=indices[key]))
            total+=len(f)
        nodes.append(dict(name=o.name,mesh=len(meshes)));meshes.append(dict(name=o.name,primitives=prim))
    assert total<budget,(name,total,budget)
    doc=dict(asset=dict(version='2.0',generator='Village Uthan procedural source',extras=dict(units='meters',upAxis='Y')),scene=0,scenes=[dict(nodes=list(range(len(nodes))))],nodes=nodes,meshes=meshes,materials=material,buffers=[dict(byteLength=len(blob))],bufferViews=views,accessors=access)
    if images:doc.update(images=images,textures=[dict(source=i,sampler=0) for i in range(len(images))],samplers=[dict(wrapS=10497,wrapT=10497,magFilter=9729,minFilter=9987)])
    js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);blob+=b'\0'*((-len(blob))%4)
    glb=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(blob))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(blob),0x004e4942)+blob
    (OUT/f'{name}.glb').write_bytes(glb)
    bounds=[o.bounds() for o in objects]
    report=dict(name=name,triangles=total,budget=budget,objects=len(objects),embedded_textures=len(images),bytes=len(glb),dimensions_m=[(hi-lo).round(6).tolist() for lo,hi in bounds],bottom_center_origins=all(abs(lo[2])<1e-7 and abs(lo[0]+hi[0])<1e-7 and abs(lo[1]+hi[1])<1e-7 for lo,hi in bounds))
    print(json.dumps(report));REPORT.append(report)
    return objects

REPORT=[]
def make_pieces():
    for color in ['dark','cream']:
        name='guti_pebble_'+('light' if color=='cream' else 'dark');o=Mesh(name)
        ellipsoid(o,(0,0,0),(1,.84,.55),color,32,16,.045,.72)
        o.fit([.025,.021,.012]);export([o],name,3000)
    objects=[]
    for color in ['dark','cream']:
        for i in range(3):
            o=Mesh(f'{color}_variation_{i+1}');ellipsoid(o,(0,0,0),(1,.72+i*.08,.6),color,28,14,.065+i*.016,.65,rot=i*.7);o.fit([.025,.018+i*.002,.011+i*.0006]);objects.append(o)
    export(objects,'guti_pebble_variations',18000)
    o=Mesh('guti_clay_shard');ellipsoid(o,(0,0,0),(1,.76,.24),'clay',28,12,.11,.7);o.fit([.025,.020,.008]);export([o],o.name,3000)
    o=Mesh('guti_tamarind_seed');ellipsoid(o,(0,0,0),(1,.79,.66),'seed',28,14,.025,.78)
    ellipsoid(o,(.7,0,.12),(.14,.25,.19),'clay',12,6);o.fit([.025,.019,.015]);export([o],o.name,2000)

def make_props():
    o=Mesh('prop_kolshi');pot(o,.35,.145,'clay');o.fit(height=.35);export([o],o.name,8000)
    o=Mesh('prop_chula')
    profile=[(.15,0),(.245,0),(.25,.04),(.225,.22),(.21,.25),(.145,.25),(.13,.20),(.14,.035),(.15,0)]
    lathe(o,profile,'clay',40,start=-.1,arc=math.pi+ .2,wobble=.025)
    lathe(o,[(.139,.035),(.128,.20),(.143,.245)],'soot',40,start=-.1,arc=math.pi+.2)
    # Closed exposed end walls at the front opening.
    for a in [-.1,math.pi+.1]:
        verts=[[r*math.cos(a),r*math.sin(a),z] for r,z in profile[:-1]]
        o.add(verts,[[0,i,i+1] for i in range(1,len(verts)-1)],'clay')
    for a in [.25,math.pi/2,math.pi-.25]:
        ellipsoid(o,(.18*math.cos(a),.18*math.sin(a),.24),(.035,.032,.025),'soot',12,6)
    o.fit([.50,.32,.25]);export([o],o.name,6000)
    o=Mesh('prop_piri')
    for y in [-.083,0,.083]:box(o,(0,y,.085),(.40,.080,.03),'wood')
    for x in [-.15,.15]:box(o,(x,0,.035),(.035,.22,.07),'wood')
    o.fit([.4,.25,.1]);export([o],o.name,3000)
    o=Mesh('prop_pati');v=[];f=[];uv=[];nx=24;ny=18
    for j in range(ny+1):
        for i in range(nx+1):
            x=i/nx;y=j/ny;z=.003+.003*math.sin(x*19+y*7)+.045*(abs(x-.5)*2)**12*(abs(y-.5)*2)**9
            v.append([(x-.5)*1.2,(y-.5)*.9,z]);uv.append([x*2,y*1.5])
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+nx+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,'jute',uv)
    for edge in [-1,1]:
        for i in range(35):
            x=-.58+i*.034;tube(o,[(x,edge*.45,.006),(x+.005,edge*.465,.005)],.0012,'jute',3)
    o.fit([1.2,.9,.05]);export([o],o.name,2000)
    o=Mesh('prop_lantern')
    lathe(o,[(0,0),(.058,0),(.066,.012),(.063,.032),(.047,.048),(.018,.05),(0,.05)],'red',28)
    lathe(o,[(.030,.05),(.043,.07),(.047,.105),(.041,.15),(.028,.19)],'glass',28)
    lathe(o,[(0,.181),(.032,.181),(.052,.192),(.053,.202),(.025,.217),(.026,.23),(0,.23)],'red',28)
    for x in [-.056,.056]:tube(o,[(x,0,.025),(x*1.15,0,.07),(x*1.1,0,.18),(x*.55,0,.215)],[.009,.008,.008,.007],'red',8)
    tube(o,[(.057*math.cos(a),0,.23+.07*math.sin(a)) for a in np.linspace(0,math.pi,20)],.0022,'iron',6)
    lathe(o,[(0,.05),(.015,.05),(.015,.063),(0,.063)],'iron',16)
    for z,r in [(.065,.043),(.17,.036)]:ring(o,(0,0,z),r,.002,'iron',28)
    o.fit(height=.3);export([o],o.name,5000)
    o=Mesh('prop_haystack')
    lathe(o,[(0,0),(1.0,0),(1.12,.18),(1.09,.6),(.94,1.1),(.72,1.55),(.43,1.95),(.12,2.25),(0,2.3)],'straw',48,wobble=.025)
    tube(o,[(0,0,0),(0,0,2.5)],.035,'bamboo',10)
    for k in range(240):
        a=random.uniform(0,TAU);z=random.uniform(.08,2.15);r=np.interp(z,[.08,.6,1.1,1.55,1.95,2.2],[1.1,1.1,.95,.73,.44,.15]);length=random.uniform(.10,.3)
        tube(o,[(r*math.cos(a),r*math.sin(a),z),((r+.06)*math.cos(a+.015),(r+.06)*math.sin(a+.015),max(0,z-length))],.003,'straw',3)
    o.fit(height=2.5);export([o],o.name,8000)
    o=Mesh('prop_fence')
    for x in [-.97,0,.97]:tube(o,[(x,0,0),(x,0,1.5)],.03,'bamboo',8)
    for z in [.2,.75,1.35]:tube(o,[(-1,0,z),(1,0,z)],.025,'bamboo',8)
    for i in range(31):
        x=-.98+i*1.96/30
        tube(o,[(x,.015,0.08),(x+.004,.025,.8),(x,0,1.43)],.012,'bamboo',4)
    for j in range(10):
        z=.15+j*.125
        pts=[(-1+i*.1,.025+(.015 if i%2 else -.015),z) for i in range(21)]
        tube(o,pts,.009,'bamboo',4)
    o.fit([2,.09,1.5]);export([o],o.name,4000)
    make_house()
    o=Mesh('prop_chouki')
    for i in range(10):box(o,(-.81+i*.18,0,.42),(.174,1.2,.06),'wood')
    for x in [-.79,.79]:
        for y in [-.49,.49]:box(o,(x,y,.2),(.095,.095,.4),'wood')
    for y in [-.54,.54]:box(o,(0,y,.35),(1.8,.055,.15),'wood')
    for x in [-.84,.84]:box(o,(x,0,.35),(.055,1.2,.15),'wood')
    o.fit([1.8,1.2,.45]);export([o],o.name,5000)
    make_clothesline()
    o=Mesh('prop_kula');lathe(o,[(0,0),(.18,0),(.24,.012),(.25,.034),(.242,.042),(.232,.025),(.18,.012),(0,.012)],'bamboo',48,wobble=.009)
    ring(o,(0,0,.035),.245,.006,'bamboo',48);o.fit([.5,.5,.045]);export([o],o.name,4000)
    o=Mesh('prop_dala');lathe(o,[(0,0),(.13,0),(.16,.025),(.20,.13),(.225,.20),(.22,.208),(.21,.19),(.19,.13),(.15,.03),(0,.014)],'bamboo',48,wobble=.012)
    ring(o,(0,0,.202),.219,.007,'bamboo',48);o.fit([.45,.45,.21]);export([o],o.name,4000)
    pots=[]
    for name,h,r,m in [('aluminium_handi',.24,.19,'aluminium'),('brass_lota',.22,.105,'brass'),('clay_rice_pot',.30,.17,'clay')]:
        o=Mesh(name);pot(o,h,r,m,n=28);o.fit(height=h);pots.append(o)
    export(pots,'prop_pots',5000)
    o=Mesh('prop_jharu')
    for i in range(40):
        a=random.uniform(0,TAU);r=random.uniform(.005,.022);spread=random.uniform(-.12,.12)
        tube(o,[(r*math.cos(a),r*math.sin(a),.7),(r*math.cos(a),r*math.sin(a),.42),(spread,r*math.sin(a)*2,.02+random.uniform(0,.035))],[.0015,.0015,.0006],'straw',3)
    for z in [.46,.48,.5]:ring(o,(0,0,z),.023,.003,'jute',12)
    o.fit(height=.7);export([o],o.name,2000)
    make_chicken();make_banana();make_banyan()

def make_house():
    o=Mesh('prop_house')
    # Overall envelope 6 x 4 x 3.5 m including veranda and eaves.
    box(o,(0,0,.12),(5.7,3.7,.24),'mud')
    box(o,(0,1.43,1.37),(5.55,.18,2.5),'mud')
    for x in [-2.68,2.68]:box(o,(x,.25,1.37),(.18,2.55,2.5),'mud')
    # Front wall with actual door and shutter recesses.
    for c,s in [((-2.03,-1.05,1.37),(1.3,.18,2.5)),((.0,-1.05,1.37),(1.1,.18,2.5)),((2.25,-1.05,1.37),(.85,.18,2.5)),((-.95,-1.05,2.39),(.9,.18,.46)),((1.2,-1.05,.64),(1.3,.18,1.05)),((1.2,-1.05,2.33),(1.3,.18,.58))]:box(o,c,s,'mud')
    box(o,(-.95,-1.01,1.2),(.86,.075,2.05),'wood')
    for x in [-1.4,-.5]:box(o,(x,-1.18,1.25),(.065,.065,2.12),'wood')
    box(o,(-.95,-1.18,2.3),(.98,.07,.07),'wood')
    for x in np.linspace(.62,1.77,8):box(o,(x,-1.17,1.62),(.135,.045,.87),'wood')
    for z in [1.22,2.05]:box(o,(1.2,-1.2,z),(1.3,.06,.065),'wood')
    for x in [-2.55,-.3,2.55]:tube(o,[(x,-1.72,.24),(x,-1.72,2.28)],.055,'bamboo',10)
    # Two corrugated roof pitches, no baked lighting.
    for side in [-1,1]:
        v=[];f=[];uv=[];nx=120
        for j in range(2):
            for i in range(nx+1):
                x=-3+6*i/nx;y=.2+side*j*1.65;z=3.5-j*.92+.012*math.cos(i*math.pi)
                v.append([x,y,z]);uv.append([i/nx*6,j*2])
        for i in range(nx):a=i;b=i+nx+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
        o.add(v,f,'tin',uv)
    # Veranda roof and triangular gable infill.
    v=[[-2.95,-1.12,2.60],[2.95,-1.12,2.60],[2.95,-2,2.22],[-2.95,-2,2.22]]
    o.add(v,[[0,1,2],[0,2,3]],'tin',[[0,0],[6,0],[6,1],[0,1]])
    for x in [-2.68,2.68]:o.add([[x,-1.38,2.6],[x,1.78,2.6],[x,.2,3.49]],[[0,1,2]],'mud')
    for x in [-2.55,-.3,2.55]:tube(o,[(x,-1.7,2.2),(x,-.9,2.58)],.04,'wood',6)
    o.fit([6,4,3.5]);export([o],o.name,20000)

def make_clothesline():
    o=Mesh('prop_clothesline')
    for x in [-1.5,1.5]:tube(o,[(x,0,0),(x+.008,0,1.9)],.025,'bamboo',10)
    pts=[(-1.5+3*i/30,0,1.85-.12*math.sin(math.pi*i/30)) for i in range(31)]
    tube(o,pts,.004,'jute',5)
    for left,width,height,colors in [(-1.1,.65,.8,['clothred','clothcream']),(.0,1.05,1.05,['clothblue','clothcream'])]:
        nx=18;ny=20
        for j in range(ny):
            for i in range(nx):
                verts=[]
                for a,b in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
                    x=left+width*a/nx;t=b/ny;top=1.85-.12*math.sin(math.pi*(x+1.5)/3)
                    verts.append([x,.024*math.sin(a/nx*TAU*3)+.035*t*t*math.sin(a),top-height*t])
                key=colors[1] if i%6==0 or j%6==0 else colors[0]
                o.add(verts,[[0,1,2],[0,2,3]],key,[[0,0],[.2,0],[.2,.2],[0,.2]])
    # Keep poles exactly 3m apart, overall diameter adds 5cm.
    o.fit(height=1.9);export([o],o.name,4000)

def make_chicken():
    o=Mesh('prop_chicken')
    ellipsoid(o,(0,0,.17),(.065,.095,.074),'feather',24,14)
    ellipsoid(o,(0,-.058,.225),(.036,.039,.07),'feather',20,12)
    ellipsoid(o,(0,-.076,.283),(.028,.032,.031),'feather',20,10)
    # Layered wing feathers follow the flanks.
    for side in [-1,1]:
        ellipsoid(o,(side*.055,.015,.177),(.017,.061,.040),'feather',18,10)
        for j in range(6):
            leaf(o,(side*.059,-.012+j*.006,.195-j*.004),(side*.061,.065+j*.004,.145-j*.002),.010,'black' if j>3 else 'feather',3,.007)
        ellipsoid(o,(side*.026,-.089,.292),(.003,.006,.006),'beak',10,6)
        ellipsoid(o,(side*.028,-.090,.293),(.0018,.0035,.0035),'eye',10,6)
    tube(o,[(0,-.104,.282),(0,-.127,.277)],[.009,0],'beak',8)
    for i in range(5):ellipsoid(o,(0,-.09+i*.009,.313+(.012 if i in [1,2] else .006)),(.005,.008,.012),'comb',10,6)
    for x in [-.006,.006]:ellipsoid(o,(x,-.096,.262),(.005,.006,.013),'comb',10,6)
    for x in [-.025,.025]:
        tube(o,[(x,.012,.13),(x,.022,.062),(x,.009,.018)],[.009,.005,.004],'beak',8)
        for spread in [-1,0,1]:tube(o,[(x,.009,.018),(x+spread*.014,-.024,.009),(x+spread*.017,-.036,.006)],[.0035,.002,.0005],'beak',5)
        tube(o,[(x,.01,.018),(x,.037,.006)],[.003,.0005],'beak',5)
    for i in range(9):
        x=(i-4)*.007;leaf(o,(x,.063,.20),(x*1.4,.15+abs(i-4)*.004,.30-abs(i-4)*.013),.012,'black',6,.025)
    o.fit(height=.35);export([o],o.name,6000)

def make_banana():
    o=Mesh('prop_banana_tree')
    tube(o,[(0,0,0),(.02,0,.6),(-.01,.01,1.4),(.03,0,2.25)],[.15,.12,.09,.045],'leaf2',14)
    for i in range(7):
        a=i*TAU/7;pts=[(.10*math.cos(a),.10*math.sin(a),.04),(.09*math.cos(a+.08),.09*math.sin(a+.08),.7),(.05*math.cos(a+.12),.05*math.sin(a+.12),1.9)]
        tube(o,pts,[.025,.024,.008],'dryleaf' if i%3==0 else 'leaf2',5)
    for i in range(12):
        a=i*2.4;z=1.6+i*.065;length=1.25 if i<8 else .7
        base=(.02,0,z);end=(length*math.cos(a),length*math.sin(a),z+(.55 if i>7 else -.25))
        leaf(o,base,end,.29 if i<8 else .2,'dryleaf' if i==0 else ('leaf2' if i%3==0 else 'leaf'),12,.45,True)
        pts=[]
        for t in np.linspace(0,1,9):pts.append([end[0]*t,end[1]*t,z+(end[2]-z)*t+.45*math.sin(math.pi*t)])
        tube(o,pts,[.012*(1-t)+.001 for t in np.linspace(0,1,9)],'leaf2',5)
    o.fit(height=3);export([o],o.name,10000)

def make_banyan():
    o=Mesh('prop_banyan_tree');rng=random.Random(36)
    # Fused, twisting trunk strands and spreading buttresses.
    for i in range(10):
        a=TAU*i/10
        pts=[]
        for j in range(9):
            z=j*.65;r=.63*(1-j/14);ang=a+j*.12
            pts.append([r*math.cos(ang),r*math.sin(ang),z])
        tube(o,pts,[.35*(1-j/13) for j in range(9)],'bark',10)
        tube(o,[(2.3*math.cos(a),2.3*math.sin(a),.04),(1.25*math.cos(a),1.25*math.sin(a),.15),(.6*math.cos(a+.1),.6*math.sin(a+.1),1.5)],[.07,.23,.32],'bark',8)
    crowns=[]
    for i in range(14):
        a=i*TAU/14;reach=rng.uniform(4.4,6.4);h=rng.uniform(6.5,8.4)
        p0=np.array([.35*math.cos(a),.35*math.sin(a),3.3+rng.random()*1.5]);p1=np.array([reach*.45*math.cos(a+.12),reach*.45*math.sin(a+.12),h-.8]);p2=np.array([reach*math.cos(a),reach*math.sin(a),h])
        tube(o,[p0,p1,p2],[.34,.19,.04],'bark',9)
        for k in range(3):
            b=a+(k-1)*.33;end=p2+np.array([rng.uniform(.5,1.1)*math.cos(b),rng.uniform(.5,1.1)*math.sin(b),rng.uniform(.3,1.3)])
            tube(o,[p1,p2,end],[.12,.06,.012],'bark',6);crowns.append(end)
        # Aerial roots hang beneath spreading limbs, some reaching ground.
        for j in range(6):
            t=rng.uniform(.35,1);p=p1*(1-t)+p2*t;bottom=rng.choice([.03,.2,1.2,2.5,3.8])
            tube(o,[p,p+np.array([.07,-.06,-1]),[p[0]+.1,p[1]-.04,bottom]],[.024,.014,.008],'bark',5)
    crowns += [np.array([0,0,8.8]),np.array([1,0,9]),np.array([-1,0,9])]
    # Individual leaf geometry avoids opaque polygon blobs and alpha sorting.
    for c in crowns:
        for j in range(145):
            a=rng.uniform(0,TAU);r=rng.uniform(.1,1.5);z=rng.uniform(-.6,.65)
            p=c+np.array([r*math.cos(a),r*math.sin(a),z]);ang=rng.uniform(0,TAU);ln=rng.uniform(.48,.78)
            end=p+np.array([ln*math.cos(ang),ln*math.sin(ang),rng.uniform(-.16,.1)])
            leaf(o,p,end,ln*.32,'leaf2' if j%5==0 else 'leaf',2,.025)
    o.fit([15,14,12]);export([o],o.name,50000)

if __name__=='__main__':
    make_pieces()
    if 'make_props' in globals():make_props()
    (ROOT/'production'/'model_validation.json').write_text(json.dumps(REPORT,indent=2))
