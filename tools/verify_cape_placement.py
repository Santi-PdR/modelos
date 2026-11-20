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
import cape_tracks as T
import preview_cloth as P
from bbmodel_export import DOC
from verify_cape_backing import lap
from verify_v1660 import WornModel, contacts

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
            assert not any('CapePlacementProbe' in n for n in jar.namelist()), 'se empaquetó el ensayo de Forge'
    print(f'{len(original)} recursos idénticos al JAR v1.67.14 y proyecto Blockbench intacto (salvo nombre de versión).',flush=True)


def viewer(**data):
    result = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,text=True,check=True,capture_output=True,
                            input=json.dumps(dict(fit=F.viewer_profile(placed=True),**data)))
    return np.asarray(json.loads(result.stdout))


def parity(geo, java_samples=None):
    samples = [list(s) for s in product((0.,.11,.29,.49,1.),(-88.,-58.,0.,14.,25.,41.,71.,86.,89.),
                                       (-79.,-43.,0.,39.,68.),(0.,8.,35.),(1.,.3,0.),(False,True))]
    expected = [F.mount_placement(s,p,y,e,dry=d,enabled=not w) for s,p,y,e,d,w in samples]
    assert np.allclose(viewer(mountSamples=samples),expected,atol=5e-10,rtol=0)
    if java_samples:
        rows = np.loadtxt(java_samples)
        expected = [F.mount_placement(s,p,y,e,dry=d,enabled=not w) for s,p,y,e,d,w in rows[:,:6]]
        assert np.allclose(rows[:,6:],expected,atol=5e-10,rtol=0)
    parts = [G.FIT_BONE,G.DRAPE_BONE,G.GUSSET_BONE,G.SEAT_BONE,G.UNDER_YOKE_BONE,
             'v17_cowl_back_4','v18_pad_0','rim_v18_pad_0','v18_pad_1','cape_top','v17_ribbon_2_seg3']
    matrix_samples = [[s,p,y,w,a,a] for s,p,y,w,a in product((0.,.27,1.),(-89.,-58.,0.,15.,39.,69.,89.),
                                                            (0.,52.),(False,True),(0.,7.))]
    expected = []
    for s,p,y,w,a,e in matrix_samples:
        m = P.matrices(F.wearer_pose(geo,s,p,y,elytra=w,arm_back=a,arm_effort=e,placed=True))
        expected.append([m.get(n,m[n.removeprefix('rim_')]).ravel() for n in parts])
    assert np.allclose(viewer(geo=geo,torsoMatrices=matrix_samples,parts=parts),expected,atol=5e-9,rtol=0)
    print(f'Colocación: {len(samples)} muestras de perfil y {len(matrix_samples)} poses completas coinciden con el visor.'
          + (' Perfil Java verificado.' if java_samples else ''),flush=True)


def exercise(geo):
    model = WornModel(geo)
    mask = lambda test: np.asarray([test(n) for n in model.names])
    seat = mask(lambda n:n==G.SEAT_BONE)
    link = mask(lambda n:n==G.GUSSET_BONE)
    saddle = mask(lambda n:n==G.SADDLE_BONE)
    roots = mask(lambda n:n.startswith('v17_ribbon_') and n.endswith('_seg0'))
    collar = mask(lambda n:n.startswith('v17_cowl_back_'))
    core = roots|collar|mask(lambda n:n.startswith(('v17_cowl_tooth_','v17_cowl_front_','v19_cuellito_','v18_chain_')))
    clips = json.loads(A.ANIM.read_text())['animations']
    stat = []
    aims = [(s,p,y) for s,p,y in product((0.,.23,.48,1.),(0.,21.,40.,60.,74.,86.,89.),(-62.,-43.,0.,43.,62.))]
    for code in ('idle','air','fall'):
        clip = clips['animation.'+code]
        track = T.prepare_clip(clip)
        for t in (.05,.29,.56,.82):
            frame = P.pose_at(geo,track,t*clip['animation_length'])
            for aim in aims:
                before,after = [P.matrices(F.wearer_pose(frame,*aim,placed=on)) for on in (False,True)]
                v0,v1 = (model.place(m) for m in (before,after))
                # Pull both frames back to the same live torso.
                body = np.linalg.inv(after['chestplate'])
                v0,v1 = [v@body[:3,:3].T+body[:3,3] for v in (v0,v1)]
                seam = model.joins(v1)[0]
                bed = max(lap(x,v1[seat]) for x in v1[link])
                upper = max(lap(x,v1[saddle]) for x in v1[link])
                hat = F.head_in_body(*aim,outer=True)[None,None]
                margin = contacts(v1[None,core],hat,pad=.5).min()
                if aim[0]==0:
                    assert np.max(np.abs(v1[seat]-v0[seat])) < 1e-8
                stat.append([*aim,v0[roots,:,2].min(),v1[roots,:,2].min(),v0[collar,:,2].min(),v1[collar,:,2].min(),
                             seam,bed,upper,margin])
    rows = np.asarray(stat)
    straight = rows[(rows[:,0]==0)&(rows[:,1]>=60)&(rows[:,2]==0)]
    assert (straight[:,3]-straight[:,4]).min() > 1.65 and (straight[:,5]-straight[:,6]).min() > 2.4
    # The seam under the neck follows the existing gusset, while the free
    # ribbon segments still touch each other. The clearance number refers
    # to an inflated, conservative hat box, not an observed clipping claim.
    print(f'{len(rows)} poses: raíz alta Z {straight[:,3].max():.2f}→{straight[:,4].max():.2f}u; '
          f'cuello Z {straight[:,5].max():.2f}→{straight[:,6].max():.2f}u; '
          f'solapes costura/pie/fuelle {rows[:,7:10].min(0).round(3)}, '
          f'margen caja de cabeza de pie {rows[rows[:,0]==0,10].min():+.3f}u.',flush=True)
    assert rows[:,7].min() > .04
    assert rows[:,8].min() > .07 and rows[:,9].min() > .02
    assert rows[rows[:,0]==0,10].min() > -.15


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
