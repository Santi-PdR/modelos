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
    shoulders = parts.get(G.SHOULDERS_BONE)
    assert (.39 < bed < .44) if shoulders else (.02 < bed < .09), bed
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
        pose_mats = F.mannequin_pose(stance,0,0,arm_swing=(swing,-swing))
        inv = np.linalg.inv(pose_mats[1])
        for (o,s,_),m in zip(P.MANNEQUIN_BOXES[2:4],pose_mats[2:4],strict=True):
            # Jacket and sleeves, not only the base skin layer.
            transform = inv @ m
            box = np.array(o)-.25 + P.CORNERS*(np.array(s)+.50)
            arm_boxes.append(box @ transform[:3,:3].T + transform[:3,3])
    arms = np.array(arm_boxes)
    arm = min(sat(np.broadcast_to(v,arms.shape),arms).min()
              for k in np.linspace(0,max_depth,13)
              for v in np.concatenate([seat,stretch(yoke,k)]))
    assert arm > .08, arm
    if shoulders:
        returns_fit(parts, matrices, max_depth)
    if G.UNDER_YOKE_BONE in parts:
        lining_fit(parts, matrices, seat[0], yoke[0], max_depth)
    print(f'Anclaje: costura continua {width:.2f}/8u de torso; solape ≥{worst:.3f}u en ambos lados, '
          f'margen de mangas {arm:.3f}u, capa exterior de cabeza {eye:+.3f}u en {len(poses)} posturas.',flush=True)


def returns_fit(parts, mats, max_depth):
    """Shape-specific test; no phase may disconnect a return from its pad."""
    piece = parts[G.SHOULDERS_BONE]
    assert piece['parent'] == G.FIT_BONE and len(piece['cubes']) == 2
    pivot = np.array(piece['pivot']) * [-1,1,1]
    tabs = [P.cube_points(c,mats[piece['name']]) for c in piece['cubes']]
    pads = [np.array([P.cube_points(c,mats[f'v18_pad_{i}'])
                      for c in parts[f'v18_pad_{i}']['cubes']]) for i in range(2)]
    poses = list(product(np.linspace(0,1,9), np.linspace(-90,90,81), np.linspace(-90,90,81)))
    d = np.array([F.depth(*pose) for pose in poses])
    scale = np.array([F.shoulder_scales(*pose) for pose in poses])[:,None,:]
    head = np.array([F.head_in_body(*pose,outer=True) for pose in poses])
    eye = min(sat((v-pivot)*scale+pivot+d[:,None,None]*[0.,0.,1.],head).min() for v in tabs)
    assert eye > .028, eye
    lap = min(overlap(((v-pivot)*[1,.27+.73*k,k]+pivot)[None],p).max()
              for v,p in zip(tabs,pads,strict=True) for k in np.linspace(.245,1.,91))
    assert lap > .15, lap
    # 4px Steve and 3px Alex sleeves, including the outer layer.
    bins = []
    for slim,stance,swing in product((False,True), np.linspace(0,1,7), np.linspace(-60,60,57)):
        m = F.mannequin_pose(stance,0,0,arm_swing=(swing,swing))
        inverse = np.linalg.inv(m[1])
        for i,((origin,size,_),arm) in enumerate(zip(P.MANNEQUIN_BOXES[2:4],m[2:4],strict=True)):
            o,sz = np.array(origin,dtype=float),np.array(size,dtype=float)
            if slim:
                o += [1 if i==0 else 0,-.5,0]
                sz[0] -= 1
            tf = inverse@arm
            v = o-.25+P.CORNERS*(sz+.5)
            bins.append(v@tf[:3,:3].T+tf[:3,3])
    arms = np.array(bins)
    clearance = float('inf')
    for k,d in product(np.linspace(.245,1,16), np.linspace(0,max_depth,8)):
        for v in tabs:
            point = (v-pivot)*[1,.27+.73*k,k]+pivot+[0,0,d]
            clearance = min(clearance, sat(np.broadcast_to(point,arms.shape),arms).min())
    # Upper edge may graze the inflated sleeve, never cut across its core.
    assert clearance > -.055, clearance
    # Two visible bridges over the sleeves in the relaxed F5 poses, as
    # opposed to a wider attachment only in the middle of the back.
    for v in tabs:
        assert v[...,2].min() < 2.06 and v[...,2].max() > 5.50
        assert np.ptp(v[...,0]) > 2.0
    assert F.shoulder_scales(0,-89,43)[-1] == 1
    print(f'Remates: ambos cosidos a la hombrera ≥{lap:.3f}u; cabeza ≥{eye:.3f}u en {len(poses)} poses, '
          f'mangas Steve/Alex {clearance:+.3f}u (incluido el borde exterior).',flush=True)


def lining_fit(parts, mats, seat, lower_gusset, max_depth):
    piece = parts[G.UNDER_YOKE_BONE]
    assert piece['parent'] == 'chestplate' and len(piece['cubes']) == 1
    pivot = np.array(piece['pivot']) * [-1,1,1]
    v = P.cube_points(piece['cubes'][0],mats[piece['name']])
    pose = lambda scales: (v-pivot)*np.asarray(scales)[...,None,:]+pivot
    torso = P.CORNERS*[8,12,4] + [-4,12,-2]
    extended = F.yoke_scales(0,-89,2.86)
    assert extended == F.yoke_scales(0,-86,2.86) == [1.,1.,1.]
    contracted = pose(F.yoke_scales(0,-89,0,elytra=True))
    # The fully tucked lining occupies the *existing* seat/gusset volume.
    # The front stays within the seat even at maximum backset; the back
    # stays within the lowest gusset segment, never reaching the wings.
    a,b = contracted.min(0),contracted.max(0)
    gusset_start = G.MOUNT_PIVOT[2] + (lower_gusset[:,2].min()-G.MOUNT_PIVOT[2])*(1+max_depth/F.profile()['gussetDepth'])
    assert np.all(a[:2] > np.maximum(seat.min(0),lower_gusset.min(0))[:2])
    assert np.all(b[:2] < np.minimum(seat.max(0),lower_gusset.max(0))[:2])
    assert seat[:,2].min() < a[2] < gusset_start < seat[:,2].max()
    assert b[2] < lower_gusset[:,2].max()
    for arm_back in np.linspace(2.9,6.1,51):
        assert overlap(pose(F.yoke_scales(0,-89,arm_back))[None],torso[None]).item() > .05
    angles = list(product(np.linspace(0,1,9),np.linspace(-90,90,61),np.linspace(-90,90,61)))
    h = np.array([F.head_in_body(*aim,outer=True) for aim in angles])
    head_clear = min(sat(pose([F.yoke_scales(st,pitch,arm) for st,pitch,_ in angles]),h).min()
                     for arm in (0,4,4.9,5.4,5.9,6.1))
    assert head_clear > .18, head_clear
    # The relaxed liner beds just under the sleeves, like the seat in the
    # torso. Its edge must not pierce a sleeve wall during gait or lean.
    normal,core,scales = [],[],[]
    for slim,stance,swing,roll in product((False,True),np.linspace(0,1,7),np.linspace(-60,60,121),(-3.4,0,3.4)):
        t = F.mannequin_pose(stance,0,0,arm_swing=(swing,swing))
        inv = np.linalg.inv(t[1])
        for side,((o,s,_),arm) in enumerate(zip(P.MANNEQUIN_BOXES[2:4],t[2:4],strict=True)):
            o,s = np.array(o,dtype=float),np.array(s,dtype=float)
            if slim:
                o += [1 if side==0 else 0,-.5,0]
                s[0] -= 1
            p = np.array([-5 if side==0 else 5,22-3.2*stance,0.])
            m = inv @ P.T(p) @ P.R('z',roll) @ P.T(-p) @ arm
            skin = o-.25 + P.CORNERS*(s+.5)
            rear_trimmed = o-.25 + P.CORNERS*(s+[.50,.50,-.32])
            normal.append(skin@m[:3,:3].T+m[:3,3])
            core.append(rear_trimmed@m[:3,:3].T+m[:3,3])
            scales.append(F.yoke_scales(stance,0,swing+np.degrees(.4)*stance))
    states = pose(scales)
    graze = sat(states,np.array(normal)).min()
    clearance = sat(states,np.array(core)).min()
    assert graze > -.70 and clearance > .035, (graze,clearance)
    print(f'Forro interior: solape con torso en todo el recorrido; cabeza +{head_clear:.3f}u, '
          f'holgura bajo la unión de mangas +{clearance:.3f}u. Se aloja dentro del fuelle con élitros.',flush=True)


if __name__ == '__main__':
    check(P.load(P.ARMOR_GEO))
