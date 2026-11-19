#!/usr/bin/env python3
"""Check the worn mount, animation joins and locked v1.63.0 exterior.

All fit tests run in model pixels (16 per block) with Minecraft 1.20.1 part
pivots. They are numerical/renderer regressions, not a live Forge playtest.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import itertools
import json

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_fit as F
import cape_material as C
import cape_motion as M
import preview_cloth as P
from present_v1640 import BASE, OLD_GEO, OLD_TEX, OLD_CLIPS
from verify_v1590 import check_editor, check_tracks
from verify_v1600 import iou, registered_metrics, sat
from verify_v1610 import pose_samples, visor_fit
from verify_v1620 import GLOW, visor_material
from verify_v1630 import visor_embers


def preservation(geo, atlas, light):
    for line in (BASE / 'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        ref = BASE / name
        assert sha256(ref.read_bytes()).hexdigest() == digest, name
        changes = {P.ARMOR_GEO, A.ANIM, P.ICON}
        current = P.ASSETS/name
        if current.is_file() and current not in changes and not name.startswith('lang/'):
            assert current.read_bytes() == ref.read_bytes(), name
    old = P.load(OLD_GEO)
    new = {b['name']: b for b in geo['bones']}
    assert old['description'] == geo['description']
    assert new['cape_top']['parent'] == G.DRAPE_BONE
    for b in old['bones']:
        expect = dict(b,parent=G.DRAPE_BONE) if b['name']=='cape_top' else b
        assert expect == new[b['name']], b['name']
    assert new[G.DRAPE_BONE]['parent'] == new[G.SADDLE_BONE]['parent'] == G.FIT_BONE
    assert new[G.SEAT_BONE]['parent'] == new[G.GUSSET_BONE]['parent'] == 'chestplate'
    f = F.profile()
    assert np.isclose(new[G.SADDLE_BONE]['pivot'][2] - new[G.GUSSET_BONE]['pivot'][2], f['gussetDepth'])
    for p, expected in ((P.ARMOR_TEX,atlas),(GLOW,light)):
        got = np.asarray(Image.open(p).convert('RGBA'))
        assert np.array_equal(got,np.asarray(expected))
        assert np.array_equal(got,np.asarray(Image.open(BASE/p.relative_to(P.ASSETS)).convert('RGBA')))
    (was,now),_ = registered_metrics(old,geo,atlas,baseline_atlas=OLD_TEX)
    exterior = iou(was['match'],now['match'])
    assert exterior > .996 and now['all'] > .952 and now['mae'] < 1.65
    assert now['lower'] >= was['lower']-.0005 and now['seam'] >= was['seam']-.001
    print(f'Exterior original: {exterior:.2%} de coincidencia con v1.63; '
          f'IoU {now["all"]:.2%} con el PNG, RGB {now["mae"]:.2f}/255. Atlas y emisión intactos.',flush=True)


def motion(geo, runtime, bb):
    old = json.loads(OLD_CLIPS.read_text())
    hidden = P.effective_hidden(geo)
    for key,clip in runtime['animations'].items():
        prev = old['animations'][key]
        active = {n for n in clip['bones'] if n not in hidden or n in M.SECTIONS}
        assert active == {b['name'] for b in geo['bones'] if A.animated(b['name'])}
        assert all(set(clip['bones'][n]) == {'rotation'} for n in active)
        assert all(t == prev['bones'][n] for n,t in clip['bones'].items() if n not in active)
        # Existing comparison checks the durations, UUID values, smoothing
        # tangents, cyclic endpoints and runtime/editor sample equivalence.
        prev['bones'] = {n:t for n,t in prev['bones'].items()
                         if n not in active and not n.startswith(A.RETIRED)}
    M._self_test()
    check_tracks(runtime,old,bb)


def pairing(left,right):
    return list(itertools.product(left,right))


def offsets(links):
    a,b = np.array([p for j in links.values() for p in j]).T
    return a,b, np.cumsum([0]+[len(j) for j in links.values()])[:-1]


def overlap(a,b):
    ia,ib = np.array(pairing(range(len(a)),range(len(b)))).T
    return -sat(a[ia],b[ib]).reshape(len(a),len(b))


def body_parity(geo):
    # Reconstruct the vanilla ModelPart matrix independently of the GEO
    # composition: GUI/Curios must not apply an extra player sneak offset.
    convert = P.T([0,24,0]) @ np.diag([-1.,-1.,1.,1.])
    for pitch,yaw,roll,x,y,z in ((0,0,0,0,0,0),(28.64789,0,0,0,3.2,0),
                                 (13,17,4,.65,1.6,.34), (0,-14,-6,-.5,0.,.22)):
        vanilla = P.T([x,y,z]) @ P.R('z',roll) @ P.R('y',yaw) @ P.R('x',pitch)
        posed = dict(geo,bones=[dict(b, rotation=[pitch,yaw,roll], offset=[x,-y,z])
                      if b['name']=='chestplate' else b for b in geo['bones']])
        m = P.matrices(posed)[G.SEAT_BONE]
        assert np.allclose(m,F.body_transform(pitch,yaw,roll,(x,y,z)),atol=1e-8)
        assert np.allclose(convert @ m,vanilla @ convert,atol=1e-8)


def fit_check(geo, clips, quick):
    hidden = P.effective_hidden(geo)
    cubes = [(b['name'],i,P.cube_points(c,np.eye(4)))
             for b in geo['bones'] if b['name'] not in hidden for i,c in enumerate(b.get('cubes',()))]
    names = np.array([n for n,_,_ in cubes]); local = np.array([p for _,_,p in cubes])
    groups, joints = defaultdict(list), defaultdict(list)
    for i,(n,j,_) in enumerate(cubes):
        groups[n].append(i)
        if m := M.RIBBON.fullmatch(n):
            k,seg = map(int,m.groups())
            joints[k,seg+G.source_cube(n,j)].append(i)
    collar = [i for i,n in enumerate(names) if n.startswith(('v17_cowl_', 'v19_cuellito_'))]
    heads = collar + [i for i,n in enumerate(names) if n.startswith(('v18_pad_', 'v18_chain_'))]
    seat,gusset,saddle = (groups[b] for b in (G.SEAT_BONE,G.GUSSET_BONE,G.SADDLE_BONE))
    links = {f'{k}:{s}': pairing(j,joints[k,s+1]) for (k,s),j in list(joints.items()) if s<6}
    binds = {k: pairing(joints[k,0],heads+saddle) for k in range(12)}
    a,b,l = offsets(links); aa,bb,ll = offsets(binds)
    f=F.profile(); max_depth = float(np.max(f['backset']))
    assert F.depth(0,0,0) == F.depth(0,-90,0) == 0 and max_depth < 8
    depths = np.linspace(0,max_depth,7)
    torso = P.CORNERS * [8,12,4] + [-4,12,-2]
    is_cloth = np.array([M.RIBBON.fullmatch(n) is not None for n in names])
    upper = np.array(heads + saddle)
    fold = lambda v,d: F.rotate(v,np.array(G.DRAPE_PIVOT),f['drapePerUnit']*d)
    stretch = lambda v,d: (v-G.MOUNT_PIVOT)*[1.,1.,1.+d/f['gussetDepth']]+G.MOUNT_PIVOT
    shift = lambda d: np.array([0.,0.,d])

    def sample(model):
        m=P.matrices(model)
        packed=np.array([m[n] for n in names])
        return local @ packed[:,:3,:3].transpose(0,2,1) + packed[:,None,:3,3]

    ref = sample(geo)
    old_parts = ref[np.r_[np.flatnonzero(is_cloth),heads]]
    old_gap = float(old_parts[...,2].min()-2)
    bed = overlap(ref[seat],torso[None]).max()
    assert old_gap > .70 and .02 < bed < .09, (old_gap,bed)
    assert ref[seat+gusset,...,2].min() > 1.9
    assert all(overlap(ref[groups[f'v18_pad_{i}']],ref[saddle]).max() > .14 for i in range(2))
    assert overlap(ref[saddle],ref[collar]).max() > .14
    assert min(overlap(ref[groups[f'v18_chain_{i}']],ref[collar]).max() for i in range(8)) > .14
    # Test every rigid component for connectivity, not just the largest cube.
    for ids in (seat,gusset,saddle):
        connected = overlap(ref[ids],ref[ids]) > .04
        seen = connected[0]
        for _ in ids:
            seen = connected[seen].any(0)
        assert seen.all(), names[ids]
    socket = []
    for d in np.linspace(0,max_depth,101):
        fitted = stretch(ref[gusset],d)
        socket.append(min(overlap(fitted,ref[seat]).max(),overlap(fitted,ref[saddle]+shift(d)).max()))
    assert min(socket) > .16, min(socket)
    # The small split solid fragments stay in the same bone; keeping every
    # original cubic transform also keeps their inset local overlap.
    cloth_sample, control_sample = [], []
    seams = (1e6,)
    roots = (1e6,)
    body = (1e6,)
    count = 0
    root_names = list(binds)
    for g,title,control in pose_samples(geo,clips):
        v = sample(g)
        assert np.array_equal(v[upper],ref[upper]), 'el cuello/placas se animan fuera del paño'
        joint = -np.minimum.reduceat(sat(v[a],v[b]),l)
        seams = min(seams,(joint.min(),title,list(links)[int(joint.argmin())]))
        for d in depths:
            root = -np.minimum.reduceat(sat(fold(v[aa],d),v[bb]),ll)
            roots = min(roots,(root.min(),title,d,root_names[int(root.argmin())]))
            cloth = fold(v[is_cloth],d)+shift(d)
            body = min(body,(cloth[...,2].min(),title,d))
        points = v[is_cloth & (v[...,1].max(1)>14.5)]
        if not quick or control:
            cloth_sample.append(points)
        if control:
            control_sample.append(points)
        count += 1
    assert seams[0] > .038 and roots[0] > .025 and body[0] > 2.45, (seams,roots,body)
    print(f'Torso: hueco neutro {old_gap:.3f} u → asiento {bed:.3f} u. Fuelle ≥ {min(socket):.3f} u de solape. '
          f'{count} poses y mezclas, costuras ≥ {seams[0]:.3f}/{roots[0]:.3f} u; paño Z ≥ {body[0]:.3f}.',flush=True)

    def envelope(frames):
        v = np.unique(np.concatenate(frames).round(7),axis=0)
        return v,v.min(1),v.max(1)

    def clearance(head, vertices, label, worst):
        v,lo,hi = vertices
        test = ((hi>head.min(0)-.22) & (lo<head.max(0)+.22)).all(1)
        if np.any(test):
            points = v[test]
            distance = sat(points,np.broadcast_to(head,points.shape)).min()
            return min(worst,(float(distance),label))
        return worst

    fixed = envelope([ref[upper]])
    def sweep(pool, aims):
        env = envelope(pool)
        worst = (.22,)
        for st,pitch,yaw in aims:
            head = F.head_in_body(st,pitch,yaw)
            d = F.depth(st,pitch,yaw)
            base = head-shift(d)
            mark = (st,pitch,yaw,d)
            worst = clearance(base,fixed,(*mark,'cuello'),worst)
            worst = clearance(fold(base,-d),env,(*mark,'paño'),worst)
            mount = np.concatenate((ref[seat],stretch(ref[gusset],d)))
            worst = clearance(head,(mount,mount.min(1),mount.max(1)),(*mark,'montura'),worst)
        return worst

    core = list(itertools.product((0.,.5,1.),range(-90,91,15),range(-90,91,15)))
    fine = list(itertools.product((0.,.25,.5,.75,1.),np.linspace(-90,90,33),np.linspace(-90,90,33)))
    worst = min(sweep(cloth_sample,core),sweep(control_sample,fine))
    print(f'Cabeza: {len(core)} orientaciones × {len(cloth_sample)} poses, '
          f'{len(fine)} × {len(control_sample)} controles, mínimo {worst[0]:+.3f} u.',flush=True)
    assert worst[0] > .015, worst
    body_parity(geo)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--quick',action='store_true',help='no cruza todas las mezclas con las orientaciones de cabeza')
    cli.add_argument('--fit-only',action='store_true')
    args=cli.parse_args()
    geo=P.load(P.ARMOR_GEO)
    runtime=json.loads(A.ANIM.read_text())
    if not args.fit_only:
        rebuilt=G.build_base()['minecraft:geometry'][0]
        atlas,light,layout=C.map_material(rebuilt,paint=True)
        assert geo == rebuilt and runtime == A.build(geo)
        assert layout['cards'] == 288 and layout['emissive'] == 1848
        preservation(geo,atlas,light)
        bb=json.loads(B.DOC.read_text())
        check_editor(json.loads((BASE/'CAPA_v1.63.0.bbmodel').read_text()),bb,geo,atlas,runtime)
        motion(geo,runtime,bb)
        visor_fit(geo,runtime)
        visor_material(geo,atlas,light)
        visor_embers()
    fit_check(geo,runtime['animations'],args.quick)


if __name__=='__main__':
    main()
