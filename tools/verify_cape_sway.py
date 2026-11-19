#!/usr/bin/env python3
"""Compare the equipped lateral response with the visor and the sewn rig."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

import cape_animation_pipeline as A
import cape_fit as F
import cape_motion as M
import cape_stride as S
import cape_sway as W
import cape_tracks as T
import preview_cloth as P
from verify_v1660 import WornModel, actors, contacts


def verify_demo(samples, p):
    data = np.loadtxt(samples)
    assert data.shape == (41, 9) and np.allclose(data[:, 0], np.arange(41)/20)
    angles = np.array([[W.angles(p, t, seg) for seg in range(1, 5)] for t in data[:, 0]])
    np.testing.assert_allclose(angles.reshape(-1, 8), data[:, 1:], rtol=0, atol=1e-12)
    assert angles[22, 0, 1] < 0 < angles[22, 3, 1], 'el extremo no tarda más en volver'
    run = subprocess.run(['node','tools/check_viewer_pose.js'], cwd=P.ROOT, check=True, text=True,
                         input=json.dumps(dict(swayTimes=data[:, 0].tolist(), sway=p)), capture_output=True)
    np.testing.assert_allclose(json.loads(run.stdout), data[:, 1:], rtol=0, atol=1e-12)
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    assert json.loads(re.search(r'^const INLINE_SWAY = (.+);$', html, re.M)[1]) == p
    print(f'{angles.size} ángulos coinciden en Java/Python/visor; a 1,10 s el primer tramo ya gira y el último no.', flush=True)
    return data[:, 0], angles


def clip_pose(geo, clip, t, angles, pitch, turn, roll, p):
    def overlay(name):
        m = M.RIBBON.fullmatch(name)
        if not m or not 1 <= (seg := int(m[2])) <= p['LAST_SEGMENT']:
            return (0, 0, 0)
        q = (seg/p['LAST_SEGMENT'])**p['SEGMENT_POWER']
        y, z = angles[seg-1]
        # Add the new component before the existing limits, in baked signs.
        return (-pitch*q, -np.clip(turn*q+y, -p['MAX_YAW']*q, p['MAX_YAW']*q),
                np.clip(roll*q+z, -p['MAX_ROLL']*q, p['MAX_ROLL']*q))
    return P.pose_at(geo, clip, t, overlay)


def verify_fit(geo, clips, times, angles, p):
    rig = WornModel(geo)
    fixed = rig.rigid | np.array([n.endswith('_seg0') for n in rig.names])
    tips = np.array([n.endswith('_seg4') for n in rig.names])
    zero = np.zeros((4, 2))
    track = T.prepare_clip(clips['animation.moving'])
    static = [rig.vertices(clip_pose(geo,track,0,offset,0,0,0,p),(0,0,0))[0]
              for offset in (zero, angles[16], angles[36])]
    ends = static[0][tips, :, 1] < np.quantile(static[0][tips, :, 1], .15)
    deltas = [(pose[tips] - static[0][tips])[ends].mean(0) for pose in static[1:]]
    # LivingEntityRenderer and GeoArmorRenderer cancel their two X/Y
    # reflections. What remains in the standing body frame is Y(180-yaw).
    for yaw in range(-180, 180, 15):
        facing = P.R('y', 180-yaw)[:3, :3]
        radians = np.deg2rad(yaw)
        side = np.array([np.cos(radians), 0, np.sin(radians)])
        projections = [side @ facing @ delta for delta in deltas]
        assert projections[0] < -.08 and projections[1] > .08, (yaw, projections)
    print(f'Las puntas quedan {-deltas[0][0]:+.3f}/{-deltas[1][0]:+.3f} u '
          'contra el desplazamiento (24 ángulos del torso).', flush=True)

    count = 0
    minimum = np.full(2,np.inf)
    for name, amplitude, aim, damping in (
            ('idle', .18, (0.,0.,0.), 1), ('moving', .75, (0.,0.,0.), 1),
            ('sprint', .85, (0.,18.,35.), 1), ('sneak', .50, (1.,14.,38.), 1),
            ('swim', .45, (0.,0.,0.), .35), ('air', .40, (0.,0.,0.), 1),
            ('fall', .40, (0.,0.,0.), 1), ('deterioro', .75, (0.,0.,0.), 1)):
        clip = clips['animation.'+name]
        track = T.prepare_clip(clip)
        gaits = [S.gait(j/16, amplitude) for j in range(16)]
        boxes = np.array([actors(aim,*gait,.25) for gait in gaits])
        depth = F.depth(*aim)
        demand = [S.demand(aim[0],*gait) for gait in gaits]
        for i in range(0, 41, 2):
            time = times[i] % clip['animation_length']
            drift = damping*angles[i]
            parts = P.pose_at(geo, track, time)['bones']
            root_angles = [b['rotation'][0] for b in parts if b['name'] in ('cape_top','cape_mid')]
            lift = np.array([S.lifts(*root_angles,*d,aim[0],depth) for d in demand])
            for pitch, turn, roll in ((0,0,0),(-2.1,-.75,.5),(1.2,.75,-.5)):
                before, after = [rig.lifted(rig.vertices(clip_pose(geo,track,time,e,pitch,turn,roll,p),aim),lift)
                                 for e in (zero,drift)]
                assert np.array_equal(before[:,fixed],after[:,fixed]), 'la montura, cuello o raíz cosida cambió'
                old = contacts(before[:,rig.cloth],boxes)
                new = contacts(after[:,rig.cloth],boxes)
                assert not ((new < -.015) & (old >= -.015)).any(), (name,time,new.min())
                count += len(gaits)
                for j in {0,*lift.argmax(0)}:
                    minimum = np.minimum(minimum,rig.joins(after[j]))
    assert minimum[0] > .038 and minimum[1] > .025, minimum
    print(f'{count} poses: sin cruces nuevos de brazos/piernas. '
          f'Solape costura/raíz ≥ {minimum[0]:.3f}/{minimum[1]:.3f} u en la muestra.', flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('samples', type=Path, help='TSV de CapeSwayTest --samples')
    cli.add_argument('--plate', type=Path, help='guardar la comparativa de arrastre')
    args = cli.parse_args()
    p = W.profile()
    times, angles = verify_demo(args.samples, p)
    geo = P.load(P.ARMOR_GEO)
    clips = json.loads(A.ANIM.read_text())['animations']
    verify_fit(geo, clips, times, angles, p)
    if args.plate:
        from present_v1674 import plate
        plate(args.plate, geo, clips['animation.moving'], times, angles, p, clip_pose)


if __name__ == '__main__':
    main()
