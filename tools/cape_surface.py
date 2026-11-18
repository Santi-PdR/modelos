#!/usr/bin/env python3
"""Material de la capa a partir de su referencia registrada.

Una carta por cara expuesta. Se proyectan muestras RGB sólo de la región
trazada del mismo material y sólo en superficies visibles en esa vista.
Los cantos, el revés y lo que la imagen no enseña tienen acabados mates
propios. No se proyecta el PNG entero ni se usan recortes alfa. El atlas
128² reserva byte por byte la máscara emisiva anterior y todos sus RGB.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

import cape_reference as R
import cape_shape as shape
import preview_cloth as P

BACKUP = P.ROOT / 'docs/respaldos/v1.59.0'
ATLAS_FILE = BACKUP / P.ARMOR_TEX.relative_to(P.ASSETS)
MASK_FILE = ATLAS_FILE.with_stem(ATLAS_FILE.stem + '_glowmask')
DENSITIES = {R.COLLAR: 3.4, R.CLOTH: 3.0, R.SHOULDER: 3.15, R.SEAM: 3.4}
CRACK_UV = {'uv': [98.1, 47.1], 'uv_size': [.8, .8]}

# Matices libres de la proyección, para los ángulos no observables.
MATERIAL = {
    'red': ((28,10,20), (85,25,37), (118,43,54)),
    'violet': ((18,11,27), (58,37,80), (85,49,100)),
    'reverse': ((19,12,27),(50,32,67),(79,50,93)),
    'seam': ((40,24,36), (91,57,68), (116,76,84)),
    'iron': ((19,17,24), (36,30,42), (65,48,63)),
    'lip': ((37,20,30), (74,48,62), (94,61,71)),
    'edge': ((17,10,19), (41,21,34), (62,31,42)),
}
SWATCHES = dict(red=(10,19), violet=(8,22), reverse=(8,42), seam=(16,6),
                lip=(12,5), iron=(8,14), edge=(6,13))


def spec(box):
    x,y,w,h = box
    return dict(uv=[x+.03125, y+.03125], uv_size=[w-.0625, h-.0625])


def label_for(name):
    if name.startswith('v17_ribbon_'):
        return R.CLOTH, 'red' if int(name.split('_')[2])%2==0 else 'violet'
    if name.startswith('v18_pad_'):
        return R.SHOULDER, 'iron'
    if name.startswith('v18_chain_'):
        return R.SEAM, 'seam'
    return R.COLLAR, 'red'


def swatch(name, w, h, phase=0):
    dark, body, light = np.array(MATERIAL[name], float)
    y,x = np.mgrid[0:h,0:w].astype(float)
    u = (x+.5)/w; v = (y+.5)/h
    if name in ('seam','iron','lip'):
        ridge = .18 + .09*np.sin(3.7*u + phase)
        weight = .52+.38*(v < ridge) - .41*(v > .76)
        if name=='iron':
            weight -= .30*((u>.31)&(u<.42)&(v>.20))
    else:
        ridge = .37 + .12*np.sin(v*5.8+.6*phase)+.08*np.cos(v*11.2-phase)
        weight = .72 - .70*np.abs(u-ridge) + .32*(np.abs(u-ridge) < .13)
        weight -= .27*(v>.75)*(u>.67)
        if name=='reverse':
            weight -= .18*(v>.84)*(np.abs(u-ridge)>.14)
            weight += .11*(v>.51)*(np.abs(u-ridge)<.18)
    points = np.clip(np.round(weight*9)/9,0,1.18)[...,None]
    return np.where(points<.65,dark+(body-dark)*(points/.65),
                    body+(light-body)*((points-.65)/.53))


def pack(lock, requests):
    """Colocación determinista, con un texel de guarda en cada cara."""
    occupied = lock.copy()
    slots = {}
    # Rectángulos mayores antes de que el espacio quede fragmentado.
    for key, width, height in sorted(requests, key=lambda i: (max(i[1:]), i[1]*i[2]), reverse=True):
        w,h = width+2,height+2
        integral = np.pad(occupied.astype(np.int16),((1,0),(1,0))).cumsum(0).cumsum(1)
        sums = integral[h:,w:] - integral[:-h,w:] - integral[h:,:-w] + integral[:-h,:-w]
        ys,xs = np.where(sums == 0)
        if not len(xs):
            return None
        # Rellenar en diagonal deja huecos menos largos junto a la
        # reserva emisiva que agotar primero todas las filas superiores.
        k = int(np.argmin(ys+xs))
        x,y = int(xs[k]), int(ys[k])
        occupied[y:y+h,x:x+w] = True
        slots[key] = (x+1,y+1,width,height)
    return slots


def face_record(b,c,ci,vertices,fn):
    pts = vertices[P.FACE_ORDER[fn]]
    proj = pts @ R.projector().T
    px = proj[:, :2] * (R.SCALE,-R.SCALE) + R.ORIGIN
    n = np.cross(proj[1]-proj[0], proj[2]-proj[0]); n /= max(1e-8,np.linalg.norm(n))
    light = np.array([-.35,.65,.68]); light /= np.linalg.norm(light)
    family, mat = label_for(b['name'])
    return dict(b=b,c=c,ci=ci,fn=fn,px=px,depth=proj[:,2],pts=pts,
                family=family,mat=mat,shade=.40+.60*abs(n@light))


def visible_faces(geometry):
    """Mapa de propietarios de píxel, con el portador como oclusor."""
    matrices=P.matrices(geometry)
    faces=[]
    for b in geometry['bones'][72:]:
        if b['name'].startswith(('v15_cloth_','v17_vein_')):
            continue
        for ci,c in enumerate(b.get('cubes',())):
            v=P.cube_points(c,matrices[b['name']])
            faces.extend(face_record(b,c,ci,v,fn) for fn in P.FACE_ORDER)
    backdrop=[]
    for o,s,_ in P.MANNEQUIN_BOXES:
        v=np.asarray(o)+P.CORNERS*s
        for ids in P.FACE_ORDER.values():
            coords = v[ids] @ R.projector().T
            backdrop.append(dict(px=coords[:,:2]*(R.SCALE,-R.SCALE)+R.ORIGIN, depth=coords[:,2]))
    x0,y0,x1,y1 = R.CROP
    owner = np.full((y1-y0,x1-x0),-1,np.int32)
    zbuf = np.full(owner.shape,-1e6)
    for index, f in [*((-2,f) for f in backdrop), *enumerate(faces)]:
        p, z = f['px'], f['depth']
        xlo = max(x0,math.floor(min(p[:,0]))); xhi = min(x1,math.ceil(max(p[:,0]))+1)
        ylo = max(y0,math.floor(min(p[:,1]))); yhi = min(y1,math.ceil(max(p[:,1]))+1)
        if xlo>=xhi or ylo>=yhi:
            continue
        matrix = np.stack((p[0]-p[1],p[2]-p[1]),axis=1)
        if abs(np.linalg.det(matrix))<1e-6:
            continue
        ny,nx = np.mgrid[ylo:yhi,xlo:xhi]
        u,v = np.linalg.solve(matrix, np.array((nx-p[1,0],ny-p[1,1])).reshape(2,-1)).reshape(2,*nx.shape)
        d = z[1]+u*(z[0]-z[1])+v*(z[2]-z[1]); rect=np.s_[ylo-y0:yhi-y0,xlo-x0:xhi-x0]
        inner=(u>=0)&(u<=1)&(v>=0)&(v<=1)&(d>zbuf[rect])
        owner[rect][inner] = index; zbuf[rect][inner] = d[inner]
    return faces, owner


def photograph(f, ix, owner, w, h):
    im,labels,pink = R.reference()
    name = f['b']['name']; code=f['family']; phase = int(name.rsplit('_',1)[1]) if name.rsplit('_',1)[1].isdigit() else f['ci']
    mat = 'lip' if code==R.SHOULDER and f['ci'] in (1,3) else f['mat']
    fallback=swatch(mat,w,h,phase).reshape((-1,3))
    p = f['px']; xu=p[0]-p[1]; yv=p[2]-p[1]
    x0,y0,_,_=R.CROP
    jj,ii=np.where(owner==ix)
    u,v=ii+x0,jj+y0
    pick=(labels[v,u]==code) | ((code==R.COLLAR)&(labels[v,u]==R.SEAM))
    if not pick.any():
        return np.uint8(np.round(fallback.reshape(h,w,3)))
    u,v=u[pick],v[pick]
    uv=np.linalg.solve(np.stack((xu,yv),axis=1),np.stack((u-p[1,0],v-p[1,1])))
    tx=np.clip(np.floor(.03125+uv[0]*(w-.0625)).astype(int),0,w-1)
    ty=np.clip(np.floor(.03125+uv[1]*(h-.0625)).astype(int),0,h-1)
    index=ty*w+tx
    c=im[v,u].astype(float)
    # Agrupar por huella del texel en esa cara. La mediana de zona evita
    # arrastrar trazos de rejilla o un pixel caliente hacia todo un gajo.
    # El render aplicará esta luz una vez. Compensamos aquí para no
    # incorporarla dos veces al bordó y al gris carbón.
    shade = f['shade']
    for j in np.unique(index):
        take=index==j
        q=c[take]
        color=np.median(q,axis=0)
        pnk=pink[v[take],u[take]]
        if code==R.CLOTH and .30 < pnk.mean() < .62:
            color=.78*color+.22*np.median(q[pnk],axis=0)
        strength=min(.995,.66+.11*len(q))
        fallback[j]=fallback[j]*(1-strength)+np.clip(color/shade,0,255)*strength
    return np.uint8(np.clip(np.round(fallback.reshape(h,w,3)),0,255))


def placed_cracks(geometry, faces, owner):
    bones={b['name']: b for b in geometry['bones']}
    x0,y0,_,_ = R.CROP
    gy,gx = np.indices(owner.shape)
    is_cloth_surface=np.array([f['family']==R.CLOTH and f['fn']=='south' for f in faces])
    valid=(owner>=0)&is_cloth_surface[owner]
    used=np.zeros_like(valid)
    for i,(u,v,dx,dy) in enumerate(R.MARKS):
        metric=(gx+x0-u)**2+(gy+y0-v)**2
        where=np.argmin(np.where(valid&~used,metric,np.inf))
        y,x=np.unravel_index(where,owner.shape)
        f=faces[int(owner[y,x])]
        c = f['c']; o=c['origin']; w,h,d=c['size']
        px=f['px']; mat=np.stack((px[0]-px[1],px[2]-px[1]),axis=1)
        a,b=np.linalg.solve(mat,np.array((x+x0,y+y0))-px[1])
        # El núcleo se corta antes del borde aunque el pixel rosa del
        # original atraviese una unión entre dos tramos.
        vw=min(dx/R.SCALE*.89,w*.38); vh=min(dy/R.SCALE*.72,h*.74)
        a=np.clip(a,.5*vw/w+.04,1-.5*vw/w-.04)
        b=np.clip(b,.5*vh/h+.05,1-.5*vh/h-.05)
        z=o[2]+d+c['inflate']
        sign=np.array([-1.,1.,1.])
        mid=sign*np.array([o[0]+(1-a)*w,o[1]+(1-b)*h,z])
        pivot=sign*np.asarray(c.get('pivot',[0.,0.,0.]))
        rotation=c.get('rotation',[0.,0.,0.])
        center=sign*(pivot + P.rotmat(rotation)[:3,:3] @ (mid-pivot))
        org=center - [vw/2,vh/2,.028]
        bone=bones[f'v17_vein_{i}']
        bone['parent']=f['b']['name']
        bone['pivot']=[round(float(j),4) for j in center]
        bone['rotation']=rotation
        bone['cubes']=[dict(origin=[round(float(j),4) for j in org],
                            size=[round(vw,4),round(vh,4),.056],inflate=.01,
                            uv={k:dict(CRACK_UV) for k in P.FACE_ORDER})]
        used |= (metric < 100)


def map_surface(geometry, *, paint=False):
    """Asigna el mismo layout en ambos builds (textura/GEO)."""
    glow=Image.open(MASK_FILE).convert('RGBA'); locked=np.asarray(glow)[...,3] > 0
    faces, owner = visible_faces(geometry)
    counts=np.bincount(owner[owner>=0], minlength=len(faces))
    # Una carta propia para el exterior. Añade el canto visible si es
    # suficiente para mostrar píxeles en la cámara calibrada.
    ids=[k for k,f in enumerate(faces) if (f['fn']=='south' and counts[k] > 3)
         or (counts[k]>57 and f['fn']!='north')]
    for scale in (1.0,.95,.90,.85,.82):
        req=[(name,w,h) for name,(w,h) in SWATCHES.items()]
        for k in ids:
            f=faces[k]; p=f['pts']; density=DENSITIES[f['family']]*scale
            w,h=(max(2, round(np.linalg.norm(p[1]-p[j])*density)) for j in (0,2))
            req.append((k,w,h))
        slots=pack(locked,req)
        if slots is not None:
            break
    assert slots is not None, 'el atlas de armadura no cabe, o se modificó la máscara'
    proof=dict(factor=scale, cards=len(ids), density={k: v*scale for k,v in DENSITIES.items()})
    for k,f in enumerate(faces):
        name=f['b']['name']; code=f['family']; fn=f['fn']
        mat=f['mat']
        if code==R.CLOTH:
            mat='reverse' if fn=='north' else ('edge' if fn in ('up','down') else mat)
        if code==R.SHOULDER and f['ci'] in (1,3): mat='lip'
        f['c']['uv'][fn]=spec(slots[k] if k in slots else slots[mat])
        if code == R.CLOTH and fn == 'north':
            # Una franja continua por altura del forro; no se repite el
            # dibujo completo en cada tramo de la espalda interior.
            col, seg = int(name.split('_')[2]), int(name.rsplit('seg',1)[1])+f['ci']
            start,end=shape.segment_bounds(col,seg) if seg<shape.SEGS else (shape.tip_t(col)-.027,shape.tip_t(col))
            x,y,w,h=slots[mat]
            f['c']['uv'][fn]=dict(uv=[x+.03125,round(y+.04+(h-1)*start,4)],
                                  uv_size=[w-.0625,round(max(.65,(h-1)*(end-start)),4)])
    placed_cracks(geometry,faces,owner)
    if not paint:
        return proof
    base = np.array(Image.open(ATLAS_FILE).convert('RGBA'))
    base[~locked] = (23,13,25,255)
    for key,(x,y,w,h) in slots.items():
        sample=(np.uint8(np.clip(np.round(swatch(key,w,h)),0,255)) if isinstance(key,str)
                else photograph(faces[key],key,owner,w,h))
        assert not locked[y-1:y+h+1,x-1:x+w+1].any(), key
        base[y-1:y+h+1,x-1:x+w+1,:3]=np.pad(sample,((1,1),(1,1),(0,0)),mode='edge')
    return Image.fromarray(base), glow, proof


def atlas():
    from armor_model_pipeline import build_base
    model = build_base()['minecraft:geometry'][0]
    image, glow, _ = map_surface(model,paint=True)
    return image, glow
