#!/usr/bin/env python3
"""Verify the wing guide with pose and hull parity, then compare cloth clearance."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess

import numpy as np

import cape_animation_pipeline as A
import cape_fit as F
import cape_motion as M
import cape_stride as S
import cape_tracks as T
import cape_wings as W
import preview_cloth as P
from verify_v1600 import interpolate, response_variants
from verify_v1660 import WornModel, actors, contacts


def parity(tsv):
    rows = np.loadtxt(tsv)
    assert rows.shape == (1152, 11)
    expected = []
    angle = F.profile()['bodyAngle']
    for pitch, roll, body, d, arm, leg, top, mid in rows[:, :8]:
        goal = W.goal(pitch, roll, body, d)
        expected.append((goal, *S.lifts(top, mid, arm, leg, body/angle, d, wing_lift=W.lift(top, goal))))
    np.testing.assert_allclose(rows[:, 8:], expected, rtol=0, atol=1e-10)
    wing_pos = [W.profile()[name] for name in ('folded', 'crouched', 'open')] + [[18, 2.5, 60, 1.2]]
    args = dict(wings=W.profile(), stride=S.profile(), wingSamples=rows[:, :8].tolist(), wingPoses=wing_pos)
    result = subprocess.run(['node', 'tools/check_viewer_pose.js'], cwd=P.ROOT, check=True, text=True,
                            input=json.dumps(args), capture_output=True)
    js = json.loads(result.stdout)
    np.testing.assert_allclose(js['angles'], expected, rtol=0, atol=1e-10)
    np.testing.assert_allclose(js['hulls'], [W.hulls(*p) for p in wing_pos], rtol=0, atol=1e-10)
    visor = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    assert json.loads(re.search(r'^const INLINE_WINGS = (.+);$', visor, re.M)[1]) == W.profile()
    print(f'{len(rows)} perfiles de la bisagra y cuatro pares de alas coinciden con el visor.', flush=True)


def posed(geo, aim, pose):
    """Frame for the comparison plate, with a quiet mannequin."""
    pitch, _, roll, _ = pose
    by = {b['name']: b for b in geo['bones']}
    top = by['cape_top']['rotation'][0]
    lift = W.lift(top, W.goal(pitch, roll, aim[0]*F.profile()['bodyAngle'], F.depth(*aim)))
    return dict(geo, bones=[dict(b, rotation=[top+lift, *b['rotation'][1:]])
                           if b is by['cape_top'] else b for b in geo['bones']])


def exercise(geo, clips):
    rig = WornModel(geo)
    profile = W.profile()
    tracks = {n.removeprefix('animation.'): T.prepare_clip(c) for n,c in clips.items()}
    free = np.array([bool((m := M.RIBBON.fullmatch(n)) and int(m[2]) > 0) for n in rig.names])
    tip = np.array([n.endswith('_seg4') for n in rig.names])
    folded, crouched, spread = [np.array(profile[k]) for k in ('folded', 'crouched', 'open')]
    part_open = [folded+(spread-folded)*t for t in (.25,.5,.75)]
    transition = [folded, *part_open, spread]
    standing, crouch = (0.,0.,0.), (1.,0.,0.)
    fixtures = [
        ('reposo', 'idle', .12, standing, [folded, *transition[1:], [7,0,7,0]], None),
        ('reposo', 'idle', .12, (0.,30.,35.), [folded], None),
        ('caminar', 'moving', .72, standing, [folded, *part_open], None),
        ('sprint', 'sprint', .90, (0.,-15.,0.), [folded], None),
        ('deteriorado', 'deterioro', .16, standing, [folded], None),
        ('agachado', 'sneak', .4, crouch, [folded+[0,0,0,3], (folded+crouched)/2+[0,0,0,1.5], crouched], None),
        ('agachado', 'sneak', .4, (1.,20.,38.), [crouched], None),
        ('planeo', 'air', .30, standing, transition, 'moving'),
        ('aterrizaje', 'idle', .46, (0.,-12.,30.), transition, 'air'),
        ('caída', 'fall', .2, standing, [folded, *part_open[1:]], None),
        ('agua', 'swim', .45, standing, [folded], None),
    ]
    min_seams = np.full(2, np.inf)
    min_wings = defaultdict(lambda: np.zeros((2,2), int))
    total = 0
    angles = F.profile()['bodyAngle']
    for label, name, amp, aim, wings, from_clip in fixtures:
        gaits = [S.gait(i/12, amp) for i in range(12)]
        legs = np.array([actors(aim,*g,.25) for g in gaits])
        head, body = F.mannequin_pose(*aim)[:2]
        head = (F.HEAD_OUTER+F.HEAD_PIVOT) @ head[:3,:3].T + head[:3,3]
        body = (P.CORNERS*[8.5,12.5,4.5]+[-4.25,11.75,-2.25]) @ body[:3,:3].T + body[:3,3]
        body_boxes = np.broadcast_to([head,body], (len(gaits),2,8,3))
        skin = np.concatenate([legs,body_boxes], axis=1)
        needs = [S.demand(aim[0],*g) for g in gaits]
        d = F.depth(*aim)
        track = tracks[name]
        length = clips['animation.'+name]['animation_length']
        for i, overlay in enumerate([None, *response_variants()[::3]]):
            for phase in (0., .2, .4, .6, .8):
                frame = P.pose_at(geo, track, phase*length, overlay)
                if from_clip and i != 0:
                    before = P.pose_at(geo, tracks[from_clip], .22, overlay)
                    frame = interpolate(before, frame, phase)
                rotations = {b['name']: b['rotation'][0] for b in frame['bones']}
                top, mid = (rotations[n] for n in ('cape_top','cape_mid'))
                packed = rig.vertices(frame, aim)
                a = np.array([S.lifts(top,mid,arm,knee,aim[0],d) for arm,knee in needs])
                old = rig.lifted(packed, a)
                old_skin = contacts(old[:,rig.cloth], skin)
                for p in wings:
                    wing = np.broadcast_to(W.hulls(*p), (len(gaits),2,8,3))
                    goal = W.goal(p[0],p[2],aim[0]*angles,d)
                    lift = W.lift(top,goal)
                    b = np.array([S.lifts(top,mid,arm,knee,aim[0],d,wing_lift=lift) for arm,knee in needs])
                    new = rig.lifted(packed, b)
                    np.testing.assert_array_equal(old[:,rig.rigid], new[:,rig.rigid])
                    new_skin = contacts(new[:,rig.cloth], skin)
                    assert not ((new_skin < -.015) & (old_skin >= -.015)).any(), (label,aim,p,phase,overlay)
                    for j in {0,*b.argmax(0)}:
                        min_seams = np.minimum(min_seams, rig.joins(new[j]))
                    if p[2] >= profile['CLEAR_SPAN']:
                        np.testing.assert_array_equal(old,new)
                    if np.array_equal(p,folded) and label in ('reposo','caminar','sprint','deteriorado'):
                        for j, v in enumerate((old,new)):
                            hit = (contacts(v,wing).min(1)<-.015)
                            min_wings[label][j] += [hit[:,free].sum(), hit[:,tip].sum()]
                    total += len(gaits)
    for name, hit in min_wings.items():
        print(f'{name:10}: cruces caja-paño libre/punta con alas plegadas: {hit[0].tolist()} → {hit[1].tolist()}', flush=True)
    old, new = sum(min_wings.values())
    assert new[0] < .27*old[0] and new[1] < .025*old[1], (old, new)
    assert min_seams[0] > .038 and min_seams[1] > .025, min_seams
    print(f'{total} poses: {old[0]} → {new[0]} cruces ala/paño libre en plegado estable. '
          f'Sin cruces nuevos con el maniquí; solape costura/raíz {min_seams[0]:.3f}/{min_seams[1]:.3f} u.', flush=True)
    return old, new


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('samples', type=Path, help='TSV de CapeWingFitTest --samples')
    cli.add_argument('--plate', type=Path, help='exportar la vista comparada')
    args = cli.parse_args()
    parity(args.samples)
    geo = P.load(P.ARMOR_GEO)
    clips = json.loads(A.ANIM.read_text())['animations']
    counts = exercise(geo, clips)
    if args.plate:
        from present_v1675 import plate
        plane = W.profile()['folded']
        raw = P.pose_at(geo, T.prepare_clip(clips['animation.idle']), 1.22)
        plate(args.plate, [raw, posed(raw, (0,0,0), plane)], plane, counts)


if __name__ == '__main__':
    main()
