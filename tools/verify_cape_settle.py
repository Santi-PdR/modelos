#!/usr/bin/env python3
"""Apply the runtime's sampled hem response to authored clip blends and check fit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import cape_animation_pipeline as A
import cape_fit as F
import cape_motion as M
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_v1600 import interpolate
from verify_v1660 import WornModel, actors, contacts


def samples(path):
    rows = np.loadtxt(path, dtype=str)
    assert set(rows[:, 0]) == {'BRAKE', 'LAND'}
    data = {m: rows[rows[:, 0] == m, 1:].astype(float) for m in ('BRAKE', 'LAND')}
    for values in data.values():
        assert values.shape == (31, 9) and np.allclose(values[:,0], np.arange(31)/20)
    return data


def add_response(geo, pitch, yaw, roll):
    bones = []
    for b in geo['bones']:
        m = M.RIBBON.fullmatch(b['name'])
        if m and 1 <= (seg := int(m[2])) <= M.LAST_JOINT:
            q = (seg / M.LAST_JOINT)**1.45
            x, y, z = b['rotation']
            # GeckoLib mirrors X and Y; these are rotations of the free
            # hinges, not translations or new keyframes.
            b = dict(b, rotation=[x-pitch[seg-1], y-yaw*q, z+roll*q])
        bones.append(b)
    return dict(geo, bones=bones)


def verify(geo, samples):
    rig = WornModel(geo)
    clips = json.loads(A.ANIM.read_text())['animations']
    tracks = {n: T.prepare_clip(clips['animation.'+n]) for n in ('idle', 'sprint', 'fall')}
    fixed = rig.rigid | np.array([n.endswith('_seg0') for n in rig.names])
    aim = (0., 12., 32.)
    depth = F.depth(*aim)
    # Cross the transition with different limb phases even when the actual
    # player's gait would be fading. This samples the existing stride guide,
    # not a claim about all possible armor, skins or in-game poses.
    gaits = [S.gait(i/16, .85) for i in range(16)]
    boxes = np.array([actors(aim, *gait, .25) for gait in gaits])
    demand = [S.demand(aim[0], *gait) for gait in gaits]
    for motion, rows in samples.items():
        source, blend_sec = ('sprint', .30) if motion == 'BRAKE' else ('fall', .15)
        minimum = np.full(2, np.inf)
        worst = .04
        count = 0
        for phase in (.07, .42, .77):
            initial = P.pose_at(geo, tracks[source], clips['animation.'+source]['animation_length']*phase)
            for time, *pitches in rows:
                target = P.pose_at(geo, tracks['idle'], time)
                pose = interpolate(initial, target, min(1, time/blend_sec))
                angles = {b['name']: b['rotation'][0] for b in pose['bones']}
                lift = np.asarray([S.lifts(angles['cape_top'], angles['cape_mid'], *d, aim[0], depth)
                                   for d in demand])
                for y, z in ((0., 0.), (-1.55, -1.4), (-1.55, 1.4), (1.55, -1.4), (1.55, 1.4)):
                    before, after = [rig.lifted(rig.vertices(add_response(pose, pitches[i::2], y, z), aim), lift)
                                     for i in (0, 1)]
                    assert np.array_equal(before[:,fixed], after[:,fixed]), 'se movió la montura o una raíz cosida'
                    old = contacts(before[:,rig.cloth], boxes).min(2)
                    new = contacts(after[:,rig.cloth], boxes).min(2)
                    assert not ((new < -.015) & (old >= -.015)).any(), (motion, phase, time, new.min())
                    worst = min(worst, new.min())
                    for ix in {0, *lift.argmax(0)}:
                        minimum = np.minimum(minimum, rig.joins(after[ix]))
                    count += len(gaits)
        assert minimum[0] > .038 and minimum[1] > .025, minimum
        print(f'{motion}: {count} poses con holgura activa, sin cruces nuevos; '
              f'cota de separación brazo/pierna {worst:+.3f} u, solape costura/raíz {minimum[0]:.3f}/{minimum[1]:.3f} u.')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('samples', type=Path, help='TSV de CapeSettleTest --samples')
    cli.add_argument('--plate', type=Path, help='guardar la comparativa de halo y dobladillo')
    arg = cli.parse_args()
    data = samples(arg.samples)
    geo = P.load(P.ARMOR_GEO)
    verify(geo, data)
    if arg.plate:
        from present_v1673 import plate
        plate(arg.plate, geo, data)


if __name__ == '__main__':
    main()
