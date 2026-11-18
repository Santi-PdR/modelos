#!/usr/bin/env python3
"""Compare v1.62 with the exact v1.61 backup and validate the worn model.

The reference trace and camera are unchanged. Fits are sampled on vanilla
head and torso boxes; this is not a test of all skins, hats or armor mods.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import nullcontext
import hashlib
from io import BytesIO
import json
import re
import subprocess

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
    assert new['all'] >= .952 and new['all'] > base['all']+.011, new['all']
    assert new['seam'] > .924 and new['upper'] > .945 and new['lower'] > .952
    print(f"RGB común: {base['mae']:.2f} → {new['mae']:.2f}/255 (menor es mejor)")
    assert new['mae'] < 4.10 and new['mae'] < .60*base['mae'], new['mae']
    assert abs(new['pink']-p) < .011
    source, labels, rose = (crop(v) for v in R.reference())
    common = (labels>0) & base['match'] & new['match']
    aim = rose & common
    a,b = (iou(bright(view)&common,aim) for view in (views(old,TEX_BASE), views(geo,atlas)))
    print(f'Rosa visible: IoU {a:.2%} → {b:.2%}, no sólo área total')
    assert b > a+.15 and b >= .73, (a,b)
    cores = bright(source, cores=True) & rose & common
    projected = emission_projection(geo,atlas,emission)
    old_live = emission_projection(old,TEX_BASE,GLOW_BASE)
    fit = iou(projected & common, cores)
    print(f'Núcleos emisivos en la referencia: IoU {iou(old_live&common,cores):.2%} → {fit:.2%}')
    assert fit > .74 and np.count_nonzero(projected & cores) / projected.sum() > .68, fit

    faces,owner = S.visible_faces(geo)
    family = np.where(owner>=0,np.array([f['family'] for f in faces])[owner],0)
    for label,threshold in ((R.COLLAR,.92),(R.SHOULDER,.785)):
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


def protection(geo, atlas, glow, runtime, candidate, *, backup=BACKUP, changed=()):
    assert hashlib.sha256(R.SOURCE.read_bytes()).hexdigest() == R.SOURCE_SHA256
    allowed = {GEO_BASE.relative_to(BACKUP).as_posix(), TEX_BASE.relative_to(BACKUP).as_posix(),
               GLOW_BASE.relative_to(BACKUP).as_posix(), *changed}
    for line in (backup/'SHA256SUMS.txt').read_text().splitlines():
        digest,name = line.split('  ',1)
        f = backup/name
        assert hashlib.sha256(f.read_bytes()).hexdigest() == digest, f
        if name not in allowed and f.suffix != '.bbmodel' and not candidate:
            assert f.read_bytes() == (P.ASSETS/name).read_bytes(), name
    assert runtime == json.loads((backup/CLIPS.relative_to(BACKUP)).read_text())
    prev,cur = P.load(backup/GEO_BASE.relative_to(BACKUP)),geo
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
    assert active.sum() > 650
    print(f'Atlas {C.SIZE}² opaco, {active.sum()} texels de luz sólo en el paño; icono, plegado y clips conservados')


def visor_material(geo, atlas, glow):
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    def embedded(key):
        return json.loads(re.search(rf'^const {key} = (.+);$',html,re.M)[1])
    ref = json.loads(json.dumps(R.viewer_camera()))
    assert embedded('INLINE_REFERENCE') == ref
    with Image.open(R.SOURCE) as actual:
        original = np.asarray(actual.convert('RGB').crop(R.CROP))
    for name,expected in (('reference-crop.png', original),
                          ('armor.png',np.asarray(atlas)),('armor_glowmask.png',np.asarray(glow))):
        data = embedded('INLINE_IMAGES')[name].split(',',1)[1]
        with Image.open(BytesIO(base64.b64decode(data))) as packed:
            assert np.array_equal(np.asarray(packed),expected), name
    tests = [dict(yaw=R.YAW,pitch=R.PITCH,ambient=.24,tint=t) for t in (None,(.89,.60,.77))]
    tests.append(dict(yaw=180.,pitch=8.,ambient=.24,tint=(.72,.50,.68)))
    size = 224
    packet = dict(geo=geo,reference=ref,size=size,atlasSize=C.SIZE,tests=tests,
                  albedo=base64.b64encode(atlas.tobytes()).decode(),
                  emission=base64.b64encode(glow.tobytes()).decode())
    run = subprocess.run(['node','tools/check_viewer_raster.js'],cwd=P.ROOT,check=True,
                         input=json.dumps(packet),capture_output=True,text=True)
    frame = [*ref['center'],R.SCALE*size/max(ref['cropSize'])]
    bitmaps=[]
    for test,result in zip(tests,json.loads(run.stdout),strict=True):
        assert np.allclose(frame,result['frame'],rtol=0,atol=1e-12)
        tint=test['tint']
        py = P.render(geo,atlas,P.effective_hidden(geo),size=size,frame=frame,
                      bg=(18,14,26), emission=glow if tint else None, **test)
        js = np.frombuffer(base64.b64decode(result['rgba']),np.uint8).reshape((size,size,4))
        assert np.all(js[...,3]==255)
        rgb=js[...,:3].astype(np.int16)
        discrepancy=np.abs(rgb-np.asarray(py))
        assert (discrepancy<=1).mean()>.997, (test,discrepancy.mean())
        bitmaps.append(rgb)
    base,light,_ = bitmaps
    assert np.count_nonzero(np.max(light-base,axis=2)>64)>200
    # Same occlusion and coverage: low ambient exposes only the hotspots.
    scene=np.array([18,14,26])
    assert np.array_equal((base==scene).all(2),(light==scene).all(2))
    print('Visor: PNG original y encuadre exactos; RGB/alpha del pase de luz contrastados con el raster Python')


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
    assert layout['density'][R.CLOTH]>=8.0 and layout['cards']>=240, layout
    print(f"{layout['cards']} cartas · {layout['density'][R.CLOTH]:.2f} texels/u nominales del paño antes de ajustar ejes por cara")
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
        visor_material(geo,atlas,glow)


if __name__=='__main__':
    main()
