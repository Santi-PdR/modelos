#!/usr/bin/env python3
"""Numerical regression of the rotation-only stride guide, not a client playtest."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from itertools import product
import json
import re
import subprocess
from pathlib import Path

import numpy as np

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_fit as F
import cape_motion as M
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from verify_v1600 import interpolate, response_variants, sat
from verify_v1640 import offsets, pairing

BASE = P.ROOT / 'docs/respaldos/v1.65.0'
HINGES = ('cape_top', 'cape_mid')


def preservation():
    for line in (BASE/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha256((BASE/name).read_bytes()).hexdigest() == digest, name
        if name == 'fit.json':
            assert json.loads((BASE/name).read_text()) == F.profile()
        elif name.endswith('.bbmodel'):
            old = json.loads((BASE/name).read_text())
            current = json.loads(B.DOC.read_text())
            assert current == dict(old, name=current['name']), 'sólo el nombre del proyecto cambia'
        else:
            assert (P.ASSETS/name).read_bytes() == (BASE/name).read_bytes(), name
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    assert json.loads(re.search(r'^const INLINE_STRIDE = (.+);$', html, re.M)[1]) == S.profile()
    print('v1.65.0: GEO, clips, ajuste de cabeza, atlas, partículas, icono y lore intactos; mismo rig de Blockbench.', flush=True)


def js_samples(samples):
    run = subprocess.run(['node', 'tools/check_viewer_pose.js'], cwd=P.ROOT, check=True, text=True,
                         input=json.dumps(dict(strideSamples=samples, stride=S.profile(), fit=F.profile())),
                         capture_output=True)
    return np.array(json.loads(run.stdout))


def parity(java_samples):
    if java_samples is None:
        rows = [[8 + a*.21, 5.5 + l*.16, a, l, s, s*2.39 + (.8 if l==48 else 0)]
                for s,a,l in product((0,.25,.75,1), (0,12,23,34,48,57.3,70), (0,32,48,68,80))]
    else:
        rows = np.loadtxt(java_samples).tolist()
    samples = [r[:6] for r in rows]
    expected = np.array([S.lifts(*r) for r in samples])
    assert np.allclose(js_samples(samples), expected, atol=1e-9, rtol=0)
    if java_samples is not None:
        assert np.allclose([r[6:] for r in rows], expected, atol=1e-9, rtol=0)
    print(f'Holgura: {len(rows)} muestras del visor y Python' + (' también coinciden con Java.' if java_samples else '.'), flush=True)


def actors(aim, arms, legs, inflate):
    skin = P.MANNEQUIN_BOXES[2:]
    cubes = []
    for i,((o,s,_),mat) in enumerate(zip(skin,F.mannequin_pose(*aim,arms,legs)[2:],strict=True)):
        outside = np.array(o,dtype=float) - inflate
        if i>=2:
            outside[0] += .1 if i==2 else -.1  # 1.9u leg pivots
        box = outside + P.CORNERS * (np.array(s)+2*inflate)
        cubes.append(box @ mat[:3,:3].T + mat[:3,3])
    return cubes


def contacts(shapes, obstacles, pad=.04):
    c,d = shapes.min(2), shapes.max(2)
    lo,hi = obstacles.min(2), obstacles.max(2)
    near=((lo[:,:,None,:]-pad < d[:,None,:,:]) & (c[:,None,:,:]-pad < hi[:,:,None,:])).all(3)
    i,j,k = np.where(near)
    gap = np.full(near.shape,pad)
    if i.size:
        gap[i,j,k] = sat(shapes[i,k],obstacles[i,j])
    return gap


class WornModel:
    def __init__(self, geo):
        self.by = {b['name']: b for b in geo['bones']}
        hidden = P.effective_hidden(geo)
        parts = [(b['name'],i,P.cube_points(c,np.eye(4))) for b in geo['bones'] if b['name'] not in hidden
                 for i,c in enumerate(b.get('cubes',[]))]
        self.names = [n for n,i,c in parts]
        self.coords = np.array([c for n,i,c in parts])
        self.pivots = [np.asarray(self.by[n]['pivot'])*[-1,1,1] for n in HINGES]
        masks = [[n in self.parents(part) for part in self.names] for n in HINGES]
        self.masks = [np.array(m) for m in masks]
        self.cloth = self.masks[0]
        self.rigid = ~self.cloth

        joints = defaultdict(list)
        for i,(n,c,_) in enumerate(parts):
            if m := M.RIBBON.fullmatch(n):
                k,j = map(int,m.groups()); joints[k,j+G.source_cube(n,c)].append(i)
        supports = [i for i,n in enumerate(self.names) if n.startswith(
            ('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_', G.SADDLE_BONE))]
        self.seams = offsets({(k,j): pairing(ids,joints[k,j+1]) for (k,j),ids in list(joints.items()) if j<6})
        self.roots = offsets({k: pairing(joints[k,0],supports) for k in range(12)})

    def parents(self, part):
        while part is not None:
            yield part
            part=self.by[part].get('parent')

    def vertices(self, frame, aim):
        mm = P.matrices(F.wearer_pose(frame,*aim))
        mats = np.array([mm[n] for n in self.names])
        verts = self.coords @ mats[:,:3,:3].transpose(0,2,1) + mats[:,None,:3,3]
        pivots = [mm[n][:3,:3]@p+mm[n][:3,3] for n,p in zip(HINGES,self.pivots,strict=True)]
        axes = [mm[n][:3,0] for n in HINGES]
        return verts,pivots,axes

    def lifted(self, packed, corrections):
        # ZYX Euler: adjusting only X can be evaluated about the current X
        # axis. Apply the deeper hinge first, then its parent. No skinning.
        pose,pivots,axes=packed
        v = np.repeat(pose[None],len(corrections),axis=0)
        for j in (1,0):
            m,p,axis = self.masks[j],pivots[j],axes[j]
            rad = -np.radians(corrections[:,j,None,None,None])
            c,s = np.cos(rad),np.sin(rad)
            x = v[:,m] - p
            v[:,m] = p+x*c+np.cross(axis,x)*s+(x@axis)[...,None]*axis*(1-c)
        return v

    def joins(self, vertices):
        return tuple(float(-np.minimum.reduceat(sat(vertices[a],vertices[b]),j).max())
                     for a,b,j in (self.seams,self.roots))


def exercise(geo, clips):
    rig = WornModel(geo)
    pre = {n: T.prepare_clip(c) for n,c in clips.items()}
    def frame(name, f, extra=None):
        n = 'animation.'+name
        return P.pose_at(geo,pre[n],clips[n]['animation_length']*f,extra)

    zero = (0.,0.,0.)
    tests = [(name,amp,zero) for name,amps in (
        ('idle',(0.,.18)), ('moving',(.40,.60,.80)), ('sprint',(.65,.85,1.0)),
        ('deterioro',(.65,.85)), ('air',(.40,)), ('fall',(.40,)), ('swim',(.40,))) for amp in amps]
    tests += [('sneak',.35,(1.,0.,0.)), ('sneak',.50,(1.,20.,38.)),
              ('moving',.60,(0.,15.,0.)), ('sprint',.85,(0.,0.,32.))]
    envelope = response_variants()
    missed = np.zeros(2,dtype=int); count = 0; worst = np.full(3,np.inf)
    for name,amp,aim in tests:
        steps = [S.gait(i/40,amp) for i in range(40)]
        boxes = np.array([actors(aim,*gait,.25) for gait in steps])
        demand = [S.demand(aim[0],*step) for step in steps]
        dep = F.depth(*aim); summary=np.zeros((3,2),dtype=int); minima=np.full(3,np.inf)
        frames = [frame(name,i/25) for i in range(25)]
        frames += [frame(name,i/5,e) for i,e in product(range(5),envelope)]
        if name in ('moving','sprint','fall','air'):
            for old in ('idle','moving','sprint','air','fall','deterioro'):
                if old!=name:
                    frames += [interpolate(frame(old,t),frame(name,0),w) for t,w in product((.25,.72),(.25,.5,.75))]
        head_tf = F.mannequin_pose(*aim)[0]
        head = (F.HEAD + F.HEAD_PIVOT) @ head_tf[:3,:3].T + head_tf[:3,3]
        for j,g in enumerate(frames):
            angle = {b['name']: b['rotation'][0] for b in g['bones'] if b['name'] in HINGES}
            corr = np.array([S.lifts(*(angle[h] for h in HINGES),*d,aim[0],dep) for d in demand])
            packed = rig.vertices(g,aim)
            before = contacts(np.broadcast_to(packed[0],(len(steps),*packed[0].shape)),boxes)
            v = rig.lifted(packed,corr)
            after = contacts(v[:,rig.cloth],boxes)
            for i,gaps in enumerate((before[:,:,rig.cloth],after,before[:,:,rig.rigid])):
                m = gaps.min(2).reshape(-1,2,2).min(2)
                summary[i] += (m<-.015).sum(0)
                minima[i] = min(minima[i],float(m.min()))
            for ix in set(corr.argmax(0)):
                a,b=rig.joins(v[ix])
                h=float(contacts(v[ix:ix+1,rig.cloth],head[None,None]).min())
                worst=np.minimum(worst,(a,b,h))
            if j == 0:
                ix=int(corr[:,0].argmax())
                d = S.adjust(g,*demand[ix],aim)
                assert np.allclose(v[ix],rig.vertices(d,aim)[0],atol=1e-9,rtol=0)
        count += len(steps)*len(frames)
        missed += summary[1]
        print(f'{name:10s} {amp:.2f} {aim}: {len(steps)*len(frames)} cruces de fases, paño '
              f'{list(map(int,summary[0]))} → {list(map(int,summary[1]))}, '
              f'piezas rígidas {list(map(int,summary[2]))} (brazo/pierna), mínimo {minima[1]:+.3f} u',flush=True)
        if amp == 1:
            assert summary[1,0] < summary[0,0]*.55 and not summary[1,1], summary
        else:
            assert not summary[1].any(), (name,amp,aim,summary)
    assert worst[0]>.038 and worst[1]>.025 and worst[2]>.02, worst
    print(f'{count} combinaciones con piel de +0,25 u, incluidas mezclas y extremos de respuesta. '
          f'Paño: {missed[0]} de brazo en estrés, {missed[1]} de pierna. '
          f'Mínimos costura/raíz {worst[0]:.3f}/{worst[1]:.3f} u; cabeza ≥ {worst[2]:.3f} u en estas poses.',flush=True)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--java-samples',type=Path)
    cli.add_argument('--parity-only',action='store_true')
    arg=cli.parse_args()
    parity(arg.java_samples)
    if not arg.parity_only:
        preservation()
        exercise(P.load(P.ARMOR_GEO),json.loads(A.ANIM.read_text())['animations'])


if __name__=='__main__':
    main()
