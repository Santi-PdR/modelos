#!/usr/bin/env python3
"""Sweep idle fit outside the historical F5 poses. Geometry only, not a skin test."""
from itertools import product
import json
import math

import numpy as np

import cape_animation_pipeline as A
import cape_fit as F
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_cape_seat import wardrobe
from verify_v1660 import WornModel, contacts


def audit():
    geo = P.load(P.ARMOR_GEO)
    rig = WornModel(geo)
    clip = json.loads(A.ANIM.read_text())['animations']['animation.idle']
    idle = P.pose_at(geo, T.prepare_clip(clip), .22 * clip['animation_length'])
    crown = np.array([n.startswith('v17_cowl_back_') for n in rig.names])
    collar = np.array([n.startswith(('v17_cowl_', 'v19_cuellito_', 'v18_chain_'))
                       and n != 'v17_cowl_return' for n in rig.names])
    roots = np.array([n.startswith('v17_ribbon_') and n.endswith('_seg0') for n in rig.names])
    pitches = (0,-19,-32,-42,-48,-58,-66,-76,-89.5)
    turns = (0, *(s*y for y in (30,43,48,52,56,60,67,74,82) for s in (-1,1)))
    laps = np.full(2, np.inf)
    min_head, min_hat, min_sleeve = np.inf, np.inf, np.inf
    hat_contacts = count = 0
    for stance, pitch, yaw, swing in product((0.,.12,.32,1.), pitches, turns, (0.,4.6,17.)):
        aim, arms, legs = (stance,pitch,yaw), (swing,-swing), (0.,0.)
        arm, leg = S.demand(stance, arms, legs)
        effort = max(arm, *(abs(a+math.degrees(.4*stance)) for a in arms))
        frame = S.adjust(idle,arm,leg,aim) if arm or leg else idle
        mats = P.matrices(F.wearer_pose(frame,*aim,arm_back=arm,arm_effort=effort))
        verts = rig.place(mats)
        boxes = wardrobe(aim,arms,legs)
        trim = verts[None,collar]
        gaps = contacts(trim,boxes,pad=.65)[0]
        hat_gap = float(gaps[0].min())
        min_hat = min(min_hat, hat_gap)
        min_sleeve = min(min_sleeve, float(gaps[2:-2].min()))
        hat_contacts += int(hat_gap < 0)
        # The inflated 9u hat is only an envelope: transparent skin pixels
        # may leave it empty. Distinguish it from the solid vanilla 8u head.
        outer = boxes[0,0]
        center = outer.mean(0)
        head = center + (outer-center)*(8/9)
        head_gap = contacts(trim,head[None,None],pad=.65).min()
        min_head = min(min_head, float(head_gap))
        joined = rig.joins(verts)
        laps = np.minimum(laps, joined)
        count += 1
        if stance == swing == 0 and pitch in (-48,-58,-76) and yaw in (0,43,52,60,74):
            torso = F.mannequin_pose(*aim)[1]
            body = (verts-torso[:3,3]) @ torso[:3,:3]
            print(f'{-pitch:g}° abajo/{yaw:+g}° giro: cuello Z {body[crown,:,2].min():.2f}u; '
                  f'raíces Z {body[roots,:,2].min(1).mean():.2f}u.')
    assert min(laps) > .025, ('solape de costuras y raíces', laps)
    assert min_head > .015 and min_sleeve > .015, ('cuello vs. cabeza y mangas', min_head, min_sleeve)
    print(f'{count} poses geométricas; solape mínimo costura/raíz {laps[0]:.3f}/{laps[1]:.3f}u; '
          f'holgura mínima del cuello a cabeza/mangas {min_head:.3f}/{min_sleeve:.3f}u.')
    print(f'Capa exterior de la piel: envolvente mínima {min_hat:+.3f}u, {hat_contacts} contactos posibles. '
          'Confirmar su visibilidad con una textura real en F5.')


if __name__ == '__main__':
    audit()
