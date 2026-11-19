#!/usr/bin/env python3
"""Check the widened wearer join in model pixels, not camera space."""
from itertools import product

import numpy as np

import armor_model_pipeline as G
import cape_fit as F
import preview_cloth as P
from verify_v1640 import overlap
from verify_v1600 import sat


def check(geo):
    parts = {b['name']: b for b in geo['bones']}
    names = (G.SEAT_BONE, G.GUSSET_BONE, G.SADDLE_BONE)
    assert tuple(parts[n]['parent'] for n in names) == ('chestplate','chestplate',G.FIT_BONE)
    matrices = P.matrices(geo)
    seat, yoke, saddle = (np.array([P.cube_points(c, matrices[n]) for c in parts[n]['cubes']]) for n in names)
    fit = F.profile()
    max_depth = np.max(fit['backset'])
    stretch = lambda v,d: (v-G.MOUNT_PIVOT)*[1.,1.,1.+d/fit['gussetDepth']] + G.MOUNT_PIVOT
    # All the centre panels cross the same two lateral coordinates. With
    # X-only folds, their overlap in the YZ plane extends across this width.
    spine = np.concatenate((seat,yoke))
    width = 2*min(spine[...,0].max(1).min(), -spine[...,0].min(1).max())
    assert width >= 6.8, width  # the old 4.4u gusset fails across the torso
    torso = P.CORNERS*[8,12,4] + [-4,12,-2]
    bed = overlap(seat[:1],torso[None])[0,0]
    assert .02 < bed < .09
    worst = float('inf')
    for d in np.linspace(0,max_depth,101):
        a,b,c = stretch(yoke,d)
        # Not just a single contact point: continuous from the plate,
        # through both yoke folds, and into *both* fitted cuff roots.
        seams = [overlap(seat[:1],a[None])[0,0],
                 overlap(a[None],b[None])[0,0], overlap(b[None],c[None])[0,0],
                 *overlap(c[None],saddle[1:3] + [0.,0.,d])[0]]
        worst = min(worst, *seams)
    assert worst > .12, worst

    poses = list(product(np.linspace(0,1,9), np.linspace(-90,90,49), np.linspace(-90,90,49)))
    d = np.array([F.depth(*pose) for pose in poses])
    head = np.array([F.head_in_body(*pose,outer=True) for pose in poses])
    scale = np.column_stack((np.ones_like(d),np.ones_like(d),1+d/fit['gussetDepth']))[:,None,:]
    eye = min(*[sat(np.broadcast_to(v,head.shape),head).min() for v in seat],
              *[sat((v-G.MOUNT_PIVOT)*scale+G.MOUNT_PIVOT,head).min() for v in yoke])
    # Allow the existing tiny contact at the limit of the inflated hat
    # when deeply crouched and looking straight up; not a new head bite.
    assert eye > -.04, eye
    arm_boxes = []
    for stance,swing in product(np.linspace(0,1,7),np.linspace(-60,60,61)):
        matrices = F.mannequin_pose(stance,0,0,arm_swing=(swing,-swing))
        inv = np.linalg.inv(matrices[1])
        for (o,s,_),m in zip(P.MANNEQUIN_BOXES[2:4],matrices[2:4],strict=True):
            # Jacket and sleeves, not only the base skin layer.
            transform = inv @ m
            box = np.array(o)-.25 + P.CORNERS*(np.array(s)+.50)
            arm_boxes.append(box @ transform[:3,:3].T + transform[:3,3])
    arms = np.array(arm_boxes)
    arm = min(sat(np.broadcast_to(v,arms.shape),arms).min()
              for k in np.linspace(0,max_depth,13)
              for v in np.concatenate([seat,stretch(yoke,k)]))
    assert arm > .08, arm
    print(f'Anclaje: costura continua {width:.2f}/8u de torso; solape ≥{worst:.3f}u en ambos lados, '
          f'margen de mangas {arm:.3f}u, capa exterior de cabeza {eye:+.3f}u en {len(poses)} posturas.',flush=True)


if __name__ == '__main__':
    check(P.load(P.ARMOR_GEO))
