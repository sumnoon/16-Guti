"""Finish the fine cotton scan and make a small woven-check lungi material."""
from pathlib import Path
import numpy as np
from PIL import Image
import process_images as p
ROOT=Path(__file__).resolve().parents[1]
a=p.load(ROOT/'production/rooftop_source/textures/support_rooftop_cotton.png')
for axis in [0,1]:
    if axis:a=a.transpose(1,0,2)
    w=a.shape[1];ov=p.best_overlap(a,w//18,w//7,w//25)
    a=p.wrap_horizontal(a,ov,circular=bool(axis))
    if axis:a=a.transpose(1,0,2)
a=p.resize(p.flatten_lighting(a,.8),(1024,1024))
# The scan remains off-white; colour factors are linearized by the model builder.
p.save(a,ROOT/'textures/support_rooftop_cotton.png')
y,x=np.mgrid[:1024,:1024];base=np.ones_like(a)*[.27,.42,.37]
for coord in [x,y]:
    stripe=coord%256
    base[stripe<20]*=.45;base[(stripe>=28)&(stripe<34)]=[.67,.66,.49]
    base[(stripe>=120)&(stripe<126)]=[.14,.24,.3]
base*=np.clip(p.luminance(a)[...,None]/.88,.7,1.15)
p.save(base,ROOT/'textures/support_rooftop_lungi.png')
print('Prepared cotton and woven-check lungi materials')
