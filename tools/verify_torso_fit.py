#!/usr/bin/env python3
"""Validate the historical torso fit without using a camera as an input."""
from itertools import product
import json
import math
import subprocess
import sys

import numpy as np

import armor_model_pipeline as G
import cape_animation_pipeline as A
import cape_backing as B
import cape_fit as F
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_cape_backing import patches
from verify_cape_seat import wardrobe
from verify_v1600 import interpolate
from verify_v1660 import WornModel, contacts


def placement(geo):
    for aim in [(0.,-58.,43.), (0.,-48.,-48.), (0.,-89.5,0.)]:
        old, new = [patches(F.wearer_pose(geo,*aim,torso=t)) for t in (False,True)]
        outer = lambda m: -min(m[n][...,0].min() for n in ('v18_pad_1','rim_v18_pad_1') if n in m)
        cowl = lambda m: np.concatenate([v for n,v in m.items() if n.startswith('v17_cowl_back_')])
        before, after = cowl(old), cowl(new)
        if aim[1] > -80:
            assert 6.0 < outer(new) < 7.20 and outer(old)-outer(new) > 2.55, aim
            roots = [n for n in new if n.startswith('v17_ribbon_') and n.endswith('_seg0')]
            assert np.mean([old[n][...,2].min()-new[n][...,2].min() for n in roots]) > .39, aim
            assert before[...,2].min()-after[...,2].min() > 1.75, aim
        else:
            # Keep the leading rim against the sleeve as the rear contracts.
            old_rim,new_rim = (m['rim_v18_pad_1'][...,2] for m in (old,new))
            assert abs(old_rim.min()-new_rim.min()) < .045 and old_rim.max()-new_rim.max() > .15, aim
            assert np.array_equal(old['v18_pad_0'],new['v18_pad_0']), aim
            assert before[...,2].min()-after[...,2].min() > .95, aim
        assert before[...,1].max()-after[...,1].max() >= 1.75, aim
        print(f'{aim[1]:g}°/{aim[2]:+g}°: ancho parcial {outer(old):.2f} → {outer(new):.2f}u; '
              f'delante del cuello {before[...,2].min():.2f} → {after[...,2].min():.2f}u.')


def safe(geo):
    rig = WornModel(geo)
    clips = json.loads(A.ANIM.read_text())['animations']
    frames = [P.pose_at(geo,T.prepare_clip(c),c['animation_length']*t) for c,t in product(clips.values(),(.10,.48,.81))]
    frames += [interpolate(a,b,.5) for a,b in zip(frames[::3],frames[2::3][1:]+frames[2:3],strict=True)]
    still = [(xyz,geo,(a,-a),(0.,0.)) for xyz,a in product(
        product((0.,.12,.26,.42,1.),(-89.5,-79,-67,-58,-48,-38,-27,-13,0,8,23,35),
                (0,-18,28,-36,43,-48,57,-69,80,86)),(0.,-4.6,8.,-19.,32.))]
    gait = [(aim,g,*S.gait(t,amp)) for aim,g,amp,t in product(
        ((0,-58,43),(0,-48,-48),(0,-79,16),(.12,-43,48),(0,8,0)),frames,(.35,.75),(0.,.25,.65))]
    internal = np.asarray([n.startswith('v20_mount_') for n in rig.names])
    minima = (.5,.5)
    count = 0
    for aim,g,arms,legs in still+gait:
        arm,leg = S.demand(aim[0],arms,legs)
        # Vanilla sleeves have both the locomotion envelope and a small roll;
        # use both 3u and 4u sleeves with their .25u jacket dilation.
        effort = max(arm, *(abs(a+math.degrees(.4*aim[0])) for a in arms))
        frame = S.adjust(g,arm,leg,aim) if g is not geo else geo
        verts = [rig.place(P.matrices(F.wearer_pose(frame,*aim,arm_back=arm,arm_effort=effort,torso=t))) for t in (False,True)]
        if np.array_equal(*verts):
            continue
        box = wardrobe(aim,arms,legs)
        before, now = (contacts(v[None],box,pad=.30)[0] for v in verts)
        # Intentional overlap of the mount with the shirt, never the head.
        worse = (now < -.013) & (now < before-.025)
        worse[1,internal] = False
        if worse.any():
            issues = [(j,rig.names[k],float(before[j,k]),float(now[j,k])) for j,k in zip(*np.where(worse),strict=True)]
            raise AssertionError((aim,arms,legs,issues))
        minima = tuple(map(min,zip(minima,rig.joins(verts[1]),strict=True)))
        count += 1
    assert count >= 2900 and minima[0] > .038 and minima[1] > .025, (count,minima)
    for aim in ((0.,-58.,43.),(.33,-76.,3.),(0.,-89.5,0.)):
        assert F.wearer_pose(geo,*aim,elytra=True) == F.wearer_pose(geo,*aim,elytra=True,torso=False)
    print(f'{count} poses nuevas: sin cruces nuevos de cabeza y mangas dentro de 0.025u; '
          f'costuras/raíces ≥{minima[0]:.3f}/{minima[1]:.3f}u; perfil de alas intacto.')


def viewer(data):
    run = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,check=True,text=True,
                         capture_output=True,input=json.dumps(dict(fit=F.viewer_profile(),**data)))
    return np.asarray(json.loads(run.stdout))


def matrix_parity(geo):
    names = [G.FIT_BONE, G.DRAPE_BONE, G.SHOULDERS_BONE, G.SADDLE_BONE, 'cape_top',
             'v17_ribbon_1_seg0', 'v17_cowl_back_2', 'v17_cowl_tooth_5', 'v17_cowl_return',
             'v18_pad_0', 'v18_pad_1', 'rim_v18_pad_0', 'rim_v18_pad_1', *B.profile()['names']]
    aims = list(product((0.,.12,.42),((-89.5,0),(-76,3),(-58,43),(-48,-48),(-35,316),(8,0)),
                        (False,True),(0.,4.1,17.)))
    samples = [(s,p,y,w,a,a+1.15) for s,(p,y),w,a in aims]
    expected = []
    for s,p,y,w,a,e in samples:
        mats = P.matrices(F.wearer_pose(geo,s,p,y,elytra=w,arm_back=a,arm_effort=e))
        expected.append([mats.get(n,mats[n.removeprefix('rim_')]).ravel() for n in names])
    np.testing.assert_allclose(viewer(dict(geo=geo,torsoMatrices=samples,parts=names)),expected,rtol=0,atol=2e-9)
    print(f'{len(samples)} matrices de la montura, placas, luz y raíces coinciden con el visor.')


def parity(path):
    rows = np.loadtxt(path)
    assert rows.shape == (5*11*10*4*3,44), rows.shape
    params = rows[:,:7].tolist()
    js = viewer(dict(torsoSamples=params))
    staged = []
    for s,p,y,arm,effort,dry,w in params:
        w = bool(w)
        previous = F.seating(s,p,y,arm,elytra=w)*dry
        plate = float(np.float32(F.plate_influence(s,p,y,effort,elytra=w)))*dry
        seat, *affines = F.torso_shape(s,p,y,F.depth(s,p,y),previous,plate,arm,effort,dry,w)
        staged.append([seat,*[v for a in affines for v in (a if a is not None else [0,0,0,0,0,0,1,1,1])]])
    rounded = np.asarray(staged,dtype=np.float32).astype(float)
    assert np.allclose(rounded,rows[:,7:],rtol=0,atol=1.5e-7), abs(rounded-rows[:,7:]).max()
    assert np.allclose(staged,js,rtol=0,atol=2.6e-7)
    print(f'Montura histórica: {len(rows)} muestras Java / Python / visor coinciden.')


if __name__ == '__main__':
    if len(sys.argv) == 2:
        parity(sys.argv[1])
    else:
        geo = P.load(P.ARMOR_GEO)
        placement(geo)
        matrix_parity(geo)
        safe(geo)
