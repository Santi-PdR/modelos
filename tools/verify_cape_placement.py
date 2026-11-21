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
from cape_contact import seat_contacts, upper_back_fit
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
            assert not any(any(probe in n for probe in ('CapePlacementProbe','CapeFxSmoke','CapeWalkProbe'))
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
                np.testing.assert_array_equal(frame[name],base[name],err_msg=f'{name}: {aim}')
            cases.append(aim)
            expected.append([frame[n].ravel() for n in parts])
    np.testing.assert_allclose(viewer(geo=geo,torsoMatrices=cases,parts=parts),expected,atol=5e-9,rtol=0)
    print(f'{len(cases)} poses coinciden con el visor y no dependen de la cabeza.'
          + (' Perfil fijo de Java verificado.' if java_samples else ''),flush=True)


def exercise(geo):
    model = WornModel(geo)
    names = np.asarray(model.names)
    seat,link,saddle = (names == bone for bone in (G.SEAT_BONE,G.GUSSET_BONE,G.SADDLE_BONE))
    mount = names != ''
    mount[model.cloth] = False
    clips = json.loads(A.ANIM.read_text())['animations']
    posed_data = []
    box_estimates = []
    seat_estimates = []
    depth_estimates = []
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
                fitted = model.place(P.matrices(F.fixed_wearer_pose(geo,0.,slim=slim)))
                parts = {n:fitted[names==n] for n in np.unique(names)}
                parts['body'] = (P.CORNERS*[8,12,4]+[-4,12,-2])[None]
                parts['jacket'] = (P.CORNERS*[8.5,12.5,4.5]+[-4.25,11.75,-2.25])[None]
                sleeve = P.CORNERS*[3.5 if slim else 4.5,12.5,4.5]+[3.75,11.25 if slim else 11.75,-2.25]
                parts['left_sleeve'],parts['right_sleeve'] = sleeve[None],(sleeve*[-1,1,1])[None]
                neutral_hat = F.head_in_body(0.,0.,0.,outer=True)[None,None]
                assert contacts(fitted[None,mount],neutral_hat).min() > 0, 'la montura corta la cabeza en reposo'
                label = 'Alex' if slim else 'Steve'
                seat_estimates.append(seat_contacts(parts,label))
                depth_estimates.append(upper_back_fit(parts,label))
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
    print('Encastre espalda alta → forro → cuello → retornos → placas → mangas (u):',
          np.min(seat_estimates,axis=0).round(3).tolist(),flush=True)
    depth = np.array(depth_estimates)
    print('Piel sin chaqueta: resalte/hueco/solape/raíces (u):',
          np.r_[depth[:,:2].max(0),depth[:,2:].min(0)].round(3).tolist(),flush=True)
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
    ap.add_argument('--assets-only',action='store_true')
    args = ap.parse_args()
    asset_contract(args.jar)
    if not args.assets_only:
        geo = P.load(P.ARMOR_GEO)
        parity(geo,args.java_samples)
        exercise(geo)
