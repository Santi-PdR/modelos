#!/usr/bin/env python3
"""Prove the yoke is sewn in 3D and the skirt/atlas remain the same assets."""
from __future__ import annotations

from itertools import product
from math import hypot
import json
import re
import subprocess

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
from cape_attachment import ARMS, FACING, FOLD_LINE, FRAME, LININGS, PADS
import cape_animation_pipeline as A
import cape_fit as F
import cape_material as C
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_cape_backing import lap, occupied, patches
from verify_v1600 import interpolate, sat
from verify_v1660 import contacts


def asset_contract(geo):
    legacy = G.build_base()['minecraft:geometry'][0]
    atlas, glow, _ = C.map_material(legacy, paint=True)
    for image, name in ((atlas, P.ARMOR_TEX), (glow, P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem+'_glowmask'))):
        assert np.array_equal(image, Image.open(name).convert('RGBA')), name
    assert geo == G.build()['minecraft:geometry'][0], 'generated GEO is stale'
    by = {b['name']: b for b in geo['bones']}
    fixed = {FRAME, G.GUSSET_BONE, G.SADDLE_BONE, *PADS, *LININGS} | {n for n,b in by.items() if b.get('parent') == FRAME}
    assert [b['name'] for b in geo['bones'] if b['name'] not in fixed] == [
        b['name'] for b in legacy['bones'] if b['name'] not in fixed]
    crease = set()
    rest = dict(legacy, bones=[dict(b, rotation=[0.,0.,0.]) if b['name'] == 'cape_top' else b
                              for b in legacy['bones']])
    mats = P.matrices(rest)
    for b in legacy['bones']:
        name = b['name']
        if name in fixed:
            continue
        new = by[name]
        if b == new:
            continue
        assert b.get('parent') == 'cape_top' and name.startswith(('v17_ribbon_', 'v17_vein_')), name
        assert {**b, 'cubes': None} == {**new, 'cubes': None}, name
        for a,c in zip(b['cubes'], new['cubes'], strict=True):
            assert a['uv'] == c['uv'] and a['inflate'] == c['inflate'], name
            if a != c:
                assert P.cube_points(a, mats[name], inflate=False)[:,1].max() > FOLD_LINE, name
                crease.add(name)
    print(f'UV, atlas, emisión y piezas bajo el pliegue intactos; {len(crease)} huesos de tela con el extremo plegado.', flush=True)
    assert by[FRAME]['parent'] == 'chestplate'
    for pad, lining, arm in zip(PADS, LININGS, ARMS, strict=True):
        assert by[pad]['parent'] == by[lining]['parent'] == arm and len(by[pad]['cubes']) == 4
    clips = json.loads(A.ANIM.read_text())
    assert clips == A.build(legacy), 'a skirt clip changed'
    assert not any(set(c['bones']) & fixed for c in clips['animations'].values())
    editor = json.loads(B.DOC.read_text())
    assert B.build(geo, atlas, clips) == editor, 'editable rig does not match equipped rig'
    viewer = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    for key, asset in (('GEO', json.loads(P.ARMOR_GEO.read_text())), ('ANIMATIONS', clips)):
        inline = re.search(r'^const INLINE_' + key + r' = (.+);$', viewer, re.M)
        assert inline and json.loads(inline[1]) == asset, f'visor offline desactualizado: {key}'
    return by, fixed, clips['animations']


def seam_contract(geo, by, clips):
    local = patches(geo)
    anchors = [n for n,b in by.items() if b.get('parent') == FRAME and len(local[n])]
    jersey = P.CORNERS*[8,12,4]+[-4,12,-2]
    # Real positive-volume overlaps. No piece of the yoke may be reachable
    # only via a pad or an animated flap, or touch the shirt just in projection.
    solids = np.concatenate([[jersey], *[local[n] for n in anchors]])
    lhs, rhs = np.indices((len(solids),len(solids)))
    adjacency = (sat(solids[lhs.ravel()], solids[rhs.ravel()]) < -.025).reshape(lhs.shape)
    sewn = {0}
    while True:
        reached = sewn | set(np.flatnonzero(adjacency[list(sewn)].any(axis=0)))
        if reached == sewn:
            break
        sewn = reached
    assert len(sewn) == len(solids), 'unattached fold or fastener'
    # A physical hem along the torso back, not just one point of intersection
    # or an overlapping shadow in an F5 view. The jacket has 0.25u of dilation.
    edge = np.asarray(list(product(np.linspace(-3.52, 3.52, 35), (17.44, 18.07, 18.97), (2.01, 2.15, 2.26))))
    assert occupied(solids[1:], edge) == 1, 'open strip on the back of the shirt'
    fore_edge = np.asarray(list(product((-3.59, -3.41, 3.41, 3.59), (18.44, 18.90), (-2.04, -2.26))))
    assert occupied(solids[1:], fore_edge) == 1, 'open front returns'

    skin_lap = float('inf')
    for i, (name, lining) in enumerate(zip(PADS, LININGS, strict=True)):
        pad, *trim = local[name]
        front, crown, back, facing = local[lining]
        rail = local[lining]
        assert min(lap(front, solids[1:]), lap(back, solids[1:]), lap(facing, local[FACING])) > .16, 'unsewn returns'
        assert min(lap(front, crown[None]), lap(back, crown[None]), lap(facing, back[None]),
                   lap(crown, pad[None])) > .10, 'unsewn sleeve lining'
        assert min(lap(c, pad[None]) for c in trim) > .05, 'detached crest or lip'
        for width, stance, swing in product((3,4), (0.,.5,1.), (-60,-22,0,22,60)):
            left = 4 if i == 0 else -4-width
            skin = P.CORNERS*[width,12,4]+[left,12,-2]
            # For a slim sleeve both the visible armor and vanilla arm inherit
            # ModelPart.y = 2.5 (+3.2 while crouched), not the Steve pivot of 2.
            poses = F.wearer_pose(geo,stance,0,0,arm_swing=(-swing,swing))
            arm = P.matrices(poses)[ARMS[i]]
            arm = P.T([0., -.5*(4-width), 0.]) @ arm
            worn_sleeve = (skin @ arm[:3,:3].T + arm[:3,3])[None]
            worn_base = pad @ arm[:3,:3].T + arm[:3,3]
            worn_rail = rail @ arm[:3,:3].T + arm[:3,3]
            lap_base = lap(worn_base,worn_sleeve)
            skin_lap = min(skin_lap, lap_base, *(lap(v,worn_sleeve) for v in worn_rail))
    assert skin_lap > .16, ('floating pad or tongue', skin_lap)
    print(f'Steve/Alex con mangas a ±60°: placa y forro pisan piel ≥ {skin_lap:.3f}u.', flush=True)

    # The two folds of the flexible lining link the torso to the cape_top
    # saddle, including when `air` raises it and after crouch moves it out.
    steps = (0.,.28,.64,1.)
    samples = [P.pose_at(geo,T.prepare_clip(c),t*c['animation_length']) for c,t in product(clips.values(),steps)]
    samples += [interpolate(a,b,t) for a,b in zip(samples[::4],samples[3::4][1:]+samples[3:4],strict=True)
                for t in (.25,.5,.75)]
    dmin = np.full(3,np.inf)
    cases = 0
    for frame, stance, wings in product(samples, (0.,.27,.62,1.), (False,True)):
        h = S.adjust(frame, 29, 42, (stance,0,0))
        if wings:
            h['bones'] = [dict(b, rotation=[max(34,b['rotation'][0]), *b['rotation'][1:]])
                          if b['name'] == 'cape_top' else b for b in h['bones']]
        p = patches(F.wearer_pose(h,stance,0,0))
        g0,g1 = p[G.GUSSET_BONE]
        fixed_mesh = np.concatenate([p[n] for n in anchors])
        saddle = p[G.SADDLE_BONE]
        roots = [p[f'v17_ribbon_{i}_seg0'] for i in range(12)]
        scores = [lap(g0,fixed_mesh), min(lap(g0,g1[None]),lap(g1,saddle)),
                  min(max(lap(c,saddle) for c in r) for r in roots)]
        dmin = np.minimum(dmin,scores)
        cases += 1
    assert (dmin > .08).all(), dmin
    print(f'{cases} clips, mezclas, agachados y alas: solape torso / fuelle / las 12 raíces ≥ '
          + ' / '.join(f'{d:.3f}u' for d in dmin), flush=True)


def head_contract(geo, by):
    """Clearance of the rigid body yoke, independent of the arm and drape pose."""
    p = patches(geo)
    yoke = np.concatenate([p[n] for n,b in by.items() if b.get('parent') == FRAME and n != FACING and len(p[n])])
    # The facing belongs to the shirt surface, not the raised collar test.
    # Its front plane is embedded in the skin and its back is only a hem's
    # thickness outside the jacket, even where the head occludes the shirt.
    facing = p[FACING]
    assert facing[...,2].min() < 2 and facing[...,2].max() <= 2.35
    assert facing[...,0].min() >= -4.25 and facing[...,0].max() <= 4.25
    # Even between sampled angles, a standing head never reaches below
    # its pivot minus the radius of its lower edge in the pitch plane.
    floor = F.HEAD_PIVOT[1] - hypot(.5, 4.5)
    assert floor - yoke[...,1].max() > .025, 'fixed torso yoke enters the standing head sweep'
    # The full standing head sweep and the ordinary crouched poses; the
    # moving arms and skirt are measured separately, not put in this hull.
    aims = [(0.,p,y) for p,y in product(range(-90,91,3),range(-84,85,3))]
    aims += [(s,p,y) for s,p,y in product((.33,.66,1.),(-20,0,10),(-30,0,30))]
    hats = np.asarray([F.head_in_body(*a,outer=True) for a in aims])
    gap = contacts(yoke[None], hats[None], pad=.08)[0].min(axis=1)
    assert gap.min() > .035, (aims[np.argmin(gap)], gap.min(), 'outer yoke inside the head')
    print(f'Yugo exterior: {len(aims)-27} giros de pie y 27 poses agachadas, holgura ≥ {gap.min():.3f}u.', flush=True)


def jump_clearance(geo, clips):
    # The user's straight-up case, including the entire fall cycle and a
    # landing mix, tested against the inflated vanilla head, not the camera.
    # On the wider diagonal/crouch sweep we require attachment continuity,
    # not that the head never occludes soft lining or the inboard relief.
    hats = np.array([F.head_in_body(0., pitch, 0., outer=True) for pitch in range(0,91,2)])[None]
    by = {b['name']: b for b in geo['bones']}
    names = [*PADS, G.GUSSET_BONE, G.SADDLE_BONE] + [n for n,b in by.items()
             if b.get('parent') == 'cape_top' and n.startswith('v17_ribbon_') and b['cubes']]
    phases = (0.,.18,.33,.5,.68,.85,1.)
    measured = float('inf')
    idle, fall = [clips['animation.'+n] for n in ('idle', 'fall')]
    neutral = P.pose_at(geo,T.prepare_clip(idle),0.)
    samples = [P.pose_at(geo,T.prepare_clip(c),t*c['animation_length']) for c,t in product((idle,fall),phases)]
    samples += [interpolate(samples[-1],neutral,t) for t in (.25,.5,.75)]
    for frame, swing, slim in product(samples, (-5.,0.,5.), (False,True)):
        worn = F.wearer_pose(frame,0.,0.,0.,arm_swing=(-swing,swing))
        if slim:
            for b in worn['bones']:
                if b['name'] in ARMS:
                    b['offset'][1] -= .5
        data = patches(worn)
        shapes = np.concatenate([data[n] for n in names])
        measured = min(measured, contacts(shapes[None],hats,pad=.10).min())
    assert measured > .006, ('straight-up idle/jump fold clips the head', measured)
    print(f'{len(samples)*6*len(hats[0])} muestras de mirada arriba, reposo/salto/aterrizaje: placas, fuelle y raíces ≥ {measured:.3f}u.', flush=True)


def view_contract(geo, fixed):
    # Rotate the head at fixed torso & sleeve poses. Rotating the body and
    # translating it up (jump) is a rigid world transform, not a cape input.
    names = sorted(fixed)
    numeric, aims = [], []
    for stance, swings in product((0.,.48,1.), ((0.,0.),(-26.,32.))):
        rest = P.matrices(F.wearer_pose(geo,stance,0,0,arm_swing=swings))
        for pitch,yaw in product((-89.5,-55,0,48,89.5),(-79,-30,0,35,79)):
            aim = [stance,pitch,yaw]
            pose = P.matrices(F.wearer_pose(geo,*aim,arm_swing=swings))
            assert all(np.array_equal(rest[n],pose[n]) for n in rest)
            aims.append([*aim,False,0,0,list(swings)])
            numeric.append([pose[n].ravel().tolist() for n in names])
    payload = dict(geo=geo, parts=names, fit=F.viewer_profile(), torsoMatrices=aims)
    run = subprocess.run(['node','tools/check_viewer_pose.js'], cwd=P.ROOT, check=True,
                         input=json.dumps(payload), text=True, capture_output=True)
    np.testing.assert_allclose(json.loads(run.stdout),numeric,rtol=0,atol=1e-9)
    print(f'{len(aims)} poses: yugo y hombreras invariantes ante la cabeza, visor y GEO coincidentes.', flush=True)


if __name__ == '__main__':
    geo = P.load(P.ARMOR_GEO)
    by, fixed, clips = asset_contract(geo)
    seam_contract(geo, by, clips)
    head_contract(geo, by)
    jump_clearance(geo, clips)
    view_contract(geo, fixed)
