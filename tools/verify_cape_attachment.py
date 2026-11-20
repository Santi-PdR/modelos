#!/usr/bin/env python3
"""Prove the yoke is sewn in 3D and the skirt/atlas remain the same assets."""
from __future__ import annotations

from itertools import product
import json
import subprocess

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
from cape_attachment import ARMS, FRAME, PADS
import cape_animation_pipeline as A
import cape_fit as F
import cape_material as C
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_cape_backing import lap, patches
from verify_v1600 import interpolate, sat


def asset_contract(geo):
    legacy = G.build_base()['minecraft:geometry'][0]
    atlas, glow, _ = C.map_material(legacy, paint=True)
    for image, name in ((atlas, P.ARMOR_TEX), (glow, P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem+'_glowmask'))):
        assert np.array_equal(image, Image.open(name).convert('RGBA')), name
    assert geo == G.build()['minecraft:geometry'][0], 'generated GEO is stale'
    by = {b['name']: b for b in geo['bones']}
    fixed = {FRAME, G.GUSSET_BONE, G.SADDLE_BONE, *PADS} | {n for n,b in by.items() if b.get('parent') == FRAME}
    assert [b for b in geo['bones'] if b['name'] not in fixed] == [b for b in legacy['bones'] if b['name'] not in fixed]
    assert by[FRAME]['parent'] == 'chestplate'
    for pad, arm in zip(PADS, ARMS, strict=True):
        assert by[pad]['parent'] == arm and len(by[pad]['cubes']) == 4
    clips = json.loads(A.ANIM.read_text())
    assert clips == A.build(legacy), 'a skirt clip changed'
    assert not any(set(c['bones']) & fixed for c in clips['animations'].values())
    editor = json.loads(B.DOC.read_text())
    assert B.build(geo, atlas, clips) == editor, 'editable rig does not match equipped rig'
    return by, fixed, clips['animations']


def seam_contract(geo, by, fixed, clips):
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
    for i,n in enumerate(PADS):
        assert max(lap(c, np.concatenate([local[a] for a in anchors])) for c in local[n]) > .12
        pad, *trim = local[n]
        assert min(lap(c, pad[None]) for c in trim) > .025, 'detached crest or lip'
        # Skin first; surrounds and underlaps the outer jacket, it does not
        # depend on the optional sleeve layer existing on the current skin.
        for width in (3,4):
            x = 4 if i == 0 else -4-width
            sleeve = (P.CORNERS * [width,12,4] + [x,12-.5*(4-width),-2])[None]
            assert max(lap(c, sleeve) for c in local[n]) > .12, (n,width,'floating pad')

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
    seam_contract(geo, by, fixed, clips)
    view_contract(geo, fixed)
