"""Old Dhaka Rooftop Night: reproducible static low-poly GLBs, metres, bottom-centred.
Uses the existing mesh/export library without rebuilding or replacing Village Uthan assets.
Run with the bundled Python (numpy, Pillow). Raster assets must exist first.
"""
import math, json, io, random
from pathlib import Path
import numpy as np
from PIL import Image
import build_models as b
from build_models import Mesh, box, lathe, ellipsoid, tube, ring, leaf
ROOT=Path(__file__).resolve().parents[1]
TAU=math.tau
random.seed(16016)
M=b.M
def material(key,color,tex=None,rough=.8,metal=0,alpha=1):
    # Palette colours are authored in sRGB; glTF constant factors use linear RGB.
    if tex is None:color=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in color]
    M[key]=b.mat(key,color,tex,rough,metal,alpha)
material('cement',[1,1,1],'rooftop_tex_cement')
material('plaster',[1,1,1],'rooftop_tex_plaster_old')
material('turquoise',[1,1,1],'rooftop_tex_parapet_paint')
material('brick',[1,1,1],'rooftop_tex_brick_old')
material('facade',[1,1,1],'rooftop_tex_facade_day')
material('wood',[.5,.36,.22],'uthan_tex_bark_banyan')
material('blackplastic',[.055,.058,.063],'rooftop_tex_cement',.65)
material('rust',[.27,.17,.12],'rooftop_tex_cement',.72,.65)
material('steel',[.68,.7,.72],None,.3,.85)
material('paper',[.94,.63,.19],None,.8)
material('redplastic',[.60,.055,.09],'rooftop_tex_cement',.65)
material('magenta',[.65,.035,.24],None,.9)
material('green',[.07,.46,.35],None,.85)
material('yellow',[.94,.70,.20],None,.85)
material('amber',[1,.56,.15],None,.3)
material('glass',[.91,.97,1],None,.055,0,.28)
material('skin',[.47,.25,.13],None,.75)
material('skinlight',[.57,.33,.19],None,.75)
material('hair',[.025,.019,.016],None,.95)
material('shirt',[.065,.19,.29],None,.95)
material('lungi',[.14,.31,.28],'rooftop_tex_jute_mat',.95)
material('cloth',[.73,.64,.48],'rooftop_tex_jute_mat',.95)
material('leaf',[.16,.32,.11],None,.9)
material('flower',[.98,.40,.035],None,.9)
material('soil',[.13,.08,.045],None,1)
material('rice',[.82,.65,.37],None,.9)
material('kite',[1,1,1],'rooftop_tex_kite_atlas',.9)

# Export library expects a normal map slot; use a neutral tangent normal, never
# infer depth from colour stains. Source image resampling is only for GLB packing.
def packed_texture(name,size,kind):
    key=(name,size,kind)
    if key not in b.TEXCACHE:
        im=Image.new('RGB',(4,4),(128,128,255)) if kind=='normal' else Image.open(ROOT/'textures'/f'{name}.png').convert('RGB').resize((size,size),Image.Resampling.LANCZOS)
        out=io.BytesIO();im.save(out,'PNG' if kind=='normal' else 'JPEG',quality=92)
        b.TEXCACHE[key]=(out.getvalue(),'image/png' if kind=='normal' else 'image/jpeg')
    return b.TEXCACHE[key]
b.texture_image=packed_texture
original_save=b.GLB.save
def save_glb(self,path,doc):
    doc['asset']['generator']='Sholo Guti / Old Dhaka Rooftop procedural source'
    used=[]
    for m in doc['materials']:
        if m['name']=='glass':
            m['extensions']={'KHR_materials_transmission':{'transmissionFactor':.9},'KHR_materials_ior':{'ior':1.5}}
            m['pbrMetallicRoughness']['baseColorFactor'][3]=1
            m.pop('alphaMode',None);used+=['KHR_materials_transmission','KHR_materials_ior']
        if m['name']=='amber':m['emissiveFactor']=[1,.45,.08]
    if used:doc['extensionsUsed']=list(dict.fromkeys(used))
    # Arrange multi-object assets visibly, while each mesh keeps its own bottom centre.
    if path.stem in ('prop_flower_pots','char_kite_flyers'):
        stride=.5 if path.stem=='prop_flower_pots' else .9
        for i,n in enumerate(doc['nodes']):n['translation']=[(i-(len(doc['nodes'])-1)/2)*stride,0,0]
    return original_save(self,path,doc)
b.GLB.save=save_glb
ASSETS=[]
def register(name,budget,objects,dims=None,height=None):
    if not isinstance(objects,list):objects=[objects]
    for o in objects:o.fit(dims=dims,height=height)
    ASSETS.append((name,budget,objects))
def cyl(o,c,r,h,m,n=20):
    lathe(o,[(0,0),(r,0),(r,h),(0,h)],m,n,c)
def beam(o,a,z,r,m='rust',n=8):tube(o,[a,z],r,m,n)
def sagline(o,a,z,sag=.2,r=.006,m='rust',n=16):
    a=np.array(a);z=np.array(z)
    pts=[a+(z-a)*t+np.array([0,0,-sag*4*t*(1-t)]) for t in np.linspace(0,1,n)]
    tube(o,pts,r,m,5)
    return pts
def spool(o,center=(0,0,0),scale=1):
    p=np.array(center)
    tmp=Mesh('spool')
    beam(tmp,(-.15,0,0),(.15,0,0),.014,'wood',10)
    beam(tmp,(-.075,0,0),(.075,0,0),.045,'green',16)
    for x in [-.085,.085]:
        for a in [0,math.pi/2]:
            beam(tmp,(x,-.075*math.cos(a),-.075*math.sin(a)),(x,.075*math.cos(a),.075*math.sin(a)),.008,'wood',8)
    for x in np.linspace(-.07,.07,13):
        pts=[(x,.046*math.cos(a),.046*math.sin(a)) for a in np.linspace(0,TAU,17)]
        tube(tmp,pts,.0015,'green',3,False)
    for v,f,m,uv,_ in tmp.parts:o.add(v*scale+p,f,m,uv)

def make_guti():
    o=Mesh('guti_marble_glass')
    ellipsoid(o,(0,0,.0122),(.0125,.0125,.0125),'glass',28,16,flatten=.96)
    for phase,m in [(0,'green'),(2.1,'magenta'),(4.2,'yellow')]:
        pts=[(.005*math.cos(t*5+phase)*math.sin(t*math.pi),.005*math.sin(t*5+phase)*math.sin(t*math.pi),.004+t*.016) for t in np.linspace(0,1,15)]
        tube(o,pts,[.0005+.0013*math.sin(t*math.pi) for t in np.linspace(0,1,15)],m,5)
    register(o.name,2000,o,dims=[.025,.025,.0245])
    o=Mesh('guti_bottle_cap');n=84;v=[];f=[];uv=[]
    for j,(r,z) in enumerate([(.0113,.0035),(.012,.003),(.0125,0),(.0114,.0003),(.0108,.0027)]):
        for i in range(n+1):
            a=TAU*i/n;rr=r+(.0005*math.cos(21*a) if j in [1,2,3] else 0)
            v.append([rr*math.cos(a),rr*math.sin(a),z+.0003*math.sin(2*a)]);uv.append([i/n,j/4])
    for j in range(4):
        for i in range(n):
            k=j*(n+1)+i;f.extend([[k,k+1,k+n+2],[k,k+n+2,k+n+1]])
    o.add(v,f,'steel',uv)
    lathe(o,[(0,.0035),(.0113,.0035)],'redplastic',42)
    lathe(o,[(.0108,.0027),(0,.0027)],'cloth',42)
    register(o.name,2000,o,dims=[.025,.025,.004])

def architecture_props():
    o=Mesh('prop_parapet_segment');box(o,(0,0,.5),(2,.15,1),'turquoise');register(o.name,1500,o)
    o=Mesh('prop_water_tank')
    box(o,(0,0,.11),(1.04,1.04,.22),'brick')
    lathe(o,[(0,.22),(.47,.22),(.5,.28),(.5,1.22),(.45,1.30),(.23,1.34),(.23,1.38),(0,1.38)],'blackplastic',32)
    for z in [.34,.53,.72,.91,1.1,1.24]:ring(o,(0,0,z),.501,.012,'blackplastic',32)
    cyl(o,(0,0,1.38),.25,.02,'blackplastic',24)
    beam(o,(.46,0,.30),(.58,0,.30),.025,'rust')
    register(o.name,4000,o,height=1.4)
    o=Mesh('prop_chilekotha')
    # Door opening at front, separate jamb walls and lintel; hollow interior.
    box(o,(0,1.17,1.12),(2.5,.16,2.24),'plaster')
    box(o,(-1.17,0,1.12),(.16,2.34,2.24),'plaster')
    for cy,sy in [(-.84,.66),(.84,.66)]:box(o,(1.17,cy,1.12),(.16,sy,2.24),'plaster')
    box(o,(1.17,0,.48),(.16,1.02,.96),'plaster');box(o,(1.17,0,2.02),(.16,1.02,.44),'plaster')
    for cx,sx in [(-.86,.78),(.86,.78)]:box(o,(cx,-1.17,1.12),(sx,.16,2.24),'turquoise')
    box(o,(0,-1.17,2.12),(.94,.16,.24),'turquoise')
    box(o,(0,0,2.32),(2.5,2.5,.16),'cement')
    box(o,(-.46,-.9,1),(.06,.55,2),'wood')
    for y in np.linspace(-.45,.45,6):beam(o,(1.18,y,.98),(1.18,y,1.79),.012)
    register(o.name,6000,o,dims=[2.5,2.5,2.4])

def hand_props():
    o=Mesh('prop_natai_spool');spool(o);register(o.name,3000,o,dims=[.30,.166,.166])
    o=Mesh('prop_kite_ghuri')
    # First atlas cell diamond, UV coordinates reference complete embedded atlas.
    o.add([[0,0,.5],[-.24,0,.25],[0,0,0],[.24,0,.25],[0,-.018,.25]],[[0,1,4],[1,2,4],[2,3,4],[3,0,4]],'kite',[[.125,.008],[.008,.125],[.125,.242],[.242,.125],[.125,.125]])
    beam(o,(0,.003,0),(0,.003,.5),.002,'wood',4)
    tube(o,[(-.24,.003,.25),(0,.006,.29),(.24,.003,.25)],.002,'wood',4)
    o.add([[-.015,0,0],[.015,0,0],[.025,0,-.07],[0,0,-.11],[-.025,0,-.06]],[[0,1,2],[0,2,3],[0,3,4]],'magenta')
    register(o.name,300,o,height=.5)
    o=Mesh('prop_plastic_chair')
    box(o,(0,0,.43),(.45,.44,.035),'redplastic')
    for x in [-.19,.19]:
        for y in [-.17,.17]:beam(o,(x*1.15,y*1.15,0),(x,y,.43),.025,'redplastic',8)
    # One moulded curved back shell with narrow vertical ventilation slots.
    v=[];uv=[];f=[];nx=16;ny=12
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*.45;z=.45+j/ny*.40
            v.append([x,.17+(z-.45)*.15+.045*(1-(x/.225)**2),z]);uv.append([i/nx,j/ny])
    for j in range(ny):
        for i in range(nx):
            if 2<=j<=9 and i in [3,6,9,12]:continue
            a=j*(nx+1)+i;f.extend([[a,a+1,a+nx+2],[a,a+nx+2,a+nx+1]])
    o.add(v,f,'redplastic',uv)
    register(o.name,3000,o,height=.85)
    o=Mesh('prop_string_lights');pts=sagline(o,(-2.5,0,.48),(2.5,0,.48),.4,.006,n=41)
    for i in range(1,40,2):
        x,y,z=pts[i];beam(o,(x,y,z),(x,y,z-.045),.007,'blackplastic',6)
        ellipsoid(o,(x,y,z-.07),(.018,.018,.028),'amber',8,5)
    o.fit();lo,hi=o.bounds();register(o.name,3000,o,dims=[5,float(hi[1]-lo[1]),float(hi[2]-lo[2])])
    o=Mesh('prop_paper_lantern')
    profile=[(.035,0)]+[(.175*math.sin(t),.175-.175*math.cos(t)) for t in np.linspace(.22,math.pi-.22,12)]+[(.035,.35)]
    lathe(o,profile,'magenta',24)
    for t in np.linspace(.25,math.pi-.25,6):ring(o,(0,0,.175-.175*math.cos(t)),.175*math.sin(t),.0016,'wood',12)
    register(o.name,1500,o,height=.35)
    o=Mesh('prop_fanush')
    lathe(o,[(.16,0),(.27,.13),(.35,.5),(.32,.86),(.23,.98),(0,1)],'paper',24)
    ring(o,(0,0,0),.16,.004,'wood',20)
    for a in [0,math.pi/2]:beam(o,(-.16*math.cos(a),-.16*math.sin(a),.02),(.16*math.cos(a),.16*math.sin(a),.02),.002,'rust',5)
    box(o,(0,0,.025),(.045,.045,.015),'amber');register(o.name,1500,o,height=1)

def flower_pots():
    pots=[]
    for idx in range(3):
        o=Mesh(['marigold_terracotta','tulsi_plastic','marigold_clay'][idx]);r=.13;h=.23
        lathe(o,[(0,0),(.085,0),(.13,.2),(.14,.21),(.14,.23),(.124,.23),(.115,.20),(.075,.02),(0,.02)],'clay' if idx!=1 else 'redplastic',20)
        cyl(o,(0,0,.18),.115,.005,'soil',18)
        for k in range(7):
            a=k*TAU/7;end=np.array([.1*math.cos(a),.1*math.sin(a),.40+.10*(k%3)])
            beam(o,(0,0,.18),end,.004,'leaf',5)
            for j in range(3):
                p=end*np.array([.7,.7,.7])+np.array([0,0,.04*j]);a2=a+j*1.8
                leaf(o,p,p+np.array([.07*math.cos(a2),.07*math.sin(a2),.025]),.022,'leaf',2,.008)
            if idx!=1:
                ellipsoid(o,end,(.028,.028,.023),'flower',10,6,wobble=.15)
                for q in range(5):
                    a2=q*TAU/5;c=end+np.array([.02*math.cos(a2),.02*math.sin(a2),.008])
                    ellipsoid(o,c,(.012,.012,.012),'yellow',6,4)
        pots.append(o)
    register('prop_flower_pots',6000,pots)

def food_and_utilities():
    o=Mesh('prop_moa_plate');lathe(o,[(0,0),(.15,0),(.18,.012),(.18,.021),(.15,.012),(0,.012)],'steel',36)
    for i in range(8):
        a=i*2.4;r=.075*math.sqrt(i/7);c=np.array([r*math.cos(a),r*math.sin(a),.04])
        ellipsoid(o,c,(.031,.031,.029),'rice',12,7,wobble=.06)
        for j in range(4):
            aa=j*2.4;z=-.015+.04*j/3;rr=math.sqrt(max(0,.031**2-z*z));cc=c+[rr*math.cos(aa),rr*math.sin(aa),z]
            ellipsoid(o,cc,(.004,.002,.002),'cloth',6,4)
    for i in range(3):
        a=-1.1+i*.55;c=(.135*math.cos(a),.135*math.sin(a),.033)
        ellipsoid(o,c,(.022,.022,.022),'cloth',10,5,wobble=.045)
    register(o.name,3000,o)
    o=Mesh('prop_speaker');box(o,(0,0,1.35),(.42,.32,.62),'blackplastic')
    for z,r in [(1.22,.13),(1.52,.065)]:
        tmp=Mesh('driver');lathe(tmp,[(0,0),(r*.5,-.02),(r,0),(r,.02)],'blackplastic',24)
        for v,f,m,uv,_ in tmp.parts:o.add(np.stack([v[:,0],-v[:,2]-.17,v[:,1]+z],1),f,m,uv)
    beam(o,(0,0,.1),(0,0,1.05),.025,'rust')
    for a in np.linspace(0,TAU,4)[:-1]:beam(o,(0,0,.4),(.36*math.cos(a),.36*math.sin(a),0),.018,'rust')
    register(o.name,2000,o)
    o=Mesh('prop_wire_pole');lathe(o,[(.14,0),(.1,7.8)],'cement',12)
    for z in [6.6,7.2,7.7]:
        beam(o,(-.65,0,z),(.65,0,z),.035,'rust')
        for x in [-.55,-.3,.3,.55]:
            cyl(o,(x,0,z),.04,.12,'cloth',8)
            for zz in [z+.03,z+.08]:ring(o,(x,0,zz),.055,.008,'cloth',12)
    for i in range(15):
        z=6.4+i*.08;x=-.8+(i%5)*.4
        sagline(o,(-1.8,x,z),(1.8,-x,z+.1),.3+(i%4)*.16,.008,n=15)
    for i in range(4):
        pts=[(.28*math.cos(t),-.18,6.4+.5*math.sin(t)) for t in np.linspace(0,TAU,30)]
        pts=np.array(pts)+[i*.03,0,-i*.12];tube(o,pts,.009,'rust',5)
    register(o.name,8000,o,height=8)
    o=Mesh('prop_clothesline_roof')
    for x in [-1.5,1.5]:beam(o,(x,0,0),(x,0,2.2),.025,'rust')
    sagline(o,(-1.5,0,2.15),(1.5,0,2.15),.15,.004,n=25)
    for x0,w,h,m in [(-1.3,1.2,1.45,'magenta'),(.1,.5,.85,'cloth'),(.75,.45,.8,'green')]:
        v=[];uv=[];f=[];nx=12;ny=8
        for j in range(ny+1):
            for i in range(nx+1):
                x=x0+w*i/nx;top=2.15-.15*(1-(x/1.5)**2)
                v.append([x,.035*math.sin(i/nx*math.pi*8)+.06*(j/ny)**2,top-h*j/ny]);uv.append([i/nx,j/ny])
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;f.extend([[a,a+1,a+nx+2],[a,a+nx+2,a+nx+1]])
        o.add(v,f,m,uv)
        for x in [x0+.03,x0+w-.03]:box(o,(x,0,2.10),(.016,.025,.06),'wood')
    register(o.name,4000,o)

def facade_plane(o,w,depth,z0,h,upper=False):
    # Source facade has two floors. Sample a half-height band per model floor.
    top,bottom=(0,.5) if upper else (.5,1)
    o.add([[-w/2,-depth/2-.002,z0],[w/2,-depth/2-.002,z0],[w/2,-depth/2-.002,z0+h],[-w/2,-depth/2-.002,z0+h]],[[0,1,2],[0,2,3]],'facade',[[0,bottom],[1,bottom],[1,top],[0,top]])
def balcony(o,x,y,z,w,corner=False):
    box(o,(x,y-.38,z),(w,.8,.12),'cement')
    for xx in np.linspace(x-w/2,x+w/2,9):beam(o,(xx,y-.75,z),(xx,y-.75,z+.85),.016,'rust',5)
    for zz in [z+.08,z+.85]:beam(o,(x-w/2,y-.75,zz),(x+w/2,y-.75,zz),.022,'rust',6)
    for xx in [x-w/2,x+w/2]:beam(o,(xx,y, z+.85),(xx,y-.75,z+.85),.02,'rust',5)
def building(name,w,d,floors,budget,corner=False,newer=False,arches=False):
    o=Mesh(name);h=floors*2.8
    box(o,(0,0,h/2),(w,d,h),'plaster' if not newer else 'cement')
    for floor in range(floors):
        facade_plane(o,w,d,floor*2.8,2.8,upper=floor%2==1)
        if floor>0 and (floor==1 or corner):balcony(o,0,-d/2,floor*2.8,w*.66)
    if corner:
        # Balcony return along the right side, forming a true L at the front corner.
        z=2.8;box(o,(w/2-.38,-d/2+.6,z),(.76,1.2,.12),'cement')
        for yy in np.linspace(-d/2-.75,-d/2+1.2,11):beam(o,(w/2-.02,yy,z),(w/2-.02,yy,z+.85),.016,'rust',5)
        beam(o,(w/2-.02,-d/2-.75,z+.85),(w/2-.02,-d/2+1.2,z+.85),.02,'rust',6)
        beam(o,(w*.33,-d/2-.75,z+.85),(w/2-.02,-d/2-.75,z+.85),.02,'rust',6)
    for y in [-d/2+.075,d/2-.075]:box(o,(0,y,h+.45),(w,.15,.9),'turquoise')
    for x in [-w/2+.075,w/2-.075]:box(o,(x,0,h+.45),(.15,d-.3,.9),'turquoise')
    if newer:
        for x in [-w*.25,w*.25]:
            lathe(o,[(0,0),(.48,0),(.48,1.1),(.2,1.2),(0,1.2)],'blackplastic',16,(x,0,h))
            for zz in [.2,.5,.8]:ring(o,(x,0,h+zz),.48,.015,'blackplastic',16)
    if arches:
        for floor in range(floors):
            for x in [-w*.33,0,w*.33]:
                y=-d/2-.02;z=floor*2.8+.65
                box(o,(x,y,z+.48),(.9,.03,.96),'wood')
                pts=[(x+.53*math.cos(a),y-.035,z+.95+.53*math.sin(a)) for a in np.linspace(0,math.pi,13)]
                tube(o,pts,.055,'plaster',6)
                for xx in [x-.53,x+.53]:beam(o,(xx,y,z),(xx,y,z+.95),.055,'plaster',6)
    register(name,budget,o)
def mosque():
    o=Mesh('bld_mosque');box(o,(0,0,1.75),(7,6,3.5),'plaster')
    for x in [-3.4,3.4]:box(o,(x,0,3.7),(.2,6,.4),'turquoise')
    for y in [-2.9,2.9]:box(o,(0,y,3.7),(7,.2,.4),'turquoise')
    profile=[(1.65,3.5),(1.65,3.8),(1.55,4.15),(1.3,4.65),(.85,5.1),(.3,5.4),(0,5.55)]
    lathe(o,profile,'turquoise',32);beam(o,(0,0,5.5),(0,0,5.95),.025,'brass',8)
    for x in [-2.2,0,2.2]:
        box(o,(x,-3.01,1.15),(1.1,.04,2.3),'wood')
        pts=[(x+.62*math.cos(a),-3.05,2.3+.62*math.sin(a)) for a in np.linspace(0,math.pi,13)]
        tube(o,pts,.07,'turquoise',6)
    x=2.5;y=1.8
    lathe(o,[(.6,0),(.6,3.5),(.45,3.8),(.45,7.1),(.65,7.15),(.65,7.4),(.35,7.5),(.35,8.4),(.45,8.5),(.2,8.9),(0,9.1)],'plaster',20,(x,y,0))
    for z in [3.6,6.1,7.4,8.4]:ring(o,(x,y,z),.48,.045,'turquoise',20)
    register(o.name,6000,o)

def human(name,pose,shirt='shirt'):
    o=Mesh(name)
    # Anatomically proportioned static figure, Z-up, facing -Y.
    for x in [-.105,.105]:
        ellipsoid(o,(x,-.065,.065),(.065,.14,.06),'blackplastic',10,6)
        tube(o,[(x,0,.12),(x*.95,0,.48),(x,0,.86)],[.058,.068,.085],'cloth' if pose!='fire' else 'skin',10)
    if pose=='fire':lathe(o,[(.19,.55),(.21,.72),(.17,1.0)],'lungi',20)
    lathe(o,[(.15,.86),(.17,.99),(.20,1.23),(.23,1.34),(.14,1.40)],'skin' if pose=='fire' else shirt,20)
    cyl(o,(0,0,1.38),.065,.12,'skin',12)
    ellipsoid(o,(0,-.005,1.60),(.098,.087,.13),'skin',18,12)
    ellipsoid(o,(0,.008,1.67),(.101,.088,.065),'hair',16,8)
    for x in [-.099,.099]:ellipsoid(o,(x,0,1.60),(.018,.023,.035),'skin',8,5)
    ellipsoid(o,(0,-.091,1.60),(.021,.031,.036),'skinlight',10,6)
    for x in [-.038,.038]:
        ellipsoid(o,(x,-.084,1.63),(.017,.008,.008),'eye',8,4)
        beam(o,(x-.018,-.085,1.65),(x+.018,-.085,1.65),.004,'hair',5)
    ellipsoid(o,(0,-.087,1.548),(.025,.007,.008 if pose=='hold' else .019),'hair',8,5)
    if pose=='point':arms=[([-.22,0,1.33],[-.35,-.08,1.53],[-.4,-.18,1.77]),([.22,0,1.33],[.32,-.05,1.12],[.28,-.22,1.12])]
    elif pose=='cheer':arms=[([-.22,0,1.33],[-.34,-.05,1.55],[-.28,-.12,1.76]),([.22,0,1.33],[.34,-.05,1.55],[.28,-.12,1.76])]
    elif pose=='fire':arms=[([-.22,0,1.33],[-.33,-.08,1.38],[-.35,-.28,1.52]),([.22,0,1.33],[.3,.05,1.13],[.34,.08,.95])]
    else:arms=[([-.22,0,1.33],[-.31,-.10,1.15],[-.19,-.27,1.17]),([.22,0,1.33],[.31,-.1,1.15],[.19,-.27,1.17])]
    for shoulder,elbow,wrist in arms:
        tube(o,[shoulder,elbow],[.066,.048],'skin' if pose=='fire' else shirt,10)
        tube(o,[elbow,wrist],[.046,.029],'skin',10)
        ellipsoid(o,wrist,(.038,.026,.055),'skin',10,6)
    if pose=='hold':spool(o,(0,-.28,1.17),1)
    if pose=='point':beam(o,(-.4,-.18,1.77),(-.41,-.19,1.84),.009,'skin',6)
    if pose=='fire':
        beam(o,(-.35,-.28,1.47),(-.35,-.38,1.91),.012,'wood',8)
        ellipsoid(o,(-.35,-.38,1.92),(.026,.026,.038),'cloth',8,5)
        # Head tilted back around neck; face and hair are moved together.
        pivot=np.array([0,0,1.43]);angle=math.radians(-24)
        rot=np.array([[1,0,0],[0,math.cos(angle),-math.sin(angle)],[0,math.sin(angle),math.cos(angle)]])
        for p in o.parts:
            if p[0][:,2].min()>1.46 and p[0][:,0].min()>-.13 and p[0][:,0].max()<.13:p[0]=(p[0]-pivot)@rot.T+pivot
    return o

def build():
    import sys,rooftop_refinements
    rooftop_refinements.apply(sys.modules[__name__])
    import rooftop_surface_pass
    rooftop_surface_pass.apply(sys.modules[__name__])
    import rooftop_geometry_finish
    rooftop_geometry_finish.apply(sys.modules[__name__])
    make_guti();architecture_props();hand_props();flower_pots();food_and_utilities()
    building('bld_oldhaka_block_1',5,5.8,4,3000)
    building('bld_oldhaka_block_2',7,5.4,3,3000,corner=True)
    building('bld_oldhaka_block_3',6,5.6,5,3000,newer=True)
    building('bld_oldhaka_block_4',8,5.8,2,3500,arches=True)
    mosque()
    register('char_kite_flyers',12000,[human('flyer_natai','hold'),human('flyer_pointing','point','magenta'),human('flyer_cheering','cheer','green')])
    register('char_fire_breather',6000,human('char_fire_breather','fire'))
    report=[]
    for name,budget,objects in ASSETS:
        entry=b.export(objects,name,budget,folder=ROOT/'models',ao=False)
        report.append(entry);print(json.dumps(entry),flush=True)
    (ROOT/'production'/'rooftop_model_validation.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':build()
