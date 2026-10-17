"""Split the generated surface atlas and finish repeatable supplemental materials."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
import process_images as p
ROOT=Path(__file__).resolve().parents[1]
names=['tank','redplastic','iron','wood','clay','paper','skin','leaf','moa']
im=Image.open(ROOT/'production/rooftop_source/textures/support_rooftop_surfaces.png').convert('RGB')
for i,name in enumerate(names):
    col,row=i%3,i//3
    tile=im.crop((round(col*im.width/3)+6,round(row*im.height/3)+6,round((col+1)*im.width/3)-6,round((row+1)*im.height/3)-6))
    a=np.asarray(tile,dtype=float)/255
    for axis in [0,1]:
        if axis:a=a.transpose(1,0,2)
        a=p.wrap_horizontal(a,max(16,a.shape[1]//8),circular=bool(axis))
        if axis:a=a.transpose(1,0,2)
    a=p.resize(p.flatten_lighting(a,.65),(768,768))
    a[:,0]=a[:,-1]=(a[:,0]+a[:,-1])/2
    a[0]=a[-1]=(a[0]+a[-1])/2
    dest=ROOT/'textures'/f'support_rooftop_{name}.png';p.save(a,dest)
    # Synthetic microrelief only. Never interpret coloured rust/dirt as deep relief.
    y,x=np.mgrid[:768,:768];rng=np.random.default_rng(i+1616)
    noise=rng.normal(0,1,(768,768))
    h=np.asarray(Image.fromarray(np.uint8(np.clip(noise*20+128,0,255))).filter(ImageFilter.GaussianBlur(.6)),float)/255
    if name=='wood':h+=.09*np.sin(x*.40+np.sin(y*.016))
    if name=='paper':h+=.025*np.sin(x*.8+y*.07)
    strength={'tank':.10,'redplastic':.08,'iron':.22,'wood':.18,'clay':.22,'paper':.10,'skin':.04,'leaf':.06,'moa':.08}[name]
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*strength;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*strength
    n=np.stack([-dx,-dy,np.ones_like(h)],2);n/=np.linalg.norm(n,axis=2,keepdims=True)
    p.save(n*.5+.5,dest.with_stem(dest.stem+'_normal'))
    rough={'tank':.64,'redplastic':.55,'iron':.74,'wood':.78,'clay':.94,'paper':.90,'skin':.66,'leaf':.62,'moa':.64}[name]
    orm=np.ones_like(a);orm[:,:,1]=np.clip(rough+(h-.5)*.5,.1,1)
    orm[:,:,2]=.55 if name=='iron' else 0
    p.save(orm,dest.with_stem(dest.stem+'_orm'))
print('Prepared nine supplemental base colour, micro-normal and roughness/metallic sets')
