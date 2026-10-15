"""Village Uthan procedural mesh source. Metres, Z-up internally; GLB is Y-up.
No installed modelling package required. Run with Python, numpy and Pillow after process_images.py.

Writes per asset: models/<name>.glb (LOD0, embedded JPEG base colour + PNG normal map, baked AO in COLOR_0),
models/lod/<name>_lod1.glb and _lod2.glb (fewer segments / sparser scatter), models/collision/<name>_col.glb
(simple boxes and cylinders), production/collision.json (the same shapes as primitives) and
production/model_validation.json. prop_chicken is skinned with idle, peck and walk clips.
"""
import io, json, struct, math, random
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'models'
TAU=math.tau
DETAIL=1.0          # 1 = LOD0; lower values reduce segments and scatter counts
LODS=[(1,1.0),(2,.5),(3,.25)]

def seg(n,lo=3):
    return max(lo,int(round(n*DETAIL)))
def step():
    return int(round(1/DETAIL))
def keep(i):
    return i%step()==0

def mat(name,color,tex=None,rough=.85,metal=0,alpha=1,thin=False):
    return dict(name=name,color=color,tex=tex,rough=rough,metal=metal,alpha=alpha,thin=thin)
M={
 'clay':mat('Worn terracotta',[.70,.36,.20],'uthan_tex_wall_mud'),
 'mud':mat('Hand plastered mud',[1,1,1],'uthan_tex_wall_mud'),
 'soot':mat('Soot',[.09,.075,.06],'uthan_tex_wall_mud'),
 'wood':mat('Aged wood',[.38,.26,.16],'uthan_tex_bark_banyan'),
 'bamboo':mat('Worn bamboo',[1,1,1],'uthan_tex_fence_bamboo'),
 'jute':mat('Jute weave',[1,1,1],'uthan_tex_mat_jute'),
 'straw':mat('Rice straw',[1,1,1],'uthan_tex_straw'),
 'bark':mat('Banyan bark',[1,1,1],'uthan_tex_bark_banyan'),
 'tin':mat('Weathered tin',[1,1,1],'uthan_tex_roof_tin',.64,.55,thin=True),
 'dark':mat('Slate pebble',[.30,.34,.38],'support_stone',.7),
 'cream':mat('Cream pebble',[1,.96,.84],'support_stone',.75),
 'seed':mat('Tamarind shell',[.12,.048,.018],None,.22),
 'red':mat('Rust red enamel',[.65,.17,.09],'uthan_tex_roof_tin',.62,.4),
 'iron':mat('Iron',[.13,.14,.13],None,.55,.75),
 'glass':mat('Dusty glass',[.72,.78,.73],None,.15,0,.22,thin=True),
 'brass':mat('Aged brass',[.58,.41,.16],None,.38,.8),
 'aluminium':mat('Dull aluminium',[.65,.68,.65],None,.42,.8),
 'leaf':mat('Leaf green',[.25,.40,.15],'support_stone',.92,thin=True),
 'leaf2':mat('Sunlit leaf',[.32,.48,.20],'support_stone',.9,thin=True),
 'dryleaf':mat('Dry foliage',[.48,.33,.13],'support_stone',.96,thin=True),
 'clothred':mat('Faded gamcha red',[.64,.22,.16],'uthan_tex_mat_jute',thin=True),
 'clothcream':mat('Gamcha cream',[.94,.86,.66],'uthan_tex_mat_jute',thin=True),
 'clothblue':mat('Lungi indigo',[.15,.24,.30],'uthan_tex_mat_jute',thin=True),
 'feather':mat('Deshi brown plumage',[.31,.13,.045],'uthan_tex_bark_banyan'),
 'black':mat('Dark feather',[.07,.075,.05],None,.6,thin=True),
 'comb':mat('Comb red',[.55,.07,.04],None,.7),
 'beak':mat('Horn and scales',[.48,.33,.13],None,.7),
 'eye':mat('Eyes',[.012,.009,.006],None,.15),
 'collider':mat('Collider',[.2,.8,.3],None,1,0,.35),
}

class Mesh:
    def __init__(self,name):
        self.name=name;self.parts=[];self.bone=None;self.bones=[];self.animations=[];self.colliders=[];self.xf=None
    def add(self,v,f,m,uv=None):
        v=np.asarray(v,dtype=float); f=np.asarray(f,dtype=np.uint32)
        if uv is None: uv=np.asarray([[p[0]*2,p[2]*2+p[1]*2] for p in v])
        self.parts.append([v,f,m,np.asarray(uv,dtype=float),self.bone])
    def bounds(self):
        a=np.concatenate([p[0] for p in self.parts]); return a.min(0),a.max(0)
    def fit(self,dims=None,height=None):
        lo,hi=self.bounds(); size=hi-lo
        sc=np.array(dims)/size if dims else np.full(3,height/size[2] if height else 1.)
        off=np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
        for p in self.parts: p[0]=(p[0]-off)*sc
        self.xf=(off,sc)
        self.colliders=[(k,(np.array(c)-off)*sc,np.array(s)*sc) for k,c,s in self.colliders]
        self.bones=[(n,parent,(np.array(p)-off)*sc) for n,parent,p in self.bones]
        return self
    def collide(self,kind,center,size):
        """Collider in pre-fit coordinates (converted by fit). kind is 'box' or 'cylinder' (Z axis)."""
        self.colliders.append((kind,np.array(center,float),np.array(size,float)))
    def collide_bounds(self,kind):
        lo,hi=self.bounds();self.colliders.append((kind,(lo+hi)/2,hi-lo))

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
    n=seg(n,6);v=[];uv=[];f=[]
    for j,(r,z) in enumerate(profile):
        for i in range(n+1):
            a=start+arc*i/n; rr=r*(1+wobble*math.sin(3*a+z*13)+wobble*.5*math.cos(7*a-z*6))
            v.append([center[0]+rr*math.cos(a),center[1]+rr*math.sin(a),center[2]+z]);uv.append([i/n,j/(len(profile)-1)])
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*(n+1)+i;b=a+n+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,m,uv)

def ellipsoid(o,c,r,m,n=24,rings=12,wobble=0,flatten=0,rot=0):
    n=seg(n,6);rings=seg(rings,4);v=[];f=[];uv=[]
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
    n=seg(n);p=np.asarray(points,float);v=[];f=[];uv=[]
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
    n=seg(n,6);pts=[]
    for i in range(n+1):
        a=TAU*i/n;pts.append([c[0]+r*math.cos(a),c[1]+(0 if vertical else r*math.sin(a)),c[2]+(r*math.sin(a) if vertical else 0)])
    tube(o,pts,thick,m,6,False)

def leaf(o,base,end,width,m,segments=6,sag=.1,torn=False):
    segments=seg(segments,2)
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

# ---------------------------------------------------------------- GLB writing

def to_gltf(v):
    """Internal Z-up (+Y back) to glTF Y-up (+Z front)."""
    v=np.asarray(v,float);return np.stack([v[...,0],v[...,2],-v[...,1]],-1)

TEXCACHE={}
def texture_image(name,size,kind):
    key=(name,size,kind)
    if key not in TEXCACHE:
        src=ROOT/'textures'/(f'{name}_normal.png' if kind=='normal' else f'{name}.png')
        im=Image.open(src).convert('RGB').resize((size,size),Image.LANCZOS);buf=io.BytesIO()
        # Engines recompress on import (ASTC/ETC2/BC); high-quality JPEG keeps the source small.
        im.save(buf,'JPEG',quality=94 if kind=='normal' else 90,subsampling=0 if kind=='normal' else 2);mime='image/jpeg'
        TEXCACHE[key]=(buf.getvalue(),mime)
    return TEXCACHE[key]

def texture_size(objects,lod=0):
    """Texture resolution from object size (small hand props do not need 1024 px), halved per LOD."""
    largest=max(float((hi-lo).max()) for lo,hi in (o.bounds() for o in objects))
    return max(128,(256 if largest<=.1 else 512 if largest<=1.5 else 1024)>>lod)

class GLB:
    def __init__(self):self.blob=bytearray();self.views=[];self.accessors=[]
    def view(self,data,target=None):
        while len(self.blob)%4:self.blob.append(0)
        v=dict(buffer=0,byteOffset=len(self.blob),byteLength=len(data))
        if target:v['target']=target
        self.views.append(v);self.blob.extend(data);return len(self.views)-1
    def accessor(self,a,typ,ctype,target=None,normalized=False,bounds=False):
        a=np.ascontiguousarray(np.asarray(a,dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[ctype]))
        d=dict(bufferView=self.view(a.tobytes(),target),componentType=ctype,count=len(a),type=typ)
        if normalized:d['normalized']=True
        if bounds:flat=a.reshape(len(a),-1);d.update(min=flat.min(0).tolist(),max=flat.max(0).tolist())
        self.accessors.append(d);return len(self.accessors)-1
    def save(self,path,doc):
        doc.update(buffers=[dict(byteLength=len(self.blob))],bufferViews=self.views,accessors=self.accessors)
        js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);blob=bytes(self.blob)+b'\0'*((-len(self.blob))%4)
        glb=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(blob))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(blob),0x004e4942)+blob
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(glb);return len(glb)

def unit(a,fallback):
    length=np.linalg.norm(a,axis=1,keepdims=True)
    return np.where(length>1e-12,a/np.maximum(length,1e-12),fallback)

def smooth_normals(v,f):
    cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    normals=np.zeros_like(v)
    for k in range(3):np.add.at(normals,f[:,k],cross)
    return unit(normals,[0.,1.,0.])

def tangents(v,n,uv,f):
    """Per-vertex tangents (xyz + handedness w) for the normal maps; glTF UVs have V pointing down."""
    t=uv*np.array([1,-1]);e1=v[f[:,1]]-v[f[:,0]];e2=v[f[:,2]]-v[f[:,0]];d1=t[f[:,1]]-t[f[:,0]];d2=t[f[:,2]]-t[f[:,0]]
    r=d1[:,0]*d2[:,1]-d2[:,0]*d1[:,1];ok=np.abs(r)>1e-14;r=np.where(ok,r,1.)
    sdir=(e1*d2[:,1:2]-e2*d1[:,1:2])/r[:,None]*ok[:,None];tdir=(e2*d1[:,0:1]-e1*d2[:,0:1])/r[:,None]*ok[:,None]
    tan=np.zeros_like(v);bit=np.zeros_like(v)
    for k in range(3):np.add.at(tan,f[:,k],sdir);np.add.at(bit,f[:,k],tdir)
    tan=tan-n*np.sum(n*tan,1,keepdims=True)
    alt=np.cross(n,np.where(np.abs(n[:,:1])<.9,[[1.,0,0]],[[0,1.,0]]))
    tan=unit(tan,unit(alt,[1.,0,0]))
    w=np.where(np.sum(np.cross(n,tan)*bit,1)<0,-1.,1.)
    return np.column_stack([tan,w])

def fibonacci_hemisphere(count):
    i=np.arange(count)+.5;y=1-i/count*.97;r=np.sqrt(1-y*y);a=i*math.pi*(3-math.sqrt(5))
    return np.stack([r*np.cos(a),y,r*np.sin(a)],1)

def bake_ao(v,f,n,thin,res=256,dirs=48):
    """Per-vertex sky visibility from the upper hemisphere (the ground occludes the lower half).
    Depth maps are built by splatting dense surface samples, so no external ray tracer is needed."""
    lo,hi=v.min(0),v.max(0);px=float(np.linalg.norm(hi-lo))/res
    a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];area=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
    count=np.clip(np.ceil(area/px**2*2),1,400).astype(int);tri=np.repeat(np.arange(len(f)),count)
    rng=np.random.default_rng(7);r1=np.sqrt(rng.random(len(tri)));r2=rng.random(len(tri))
    samples=a[tri]*(1-r1)[:,None]+b[tri]*(r1*(1-r2))[:,None]+c[tri]*(r1*r2)[:,None]
    visible=np.zeros(len(v));total=np.zeros(len(v))
    for d in fibonacci_hemisphere(dirs):
        u=np.cross(d,[0,0,1.] if abs(d[2])<.9 else [1.,0,0]);u/=np.linalg.norm(u);w=np.cross(d,u)
        P=np.stack([samples@u,samples@w],1);V=np.stack([v@u,v@w],1);o=np.minimum(P.min(0),V.min(0))
        size=(np.maximum(P.max(0),V.max(0))-o)/px+2;W,H=int(size[0])+1,int(size[1])+1
        zb=np.full(W*H,-np.inf);ip=((P-o)/px).astype(int);np.maximum.at(zb,ip[:,1]*W+ip[:,0],samples@d)
        iv=((V-o)/px).astype(int);vis=(v@d)>=zb[iv[:,1]*W+iv[:,0]]-2.5*px
        cos=n@d;weight=np.where(thin,np.abs(cos),np.maximum(cos,0))
        visible+=vis*weight;total+=weight
    ao=np.where(total>1e-6,visible/np.maximum(total,1e-6),.5)
    return np.clip(.3+.7*ao,0,1)

def quat(axis,deg):
    axis=np.asarray(axis,float);axis/=np.linalg.norm(axis);h=math.radians(deg)/2
    return [*(axis*math.sin(h)),math.cos(h)]

def export(objects,name,budget=None,folder=OUT,ao=True,collision=False,lod=0):
    g=GLB();mats=[];indices={};texnames=[]
    for o in objects:
        for part in o.parts:
            key=part[2]
            if key not in indices:indices[key]=len(mats);mats.append(M[key])
            tex=M[key]['tex']
            if tex and tex not in texnames:texnames.append(tex)
    size=texture_size(objects,lod);images=[]
    for tex in texnames:
        for kind in ['base','normal']:
            data,mime=texture_image(tex,size,kind);images.append(dict(bufferView=g.view(data),mimeType=mime,name=f'{tex}_{kind}'))
    material=[]
    for m in mats:
        pbr=dict(baseColorFactor=m['color']+[m['alpha']],roughnessFactor=m['rough'],metallicFactor=m['metal'])
        d=dict(name=m['name'],pbrMetallicRoughness=pbr,doubleSided=True)
        if m['tex']:
            t=texnames.index(m['tex']);pbr['baseColorTexture']=dict(index=2*t);d['normalTexture']=dict(index=2*t+1)
        if m['alpha']<1:d['alphaMode']='BLEND'
        material.append(d)
    meshes=[];nodes=[];skins=[];animations=[];roots=[];total=0
    for o in objects:
        bone_index={b[0]:i for i,b in enumerate(o.bones)}
        groups=[]
        for key in indices:
            parts=[p for p in o.parts if p[2]==key]
            if not parts:continue
            vs=[];fs=[];uvs=[];js=[];offset=0
            for v,f,_,uv,bone in parts:
                vs.append(v);fs.append(f+offset);uvs.append(uv);js.append(np.full(len(v),bone_index.get(bone,0)));offset+=len(v)
            v=to_gltf(np.concatenate(vs));f=np.concatenate(fs);uv=np.concatenate(uvs);joints=np.concatenate(js)
            cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);f=f[np.linalg.norm(cross,axis=1)>1e-13]
            # Drop vertices left unused by degenerate (zero-area) triangles, e.g. collapsed lathe poles.
            used=np.unique(f);remap=np.zeros(len(v),dtype=np.int64);remap[used]=np.arange(len(used))
            v,uv,joints,f=v[used],uv[used],joints[used],remap[f].astype(np.uint32)
            groups.append([key,v,f,uv,smooth_normals(v,f),joints])
        if ao:
            offs=np.cumsum([0]+[len(gr[1]) for gr in groups])
            allv=np.concatenate([gr[1] for gr in groups]);alln=np.concatenate([gr[4] for gr in groups])
            allf=np.concatenate([gr[2]+offs[i] for i,gr in enumerate(groups)])
            thin=np.concatenate([np.full(len(gr[1]),M[gr[0]]['thin']) for gr in groups])
            occl=bake_ao(allv,allf,alln,thin,res=384 if float(np.ptp(allv,0).max())>4 else 256)
        prim=[]
        for i,(key,v,f,uv,normals,joints) in enumerate(groups):
            attrs=dict(POSITION=g.accessor(v,'VEC3',5126,34962,bounds=True),NORMAL=g.accessor(normals,'VEC3',5126,34962),TEXCOORD_0=g.accessor(uv,'VEC2',5126,34962))
            if M[key]['tex']:attrs['TANGENT']=g.accessor(tangents(v,normals,uv,f),'VEC4',5126,34962)
            if ao:
                c=occl[offs[i]:offs[i+1]];attrs['COLOR_0']=g.accessor(np.stack([c,c,c,np.ones_like(c)],1)*255+.5,'VEC4',5121,34962,normalized=True)
            if o.bones:
                attrs['JOINTS_0']=g.accessor(np.stack([joints,0*joints,0*joints,0*joints],1),'VEC4',5121,34962)
                attrs['WEIGHTS_0']=g.accessor(np.tile([1.,0,0,0],(len(v),1)),'VEC4',5126,34962)
            small=len(v)<65536
            prim.append(dict(attributes=attrs,indices=g.accessor(f.reshape(-1),'SCALAR',5123 if small else 5125,34963),material=indices[key]))
            total+=len(f)
        mesh_node=len(nodes);nodes.append(dict(name=o.name,mesh=len(meshes)));meshes.append(dict(name=o.name,primitives=prim));roots.append(mesh_node)
        if o.bones:
            first=len(nodes);pos={n:to_gltf(p) for n,_,p in o.bones}
            for n,parent,_ in o.bones:
                rest=pos[n]-(pos[parent] if parent else 0);nodes.append(dict(name=n,translation=rest.tolist()))
            for i,(n,parent,_) in enumerate(o.bones):
                if parent:nodes[first+bone_index[parent]].setdefault('children',[]).append(first+i)
                else:roots.append(first+i)
            ibm=np.array([[1,0,0,0,0,1,0,0,0,0,1,0,-pos[n][0],-pos[n][1],-pos[n][2],1] for n,_,_ in o.bones])
            nodes[mesh_node]['skin']=len(skins)
            skins.append(dict(name=o.name+'_rig',joints=list(range(first,first+len(o.bones))),inverseBindMatrices=g.accessor(ibm,'MAT4',5126),skeleton=first))
            for clip in o.animations:
                samplers=[];channels=[]
                for bone,path,keys in clip['channels']:
                    times=np.array([k[0] for k in keys])
                    if path=='rotation':values=np.array([quat(*k[1:]) for k in keys])
                    else:values=np.array([nodes[first+bone_index[bone]]['translation']]*len(keys))+np.array([k[1] for k in keys])
                    samplers.append(dict(input=g.accessor(times,'SCALAR',5126,bounds=True),output=g.accessor(values,'VEC4' if path=='rotation' else 'VEC3',5126),interpolation='LINEAR'))
                    channels.append(dict(sampler=len(samplers)-1,target=dict(node=first+bone_index[bone],path=path)))
                animations.append(dict(name=clip['name'],samplers=samplers,channels=channels))
    if budget:assert total<budget,(name,total,budget)
    doc=dict(asset=dict(version='2.0',generator='Village Uthan procedural source',extras=dict(units='meters',upAxis='Y')),scene=0,scenes=[dict(nodes=roots)],nodes=nodes,meshes=meshes,materials=material)
    if images:doc.update(images=images,textures=[dict(source=i,sampler=0) for i in range(len(images))],samplers=[dict(wrapS=10497,wrapT=10497,magFilter=9729,minFilter=9987)])
    if skins:doc.update(skins=skins,animations=animations)
    nbytes=g.save(folder/f'{name}.glb',doc)
    report=dict(name=name,triangles=total,objects=len(objects),embedded_images=len(images),texture_px=size if images else None,bytes=nbytes)
    if collision:return report
    bounds=[o.bounds() for o in objects]
    report.update(budget=budget,dimensions_m=[(hi-lo).round(6).tolist() for lo,hi in bounds],bottom_center_origins=all(abs(lo[2])<1e-7 and abs(lo[0]+hi[0])<1e-7 and abs(lo[1]+hi[1])<1e-7 for lo,hi in bounds),baked_ao=ao)
    if any(o.bones for o in objects):report.update(joints=sum(len(o.bones) for o in objects),animations=[c['name'] for o in objects for c in o.animations])
    return report

# ---------------------------------------------------------------- assets

ASSETS={}
def asset(name,budget,ao=True):
    def wrap(fn):ASSETS[name]=(fn,budget,ao);return fn
    return wrap

def pebble(color):
    o=Mesh('guti_pebble_'+('light' if color=='cream' else 'dark'))
    ellipsoid(o,(0,0,0),(1,.84,.55),color,32,16,.045,.72)
    o.fit([.025,.021,.012]);o.collide_bounds('cylinder');return [o]
asset('guti_pebble_dark',3000,False)(lambda:pebble('dark'))
asset('guti_pebble_light',3000,False)(lambda:pebble('cream'))

@asset('guti_pebble_variations',18000,False)
def pebble_variations():
    objects=[]
    for color in ['dark','cream']:
        for i in range(3):
            o=Mesh(f'{color}_variation_{i+1}');ellipsoid(o,(0,0,0),(1,.72+i*.08,.6),color,28,14,.065+i*.016,.65,rot=i*.7);o.fit([.025,.018+i*.002,.011+i*.0006]);o.collide_bounds('cylinder');objects.append(o)
    return objects

@asset('guti_clay_shard',3000,False)
def clay_shard():
    o=Mesh('guti_clay_shard');ellipsoid(o,(0,0,0),(1,.76,.24),'clay',28,12,.11,.7);o.fit([.025,.020,.008]);o.collide_bounds('cylinder');return [o]

@asset('guti_tamarind_seed',2000,False)
def tamarind_seed():
    o=Mesh('guti_tamarind_seed');ellipsoid(o,(0,0,0),(1,.79,.66),'seed',28,14,.025,.78)
    ellipsoid(o,(.7,0,.12),(.14,.25,.19),'clay',12,6);o.fit([.025,.019,.015]);o.collide_bounds('cylinder');return [o]

@asset('prop_kolshi',8000)
def kolshi():
    o=Mesh('prop_kolshi');pot(o,.35,.145,'clay');o.fit(height=.35);o.collide_bounds('cylinder');return [o]

@asset('prop_chula',6000)
def chula():
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
    o.fit([.50,.32,.25]);o.collide_bounds('box');return [o]

@asset('prop_piri',3000)
def piri():
    o=Mesh('prop_piri')
    for y in [-.083,0,.083]:box(o,(0,y,.085),(.40,.080,.03),'wood')
    for x in [-.15,.15]:box(o,(x,0,.035),(.035,.22,.07),'wood')
    o.fit([.4,.25,.1]);o.collide_bounds('box');return [o]

@asset('prop_pati',2000)
def pati():
    o=Mesh('prop_pati');v=[];f=[];uv=[];nx=seg(24,4);ny=seg(18,4)
    for j in range(ny+1):
        for i in range(nx+1):
            x=i/nx;y=j/ny;z=.003+.003*math.sin(x*19+y*7)+.045*(abs(x-.5)*2)**12*(abs(y-.5)*2)**9
            v.append([(x-.5)*1.2,(y-.5)*.9,z]);uv.append([x*2,y*1.5])
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+nx+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
    o.add(v,f,'jute',uv)
    if DETAIL>.3:
        for edge in [-1,1]:
            for i in range(35):
                x=-.58+i*.034
                if keep(i):tube(o,[(x,edge*.45,.006),(x+.005,edge*.465,.005)],.0012*step()**.5,'jute',3)
    o.fit([1.2,.9,.05]);o.collide_bounds('box');return [o]

@asset('prop_lantern',5000)
def lantern():
    o=Mesh('prop_lantern')
    lathe(o,[(0,0),(.058,0),(.066,.012),(.063,.032),(.047,.048),(.018,.05),(0,.05)],'red',28)
    lathe(o,[(.030,.05),(.043,.07),(.047,.105),(.041,.15),(.028,.19)],'glass',28)
    lathe(o,[(0,.181),(.032,.181),(.052,.192),(.053,.202),(.025,.217),(.026,.23),(0,.23)],'red',28)
    for x in [-.056,.056]:tube(o,[(x,0,.025),(x*1.15,0,.07),(x*1.1,0,.18),(x*.55,0,.215)],[.009,.008,.008,.007],'red',8)
    tube(o,[(.057*math.cos(a),0,.23+.07*math.sin(a)) for a in np.linspace(0,math.pi,seg(20,6))],.0022,'iron',6)
    lathe(o,[(0,.05),(.015,.05),(.015,.063),(0,.063)],'iron',16)
    for z,r in [(.065,.043),(.17,.036)]:ring(o,(0,0,z),r,.002,'iron',28)
    o.collide('cylinder',(0,0,.115),(.132,.132,.23))
    o.fit(height=.3);return [o]

@asset('prop_haystack',8000)
def haystack():
    o=Mesh('prop_haystack')
    lathe(o,[(0,0),(1.0,0),(1.12,.18),(1.09,.6),(.94,1.1),(.72,1.55),(.43,1.95),(.12,2.25),(0,2.3)],'straw',48,wobble=.025)
    tube(o,[(0,0,0),(0,0,2.5)],.035,'bamboo',10)
    for k in range(240):
        a=random.uniform(0,TAU);z=random.uniform(.08,2.15);r=np.interp(z,[.08,.6,1.1,1.55,1.95,2.2],[1.1,1.1,.95,.73,.44,.15]);length=random.uniform(.10,.3)
        if keep(k):tube(o,[(r*math.cos(a),r*math.sin(a),z),((r+.06)*math.cos(a+.015),(r+.06)*math.sin(a+.015),max(0,z-length))],.003*step()**.5,'straw',3)
    for c,s in [((0,0,.55),(2.24,2.24,1.1)),((0,0,1.4),(1.6,1.6,.6)),((0,0,1.95),(.9,.9,.5)),((0,0,2.35),(.07,.07,.3))]:o.collide('cylinder',c,s)
    o.fit(height=2.5);return [o]

@asset('prop_fence',4000)
def fence():
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
    o.fit([2,.09,1.5]);o.collide_bounds('box');return [o]

@asset('prop_house',20000)
def house():
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
    # Two corrugated roof pitches, no baked lighting. Lower LODs use flat sheets and rely on the normal map.
    nx=120 if DETAIL==1 else 6;amp=.012 if DETAIL==1 else 0
    for side in [-1,1]:
        v=[];f=[];uv=[]
        for j in range(2):
            for i in range(nx+1):
                x=-3+6*i/nx;y=.2+side*j*1.65;z=3.5-j*.92+amp*math.cos(i*math.pi)
                v.append([x,y,z]);uv.append([i/nx*6,j*2])
        for i in range(nx):a=i;b=i+nx+1;f.extend([[a,a+1,b+1],[a,b+1,b]])
        o.add(v,f,'tin',uv)
    # Veranda roof and triangular gable infill.
    v=[[-2.95,-1.12,2.60],[2.95,-1.12,2.60],[2.95,-2,2.22],[-2.95,-2,2.22]]
    o.add(v,[[0,1,2],[0,2,3]],'tin',[[0,0],[6,0],[6,1],[0,1]])
    for x in [-2.68,2.68]:o.add([[x,-1.38,2.6],[x,1.78,2.6],[x,.2,3.49]],[[0,1,2]],'mud')
    for x in [-2.55,-.3,2.55]:tube(o,[(x,-1.7,2.2),(x,-.9,2.58)],.04,'wood',6)
    o.collide('box',(0,0,.12),(5.7,3.7,.24))
    o.collide('box',(0,.19,1.43),(5.54,2.66,2.4))
    o.collide('box',(0,.2,3.05),(5.9,3.3,.9))
    for x in [-2.55,-.3,2.55]:o.collide('cylinder',(x,-1.72,1.26),(.11,.11,2.04))
    o.fit([6,4,3.5]);return [o]

@asset('prop_chouki',5000)
def chouki():
    o=Mesh('prop_chouki')
    for i in range(10):box(o,(-.81+i*.18,0,.42),(.174,1.2,.06),'wood')
    for x in [-.79,.79]:
        for y in [-.49,.49]:box(o,(x,y,.2),(.095,.095,.4),'wood')
    for y in [-.54,.54]:box(o,(0,y,.35),(1.8,.055,.15),'wood')
    for x in [-.84,.84]:box(o,(x,0,.35),(.055,1.2,.15),'wood')
    o.fit([1.8,1.2,.45]);o.collide_bounds('box');return [o]

@asset('prop_clothesline',4000)
def clothesline():
    o=Mesh('prop_clothesline')
    for x in [-1.5,1.5]:tube(o,[(x,0,0),(x+.008,0,1.9)],.025,'bamboo',10)
    pts=[(-1.5+3*i/30,0,1.85-.12*math.sin(math.pi*i/30)) for i in range(31)]
    tube(o,pts,.004,'jute',5)
    s=step()
    for left,width,height,colors in [(-1.1,.65,.8,['clothred','clothcream']),(.0,1.05,1.05,['clothblue','clothcream'])]:
        nx=18//s;ny=20//s
        for j in range(ny):
            for i in range(nx):
                verts=[]
                for a,b in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
                    x=left+width*a/nx;t=b/ny;top=1.85-.12*math.sin(math.pi*(x+1.5)/3)
                    verts.append([x,.024*math.sin(a/nx*TAU*3)+.035*t*t*math.sin(a*s),top-height*t])
                key=colors[1] if (i*s)%6<s or (j*s)%6<s else colors[0]
                o.add(verts,[[0,1,2],[0,2,3]],key,[[0,0],[.2,0],[.2,.2],[0,.2]])
    for x in [-1.5,1.5]:o.collide('cylinder',(x+.004,0,.95),(.05,.05,1.9))
    # Keep poles exactly 3m apart, overall diameter adds 5cm.
    o.fit(height=1.9);return [o]

@asset('prop_kula',4000)
def kula():
    o=Mesh('prop_kula');lathe(o,[(0,0),(.18,0),(.24,.012),(.25,.034),(.242,.042),(.232,.025),(.18,.012),(0,.012)],'bamboo',48,wobble=.009)
    ring(o,(0,0,.035),.245,.006,'bamboo',48);o.fit([.5,.5,.045]);o.collide_bounds('cylinder');return [o]

@asset('prop_dala',4000)
def dala():
    o=Mesh('prop_dala');lathe(o,[(0,0),(.13,0),(.16,.025),(.20,.13),(.225,.20),(.22,.208),(.21,.19),(.19,.13),(.15,.03),(0,.014)],'bamboo',48,wobble=.012)
    ring(o,(0,0,.202),.219,.007,'bamboo',48);o.fit([.45,.45,.21]);o.collide_bounds('cylinder');return [o]

@asset('prop_pots',5000)
def pots():
    objects=[]
    for name,h,r,m in [('aluminium_handi',.24,.19,'aluminium'),('brass_lota',.22,.105,'brass'),('clay_rice_pot',.30,.17,'clay')]:
        o=Mesh(name);pot(o,h,r,m,n=28);o.fit(height=h);o.collide_bounds('cylinder');objects.append(o)
    return objects

@asset('prop_jharu',2000)
def jharu():
    o=Mesh('prop_jharu')
    for i in range(40):
        a=random.uniform(0,TAU);r=random.uniform(.005,.022);spread=random.uniform(-.12,.12);tip=.02+random.uniform(0,.035)
        if keep(i):tube(o,[(r*math.cos(a),r*math.sin(a),.7),(r*math.cos(a),r*math.sin(a),.42),(spread,r*math.sin(a)*2,tip)],[.0015*step()**.5,.0015,.0006],'straw',3)
    for z in [.46,.48,.5]:ring(o,(0,0,z),.023,.003,'jute',12)
    o.fit(height=.7);o.collide_bounds('box');return [o]

@asset('prop_chicken',6000)
def chicken():
    o=Mesh('prop_chicken')
    # Rigid-skinned joints, pivots in build coordinates (chicken faces -Y here, +Z in the GLB).
    o.bones=[('hips',None,(0,0,.17)),('neck','hips',(0,-.05,.20)),('head','neck',(0,-.072,.26)),('tail','hips',(0,.06,.20)),('leg_L','hips',(-.025,.012,.13)),('leg_R','hips',(.025,.012,.13))]
    o.bone='hips';ellipsoid(o,(0,0,.17),(.065,.095,.074),'feather',24,14)
    o.bone='neck';ellipsoid(o,(0,-.058,.225),(.036,.039,.07),'feather',20,12)
    o.bone='head';ellipsoid(o,(0,-.076,.283),(.028,.032,.031),'feather',20,10)
    # Layered wing feathers follow the flanks.
    for side in [-1,1]:
        o.bone='hips';ellipsoid(o,(side*.055,.015,.177),(.017,.061,.040),'feather',18,10)
        for j in range(6):
            leaf(o,(side*.059,-.012+j*.006,.195-j*.004),(side*.061,.065+j*.004,.145-j*.002),.010,'black' if j>3 else 'feather',3,.007)
        o.bone='head'
        ellipsoid(o,(side*.026,-.089,.292),(.003,.006,.006),'beak',10,6)
        ellipsoid(o,(side*.028,-.090,.293),(.0018,.0035,.0035),'eye',10,6)
    tube(o,[(0,-.104,.282),(0,-.127,.277)],[.009,0],'beak',8)
    for i in range(5):ellipsoid(o,(0,-.09+i*.009,.313+(.012 if i in [1,2] else .006)),(.005,.008,.012),'comb',10,6)
    for x in [-.006,.006]:ellipsoid(o,(x,-.096,.262),(.005,.006,.013),'comb',10,6)
    for x,bone in [(-.025,'leg_L'),(.025,'leg_R')]:
        o.bone=bone
        tube(o,[(x,.012,.13),(x,.022,.062),(x,.009,.018)],[.009,.005,.004],'beak',8)
        for spread in [-1,0,1]:tube(o,[(x,.009,.018),(x+spread*.014,-.024,.009),(x+spread*.017,-.036,.006)],[.0035,.002,.0005],'beak',5)
        tube(o,[(x,.01,.018),(x,.037,.006)],[.003,.0005],'beak',5)
    o.bone='tail'
    for i in range(9):
        x=(i-4)*.007;leaf(o,(x,.063,.20),(x*1.4,.15+abs(i-4)*.004,.30-abs(i-4)*.013),.012,'black',6,.025)
    o.collide('box',(0,-.01,.21),(.15,.24,.21))
    o.collide('box',(0,0,.06),(.09,.08,.12))
    o.fit(height=.35)
    X,Y=(1,0,0),(0,1,0)
    o.animations=[
        dict(name='idle',channels=[
            ('hips','translation',[(t,(0,dy,0)) for t,dy in [(0,0),(1.2,.003),(2.4,0)]]),
            ('neck','rotation',[(t,X,a) for t,a in [(0,0),(1.2,6),(2.4,0)]]),
            ('head','rotation',[(t,Y,a) for t,a in [(0,0),(.5,28),(.9,28),(1.3,-22),(1.9,-22),(2.4,0)]]),
            ('tail','rotation',[(t,X,a) for t,a in [(0,0),(1.2,-4),(2.4,0)]])]),
        dict(name='peck',channels=[
            ('neck','rotation',[(t,X,a) for t,a in [(0,0),(.25,48),(.35,52),(.45,46),(.55,52),(.9,0),(1.2,0)]]),
            ('head','rotation',[(t,X,a) for t,a in [(0,0),(.25,24),(.55,26),(.9,0),(1.2,0)]]),
            ('hips','rotation',[(t,X,a) for t,a in [(0,0),(.3,10),(.6,10),(.9,0),(1.2,0)]])]),
        dict(name='walk',channels=[
            ('leg_L','rotation',[(t,X,a) for t,a in [(0,22),(.4,-22),(.8,22)]]),
            ('leg_R','rotation',[(t,X,a) for t,a in [(0,-22),(.4,22),(.8,-22)]]),
            ('hips','translation',[(t,(0,dy,0)) for t,dy in [(0,0),(.2,.006),(.4,0),(.6,.006),(.8,0)]]),
            ('neck','rotation',[(t,X,a) for t,a in [(0,-8),(.2,10),(.4,-8),(.6,10),(.8,-8)]]),
            ('tail','rotation',[(t,X,a) for t,a in [(0,0),(.2,-5),(.4,0),(.6,-5),(.8,0)]])])]
    return [o]

@asset('prop_banana_tree',10000)
def banana():
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
        for t in np.linspace(0,1,seg(9)):pts.append([end[0]*t,end[1]*t,z+(end[2]-z)*t+.45*math.sin(math.pi*t)])
        tube(o,pts,[.012*(1-t)+.001 for t in np.linspace(0,1,len(pts))],'leaf2',5)
    o.collide('cylinder',(0,0,1.0),(.3,.3,2.0))
    o.fit(height=3);return [o]

@asset('prop_banyan_tree',50000)
def banyan():
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
            if DETAIL>.3 or j%2==0:tube(o,[p,p+np.array([.07,-.06,-1]),[p[0]+.1,p[1]-.04,bottom]],[.024,.014,.008],'bark',5)
    crowns += [np.array([0,0,8.8]),np.array([1,0,9]),np.array([-1,0,9])]
    # Individual leaf geometry avoids opaque polygon blobs and alpha sorting. Sparser LODs use larger leaves.
    grow=step()**.5
    for c in crowns:
        for j in range(145):
            a=rng.uniform(0,TAU);r=rng.uniform(.1,1.5);z=rng.uniform(-.6,.65)
            p=c+np.array([r*math.cos(a),r*math.sin(a),z]);ang=rng.uniform(0,TAU);ln=rng.uniform(.48,.78)
            end=p+np.array([ln*grow*math.cos(ang),ln*grow*math.sin(ang),rng.uniform(-.16,.1)])
            if keep(j):leaf(o,p,end,ln*grow*.32,'leaf2' if j%5==0 else 'leaf',2,.025)
    o.collide('cylinder',(0,0,2.75),(1.9,1.9,5.5))
    o.collide('cylinder',(0,0,.25),(3.8,3.8,.5))
    o.fit([15,14,12]);return [o]

# ---------------------------------------------------------------- collision

def collider_objects(objects):
    """Collision meshes plus primitive descriptions, both in the asset's glTF space."""
    meshes=[];shapes=[]
    for o in objects:
        for i,(kind,c,s) in enumerate(o.colliders):
            m=Mesh(f'{o.name}_col_{i}')
            if kind=='box':box(m,c,s,'collider')
            else:
                r=max(s[0],s[1])/2;lathe(m,[(0,0),(r,0),(r,s[2]),(0,s[2])],'collider',16,(c[0],c[1],c[2]-s[2]/2))
            meshes.append(m)
            shapes.append(dict(object=o.name,type=kind,center=to_gltf(c).round(4).tolist(),size=[round(float(s[0]),4),round(float(s[2]),4),round(float(s[1]),4)],**({'radius':round(float(max(s[0],s[1])/2),4),'height':round(float(s[2]),4),'axis':'Y'} if kind=='cylinder' else {})))
    return meshes,shapes

if __name__=='__main__':
    import sys
    only=set(sys.argv[1:])
    report=[];collision={}
    for name,(fn,budget,ao) in ASSETS.items():
        if only and name not in only:continue
        entry=None;lods=[]
        for level,detail in LODS:
            DETAIL=detail;random.seed(16016)
            objects=fn()
            if level==1:
                entry=export(objects,name,budget,ao=ao)
                meshes,shapes=collider_objects(objects);collision[name]=shapes
                col=export(meshes,f'{name}_col',folder=OUT/'collision',ao=False,collision=True)
                entry['collision']=dict(file=f'models/collision/{name}_col.glb',shapes=len(shapes),triangles=col['triangles'])
            elif not name.startswith('guti_'):
                tris=sum(len(p[1]) for o in objects for p in o.parts)
                previous=lods[-1]['triangles'] if lods else entry['triangles']
                if tris<=previous*.8:
                    r=export(objects,f'{name}_lod{level-1}',folder=OUT/'lod',ao=ao,lod=level-1)
                    lods.append(dict(file=f'models/lod/{name}_lod{level-1}.glb',triangles=r['triangles'],bytes=r['bytes']))
        entry['lods']=lods;report.append(entry);print(json.dumps(entry))
    if not only:
        (ROOT/'production'/'model_validation.json').write_text(json.dumps(report,indent=2))
        (ROOT/'production'/'collision.json').write_text(json.dumps(dict(space='glTF Y-up metres, relative to each object origin',shapes=collision),indent=2))
