"""Read back GLBs; validate structural properties and render actual mesh previews."""
import json,struct,io,math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
PREVIEW=ROOT/'previews';PREVIEW.mkdir(exist_ok=True)

def read_glb(path):
    b=path.read_bytes();magic,version,length=struct.unpack_from('<III',b)
    assert magic==0x46546c67 and version==2 and length==len(b)
    jl,jt=struct.unpack_from('<II',b,12);d=json.loads(b[20:20+jl]);bl,bt=struct.unpack_from('<II',b,20+jl);raw=b[28+jl:]
    assert bl==len(raw)
    def arr(i):
        a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        out=np.frombuffer(raw,dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']],count=a['count']*count,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,count)
        return out/{5121:255.,5123:65535.}[a['componentType']] if a.get('normalized') else out
    textures=[]
    for image in d.get('images',[]):
        assert 'uri' not in image
        v=d['bufferViews'][image['bufferView']];img=Image.open(io.BytesIO(raw[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGB');textures.append(np.asarray(img)/255.)
    parts=[];tri=0
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            v=arr(p['attributes']['POSITION']);n=arr(p['attributes']['NORMAL']);uv=arr(p['attributes']['TEXCOORD_0']);f=arr(p['indices']).reshape(-1,3)
            assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all() and f.max()<len(v)
            ao=arr(p['attributes']['COLOR_0'])[:,0] if 'COLOR_0' in p['attributes'] else np.ones(len(v))
            if 'JOINTS_0' in p['attributes']:
                assert arr(p['attributes']['JOINTS_0']).max()<len(d['skins'][0]['joints']) and np.allclose(arr(p['attributes']['WEIGHTS_0']).sum(1),1)
            tri+=len(f);v=v[:,[0,2,1]]*np.array([1,-1,1]);n=n[:,[0,2,1]]*np.array([1,-1,1]);parts.append((v,f,n,uv,d['materials'][p['material']],ao))
    return d,parts,textures,tri

def render(parts,textures,size=360):
    # Multi-object sets preview the first object in place; all nodes have individual origins.
    allv=np.concatenate([p[0] for p in parts]);lo=allv.min(0);hi=allv.max(0);center=(lo+hi)/2
    forward=np.array([4.,-6.,3.7]);forward/=np.linalg.norm(forward);right=np.cross([0,0,1.],forward);right/=np.linalg.norm(right);up=np.cross(forward,right);basis=np.array([right,up,forward]).T
    projected=(allv-center)@basis;scale=(size-38)/max(np.ptp(projected[:,0]),np.ptp(projected[:,1]))
    canvas=np.full((size,size,3),[.88,.87,.83]);depth=np.full((size,size),-np.inf)
    light=np.array([-3.,-4.,7.]);light/=np.linalg.norm(light)
    for v,f,n,uv,material,ao in parts:
        proj=(v-center)@basis;proj[:,:2]*=scale;proj[:,0]+=size/2;proj[:,1]=size/2-proj[:,1]
        pbr=material['pbrMetallicRoughness'];color=np.array(pbr['baseColorFactor'][:3]);tex=None
        if 'baseColorTexture' in pbr:tex=textures[pbr['baseColorTexture']['index']]
        if material.get('alphaMode')=='BLEND':continue
        for face in f:
            q=proj[face];x0=max(0,int(q[:,0].min()));x1=min(size-1,int(q[:,0].max()+1));y0=max(0,int(q[:,1].min()));y1=min(size-1,int(q[:,1].max()+1))
            if x0>x1 or y0>y1:continue
            den=(q[1,1]-q[2,1])*(q[0,0]-q[2,0])+(q[2,0]-q[1,0])*(q[0,1]-q[2,1])
            if abs(den)<1e-10:continue
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
            a=((q[1,1]-q[2,1])*(xx-q[2,0])+(q[2,0]-q[1,0])*(yy-q[2,1]))/den
            b=((q[2,1]-q[0,1])*(xx-q[2,0])+(q[0,0]-q[2,0])*(yy-q[2,1]))/den;c=1-a-b
            z=a*q[0,2]+b*q[1,2]+c*q[2,2];sl=depth[y0:y1+1,x0:x1+1];mask=(a>=0)&(b>=0)&(c>=0)&(z>sl)
            if not mask.any():continue
            nn=a[...,None]*n[face[0]]+b[...,None]*n[face[1]]+c[...,None]*n[face[2]];nn/=np.maximum(np.linalg.norm(nn,axis=2,keepdims=True),1e-10)
            shade=(.42+.58*np.abs(np.sum(nn*light,axis=2)))*(a*ao[face[0]]+b*ao[face[1]]+c*ao[face[2]])
            rgb=color*shade[...,None]
            if tex is not None:
                tt=a[...,None]*uv[face[0]]+b[...,None]*uv[face[1]]+c[...,None]*uv[face[2]];tx=((tt[...,0]%1)*(tex.shape[1]-1)).astype(int);ty=((tt[...,1]%1)*(tex.shape[0]-1)).astype(int);rgb=rgb*tex[ty,tx]
            canvas[y0:y1+1,x0:x1+1][mask]=rgb[mask];sl[mask]=z[mask]
    return Image.fromarray(np.uint8(np.clip(canvas,0,1)*255))

report=[];tiles=[]
for path in sorted((ROOT/'models').rglob('*.glb')):
    d,parts,textures,tri=read_glb(path)
    entry=dict(name=path.stem,file=path.relative_to(ROOT).as_posix(),readback='PASS',triangles=tri,mesh_objects=len(d['meshes']),embedded_images=len(textures),
               joints=sum(len(s['joints']) for s in d.get('skins',[])),animations=[a['name'] for a in d.get('animations',[])])
    if path.parent!=ROOT/'models':report.append(entry);continue
    # Do not overlay the separately named parts in a set for visual review.
    if len(d['meshes'])>1:
        count=len(d['meshes'][0]['primitives']);parts=parts[:count]
    img=render(parts,textures);img.save(PREVIEW/(path.stem+'.png'))
    tile=Image.new('RGB',(360,395),'#eeeae0');tile.paste(img,(0,0));draw=ImageDraw.Draw(tile);draw.text((10,365),path.stem,fill='#33291e');draw.text((10,380),f'{tri:,} triangles',fill='#6b5944');tiles.append(tile)
    report.append(entry)
sheet=Image.new('RGB',(360*4,395*math.ceil(len(tiles)/4)),'#eeeae0')
for i,t in enumerate(tiles):sheet.paste(t,((i%4)*360,(i//4)*395))
sheet.save(PREVIEW/'model_contact_sheet.jpg',quality=93)
(ROOT/'production'/'glb_readback_report.json').write_text(json.dumps(report,indent=2))

checks=[]
# Wrap errors compare pixels that become neighbours when the image repeats; they should sit near the
# interior neighbour error. Panorama poles should be one colour (row std near 0); their rows do not wrap vertically.
for folder in ['textures','panoramas']:
    for path in sorted((ROOT/folder).glob('*.png')):
        im=Image.open(path).convert('RGB');a=np.asarray(im,dtype=float)
        c=dict(name=path.stem,size=list(im.size),horizontal_wrap_error=round(float(np.abs(a[:,0]-a[:,-1]).mean()),2),interior_neighbor_error=round(float(np.abs(a[:,1:]-a[:,:-1]).mean()),2))
        if folder=='textures':c['vertical_wrap_error']=round(float(np.abs(a[0]-a[-1]).mean()),2)
        else:c.update(top_row_std=round(float(a[0].std(0).mean()),2),bottom_row_std=round(float(a[-1].std(0).mean()),2))
        checks.append(c)
(ROOT/'production'/'image_checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(dict(glbs=len(report),images=len(checks),preview=str(PREVIEW/'model_contact_sheet.jpg'))))
