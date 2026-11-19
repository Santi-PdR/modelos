#!/usr/bin/env python3
"""Check actual shirt contact at the upper yoke, before projecting to F5."""
from itertools import product

import numpy as np

import armor_model_pipeline as G
import cape_backing as B
import cape_fit as F
import preview_cloth as P
from verify_v1600 import sat


def sleeve_envelopes():
    sleeves = []
    for slim,stance,swing,roll in product((False,True),np.linspace(0,1,7),np.linspace(-60,60,81),(-3.4,0,3.4)):
        m = F.mannequin_pose(stance,0,0,arm_swing=(swing,swing))
        inv = np.linalg.inv(m[1])
        for i,((o,s,_),arm) in enumerate(zip(P.MANNEQUIN_BOXES[2:4],m[2:4],strict=True)):
            o,s = np.array(o,float),np.array(s,float)
            p = np.array([-5 if i==0 else 5,22-3.2*stance,0.])
            if slim:
                o += [1 if i==0 else 0,-.5,0]
                s[0] -= 1
            tf = inv@P.T(p)@P.R('z',roll)@P.T(-p)@arm
            box = o-.25 + P.CORNERS*(s+.5)
            sleeves.append(box@tf[:3,:3].T+tf[:3,3])
    return np.asarray(sleeves)


def patches(geo):
    matrices = P.matrices(geo)
    return {b['name']: np.asarray([P.cube_points(c,matrices[b['name']]) for c in b.get('cubes',[])])
            for b in geo['bones']}


def occupied(boxes, points):
    result = np.zeros(len(points),dtype=bool)
    for v in boxes:
        coords = (points-v[0])@np.linalg.inv(v[[1,3,4]]-v[:1])
        result |= ((coords >= -1e-9) & (coords <= 1+1e-9)).all(1)
    return float(result.mean())


def lap(cube, mesh):
    return float(-sat(np.broadcast_to(cube,mesh.shape),mesh).min())


def check(geo):
    f = B.profile()
    names = f['names']
    bones = {b['name']:b for b in geo['bones']}
    assert all(n in bones and bones[n]['parent']=='chestplate' for n in names), 'missing upper back mounts'
    local = patches(geo)
    panels = np.stack([local[n] for n in names])
    assert panels.shape == (2,3,8,3)
    p = np.asarray(f['pivot'])
    seat, gusset, saddle = [local[n] for n in (G.SEAT_BONE,G.GUSSET_BONE,G.SADDLE_BONE)]
    prior = np.concatenate([seat,gusset,saddle,local[G.UNDER_YOKE_BONE]])
    # Skin plane plus the jacket layer: this is above the old mounting seat.
    # Check solid cloth *at the shirt*, not its projected outline or shadow.
    strip = np.array(list(product(np.linspace(-2.85,2.85,31),np.linspace(19.65,20.91,8),[2.251])))
    assert occupied(prior,strip) == 0, 'the legacy seat should miss the upper shirt'
    seam = np.inf
    for pose in ((0,-89,0),(0,-58,43),(0,-58,-43),(0,-21,76),(0,-21,-76),(0,0,0)):
        d = F.depth(*pose)
        left,right,z = B.solve(F.head_in_body(*pose,outer=True),d)
        fitted = (panels-p)*np.array([[1,left,z],[1,right,z]])[:,None,None,:]+p
        assert occupied(fitted.reshape(-1,8,3),strip) >= .97, pose
        if pose[1] == -21:
            section = np.array(list(product([0],np.linspace(21.87,22.57,8),np.linspace(2.775,3.585,31))))
            assert occupied(prior,section) == 0, 'the old collar does not reach the section'
            assert occupied(fitted.reshape(-1,8,3),section) >= .97, pose
        spine = np.concatenate(((gusset-G.MOUNT_PIVOT)*[1,1,1+d/F.profile()['gussetDepth']]+G.MOUNT_PIVOT,
                                saddle + [0,0,d]))
        for a,b,c in fitted:
            seam = min(seam,lap(a,seat),lap(a,b[None]),lap(a,c[None]),lap(b,spine),lap(c,spine))
    assert seam > .65, seam
    # The backing folds entirely into the vanilla torso when supplying
    # clearance for wings; none can peek past the jacket or sleeve.
    l,r,z = B.solve(F.head_in_body(1,50,70,outer=True),F.depth(1,50,70),elytra=True)
    tuck = (panels-p)*np.array([[1,l,z],[1,r,z]])[:,None,None,:]+p
    assert np.all(tuck > [-4,12,-2]) and np.all(tuck < [4,24,2])
    head_poses = list(product(np.linspace(0,1,9),np.linspace(-90,90,61),np.linspace(-180,180,121)))
    head_gap = np.inf
    for start in range(0,len(head_poses),4096):
        poses = head_poses[start:start+4096]
        head = np.array([F.head_in_body(*aim,outer=True) for aim in poses])
        scales = B.solve(head,[F.depth(*aim) for aim in poses])
        for i in range(2):
            s = np.column_stack([np.ones(len(poses)),scales[:,i],scales[:,2]])[:,None,:]
            head_gap = min(head_gap,*(sat((v-p)*s+p,head).min() for v in panels[i]))
    assert head_gap > .085, head_gap
    arms = sleeve_envelopes()
    arm_gap = np.inf
    # Mirrored halves plus independent head, arm and roll sweeps. The wing
    # pose is already inside the torso, so only the exposed ranges matter.
    for y,z in product(np.linspace(f['tuckY'],1,12),np.linspace(f['tuckZ'],1+f['maxBackset']/f['span'],12)):
        for box in (panels[0]-p)*[1,y,z]+p:
            arm_gap = min(arm_gap,sat(np.broadcast_to(box,arms.shape),arms).min())
    assert arm_gap > .01, arm_gap
    print(f'Espalda alta: contacto en 5.7u de camiseta, solape de las costuras ≥{seam:.3f}u; '
          f'cabeza +{head_gap:.3f}u ({len(head_poses)} poses), mangas Steve/Alex +{arm_gap:.3f}u. '
          'Con élitros, el respaldo queda dentro del torso.',flush=True)


if __name__ == '__main__':
    check(P.load(P.ARMOR_GEO))
