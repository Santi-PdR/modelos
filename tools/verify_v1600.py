#!/usr/bin/env python3
"""Fidelidad registrada, profundidad, transiciones y entrega v1.60.

El PNG original se usa sólo para la vista conocida. No se considera
una reconstrucción pixel a pixel del pelo, portador o partes ocultas.
Las pruebas no sustituyen la comprobación F5 en un cliente Forge.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
from hashlib import sha256

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_motion as M
import cape_reference as R
import cape_surface as S
import cape_tracks as T
import preview_cloth as P
from verify_v1590 import check_editor, check_tracks, check_visor

BASE_GEO = S.BACKUP / P.ARMOR_GEO.relative_to(P.ASSETS)


def crop(a):
    x,y,x1,y1 = R.CROP
    return a[y:y1,x:x1]


def iou(m1,m2):
    return np.count_nonzero(m1&m2) / np.count_nonzero(m1|m2)


def registered_metrics(old, new, atlas):
    src, labels, pink = (crop(x) for x in R.reference())
    truth = labels > 0
    size,frame,box = R.render_frame()
    coverage = []
    diff = []
    for geo,img in ((old,S.ATLAS_FILE),(new,atlas)):
        faces, owner = S.visible_faces(geo)
        mask = owner >= 0
        family = np.where(mask, np.array([f['family'] for f in faces])[owner], 0)
        render = P.render(geo,img,P.effective_hidden(geo),yaw=R.YAW,pitch=R.PITCH,
                          size=size,frame=frame,mannequin=True).crop(box)
        got=np.asarray(render).astype(np.int16)
        rr,gg,bb=np.moveaxis(got,-1,0)
        bright = (rr >= 121) & (rr-gg >= 57) & (bb-gg >= 27) & (bb>=70)
        common = truth & mask
        y = R.CROP[1]
        band=slice(222-y,500-y)
        collar=slice(136-y,221-y)
        coverage.append(dict(all=iou(mask,truth), lower=iou(mask[band],truth[band]),
                        upper=iou(mask[collar],truth[collar]), seam=iou(family==R.SEAM,labels==R.SEAM),
                        pink=bright[common].mean(), match=mask))
        diff.append(np.abs(got-src).mean(2))
    both=truth & coverage[0]['match'] & coverage[1]['match']
    for row, err in zip(coverage,diff):
        row['mae'] = err[both].mean()
    return coverage, pink[truth & coverage[-1]['match']].mean()


def check_similarity(old, geo, atlas):
    old_score,new_score = registered_metrics(old,geo,atlas)[0]
    for name,title in (('all','Silueta global'),('lower','Jirones'),
                       ('upper','Región del cuello y hombreras'),('seam','Costura')):
        p,q = old_score[name],new_score[name]
        print(f'{title} (IoU) {p:.1%} → {q:.1%}')
    assert new_score['all'] > .905 and new_score['all'] > old_score['all']+.28
    assert new_score['lower'] > .91 and new_score['upper'] > .875 and new_score['seam'] > .70
    assert .032 < new_score['pink'] < .072, 'energía visible demasiado extensa o apagada'
    print(f"Error RGB medio en píxeles comunes: {old_score['mae']:.2f} → {new_score['mae']:.2f} / 255")
    assert new_score['mae'] < 9.5 and new_score['mae'] < .32*old_score['mae']
    # Las escalas reales siguen iguales entre las vistas: hay grosor y
    # acabado propio al girar; no admite una lámina con una foto.
    sizes=[]
    for yaw in (0,90,180):
        bg=(5,201,247)
        im=np.asarray(P.render(geo,atlas,P.effective_hidden(geo),yaw=yaw,pitch=0,bg=bg,
                               size=320,frame=(0,15,9)))
        sizes.append(np.count_nonzero((im!=bg).any(2)))
    assert .11 < sizes[1]/sizes[0] < .54 and .72 < sizes[2]/sizes[0] < 1.28, sizes


def sat(a,b):
    """SAT de los paralelepípedos (incluye escala no uniforme/inflate).

    Positivo = al menos un eje separa; negativo = todos solapan. Se usan
    normales reales, no ejes de arista como si todas las cajas fueran ortogonales.
    """
    e,f = (x[:,[1,3,4]]-x[:,0,None] for x in (a,b))
    ea,fa = (np.cross(x,np.roll(x,1,axis=1)) for x in (e,f))
    ax=np.concatenate((ea,fa,np.cross(e[:,:,None],f[:,None,:]).reshape(len(e),9,3)),axis=1)
    d=np.linalg.norm(ax,axis=2,keepdims=True)
    ax=ax/np.where(d>1e-8,d,1)
    pa,pb=(x @ ax.transpose(0,2,1) for x in (a,b))
    return np.where(d[:,:,0]>1e-8, np.maximum(pa.min(1)-pb.max(1),pb.min(1)-pa.max(1)), -100).max(1)


def response_variants():
    j=(P.ROOT/'src/main/java/com/capatest/client/CapeResponse.java').read_text()
    v={n:float(t) for n,t in re.findall(r'double MAX_(\w+) = (\d+\.\d+);',j)}
    assert set(v)=={'BACK','IN','YAW','ROLL'}
    def response(x,y,z):
        def sample(name):
            m=M.RIBBON.fullmatch(name)
            if not m or int(m[2])>4:
                return (0.,0.,0.)  # collar, costura, cortes quedan fijos
            r=.35+.65*int(m[2])/6
            # Java suma a las rotaciones ya reflejadas por GeckoLib.
            return (-x*r,-y*r,z*r)
        return sample
    return [response(*xyz) for xyz in itertools.product((-v['BACK'],v['IN']),
                      (-v['YAW'],v['YAW']),(-v['ROLL'],v['ROLL']))]


def interpolate(source, target, phase):
    bones=[]
    for a,b in zip(source['bones'],target['bones'],strict=True):
        assert a['name']==b['name']
        changes={}
        for k in ('offset','rotation','scale'):
            changes[k]=[x+(y-x)*phase for x,y in zip(a[k],b[k])]
        bones.append(dict(a,**changes))
    return dict(source,bones=bones)


def check_fit(geo, clips):
    hidden=P.effective_hidden(geo)
    data=[(b['name'],ci,P.cube_points(c,np.eye(4))) for b in geo['bones']
          if b['name'] not in hidden for ci,c in enumerate(b.get('cubes',()))]
    names=[n for n,_,_ in data]; vec=np.array([v for _,_,v in data]); idx={}
    for i,(name,ci,_) in enumerate(data):
        m=M.RIBBON.fullmatch(name)
        if m:
            k,s=map(int,m.groups()); idx[k,s+ci]=i
    left,right=np.array([(idx[k,s],idx[k,s+1]) for k in range(12) for s in range(6)]).T
    # Varias orientaciones de la cabeza respecto al torso quieto. Los
    # límites no representan todas las poses que puede imponer otro mod.
    h=P.CORNERS*8+[-4,0,-4]
    angles=list(itertools.product(np.linspace(-75,75,21),(-20,-16,-13,0,13,16,20)))
    heads=np.array([h@(P.R('y',yaw)@P.R('x',pitch))[:3,:3].T+[0,24,0]
                    for yaw,pitch in angles])
    head_lo,head_hi=heads.min(1),heads.max(1)
    seam_idx=np.array([i for i,n in enumerate(names) if n.startswith('v18_chain_')])
    cowl_idx=np.array([i for i,n in enumerate(names) if n.startswith(('v17_cowl_', 'v19_cuellito_'))])
    si, sj = np.repeat(seam_idx,len(cowl_idx)), np.tile(cowl_idx,len(seam_idx))
    bone_table={b['name']:b for b in geo['bones']}
    cuts=[(i, [j for j,n in enumerate(names) if n==bone_table[name]['parent']])
          for i,name in enumerate(names) if name.startswith('v17_vein_')]
    ci, par = np.array([(i,j) for i,ids in cuts for j in ids]).T
    group_starts=np.cumsum([0]+[len(ids) for _,ids in cuts[:-1]])
    joined=(np.inf,)
    seam_contact=(np.inf,)
    count=0; torso=(np.inf,); head=(.25,); contacts=(np.inf,)
    def measure(g,desc):
        nonlocal count,torso,head,contacts,joined,seam_contact
        m=P.matrices(g); mats=np.array([m[n] for n in names])
        v=vec @ mats[:,:3,:3].transpose(0,2,1)+mats[:,None,:3,3]
        lo,hi=v.min(1),v.max(1)
        i=lo[:,2].argmin(); torso=min(torso,(lo[i,2],names[i],desc))
        # AABB primero; si los límites están a más de .25 u, no hay
        # contacto posible. SAT exacto sólo para las cajas próximas.
        broad=np.maximum(lo[:,None]-head_hi, head_lo-hi[:,None]).max(2)
        model_i, head_i = np.where(broad <= .25)
        if model_i.size:
            s=sat(v[model_i],heads[head_i]); i=s.argmin()
            if s[i]<head[0]:
                head=(s[i],names[model_i[i]],data[model_i[i]][1],angles[head_i[i]],desc)
        link=-sat(v[si],v[sj]).reshape(len(seam_idx),len(cowl_idx)).min(1)
        i=int(link.argmin())
        seam_contact=min(seam_contact,(float(link[i]),names[seam_idx[i]],desc))
        s=sat(v[left],v[right]); i=s.argmax()
        contacts=min(contacts,(-s[i],names[left[i]],names[right[i]],desc))
        cut_overlap=-np.minimum.reduceat(sat(v[ci],v[par]),group_starts)
        ii=int(cut_overlap.argmin())
        joined=min(joined,(cut_overlap[ii],names[cuts[ii][0]],desc))
        count+=1
    variants=response_variants()
    measure(geo,'reposo del rig')
    sources={}
    for name,clip in clips.items():
        pre=T.prepare_clip(clip)
        length=clip['animation_length']
        sources[name]=[P.pose_at(geo,pre,length*p) for p in (0,.33,.67)]
        for i,t in enumerate(np.linspace(0,length,49)):
            measure(P.pose_at(geo,pre,t),f'{name}:{t:.3f}')
            if i%8==0:
                for j,r in enumerate(variants):
                    measure(P.pose_at(geo,pre,t,r),f'{name}:{t:.3f}/respuesta {j}')
    before=count
    for (a,pa),(b,pb) in itertools.permutations(sources.items(),2):
        for i,p in enumerate(pa):
            for f in (.25,.5,.75):
                measure(interpolate(p,pb[0],f),f'{a}[{i}] → {b}, {f}')
    print(f'{before} poses + {count-before} mezclas de clips: Z mínimo {torso[0]:.3f} u; '
          f'cabeza ±75°/±20° {head[0]:+.3f} u; solape mínimo {contacts[0]:+.3f} u')
    assert torso[0]>2.25 and head[0]>0, (torso,head)
    assert contacts[0]>.02, contacts
    assert joined[0]>0 and seam_contact[0]>0, (joined,seam_contact)
    print(f"Diez cortes adheridos ({joined[0]:.3f} u); costura ligada al cuello ({seam_contact[0]:.3f} u)")


def check_protection(geo, atlas, glow, *, candidate):
    assert sha256(R.SOURCE.read_bytes()).hexdigest()==R.SOURCE_SHA256
    for row in (S.BACKUP/'SHA256SUMS.txt').read_text().splitlines():
        h,name=row.split('  ',1)
        p=S.BACKUP/name
        assert sha256(p.read_bytes()).hexdigest()==h, name
        stable = name.startswith(('geo/','textures/','animations/')) and p not in (BASE_GEO,S.ATLAS_FILE,A.BASE_ANIM)
        if stable and not candidate:
            assert (P.ASSETS/name).read_bytes()==p.read_bytes(), name
    a,old=np.asarray(atlas),np.asarray(Image.open(S.ATLAS_FILE).convert('RGBA'))
    m=np.asarray(glow)[...,3]>0
    assert m.sum()==3380 and np.all(a[...,3]==255) and np.array_equal(a[m],old[m])
    assert set(P.effective_hidden(geo))==P.effective_hidden(P.load(BASE_GEO))
    for b in geo['bones'][72:]:
        if b['name'].startswith('v15_cloth_'):
            continue
        for c in b.get('cubes',()):
            for f,s in c['uv'].items():
                u,v=s['uv']; w,h=s['uv_size']
                assert min(u,v)>=0 and u+w<=128 and v+h<=128
                em=m[int(v):int(v+h-1e-6)+1,int(u):int(u+w-1e-6)+1]
                if b['name'].startswith('v17_vein_'):
                    assert em.all() and b['parent'].startswith('v17_ribbon_')
                else:
                    assert not em.any(), (b['name'], f, s)
    print('Atlas opaco, tela sin brillo total, diez cortes emisivos; 3380 RGB, ambos glowmasks, icono y plegado protegidos')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',action='store_true',help='mide en memoria antes del rebuild')
    ap.add_argument('--fit-only',action='store_true',help='itera sólo holgura/continuidad antes de exportar')
    opt=ap.parse_args()
    geo=G.build_base()['minecraft:geometry'][0]
    atlas,glow,layout=S.map_surface(geo,paint=True)
    runtime=A.build(geo)
    if opt.fit_only:
        check_fit(geo,runtime['animations']); return
    oldgeo=P.load(BASE_GEO)
    olds=json.loads(A.BASE_ANIM.read_text())
    oldbb=json.loads((S.BACKUP/'CAPA_v1.59.0.bbmodel').read_text())
    assert {b['name'] for b in geo['bones']}=={b['name'] for b in oldgeo['bones']}
    bdata=B.build(geo,atlas,runtime) if opt.candidate else json.loads(B.DOC.read_text())
    if not opt.candidate:
        assert P.load(P.ARMOR_GEO)==geo and json.loads(A.ANIM.read_text())==runtime
        assert np.array_equal(np.asarray(atlas),np.asarray(Image.open(P.ARMOR_TEX).convert('RGBA')))
    check_protection(geo,atlas,glow,candidate=opt.candidate)
    print(f"{layout['cards']} cartas UV únicas; {layout['density'][R.CLOTH]:.2f} texels/u en los gajos")
    check_similarity(oldgeo,geo,atlas)
    check_editor(oldbb,bdata,geo,atlas,runtime)
    check_tracks(runtime,olds,bdata)
    check_fit(geo,runtime['animations'])
    if not opt.candidate:
        check_visor(geo,runtime)


if __name__=='__main__':
    main()
