"""Second art pass: static anatomy, cotton garments, botanical leaves and puffed rice.
Geometry remains procedural and is intended for middle-distance mobile rendering.
"""
import math
import numpy as np
from build_models import Mesh,ellipsoid,tube,lathe,box
TAU=math.tau
R=None
def linear(c):return [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
def loft(o,rings,m,n=16,folds=0):
    """Elliptical body sections (z, radius x, radius y, centre x, centre y)."""
    v=[];uv=[];f=[]
    for j,(z,rx,ry,cx,cy) in enumerate(rings):
        for i in range(n+1):
            a=TAU*i/n;wrinkle=1+folds*math.sin(a*7+j*.7)
            v.append([cx+rx*math.cos(a)*wrinkle,cy+ry*math.sin(a)*wrinkle,z]);uv.append([i/n,j/(len(rings)-1)])
    for j in range(len(rings)-1):
        for i in range(n):
            q=j*(n+1)+i;f.extend([[q,q+1,q+n+2],[q,q+n+2,q+n+1]])
    o.add(v,f,m,uv)
def limb(o,points,radii,m,n=10,fold=False):
    tube(o,points,radii,m,n)
    if fold:
        # A shallow geometry fold at the elbow/knee, not a full torus band.
        a=np.array(points[0]);z=np.array(points[-1]);d=z-a
        side=np.cross(d,[0,1,0]);side/=max(np.linalg.norm(side),1e-8)
        c=a+d*.55
        tube(o,[c-side*radii[len(radii)//2]*.8,c+[0,-.008,.004],c+side*radii[len(radii)//2]*.8],.003,m,4)
def hand(o,wrist,elbow,gesture):
    wrist=np.array(wrist);d=wrist-np.array(elbow);d/=np.linalg.norm(d)
    across=np.cross(d,[0,-1,0]);across/=max(np.linalg.norm(across),1e-6)
    normal=np.cross(across,d);palm=wrist+d*.025
    # Palm is flattened in its local frame; fingers have separate tapered joints.
    tmp=Mesh('palm');ellipsoid(tmp,(0,0,0),(.030,.013,.038),'skin',8,5)
    for v,f,m,uv,_ in tmp.parts:o.add(palm+v[:,0:1]*across+v[:,1:2]*normal+v[:,2:3]*d,f,m,uv)
    for i,ln in enumerate([.046,.056,.052,.041]):
        p=palm+across*(i-1.5)*.014+d*.028
        bend=0 if gesture=='point' and i==0 else (.8 if gesture in ['grip','point'] else .12)
        end=p+d*ln*(1-bend*.65)-normal*ln*bend
        mid=p+d*ln*.60-normal*ln*bend*.30
        tube(o,[p,mid,end],[.007,.006,.0048],'skin',5)
    p=palm-across*.025;z=p-across*.022+d*.025-normal*.011
    tube(o,[p,p-across*.018+d*.012,z],[.009,.007,.0055],'skin',5)
def head(o,pose):
    start=len(o.parts)
    loft(o,[(1.47,.030,.038,0,-.027),(1.49,.054,.053,0,-.02),(1.53,.074,.068,0,-.006),(1.58,.084,.075,0,0),(1.63,.082,.079,0,.006),(1.68,.077,.075,0,.014),(1.72,.055,.056,0,.018),(1.745,0,0,0,.018)],'skin',18)
    for x in [-.084,.084]:ellipsoid(o,(x,.01,1.598),(.014,.018,.029),'skin',8,5)
    # A shaped bridge, alar wings, and nose tip replace the former spherical nose.
    o.add([[-.013,-.068,1.65],[.013,-.068,1.65],[0,-.105,1.592],[-.022,-.080,1.582],[.022,-.080,1.582],[0,-.112,1.585]],[[0,1,2],[0,2,3],[1,4,2],[2,4,5],[2,5,3],[3,5,4]],'skin')
    for x in [-.030,.030]:
        ellipsoid(o,(x,-.068,1.625),(.015,.008,.006),'eye_white',8,4)
        ellipsoid(o,(x,-.0754,1.625),(.005,.0018,.0048),'iris',6,4)
        tube(o,[(x-.014,-.070,1.626),(x,-.077,1.632),(x+.014,-.070,1.626)],[.0025,.002,.0025],'skin',4)
        tube(o,[(x-.017,-.068,1.647),(x,-.074,1.65),(x+.017,-.068,1.646)],[.003,.004,.002],'hair',4)
    if pose in ['cheer','fire']:
        o.add([[-.022,-.071,1.555],[.022,-.071,1.555],[.017,-.072,1.537],[-.017,-.072,1.537]],[[0,1,2],[0,2,3]],'mouth')
        tube(o,[(-.021,-.074,1.555),(0,-.079,1.557),(.021,-.074,1.555)],.0028,'lip',4)
    else:
        tube(o,[(-.023,-.071,1.552),(0,-.080,1.550),(.023,-.071,1.552)],[.002,.003,.002],'lip',5)
    # Sculpted hair cap with a higher front hairline and lower side/back hairline.
    v=[];f=[];uv=[];n=20;rows=5
    for j in range(rows):
        for i in range(n+1):
            a=TAU*i/n;extent=1.85+.38*math.sin(a);p=(j/(rows-1))*extent
            v.append([.086*math.sin(p)*math.cos(a),.015+.083*math.sin(p)*math.sin(a),1.68+.072*math.cos(p)]);uv.append([i/n,j/(rows-1)])
    for j in range(rows-1):
        for i in range(n):
            q=j*(n+1)+i;f.extend([[q,q+n+1,q+1],[q+1,q+n+1,q+n+2]])
    o.add(v,f,'hair',uv)
    # Head rotation is explicit and restricted to head parts (no arm/torch heuristic).
    pitch={'hold':-.03,'point':-.18,'cheer':-.12,'fire':-.40}[pose]
    yaw={'hold':.10,'point':-.18,'cheer':.16,'fire':0}[pose]
    rotX=np.array([[1,0,0],[0,math.cos(pitch),-math.sin(pitch)],[0,math.sin(pitch),math.cos(pitch)]])
    rotZ=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
    pivot=np.array([0,0,1.46])
    for part in o.parts[start:]:part[0]=(part[0]-pivot)@(rotZ@rotX).T+pivot
def human(name,pose,shirt='shirt'):
    o=Mesh(name);fire=pose=='fire';shirt={'magenta':'shirt_magenta','green':'shirt_green'}.get(shirt,shirt)
    # Asymmetric stance, shaped calves/knees/thighs, low sandals with straps.
    for side in [-1,1]:
        x=side*.105;y=.035*side if pose!='hold' else 0
        ellipsoid(o,(x,y-.055,.022),(.055,.126,.020),'blackplastic',10,5)
        ellipsoid(o,(x,y-.048,.052),(.049,.104,.033),'skin',10,5)
        for z in [-.082,-.025]:
            tube(o,[(x-.045,y+z,.045),(x,y+z-.007,.083),(x+.045,y+z,.045)],.008,'rust',5)
        rings=[(.09,.037,.040,x,y),(.21,.047,.050,x,y+.012),(.37,.057,.055,x-side*.012,y+.015),(.48,.055,.062,x-side*.015,y-.015),(.60,.074,.078,x-side*.012,y),(.78,.081,.086,x,y),(.94,.088,.080,x,y)]
        # The lungi covers the upper legs; omit hidden thigh geometry so the
        # wider thigh sections cannot protrude through its tapered waistband.
        loft(o,rings[:5] if fire else rings,'skin' if fire else 'trousers',12,folds=0 if fire else .045)
    if fire:
        loft(o,[(.58,.205,.135,0,0),(.64,.205,.13,0,0),(.79,.19,.13,0,0),(.95,.16,.11,0,0)],'lungi',24,folds=.06)
        ellipsoid(o,(.085,-.108,.94),(.045,.028,.026),'lungi',8,5)
    # Width and depth are independent: chest and abdomen no longer look cylindrical.
    loft(o,[(.88,.155,.103,0,0),(1.0,.156,.105,0,0),(1.12,.174,.111,0,0),(1.27,.202,.119,0,.006),(1.36,.207,.101,0,.008),(1.40,.11,.075,0,0)],'skin' if fire else shirt,18,folds=0 if fire else .018)
    R.cyl(o,(0,0,1.38),.049,.105,'skin',12)
    if fire:
        # Subtle clavicles; avoid disconnected bodybuilder spheres.
        for side in [-1,1]:tube(o,[(0,-.081,1.365),(side*.09,-.096,1.35),(side*.17,-.076,1.34)],[.004,.005,.003],'skinlight',5)
    else:
        for side in [-1,1]:
            o.add([[0,-.083,1.40],[side*.075,-.080,1.40],[side*.052,-.111,1.345],[side*.012,-.115,1.36]],[[0,1,2],[0,2,3]],shirt)
        for z in [1.32,1.25,1.18]:ellipsoid(o,(0,-.12,z),(.004,.002,.004),'buttons',6,4)
        tube(o,[(.005,-.121,1.18),(.005,-.121,1.33)],.0015,shirt,4)
    if pose=='point':arms=[([-.205,0,1.34],[-.36,-.04,1.53],[-.43,-.12,1.73]),([.205,0,1.34],[.32,-.03,1.12],[.28,-.18,1.07])]
    elif pose=='cheer':arms=[([-.205,0,1.34],[-.36,-.02,1.51],[-.36,-.11,1.72]),([.205,0,1.34],[.37,-.03,1.48],[.43,-.08,1.64])]
    elif fire:arms=[([-.205,0,1.34],[-.34,-.06,1.38],[-.37,-.27,1.51]),([.205,0,1.34],[.32,.03,1.13],[.36,-.01,.96])]
    else:arms=[([-.205,0,1.34],[-.30,-.06,1.15],[-.17,-.27,1.17]),([.205,0,1.34],[.30,-.06,1.15],[.17,-.27,1.17])]
    for i,(s,e,w) in enumerate(arms):
        s,e,w=map(np.array,[s,e,w]);mid=s+(e-s)*.46
        ellipsoid(o,s,(.066,.066,.069),'skin' if fire else shirt,10,6)
        limb(o,[s,mid,e],[.064,.067,.043],'skin' if fire else shirt,10,not fire)
        limb(o,[e,e+(w-e)*.35,w],[.044,.046,.027],'skin',10)
        hand(o,w,e,'grip' if pose in ['hold','fire'] else ('point' if pose=='point' and i==0 else 'open'))
    head(o,pose)
    if pose=='hold':R.spool(o,(0,-.30,1.17),.92)
    if fire:
        R.beam(o,(-.37,-.27,1.47),(-.40,-.38,1.94),.012,'wood',8)
        ellipsoid(o,(-.40,-.38,1.95),(.025,.025,.038),'cloth',8,5)
    return o

def blade(o,start,end,width,m='leaf',serrated=False):
    a=np.array(start);z=np.array(end);d=z-a;side=np.cross(d,[0,0,1.]);side/=max(np.linalg.norm(side),1e-8)
    c=a+d*.53+np.array([0,0,.008]);v=[a,z,c]
    for t,w in [(.25,.6),(.5,1),(.76,.68)]:
        v.extend([a+d*t+side*width*w,a+d*t-side*width*w])
    f=[[0,3,2],[0,2,4],[3,5,2],[4,2,6],[5,7,2],[6,2,8],[7,1,2],[8,2,1]]
    if not serrated:v=[a,z,c-side*width,c+side*width];f=[[0,1,2],[0,3,1]]
    o.add(v,f,m)
def bloom(o,c,r=.031):
    c=np.array(c)
    # Three concentric rings of cupped, irregular marigold petals.
    for row in range(3):
        rr=r*(1-row*.26)
        for i in range(12):
            a=i*TAU/12+row*.23;u=np.array([math.cos(a),math.sin(a),0]);v=np.array([-u[1],u[0],0]);base=c+u*rr*.25+[0,0,row*.006]
            end=c+u*rr+[0,0,.006+row*.004+(.004 if i%2 else 0)]
            o.add([base,end-v*r*.15,end+[0,0,.008],end+v*r*.15],[[0,1,2],[0,2,3]],'flower' if (i+row)%3 else 'yellow')
    ellipsoid(o,c+[0,0,.017],(.009,.009,.009),'yellow',6,4)
def flower_pots():
    pots=[]
    for idx in range(3):
        o=Mesh(['marigold_terracotta','tulsi_plastic','marigold_clay'][idx])
        lathe(o,[(0,0),(.080,0),(.085,.025),(.13,.20),(.14,.21),(.14,.23),(.124,.23),(.115,.20),(.076,.025),(0,.025)],'clay' if idx!=1 else 'redplastic',20)
        R.cyl(o,(0,0,.19),.117,.006,'soil',16)
        if idx==1:
            stem=np.array([0,0,.2]);tip=np.array([.025,-.01,.64]);tube(o,[stem,[.008,0,.40],tip],[.004,.003,.0015],'leaf',5)
            for j in range(6):
                z=.26+j*.052;a=j*2.2
                for side in [-1,1]:
                    p=np.array([.01,0,z]);end=p+np.array([side*.115*math.cos(a),side*.115*math.sin(a),.03])
                    tube(o,[p,end],[.002,.001],'leaf',4)
                    for k in [-1,1]:
                        base=p*.35+end*.65;leafend=end+np.array([k*.04*math.sin(a),-k*.04*math.cos(a),.008])
                        blade(o,base,leafend,.024,'leaf2',True)
                    blade(o,end,end+np.array([side*.045*math.cos(a),side*.045*math.sin(a),.025]),.022,'leaf',True)
            for z in np.linspace(.60,.68,6):
                for a in [0,2.1,4.2]:ellipsoid(o,(.025+.009*math.cos(a),-.01+.009*math.sin(a),z),(.003,.003,.005),'tulsi_flower',6,4)
        else:
            for k in range(6):
                a=k*TAU/6+.25*idx;end=np.array([.10*math.cos(a),.10*math.sin(a),.40+.075*(k%3)])
                base=np.array([0,0,.19]);tube(o,[base,end*.55+[0,0,.08],end],[.004,.003,.002],'leaf',5)
                for j in range(3):
                    p=base+(end-base)*(.30+j*.18);aa=a+j*2.1;tip=p+[.085*math.cos(aa),.085*math.sin(aa),.025]
                    tube(o,[p,tip],.0014,'leaf',3)
                    for q in range(4):
                        c=p+(tip-p)*(.2+q*.20)
                        for side in [-1,1]:blade(o,c,c+[side*.031*math.sin(aa)+.012*math.cos(aa),-side*.031*math.cos(aa)+.012*math.sin(aa),.004],.006,'leaf2' if q%2 else 'leaf')
                bloom(o,end,.026+(k%2)*.006)
        pots.append(o)
    R.register('prop_flower_pots',6000,pots)

def grain(o,c,u,v,n,length,width,m):
    # Four exposed triangles per kernel; the underside is buried in the sweet.
    c=np.array(c);a=np.array([c+u*length,c-u*length,c+v*width,c-v*width,c+n*width,c-n*width])
    o.add(a,[[0,2,4],[0,4,3],[1,4,2],[1,3,4]],m)
def moa_plate():
    o=Mesh('prop_moa_plate');lathe(o,[(0,0),(.15,0),(.18,.012),(.18,.021),(.15,.012),(0,.012)],'steel',36)
    rng=np.random.default_rng(16016)
    for i in range(8):
        a=i*TAU/6
        c=np.array([.081*math.cos(a),.081*math.sin(a),.043]) if i<6 else np.array([0,0,.043+(i-6)*.049])
        ellipsoid(o,c,(.031,.031,.030),'jaggery',10,6,wobble=.12)
        for j in range(44):
            z=1-2*(j+.5)/44;aa=j*2.39996+i*.8;n=np.array([math.sqrt(1-z*z)*math.cos(aa),math.sqrt(1-z*z)*math.sin(aa),z]);u=np.cross(n,[0,0,1]);u/=np.linalg.norm(u);v=np.cross(n,u)
            ang=rng.uniform(0,TAU);u,v=u*math.cos(ang)+v*math.sin(ang),-u*math.sin(ang)+v*math.cos(ang)
            grain(o,c+n*.030,u,v,n,.009,.004,'rice' if j%4 else 'rice_light')
    for i in range(3):
        a=-1.2+i*.48;c=np.array([.137*math.cos(a),.137*math.sin(a),.034])
        ellipsoid(o,c,(.021,.021,.021),'coconut',10,5,wobble=.08)
        for j in range(16):
            aa=j*2.4;z=j/16;n=np.array([math.sqrt(1-z*z)*math.cos(aa),math.sqrt(1-z*z)*math.sin(aa),z]);q=c+n*.021
            o.add([q+[-.002,0,0],q+[.003,.001,.001],q+[0,.002,.002]],[[0,1,2]],'rice_light')
    return o
def apply(module):
    global R
    R=module
    for key,c in [('trousers',[.48,.43,.35]),('shirt',[.08,.22,.31]),('shirt_magenta',[.64,.08,.27]),('shirt_green',[.10,.40,.32]),('cloth',[.77,.72,.61])]:
        R.material(key,[1,1,1],'support_rooftop_cotton',.95);R.M[key]['color']=linear(c)
    R.material('lungi',[1,1,1],'support_rooftop_lungi',.95)
    for key,c in [('lip',[.30,.14,.10]),('mouth',[.075,.025,.02]),('eye_white',[.60,.56,.47]),('iris',[.07,.045,.025]),('buttons',[.22,.22,.19]),('leaf2',[.24,.40,.12]),('tulsi_flower',[.45,.26,.37]),('jaggery',[.54,.30,.10]),('rice_light',[.89,.78,.53]),('coconut',[.53,.31,.16])]:R.material(key,c,None,.85)
    original=R.food_and_utilities
    def food_and_utilities():
        start=len(R.ASSETS);original()
        for i in range(start,len(R.ASSETS)):
            if R.ASSETS[i][0]=='prop_moa_plate':
                o=moa_plate();o.fit();R.ASSETS[i]=('prop_moa_plate',3000,[o]);break
    R.human=human;R.flower_pots=flower_pots;R.food_and_utilities=food_and_utilities
