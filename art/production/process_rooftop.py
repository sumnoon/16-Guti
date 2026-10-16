"""User-authorized deterministic raster finishing. Originals are preserved once.
Wraps material edges, derives night facade from exactly the daytime geometry,
normalizes 4x4 effect cells, and corrects panorama seams/poles. No invented detail.
"""
import json,math,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
import process_images as p
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'production'/'rooftop_source'
def source(folder,name):
    out=SRC/folder/(name+'.png');out.parent.mkdir(parents=True,exist_ok=True)
    if not out.exists():shutil.copy2(ROOT/folder/out.name,out)
    return out
def exact_wrap(a,vertical=False,band=8):
    if vertical:a=a.transpose(1,0,2)
    a=a.copy();target=(a[:,0]+a[:,-1])/2
    dl=target-a[:,0];dr=target-a[:,-1]
    for i in range(band):
        t=(1-i/band)**2;a[:,i]+=dl*t;a[:,-1-i]+=dr*t
    if vertical:a=a.transpose(1,0,2)
    return np.clip(a,0,1)
def quilt(a,vertical=True):
    a=p.equalize_wrap(a);w=a.shape[1];ov=p.best_overlap(a,w//16,w//5,w//24);a=p.wrap_horizontal(a,ov)
    if vertical:
        t=p.equalize_wrap(a.transpose(1,0,2));w=t.shape[1];ov=p.best_overlap(t,w//16,w//5,w//24);a=p.wrap_horizontal(t,ov,circular=True).transpose(1,0,2)
    a=p.resize(a,(1254,1254));a=exact_wrap(a)
    if vertical:a=exact_wrap(a,True)
    return a
def report(name,src,a,extra=None):
    e=dict(name=name,source_size=list(Image.open(src).size),size=[a.shape[1],a.shape[0]],before=p.edge_errors(p.load(src)),after=p.edge_errors(a))
    if extra:e.update(extra)
    return e
reports=[]
for name in ['rooftop_tex_cement','rooftop_tex_plaster_old','rooftop_tex_brick_old','rooftop_tex_parapet_paint','rooftop_tex_tarp','rooftop_tex_jute_mat']:
    src=source('textures',name);a=quilt(p.load(src));a=p.flatten_lighting(a,.55)
    # Original cement was excessively colourful. Keep old paint flecks but bring
    # the overall surface back to the art bible's neutral cement grey.
    if name.endswith('cement'):
        lum=p.luminance(a);a=.22*a+.78*lum[...,None]*np.array([1.025,1,.975])
    a=exact_wrap(exact_wrap(a),True);p.save(a,ROOT/'textures'/f'{name}.png');reports.append(report(name,src,a));print(name,flush=True)

# Facade has two floors. Preserve every pixel coordinate; only recolour lighting.
name='rooftop_tex_facade_day';src=source('textures',name);a=p.load(src)
# Keep architecture intact; a narrow symmetric wall-strip blend is less disruptive
# than removing an overlap containing windows. Both ends are the same wall strip.
width=70
for i in range(width):
    t=(1-i/width)**2;avg=(a[:,i]+a[:,-1-i])/2
    a[:,i]=a[:,i]*(1-t)+avg*t;a[:,-1-i]=a[:,-1-i]*(1-t)+avg*t
a=exact_wrap(a);p.save(a,ROOT/'textures'/f'{name}.png');reports.append(report(name,src,a))
source('textures','rooftop_tex_facade_night')
H,W=a.shape[:2];mask=Image.new('L',(W,H));draw=ImageDraw.Draw(mask)
for x0,y0,x1,y1 in [(.125,.164,.252,.368),(.747,.162,.874,.370),(.748,.672,.878,.905)]:draw.rectangle((int(x0*W),int(y0*H),int(x1*W),int(y1*H)),fill=255)
mask=np.asarray(mask.filter(ImageFilter.GaussianBlur(1.1)))/255.
lum=p.luminance(a);interior=1-np.clip((lum-.09)/.22,0,1)
glow=mask*interior
night=a*np.array([.31,.35,.46]);night=night+np.array([1,.62,.23])*glow[...,None]*.66
night=exact_wrap(night);p.save(night,ROOT/'textures'/'rooftop_tex_facade_night.png')
p.save(np.repeat(glow[...,None],3,2)*np.array([1,.56,.13]),ROOT/'textures'/'rooftop_tex_facade_emissive.png')
reports.append(dict(name='rooftop_tex_facade_night',derived_from='rooftop_tex_facade_day',geometry_pixel_aligned=True,size=[W,H],after=p.edge_errors(night)))

# Use exactly the same panorama wrap coordinates for both lighting variants.
panos={}
for name in ['rooftop_pano_dusk','rooftop_pano_night']:panos[name]=p.equalize_wrap(p.load(source('panoramas',name)))
dusk=panos['rooftop_pano_dusk'];h,w=dusk.shape[:2];ov=p.best_overlap(dusk,w//30,w//9,w//100)
aa,bb=dusk[:,w-ov:],dusk[:,:ov];cost=((aa-bb)**2).sum(2);cost[:,:11]=cost[:,-11:]=1e6;path,_=p.min_cut(cost)
t=np.clip((np.arange(ov)[None,:]-path[:,None]+10)/20,0,1)[...,None]
for name,a in panos.items():
    out=a[:,:w-ov].copy();out[:,:ov]=a[:,w-ov:]*(1-t)+a[:,:ov]*t
    band=int(h*.1)
    for edge,rows in [(0,range(band)),(h-1,range(h-band,h))]:
        pole=out[edge].mean(0)
        for y in rows:
            weight=(1-abs(y-edge)/band)**2;out[y]=out[y]*(1-weight)+pole*weight
    out=p.resize(out,(2048,1024));out=exact_wrap(out,band=12);out[0]=out[0].mean(0);out[-1]=out[-1].mean(0)
    p.save(out,ROOT/'panoramas'/f'{name}.png');reports.append(report(name,SRC/'panoramas'/f'{name}.png',out,dict(top_row_std=float(out[0].std(0).mean()),bottom_row_std=float(out[-1].std(0).mean()),shared_wrap_overlap=ov,upscaled=True)))

# Resample each atlas cell independently, remove near-black noise, align anchors,
# and give each effect a clean black gutter. 512 px cells, 2048 px sheet.
effects={}
for name in ['rooftop_fx_fireworks','rooftop_fx_fire_breath','rooftop_fx_sparks']:
    im=Image.open(source('effects',name)).convert('RGB');cells=[]
    for j in range(4):
        for i in range(4):
            crop=im.crop((round(i*im.width/4),round(j*im.height/4),round((i+1)*im.width/4),round((j+1)*im.height/4)))
            a=np.array(crop);a[a.max(2)<10]=0
            a=np.uint8(np.maximum(a.astype(float)-3,0)*255/252);cells.append(Image.fromarray(a))
    sheet=Image.new('RGB',(2048,2048));anchor=[.5,.5]
    for k,cell in enumerate(cells):
        # Same resampling ratio for every frame preserves relative burst growth.
        cell=cell.resize((432,432),Image.Resampling.LANCZOS)
        a=np.asarray(cell).copy();a[a.max(2)<5]=0;cell=Image.fromarray(a)
        dx=dy=0
        if 'fire_breath' in name:
            ys,xs=np.where(a.max(2)>45)
            if len(xs):
                left=int(xs.min());near=xs<left+14;origin=int(np.median(ys[near]));dx=12-left;dy=250-origin
            anchor=[52/512,290/512]
        frame=Image.new('RGB',(512,512));frame.paste(cell,(40+dx,40+dy));sheet.paste(frame,((k%4)*512,(k//4)*512))
    sheet.save(ROOT/'effects'/f'{name}.png')
    effects[name]=dict(columns=4,rows=4,cell_px=512,sheet_px=2048,blend='additive',depth_write=False,wrap='clamp',anchor_uv_top_left=anchor,fps=12,loop=False,clips={colour:list(range(row*4,row*4+4)) for row,colour in enumerate(['red','green','gold','magenta'])} if name.endswith('fireworks') else {'burst':list(range(16))})
    reports.append(dict(name=name,size=[2048,2048],cell_px=512,source_size=list(im.size),upscaled=True,pure_black_background=True))
(ROOT/'effects'/'rooftop_fx_playback.json').write_text(json.dumps(effects,indent=2))

# Atlas dimensions become exact cell multiples; no white-key transparency needed
# because the GLB kite uses a fitted diamond mesh.
im=Image.open(source('textures','rooftop_tex_kite_atlas'));im.resize((1280,1280),Image.Resampling.LANCZOS).save(ROOT/'textures'/'rooftop_tex_kite_atlas.png')
for folder,name in [('ui','ui_rooftop_loading')]:
    im=Image.open(source(folder,name));w=im.width//16*16;h=w//16*9
    im.crop(((im.width-w)//2,(im.height-h)//2,(im.width+w)//2,(im.height+h)//2)).save(ROOT/folder/(name+'.png'))
(ROOT/'production'/'rooftop_image_processing.json').write_text(json.dumps(reports,indent=2))
print('Finished',len(reports),'technical image operations',flush=True)
