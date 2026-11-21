#!/usr/bin/env python3
"""Lock the v1.67.14 art and check position-only changes in the torso frame."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from itertools import product
from pathlib import Path
from zipfile import ZipFile

import numpy as np

import armor_model_pipeline as G
import cape_animation_pipeline as A
import cape_fit as F
from cape_contact import back_and_sleeves, lap as group_lap, original_dimensions, shoulder_seams
import cape_tracks as T
import preview_cloth as P
from bbmodel_export import DOC
from verify_cape_backing import lap
from verify_v1660 import WornModel, contacts
import cape_stride as S

REFERENCE = P.ROOT/'entregables/v1.67.14/capatest-1.67.14.jar'
ART = ('geo', 'textures', 'animations', 'particles', 'shaders')


def art_entries(jar):
    return {n.split('assets/capatest/',1)[1]:jar.read(n) for n in jar.namelist()
            if n.startswith(tuple(f'assets/capatest/{kind}/' for kind in ART)) and not n.endswith('/')}


def asset_contract(candidate=None):
    with ZipFile(REFERENCE) as jar:
        original = art_entries(jar)
    source = {p.relative_to(P.ASSETS).as_posix():p.read_bytes() for kind in ART
              for p in (P.ASSETS/kind).rglob('*') if p.is_file()}
    assert source.keys() == original.keys(), original.keys() ^ source.keys()
    for name,data in original.items():
        assert data == source[name], f'cambió el arte original: {name}'
    assert G.build() == json.loads(P.ARMOR_GEO.read_text()), 'el generador no produce el modelo restaurado'
    model = json.loads(DOC.read_text())
    del model['name']
    digest = hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert digest == 'e6c8fbf2dd3f4f68e950e1cfee8dfc9db52f177261432d033d1664b22a17c939', 'cambió el proyecto de Blockbench'
    if candidate is not None:
        with ZipFile(candidate) as jar:
            assert jar.testzip() is None
            assert art_entries(jar) == original, 'el JAR no contiene los recursos originales'
            assert not any(any(probe in n for probe in ('CapePlacementProbe','CapeFxSmoke','CapeWalkProbe','CapeWaterProbe','CapeJumpProbe'))
                           for n in jar.namelist()), 'se empaquetó el ensayo de Forge'
    print(f'{len(original)} recursos idénticos al JAR v1.67.14 y proyecto Blockbench intacto (salvo nombre de versión).',flush=True)


def viewer(**data):
    result = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,text=True,check=True,capture_output=True,
                            input=json.dumps(dict(fit=F.viewer_profile(placed=True),**data)))
    return np.asarray(json.loads(result.stdout))


def parity(geo, java_samples=None):
    wing_modes = [False, True]
    samples = list(product(wing_modes,(False,True),(0,1)))
    expected = [F.worn_plate(i,w,slim) for w,slim,i in samples]
    np.testing.assert_allclose(viewer(mountPlateSamples=samples),expected,atol=5e-10,rtol=0)
    if java_samples:
        rows = np.loadtxt(java_samples)
        np.testing.assert_array_equal(rows[:,:3], samples)
        np.testing.assert_allclose(rows[:,3:],expected,atol=5e-10,rtol=0)
    parts = [G.FIT_BONE,G.DRAPE_BONE,G.GUSSET_BONE,G.SEAT_BONE,G.SADDLE_BONE,G.UNDER_YOKE_BONE,
             'v17_cowl_back_4',G.SHOULDERS_BONE,'v17_cowl_return',*F.B.profile()['names'],
             'v18_pad_0','v18_pad_1','cape_top','v17_ribbon_2_seg3']
    cases = []
    expected = []
    for body, wings, slim in product((0.,.27,1.),wing_modes,(False,True)):
        base = P.matrices(F.wearer_pose(geo,body,0,0,elytra=wings,placed=True,slim=slim))
        for pitch,yaw,arm in product((-89.,-60.,-30.,0.,30.,60.,89.),(-73.,0.,73.),(0.,36.)):
            aim = [body,pitch,yaw,wings,arm,arm,slim]
            frame = P.matrices(F.wearer_pose(geo,body,pitch,yaw,elytra=wings,arm_back=arm,placed=True,slim=slim))
            for name in base:
                if wings or (name != 'worn_hood' and not F.hood_moves(name)):
                    np.testing.assert_array_equal(frame[name],base[name],err_msg=f'{name}: {aim}')
            cases.append(aim)
            expected.append([frame[n].ravel() for n in parts])
    np.testing.assert_allclose(viewer(geo=geo,torsoMatrices=cases,parts=parts),expected,atol=5e-9,rtol=0)
    print(f'{len(cases)} poses coinciden con el visor; la mirada sólo mueve el borde alto de la capucha.'
          + (' Perfil fijo de Java verificado.' if java_samples else ''),flush=True)


def hood_parity(geo, java_samples=None):
    samples = np.loadtxt(java_samples) if java_samples else None
    inputs = samples[:, :6].tolist() if samples is not None else [
        [20*t,phase,pace,turn,side,42] for t,phase,pace,turn,side in
        product((0.,1.1),(.03,.53), (0.,.7,1.),(-1.,1.),(-1.,1.))]
    poses = [F.hood_pose(*args) for args in inputs]
    if samples is not None:
        np.testing.assert_allclose(poses,samples[:,6:],atol=1e-10,rtol=0)
    case = [[i % 2, (i//2) % 2, *args] for i,args in enumerate(inputs)]
    parts = ['v17_cowl_back_1','v17_cowl_front_3','v17_cowl_tooth_3','v17_cowl_return',
             'v18_pad_0',G.SADDLE_BONE,G.SHOULDERS_BONE,'v17_ribbon_6_seg0']
    expected = []
    for (stance,wings,*_),pose in zip(case,poses,strict=True):
        model = P.matrices(F.fixed_wearer_pose(geo,stance,elytra=wings,slim=True,hood=pose))
        fixed = P.matrices(F.fixed_wearer_pose(geo,stance,elytra=wings,slim=True))
        for n in model:
            if n != 'worn_hood' and (wings or not F.hood_moves(n)):
                np.testing.assert_array_equal(model[n],fixed[n],err_msg=f'la capucha movió {n}')
        expected.append([*pose, *[v for n in parts for v in model[n].ravel()]])
    np.testing.assert_allclose(viewer(geo=geo,hoodSamples=case,parts=parts),expected,atol=5e-9,rtol=0)
    print(f'{len(case)} poses de capucha: sólo gira el borde alto, sin mover el asiento ni alterar los élitros.',flush=True)


def clearance_parity(geo, java_look=None, java_edge=None):
    aims = list(product((-79.,21.,39.,64.,89.),(-390.,-55.,0.,55.,90.),(0.,6.,28.65)))
    offsets = list(product(range(12),range(7)))
    if java_look:
        rows = np.loadtxt(java_look)
        aims = rows[:,:3].tolist()
        np.testing.assert_allclose(rows[:,3],[F.hood_aim(*a) for a in aims],atol=1e-10,rtol=0)

    def edge(ribbon, segment):
        return F.sprint_edge_offset(f'v17_ribbon_{ribbon}_seg{segment}','cape_top') or (0.,0.,0.)

    expected = np.array([edge(*a) for a in offsets])
    if java_edge:
        rows = np.loadtxt(java_edge)
        np.testing.assert_array_equal(rows[:,:2],offsets)
        np.testing.assert_allclose(rows[:,2:],expected[:,[0,2]],atol=1e-10,rtol=0)
    np.testing.assert_allclose(viewer(lookClearanceSamples=aims),[F.hood_aim(*a) for a in aims],atol=1e-10,rtol=0)
    np.testing.assert_allclose(viewer(sprintEdgeSamples=offsets),expected,atol=1e-10,rtol=0)

    rig = WornModel(F.fixed_wearer_pose(geo,0.,slim=True))
    names = np.asarray(rig.names)
    moving = np.array([F.hood_moves(n) for n in names])
    collar = np.char.startswith(names,'v17_cowl_') | np.char.startswith(names,'v19_cuellito_')
    support = (collar & ~moving) | (names == G.SADDLE_BONE) | (names == G.SHOULDERS_BONE)
    old = rig.place(P.matrices(F.fixed_wearer_pose(geo,0.,slim=True)))
    new = rig.place(P.matrices(F.fixed_wearer_pose(geo,0.,slim=True,look=64.)))
    solid = (P.CORNERS*8+[-4,0,-4]) @ P.R('x',64)[:3,:3].T + F.HEAD_PIVOT
    assert group_lap(new[collar],solid[None]) <= .70 * group_lap(old[collar],solid[None])
    for look,yaw in product(range(0,91,5),range(-75,76,15)):
        v = rig.place(P.matrices(F.fixed_wearer_pose(geo,0.,look=look,turn=yaw,slim=True)))
        for sign in (-1,1):
            side = old[:,:,0].mean(1)*sign > 0
            assert group_lap(v[moving & side],v[support]) > .14, (look,yaw,'capucha separada')

    clip = json.loads(A.ANIM.read_text())['animations']['animation.sprint']
    track = T.prepare_clip(clip)
    parts = ['cape_top','cape_mid','cape_bottom',G.SHOULDERS_BONE,'v17_cowl_back_3',
             'v17_ribbon_0_seg0','v17_ribbon_1_seg1','v17_ribbon_3_seg2','v17_ribbon_7_seg2','v17_ribbon_10_seg4']
    cases, transforms = [], []
    for i in range(36):
        phase = i/36
        frame = P.pose_at(geo,track,phase * clip['animation_length'])
        by = {b['name']:b for b in frame['bones']}
        top,mid = (by[n]['rotation'] for n in ('cape_top','cape_mid'))
        arm,leg = S.demand(0.,*S.gait(phase,1.))
        # Use the sprint envelope even between footfalls in this synthetic rig.
        dx,dy = S.lifts(top[0],mid[0],max(arm,52.),max(leg,73.),0.,0.)
        top[0] += dx
        mid[0] += dy
        base = P.matrices(F.fixed_wearer_pose(frame,0.,slim=True))
        for amount in (.25,.5,1.):
            posed = P.matrices(F.fixed_wearer_pose(frame,0.,slim=True,sprint_edge=amount))
            for n in base:
                if F.sprint_edge_offset(n,by.get(n,{}).get('parent')) is None:
                    np.testing.assert_array_equal(posed[n],base[n],err_msg=f'el borde sprint desplazó {n}')
            seam,roots = rig.joins(rig.place(posed))
            assert seam > .038 and roots > .025, (phase,amount,seam,roots)
        wing = P.matrices(F.fixed_wearer_pose(frame,0.,elytra=True,slim=True))
        fitted = P.matrices(F.fixed_wearer_pose(frame,0.,elytra=True,slim=True,look=64.,sprint_edge=1.))
        for n in wing:
            np.testing.assert_array_equal(wing[n],fitted[n],err_msg=f'cambió el ajuste de élitros: {n}')
        if i%9 == 0:
            cases.append([frame,.0,64.,12.,False,True,.75])
            result = P.matrices(F.fixed_wearer_pose(frame,0.,slim=True,look=64.,turn=12.,sprint_edge=.75))
            transforms.append([result[n].ravel() for n in parts])
    np.testing.assert_allclose(viewer(clearanceMatrices=cases,parts=parts),transforms,atol=5e-9,rtol=0)
    print(f'Holgura equipada: {len(aims)} miradas, {len(offsets)} tramos y 108 poses de carrera; raíces y élitros intactos.',flush=True)


def lining_parity(geo):
    parts = F.B.profile()['names']
    source = {b['name']:b['cubes'] for b in geo['bones'] if b['name'] in parts}
    assert len(source) == 2 and all(len(cs) == 3 for cs in source.values()), source.keys()
    expected = []
    for wings in (False,True):
        pose = F.fixed_wearer_pose(geo,0.,elytra=wings)
        cubes = {b['name']:b['cubes'] for b in pose['bones'] if b['name'] in parts}
        expected.append([int(any(c is keep for keep in cubes[n])) for n in parts for c in source[n]])
    assert expected == [[1,0,1]*2,[1,1,1]*2], expected
    np.testing.assert_array_equal(viewer(geo=geo,mountLiningSamples=[False,True],parts=parts),expected)
    # Reproduce the nape stripe's geometric cause using the exact vanilla
    # solid head, not its transparent outer skin layer.
    transform = P.matrices(F.fixed_wearer_pose(geo,0.,slim=True))
    head = (P.CORNERS*8+[-4,0,-4]) @ P.R('x',-79)[:3,:3].T + F.HEAD_PIVOT
    for n in parts:
        lip = P.cube_points(source[n][1],transform[n])
        assert lap(lip[None],head[None]) > .4, n
    print('Sólo se omiten las dos pestañas que cruzaban la nuca; las demás piezas del forro y los élitros quedan intactos.',flush=True)


def exercise(geo):
    model = WornModel(geo)
    names = np.asarray(model.names)
    seat,link,saddle = (names == bone for bone in (G.SEAT_BONE,G.GUSSET_BONE,G.SADDLE_BONE))
    mount = names != ''
    mount[model.cloth] = False
    clips = json.loads(A.ANIM.read_text())['animations']
    posed_data = []
    box_estimates = []
    contacts_still = []
    authored = model.place(P.matrices(geo))
    plates = np.char.startswith(names,'v18_pad_')
    hood = np.array([F.hood_moves(n) for n in names])
    shoulders = names == G.SHOULDERS_BONE
    garment = ~(plates | saddle | hood | shoulders)
    offset = [0.,-F.mount_profile()['BACK_DROP'],-F.mount_profile()['BACK_FORWARD']]
    for body, wings in product((0.,1.),(False,True)):
        rest = P.matrices(F.wearer_pose(geo,body,0,0,elytra=wings,placed=True))
        inv = np.linalg.inv(rest['chestplate'])
        v = model.place(rest)
        local = v @ inv[:3,:3].T + inv[:3,3]
        foot = max(lap(x,local[seat]) for x in local[link])
        upper = max(lap(x,local[saddle]) for x in local[link])
        assert min(foot,upper) > .1, (body,wings,foot,upper)
        assert local[mount,:,1].min() > 10, 'cambió el soporte rígido'
        if not wings and body == 0:
            for slim in (False,True):
                pose = F.fixed_wearer_pose(geo,0.,slim=slim)
                fitted = model.place(P.matrices(pose))
                draw = WornModel(pose)
                rendered, original = (draw.place(mats) for mats in (P.matrices(pose),P.matrices(geo)))
                draw_names = np.asarray(draw.names)
                parts = {n:rendered[draw_names==n] for n in np.unique(draw_names)}
                parts_source = {n:original[draw_names==n] for n in np.unique(draw_names)}
                parts['body'] = (P.CORNERS*[8,12,4]+[-4,12,-2])[None]
                parts['jacket'] = (P.CORNERS*[8.5,12.5,4.5]+[-4.25,11.75,-2.25])[None]
                sleeve = P.CORNERS*[3.5 if slim else 4.5,12.5,4.5]+[3.75,11.25 if slim else 11.75,-2.25]
                parts['left_sleeve'],parts['right_sleeve'] = sleeve[None],(sleeve*[-1,1,1])[None]
                label = 'Alex' if slim else 'Steve'
                original_dimensions(parts, parts_source, label)
                shoulder_seams(parts, label)
                np.testing.assert_allclose(fitted[garment] - authored[garment],
                                           np.broadcast_to(offset, fitted[garment].shape), atol=1e-10, rtol=0)
                contacts_still.append(back_and_sleeves(parts,label))
        aims = list(product((-89.,-60.,-30.,0.,30.,60.,89.),(-73.,-40.,0.,40.,73.)))
        hats = np.asarray([F.head_in_body(body,p,y,outer=True) for p,y in aims])[:,None]
        vv = np.repeat(local[None,mount],len(aims),axis=0)
        box_estimates.append(contacts(vv,hats,pad=.25).min())
        for name in clips:
            clip = clips[name]
            track = T.prepare_clip(clip)
            for t in (.05,.29,.56,.82):
                frame = P.pose_at(geo,track,t*clip['animation_length'])
                by = {b['name']: b for b in frame['bones']}
                a,b = (by[n]['rotation'][0] for n in ('cape_top','cape_mid'))
                dx,dy = S.lifts(a,b,31,45,body,0)
                by['cape_top']['rotation'][0] += dx
                by['cape_mid']['rotation'][0] += dy
                v = model.place(P.matrices(F.wearer_pose(frame,body,0,0,elytra=wings,placed=True)))
                np.testing.assert_allclose(v[mount],model.place(rest)[mount],atol=1e-10,rtol=0)
                posed_data.append(model.joins(v))
    print('Sin deformación; contacto directo paño/piel y rayos con tela en la espalda:',
          [(round(seat,3), f'{rays}/63', round(seam,3), laps.round(3).tolist())
           for seat,rays,seam,laps in contacts_still], flush=True)
    seam,root = np.asarray(posed_data).min(0)
    assert seam > .038 and root > .025, (seam,root,'se abrió una costura del paño')
    # The conservative hat sweep intentionally includes extreme neck angles.
    # This is diagnostic: a fixed mount is not a collision-avoidance solver.
    print(f'{len(posed_data)} fases: unión al torso y costura del paño verificadas (solapes {seam:.3f}/{root:.3f}u). '
          f'Margen SAT mínimo caja de cabeza, incluso al extremo: {min(box_estimates):+.3f}u.',flush=True)


if __name__=='__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jar',type=Path)
    ap.add_argument('--java-samples',type=Path)
    ap.add_argument('--hood-samples',type=Path)
    ap.add_argument('--look-samples',type=Path)
    ap.add_argument('--edge-samples',type=Path)
    ap.add_argument('--assets-only',action='store_true')
    args = ap.parse_args()
    asset_contract(args.jar)
    if not args.assets_only:
        geo = P.load(P.ARMOR_GEO)
        parity(geo,args.java_samples)
        hood_parity(geo,args.hood_samples)
        clearance_parity(geo,args.look_samples,args.edge_samples)
        lining_parity(geo)
        exercise(geo)
