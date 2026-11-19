#!/usr/bin/env python3
"""Check the worn collar, mount and animation refinement (not an in-game test)."""
from __future__ import annotations

import argparse
from hashlib import sha256
from itertools import product
import json

import numpy as np

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_fit as F
import cape_material as C
import preview_cloth as P
from present_v1650 import BASE, OLD_GEO, OLD_TEX, PLAYER, worn
from verify_v1590 import check_editor
from verify_v1600 import registered_metrics, sat
from verify_v1610 import visor_fit
from verify_v1620 import visor_material
from verify_v1630 import views, visor_embers
from verify_v1640 import fit_check, motion, overlap


def preservation(geo, atlas):
    wide = tuple(map(int,P.mod_version().split('.'))) >= (1,67,6)
    for line in (BASE/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ',1)
        prior = (BASE/name).read_bytes()
        assert sha256(prior).hexdigest() == digest, name
        if name not in ('CAPA_v1.64.0.bbmodel','fit.json'):
            live = P.ASSETS/name
            if live not in (P.ARMOR_GEO,A.ANIM) and not (wide and live == P.ICON):
                assert live.read_bytes() == prior, name
    old = P.load(OLD_GEO)
    assert geo['description'] == old['description']
    updated = {G.SEAT_BONE,G.GUSSET_BONE} if wide else set()
    assert [b for b in geo['bones'] if b['name'] not in updated | {G.COLLAR_RETURN}] \
           == [b for b in old['bones'] if b['name'] not in updated]
    assert P.effective_hidden(geo) == P.effective_hidden(old)
    (before,after),_ = registered_metrics(old,geo,atlas,baseline_atlas=OLD_TEX)
    assert np.array_equal(before['match'],after['match']), 'cambió el contorno registrado del dorso'
    assert before['seam'] == after['seam']
    assert np.array_equal(views(old,OLD_TEX),views(geo,atlas)), 'cambió la vista registrada del dorso'
    print(f'Dorso: contorno, color y costura registrados idénticos; error RGB {after["mae"]:.2f}/255. '
          'Atlas, emisión dorsal y lore intactos.',flush=True)

    # Test what actually comes through in front of a worn avatar, not the
    # silhouette of a cape by itself. The cenital/locked rear shots don't
    # tell us whether there is any front-facing fabric to see.
    def front(model, tex):
        return np.asarray(worn(model,tex,180,7,(0.,0.,0.),470,17.4,(0,25.2,1.9))).astype(np.int16)
    mask = np.max(np.abs(front(old,OLD_TEX)-front(geo,atlas)),axis=2) >= 8
    left,right = (int(m.sum()) for m in np.split(mask,2,axis=1))
    assert 100 < left < 900 and 100 < right < 900, (left,right)
    print(f'Frente equipado: asoman ambos bordes ({left}/{right} px distintos, misma cámara).',flush=True)


def returns_fit(geo, quick):
    bone = next(b for b in geo['bones'] if b['name'] == G.COLLAR_RETURN)
    assert bone['parent'] == G.FIT_BONE and len(bone['cubes']) == 3
    mats = P.matrices(geo)
    v = np.array([P.cube_points(c,mats[bone['name']]) for c in bone['cubes']])
    cowl = np.array([P.cube_points(c,mats[b['name']]) for b in geo['bones']
                     if b['name'] != bone['name'] and b['name'].startswith('v17_cowl_')
                     and b['parent'] == G.FIT_BONE for c in b['cubes']])
    rooted = min(overlap(v[1:],cowl).max(1))
    folds = overlap(v[:1],v[1:2])[0,0]
    # All pieces use the same live rigid transform. These overlaps cannot
    # change with look, stance, clip or slot; no separate lapels on the torso.
    assert min(rooted,folds) > .25 and v[...,2].min() > 2.75, (rooted,folds)
    f = F.profile()
    max_depth = np.asarray(f['backset']).max()
    assert F.depth(0,0,0) == 0.

    n_stance, n_aim = (5,33) if quick else (9,49)
    aim = list(product(np.linspace(0,1,n_stance),
                       np.linspace(-90,90,n_aim),np.linspace(-90,90,n_aim)))
    h = np.array([F.head_in_body(*at,outer=True) for at in aim])
    depth = np.array([F.depth(*at) for at in aim])
    head = h-depth[:,None,None]*[0.,0.,1.]
    margins = [sat(np.broadcast_to(q,head.shape),head) for q in v]
    worst = min(map(np.min,margins))
    assert worst > .037, (worst,aim[np.argmin(np.min(margins,axis=0))])
    print(f'Cuello: solape con pliegues ≥ {rooted:.3f} u; entre piezas ≥ {folds:.3f} u. '
          f'{len(aim)} posturas con capa exterior de cabeza, margen ≥ {worst:.3f} u.',flush=True)

    # The original bed doesn't follow the sliding mount. At the artificial
    # limit (crouched and looking straight up), the inflated hat can also
    # meet that original bed; keep that separate from new-collar clearance.
    seat = next(b for b in geo['bones'] if b['name'] == G.SEAT_BONE)
    outer_bed = min(sat(np.broadcast_to(P.cube_points(c,mats[G.SEAT_BONE]),h.shape),h).min()
                    for c in seat['cubes'])
    assert outer_bed > -.04, outer_bed

    worst_arm = float('inf')
    for st, swing in product(np.linspace(0.,1.,5),np.linspace(-60.,60.,41)):
        pose = F.mannequin_pose(st,0,0,arm_swing=(swing,swing))
        body = pose[1]
        arms = np.array([(o+P.CORNERS*s)@m[:3,:3].T+m[:3,3]
                         for (o,s,_),m in zip(PLAYER[2:4],pose[2:4],strict=True)])
        depths = np.linspace(0.,max_depth,17)
        world = ((v + depths[:,None,None,None]*[0.,0.,1.]) @ body[:3,:3].T + body[:3,3]).reshape(-1,8,3)
        worst_arm = min(worst_arm,sat(np.repeat(world,2,axis=0),np.tile(arms,(len(world),1,1))).min())
    assert worst_arm > .15, worst_arm
    print(f'Hombros con balanceo ±60°: margen del remate ≥ {worst_arm:.3f} u. '
          f'Capa exterior de cabeza / asiento antiguo en extremo: {outer_bed:+.3f} u.',flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--fit-only',action='store_true')
    cli.add_argument('--quick',action='store_true',help='reduce el cruce de mezclas y miradas')
    args = cli.parse_args()
    geo = P.load(P.ARMOR_GEO)
    runtime = json.loads(A.ANIM.read_text())
    if not args.fit_only:
        built = G.build_base()['minecraft:geometry'][0]
        atlas,light,layout = C.map_material(built,paint=True)
        assert geo == built and runtime == A.build(geo)
        assert layout['cards'] == 288 and layout['emissive'] == 1848
        preservation(geo,atlas)
        bb = json.loads(B.DOC.read_text())
        check_editor(json.loads((BASE/'CAPA_v1.64.0.bbmodel').read_text()),bb,geo,atlas,runtime)
        motion(geo,runtime,bb)
        visor_fit(geo,runtime)
        visor_material(geo,atlas,light)
        visor_embers()
    returns_fit(geo,args.quick)
    fit_check(geo,runtime['animations'],args.quick)


if __name__ == '__main__':
    main()
