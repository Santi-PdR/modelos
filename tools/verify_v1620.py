#!/usr/bin/env python3
"""Compare v1.62 with the exact v1.61 backup and validate the worn model.

The reference trace and camera are unchanged. Fits are sampled on vanilla
head and torso boxes; this is not a test of all skins, hats or armor mods.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import json

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_material as C
import cape_reference as R
import cape_surface as S
import preview_cloth as P
from verify_v1590 import check_editor, check_tracks
from verify_v1600 import crop, iou, registered_metrics
from verify_v1610 import fit_check, visor_fit

BACKUP = P.ROOT/'docs/respaldos/v1.61.0'
GEO_BASE = BACKUP/P.ARMOR_GEO.relative_to(P.ASSETS)
TEX_BASE = BACKUP/P.ARMOR_TEX.relative_to(P.ASSETS)
GLOW_BASE = TEX_BASE.with_stem(TEX_BASE.stem+'_glowmask')
GLOW = P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem+'_glowmask')
CLIPS = BACKUP/A.ANIM.relative_to(P.ASSETS)
OLD_BB = BACKUP/'CAPA_v1.61.0.bbmodel'


def bright(rgb, *, cores=False):
    rr,gg,bb = np.moveaxis(np.asarray(rgb).astype(np.int16), -1, 0)
    if cores:
        return (rr>=148)&(rr-gg>=72)&(bb-gg>=42)&(bb>=70)
    return (rr>=121)&(rr-gg>=57)&(bb-gg>=27)&(bb>=70)


def views(geo, atlas, **overrides):
    size,frame,window = R.render_frame()
    return P.render(geo,atlas,P.effective_hidden(geo),yaw=R.YAW,pitch=R.PITCH,
                    frame=frame,size=size,mannequin=True,**overrides).crop(window)


def emission_projection(geo, atlas, emission):
    # Only RGBA coverage is relevant here, not how bright a state is.
    with Image.open(emission) if not isinstance(emission, Image.Image) else nullcontext(emission) as image:
        solid = Image.new('RGBA',image.size,(255,255,255,0))
        solid.putalpha(image.convert('RGBA').getchannel('A'))
    return np.asarray(views(geo, atlas, ambient=0, emission=solid, tint=(1,1,1)))[...,0] > 96


def similarity(geo, atlas, emission):
    old = P.load(GEO_BASE)
    (base,new),p = registered_metrics(old,geo,atlas,baseline_atlas=TEX_BASE)
    for key,label in (('all','Silueta'),('upper','Zona alta'),('lower','Jirones'),('seam','Costura en U')):
        print(f'{label}: {base[key]:.2%} → {new[key]:.2%}')
    assert new['all'] >= .948 and new['all'] > base['all']+.011, new['all']
    assert new['seam'] > .910 and new['upper'] > .935 and new['lower'] > .948
    print(f"RGB común: {base['mae']:.2f} → {new['mae']:.2f}/255 (menor es mejor)")
    assert new['mae'] < 4.60 and new['mae'] < .68*base['mae'], new['mae']
    assert abs(new['pink']-p) < .011
    source, labels, rose = (crop(v) for v in R.reference())
    common = (labels>0) & base['match'] & new['match']
    aim = rose & common
    a,b = (iou(bright(view)&common,aim) for view in (views(old,TEX_BASE), views(geo,atlas)))
    print(f'Rosa visible: IoU {a:.2%} → {b:.2%}, no sólo área total')
    assert b > a+.08 and b >= .57, (a,b)
    cores = bright(source, cores=True) & rose & common
    projected = emission_projection(geo,atlas,emission)
    old_live = emission_projection(old,TEX_BASE,GLOW_BASE)
    fit = iou(projected & common, cores)
    print(f'Núcleos emisivos en la referencia: IoU {iou(old_live&common,cores):.2%} → {fit:.2%}')
    assert fit > .50 and np.count_nonzero(projected & cores) / projected.sum() > .68, fit

    faces,owner = S.visible_faces(geo)
    family = np.where(owner>=0,np.array([f['family'] for f in faces])[owner],0)
    for label,threshold in ((R.COLLAR,.88),(R.SHOULDER,.765)):
        assert iou(family==label,labels==label) > threshold, label
    # This known opening is through two plies. Deep shadows elsewhere can
    # remain cloth and must not become transparent to flatter the score.
    x,y,_,_=R.CROP
    window = np.s_[404-y:421-y,495-x:512-x]
    opening = (labels[window]==0)&(owner[window]<0)  # see background *or* wearer through the cloth
    assert opening.sum() >= 100
    bg=(2,211,224)
    sizes=[np.count_nonzero((np.asarray(P.render(geo, atlas, P.effective_hidden(geo),
            yaw=yaw, pitch=0, size=320, frame=(0,15,9), bg=bg))!=bg).any(2)) for yaw in (0,90,180)]
    assert .12 < sizes[1]/sizes[0] < .55 and .77 < sizes[2]/sizes[0] < 1.30, sizes


def protection(geo, atlas, glow, runtime, candidate):
    assert hashlib.sha256(R.SOURCE.read_bytes()).hexdigest() == R.SOURCE_SHA256
    allowed = {GEO_BASE,TEX_BASE,GLOW_BASE,OLD_BB}
    for line in (BACKUP/'SHA256SUMS.txt').read_text().splitlines():
        digest,name = line.split('  ',1)
        f = BACKUP/name
        assert hashlib.sha256(f.read_bytes()).hexdigest() == digest, f
        if f not in allowed and not candidate:
            assert f.read_bytes() == (P.ASSETS/name).read_bytes(), name
    assert runtime == json.loads(CLIPS.read_text())
    prev,cur = P.load(GEO_BASE),geo
    assert P.effective_hidden(prev) == P.effective_hidden(cur)
    assert [b['name'] for b in prev['bones']] == [b['name'] for b in cur['bones']]
    assert next(b for b in prev['bones'] if b['name']==G.FIT_BONE) == next(b for b in cur['bones'] if b['name']==G.FIT_BONE)
    for x,y in zip(prev['bones'],cur['bones'],strict=True):
        if x['name'].startswith('v17_vein_'):
            assert not y['cubes'], 'vuelve la pieza de neón sobre el paño'
        else:
            assert x.get('parent') == y.get('parent'), y['name']
    base,light = np.asarray(atlas),np.asarray(glow)
    assert base.shape == light.shape == (C.SIZE,C.SIZE,4) and np.all(base[...,3] == 255)
    # A second pass is not permission to remove opacity from the first.
    active = light[...,3]>0
    linked = np.zeros_like(active)
    for i,b in enumerate(geo['bones']):
        for c in b.get('cubes',()):
            for k,uv in c['uv'].items():
                u,v=uv['uv'];w,h=uv['uv_size']
                x0,x1 = sorted((u,u+w)); y0,y1 = sorted((v,v+h))
                if i >= 72:
                    assert min(u,v)>=0 and min(w,h)>0 and max(x1,y1)<=C.SIZE, (b['name'],uv)
                else:
                    assert max(x1,y1)<=128, (b['name'],uv)
                rect=np.s_[max(0,int(y0)):int(y1)+1,max(0,int(x0)):int(x1)+1]
                if b['name'].startswith('v17_ribbon_'):
                    linked[rect] = True
                else:
                    assert not active[rect].any(), (b['name'],k)
    assert not np.any(active & ~linked)
    assert active.sum() > 450
    print(f'Atlas {C.SIZE}² opaco, {active.sum()} texels de luz sólo en el paño; icono, plegado y clips conservados')


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--candidate',action='store_true')
    cli.add_argument('--quick',action='store_true')
    cli.add_argument('--look-only',action='store_true')
    cli.add_argument('--fit-only',action='store_true')
    a=cli.parse_args()
    geo=G.build_base()['minecraft:geometry'][0]
    atlas,glow,layout=C.map_material(geo,paint=True)
    runtime=A.build(geo)
    if a.fit_only:
        fit_check(geo,runtime['animations'],a.quick,pads=True)
        return
    assert layout['density'][R.CLOTH]>=5.0 and layout['cards']>=210, layout
    print(f"{layout['cards']} cartas · {layout['density'][R.CLOTH]:.2f} texels/u de paño")
    similarity(geo,atlas,glow)
    if a.look_only:
        return
    protection(geo,atlas,glow,runtime,a.candidate)
    if not a.candidate:
        assert P.load(P.ARMOR_GEO) == geo and json.loads(A.ANIM.read_text()) == runtime
        for path,expected in ((P.ARMOR_TEX,atlas),(GLOW,glow)):
            with Image.open(path) as current:
                assert np.array_equal(np.asarray(current.convert('RGBA')),np.asarray(expected)), path
    bb=B.build(geo,atlas,runtime) if a.candidate else json.loads(B.DOC.read_text())
    retired={f'v17_vein_{i}_0' for i in range(G.CRACKS)}
    assert not (retired & {e['name'] for e in bb['elements']})
    check_editor(json.loads(OLD_BB.read_text()),bb,geo,atlas,runtime,retired_elements=retired)
    check_tracks(runtime,json.loads(CLIPS.read_text()),bb)
    fit_check(geo,runtime['animations'],a.quick,pads=True)
    if not a.candidate:
        visor_fit(geo,runtime)


if __name__=='__main__':
    main()
