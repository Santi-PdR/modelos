#!/usr/bin/env python3
"""Check the visible fit against the uncompressed v1.67.8 rig.

Uses inflated 1.20.1 player hulls in model pixels. The separate Forge test
checks visibility and offset in F5, not just these geometric distances.
"""
from hashlib import sha256
from itertools import product
import json

import numpy as np

import armor_model_pipeline as G
import cape_animation_pipeline as A
import cape_backing as B
import cape_fit as F
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_cape_backing import lap, occupied, patches
from verify_v1600 import interpolate
from verify_v1660 import WornModel, contacts


def preservation(geo):
    frame = F.seat_profile()['frame']
    parts = {b['name']:b for b in geo['bones']}
    assert parts[frame] == G.bone(frame,'chestplate',(0,24,F.seat_profile()['plane']),(0,0,0),[])
    control = dict(geo,bones=[dict(b,parent='chestplate') if b.get('parent') == frame else b
                              for b in geo['bones'] if b['name'] not in (frame,*B.profile()['names'])])
    digest = sha256(json.dumps(control,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert digest == '02fedd26c50b04b3f049e5a88101ba217350297c48a9706499b0961d6b548829', 'cambiaron piezas fuera del respaldo'
    for path,expected in {
        A.ANIM: '23d1e0bb43123b4b86cea4e5f07e672ae5bd1d89e2cb5d4cc71c52409f968999',
        P.ARMOR_TEX: 'a4cf984ead41c6ac8a0a3b09e86743786ef9c71f3d00fc109934b8bca589e549',
        P.ICON: 'b1ef3f05ee5a18a821987fc5f73734700d6721bbb4aad2456c759506aa285b2b',
        P.ICON.with_suffix('.png.mcmeta'): '332b622d2f3ea535c4ba8c1480bbfcf5d1053b61c44682cfeee918fbeb366d6b',
    }.items():
        assert sha256(path.read_bytes()).hexdigest() == expected, path


def visible_shift(geo):
    # Pose chosen to approximate the reported F5 view (not a camera input to
    # the fit). Measure the real outer collar/plates/cloth roots, not the tabs.
    aim = (0.,-76.,3.)
    old,new = (patches(F.wearer_pose(geo,*aim,close=close)) for close in (False,True))
    def center(parts, prefix):
        return np.concatenate([v for k,v in parts.items() if k.startswith(prefix)])[...,2].mean()
    trim = ('v17_cowl_back_', 'v18_pad_0', 'v18_pad_1', 'v18_chain_')
    advance = [center(old,k)-center(new,k) for k in trim]
    root = [old[k][...,2].mean()-new[k][...,2].mean() for k in new
            if k.startswith('v17_ribbon_') and k.endswith('_seg0')]
    assert min(advance) > 1.05 and advance[0] > 1.9 and min(root) > .70, (advance,root)
    stripe = np.array(list(product(np.linspace(-2.85,2.85,31),np.linspace(19.65,20.91,8),[2.251])))
    panels = np.concatenate([new[n] for n in B.profile()['names']])
    assert occupied(panels,stripe) >= .98, 'el marco ya no toca la camiseta alta'
    seams = [lap(t,new[f'v18_pad_{i}']) for i,t in enumerate(new[G.SHOULDERS_BONE])]
    assert min(seams) > .14, seams
    for pose,wings,arm in [((0,0,0),False,0), ((0,-76,3),True,0), ((0,-76,3),False,17),
                           ((1,-76,3),False,0), ((0,-76,-74),False,0)]:
        assert F.seating(*pose,arm,elytra=wings) == 0
    print(f'El propio borde se acerca: cuello {advance[0]:.2f}u, placas {advance[1]:.2f}/{advance[2]:.2f}u, '
          f'costura {advance[3]:.2f}u, nacimiento de la tela ≥{min(root):.2f}u; contacto entero con la camiseta.',flush=True)


def wardrobe(aim, arms, legs):
    st,p,y = aim
    _,torso,*limbs = F.mannequin_pose(st,p,y,arms,legs)
    def box(o,s,m):
        return (np.asarray(o)-.25+P.CORNERS*(np.asarray(s)+.50)) @ m[:3,:3].T + m[:3,3]
    head = F.head_in_body(*aim,outer=True) @ torso[:3,:3].T + torso[:3,3]
    body = box(*P.MANNEQUIN_BOXES[1][:2],torso)
    poses = [head,body]
    for slim,roll,i in product((False,True),(-5.75,0.,5.75),range(2)):
        o,s,_ = P.MANNEQUIN_BOXES[2+i]
        if slim:
            o,s = np.asarray(o)+[1 if i==0 else 0,-.5,0],np.asarray(s)-[1,0,0]
        pivot = np.array([-5 if i==0 else 5,22-3.2*st,0])
        m = P.T(pivot) @ P.R('z', roll if i==0 else -roll) @ P.T(-pivot) @ limbs[i]
        poses.append(box(o,s,m))
    for i in range(2):
        o,s,_ = P.MANNEQUIN_BOXES[4+i]
        poses.append(box(np.asarray(o)+[.1 if i==0 else -.1,0,0],s,limbs[2+i]))
    return np.array(poses)[None]


def moderate_fit(geo):
    # This frame stayed completely open in 1.67.9. Keep the actual cowl
    # and pads nearer without adding a cube or closing the free hem.
    aim = (0.,-58.,3.)
    old,new = (patches(F.wearer_pose(geo,*aim,close=close)) for close in (False,True))
    def depth(parts, prefix):
        return np.concatenate([v for k,v in parts.items() if k.startswith(prefix)])[...,2].mean()
    d = [depth(old,k) - depth(new,k) for k in ('v17_cowl_back_', 'v18_pad_0', 'v18_pad_1')]
    assert .39 < F.seating(*aim) < .43 and d[0] >= .90 and min(d[1:]) >= .46, d
    assert F.seating(0.,-42.,3.) == 0 and F.seating(*aim,arm_back=10.) == 0
    seam = min(lap(t,new[f'v18_pad_{i}']) for i,t in enumerate(new[G.SHOULDERS_BONE]))
    assert seam > .17, seam
    print(f'A 58°: cuello {d[0]:.2f}u, hombreras {d[1]:.2f}/{d[2]:.2f}u más cerca; '
          f'los remates conservan ≥{seam:.2f}u de solape.',flush=True)


def clearance(geo, clips):
    rig = WornModel(geo)
    fasteners = np.array([n.startswith('v20_mount_') for n in rig.names])
    def placed(frame,aim,arm,close):
        mats = P.matrices(F.wearer_pose(frame,*aim,arm_back=arm,close=close))
        packed = np.array([mats[n] for n in rig.names])
        return rig.coords @ packed[:,:3,:3].transpose(0,2,1) + packed[:,None,:3,3]
    samples = {n:[P.pose_at(geo,T.prepare_clip(c),c['animation_length']*t) for t in (0,.33,.67)]
               for n,c in clips.items()}
    moving = [(n,f) for n,frames in samples.items() for f in frames]
    moving += [(f'{a} → {b}',interpolate(samples[a][-1],samples[b][0],.5))
               for a,b in zip(samples,list(samples)[1:]+[next(iter(samples))],strict=True)]
    still = [(aim,'reposo',geo,(a,-a),(0.,0.)) for aim,a in product(
              product((0.,.18,.39,.60),(-50.,-54.,-58.,-63.,-68.,-76.,-89.),(-43.,-25.,-8.,3.,18.,38.)),(0.,3.9,-6.7))]
    in_motion = [(aim,name,f,arms,legs) for aim,(name,f),(arms,legs) in product(
        [(0.,-54.,3.),(.18,-58.,-18.),(0.,-76.,3.),(0.,-68.,-15.),(.19,-87.,23.),(.33,-77.,-8.)],moving,
        [((0.,0.),(0.,0.)), ((4.,-4.),(17.,-17.)), ((-6.,6.),(-20.,20.))])]
    count = 0
    clearance = .5
    stitch = (.5,.5)
    for aim,name,frame,arms,legs in still+in_motion:
        arm,leg = S.demand(aim[0],arms,legs)
        if F.seating(*aim,arm) <= 0:
            continue
        pose = S.adjust(frame,arm,leg,aim)
        boxes = wardrobe(aim,arms,legs)
        before,after = (placed(pose,aim,arm,close) for close in (False,True))
        was,now = (contacts(v[None],boxes,pad=.5)[0] for v in (before,after))
        assert now[0].min() > .025, (name,aim,arms,now[0].min(),rig.names[now[0].argmin()])
        # Contact of the internal fastener with the shirt is intentional.
        # Existing near-tangencies at cuffs can stay; don't add an intrusion.
        regressed = (now[1:] < -.013) & (was[1:] >= -.013)
        regressed[0,fasteners] = False
        assert not regressed.any(), (name,aim,arms,[(int(b),rig.names[i],now[b+1,i],was[b+1,i])
                                                    for b,i in zip(*np.where(regressed),strict=True)])
        clearance = min(clearance,float(now[0].min()))
        stitch = tuple(map(min, zip(stitch,rig.joins(after),strict=True)))
        count += 1
    assert stitch[0] > .038 and stitch[1] > .025, stitch
    print(f'{count} poses ceñidas (Steve/Alex, clips y mezclas): cabeza ≥{clearance:.3f}u, '
          f'sin cruces nuevos; solape de costuras/raíces ≥{stitch[0]:.3f}/{stitch[1]:.3f}u.',flush=True)


if __name__ == '__main__':
    geo = P.load(P.ARMOR_GEO)
    preservation(geo)
    visible_shift(geo)
    moderate_fit(geo)
    clearance(geo,json.loads(A.ANIM.read_text())['animations'])
