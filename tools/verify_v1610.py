#!/usr/bin/env python3
"""Measure v1.61 against the same trace and check the equipped rig.

SAT checks are sampled model-space tests, not a Minecraft client recording.
The fit probe uses an expanded vanilla head; it does not certify every head
accessory, armor combination or custom pose supplied by other mods.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import itertools
import json
import re
import subprocess

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_fit as F
import cape_motion as M
import cape_reference as R
import cape_surface as S
import cape_tracks as T
import preview_cloth as P
from verify_v1590 import check_editor, check_tracks, check_visor
from verify_v1600 import (crop, interpolate, iou, registered_metrics,
                          response_variants, sat)

BASELINE = P.ROOT / 'docs/respaldos/v1.60.0'
OLD_GEO = BASELINE / P.ARMOR_GEO.relative_to(P.ASSETS)
OLD_TEX = BASELINE / P.ARMOR_TEX.relative_to(P.ASSETS)
OLD_CLIPS = BASELINE / A.ANIM.relative_to(P.ASSETS)


def visual(geo, atlas):
    old = P.load(OLD_GEO)
    (before, after), pink = registered_metrics(old, geo, atlas, baseline_atlas=OLD_TEX)
    for key, label in (('all', 'Silueta'), ('upper', 'Región alta'), ('lower', 'Jirones'), ('seam', 'Costura en U')):
        print(f'{label}: {before[key]:.2%} → {after[key]:.2%}')
    assert after['all'] > max(.934, before['all'] + .024)
    assert after['upper'] > .920 and after['lower'] > .935 and after['seam'] > .873
    print(f"RGB común: {before['mae']:.2f} → {after['mae']:.2f}/255, rosa {after['pink']:.1%} (ref. {pink:.1%})")
    assert after['mae'] < min(7.2, before['mae']*.86) and abs(after['pink']-pink) < .013
    # Count the near and far plates as owners; measuring only the region
    # above the hem would allow the plates to be replaced with more cloth.
    ref = crop(R.reference()[1])
    faces, owner = S.visible_faces(geo)
    ids = np.array([f['family'] for f in faces])
    family = np.where(owner>=0, ids[owner], 0)
    for target, threshold in ((R.SHOULDER,.705), (R.COLLAR,.79)):
        score = iou(family==target, ref==target)
        assert score > threshold, (target, score, threshold)
    # A visible-through negative space, not simulated with a black texel.
    x0, y0, _, _ = R.CROP
    patch = np.s_[404-y0:421-y0, 495-x0:512-x0]
    opening = (ref[patch] == 0) & before['match'][patch] & ~after['match'][patch]
    assert opening.sum() >= 70, 'el desgarro izquierdo volvió a taparse'
    # Reverse/profile still have their own volume and material.
    bg = (2, 211, 224)
    counts = [np.count_nonzero((np.asarray(P.render(geo, atlas, P.effective_hidden(geo),
              yaw=yaw, pitch=0, size=320, frame=(0,15,9), bg=bg)) != bg).any(2)) for yaw in (0,90,180)]
    assert .12 < counts[1]/counts[0] < .55 and .77 < counts[2]/counts[0] < 1.30, counts


def protection(geo, atlas, mask, runtime, candidate):
    assert sha256(R.SOURCE.read_bytes()).hexdigest() == R.SOURCE_SHA256
    changed = {OLD_GEO, OLD_TEX}
    for line in (BASELINE / 'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        src = BASELINE/name
        assert sha256(src.read_bytes()).hexdigest() == digest, name
        if not candidate and src not in changed and not name.endswith('.bbmodel'):
            assert (P.ASSETS/name).read_bytes() == src.read_bytes(), name
    assert runtime == json.loads(OLD_CLIPS.read_text()), 'los clips del mod cambiaron'
    previous = P.load(OLD_GEO)
    assert P.effective_hidden(geo) == P.effective_hidden(previous)
    assert {b['name'] for b in geo['bones']} - {G.FIT_BONE} == {b['name'] for b in previous['bones']}
    fit = geo['bones'][72]
    assert fit['name'] == G.FIT_BONE and fit['pivot'] == list(G.FIT_PIVOT)
    assert fit['parent'] == 'chestplate' and fit['rotation'] == [0,0,0] and not fit['cubes']
    below_hinge = {b['name'] for b in geo['bones'] if b.get('parent') == G.FIT_BONE}
    orig = {b['name']: b.get('parent') for b in previous['bones']}
    assert below_hinge == {n for n, p in orig.items() if p == 'chestplate' and
                          (n == 'cape_top' or n.startswith(('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_')))}
    for b in geo['bones']:
        n = b['name']
        if n.startswith('v17_vein_'):
            # Trace placement can land on a different ribbon after trimming.
            # fit_check independently measures the join to the new ribbon.
            assert b['parent'].startswith('v17_ribbon_')
        elif n not in below_hinge | {G.FIT_BONE}:
            assert b.get('parent') == orig[n], n
    assert all(G.FIT_BONE not in c['bones'] for c in runtime['animations'].values())
    old, current = (np.asarray(image) for image in (Image.open(OLD_TEX).convert('RGBA'), atlas))
    m = np.asarray(mask)[...,3]>0
    assert m.sum() == 3380 and np.all(current[...,3] == 255) and np.array_equal(current[m], old[m])
    for b in geo['bones'][72:]:
        if b['name'].startswith('v15_cloth_'):
            continue
        for c in b.get('cubes', []):
            for face, uv in c['uv'].items():
                u,v = uv['uv']; w,h = uv['uv_size']
                assert 0 < u < u+w < 128 and 0 < v < v+h < 128
                em = m[int(v):int(v+h)+1,int(u):int(u+w)+1]
                if b['name'].startswith('v17_vein_'):
                    assert em.all() and b['parent'].startswith('v17_ribbon_')
                else:
                    assert not em.any(), (b['name'], face, uv)
    print('Atlas opaco, 3.380 RGB emisivos, dos glowmasks, icono, plegado y clips conservados')


def pose_samples(geo, clips):
    """Same full animation/response and crossfade sweep as the previous release."""
    yield geo, 'pose base', True
    sources = {}
    variants = response_variants()
    for name, clip in clips.items():
        pre = T.prepare_clip(clip)
        length = clip['animation_length']
        sources[name] = [P.pose_at(geo, pre, length*p) for p in (0,.33,.67)]
        for j,t in enumerate(np.linspace(0,length,49)):
            label = f'{name}:{t:.3f}'
            yield P.pose_at(geo,pre,t), label, j%4==0
            if j%8==0:
                for k, overlay in enumerate(variants):
                    yield P.pose_at(geo,pre,t,overlay), f'{label}/respuesta{k}', j%16==0
    for (a,pa),(b,pb) in itertools.permutations(sources.items(),2):
        for j,p in enumerate(pa):
            for weight in (.25,.5,.75):
                yield interpolate(p,pb[0],weight), f'{a}[{j}]→{b} {weight}', False


def fit_check(geo, clips, quick=False, *, pads=False):
    bones = {b['name']:b for b in geo['bones']}
    hidden = P.effective_hidden(geo)
    cubes = [(b['name'], j, P.cube_points(c, np.eye(4))) for b in geo['bones']
             if b['name'] not in hidden for j,c in enumerate(b.get('cubes', []))]
    names = [n for n,_,_ in cubes]
    geom = np.array([v for _,_,v in cubes])
    groups = {}
    sections = {}
    links = {}
    for i,(n,j,_) in enumerate(cubes):
        groups.setdefault(n, []).append(i)
        if m := M.RIBBON.fullmatch(n):
            column, section = map(int, m.groups())
            sections.setdefault((column, section+G.source_cube(n,j)), []).append(i)
    for (col,seg), here in sections.items():
        if seg == 6:
            continue
        links[f'gajo {col}:{seg}'] = list(itertools.product(here, sections[col,seg+1]))
    collar = [k for k,c in enumerate(names) if c.startswith(('v17_cowl_', 'v19_cuellito_'))]
    saddle = collar + [k for k,c in enumerate(names) if c.startswith(('v18_pad_', 'v18_chain_'))]
    for col in range(12):
        links[f'raíz {col}'] = list(itertools.product(sections[col,0], saddle))
    for n,ix in groups.items():
        if n.startswith('v17_vein_'):
            links[n] = list(itertools.product(ix, groups[bones[n]['parent']]))
        if n.startswith('v18_chain_'):
            links[n] = list(itertools.product(ix, collar))
        if pads and n.startswith('v18_pad_'):
            roots = [i for (c,j),parts in sections.items() if j==0 for i in parts]
            links[n] = list(itertools.product(ix, collar + roots))
            for k in ix[1:4]:
                links[f'{n} pieza {k}'] = [(ix[0], k)]
    # Each cut / step is joined to the same solid segment in local coordinates.
    # The four sides of a tear need not all touch each other directly.
    for n, parts in G.relief()['fragments'].items():
        index = groups[n]; count = len(index)-len(parts)
        for j in sorted({part['source'] for part in parts}):
            pieces = [index[j]] + [index[count+k] for k,p in enumerate(parts) if p['source']==j]
            graph = set(pieces[:1])
            while True:
                offsets = [(a,b) for a in sorted(graph) for b in pieces if b not in graph]
                if not offsets:
                    break
                a,b = np.array(offsets).T
                connected = set(b[sat(geom[a],geom[b]) < -.012])
                if not connected:
                    break
                graph.update(connected)
            assert graph == set(pieces), (n, 'fragmento suelto')
    ls = list(links)
    aa,bb = np.array([p for k in ls for p in links[k]]).T
    starts = np.cumsum([0]+[len(links[k]) for k in ls[:-1]])
    pivot = np.array(G.FIT_PIVOT)
    landmarks = np.radians(np.linspace(0, np.asarray(F.profile()['fold']).max(), 33))
    cos, sin = np.cos(landmarks), np.sin(landmarks)
    common = [.8] * len(ls)
    torso = (float('inf'),)
    cage, samples, selected = [], [], []
    for g, title, include in pose_samples(geo, clips):
        matrices = P.matrices(g)
        ms = np.array([matrices[k] for k in names])
        v = geom @ ms[:,:3,:3].transpose(0,2,1) + ms[:,None,:3,3]
        contact = -np.minimum.reduceat(sat(v[aa], v[bb]), starts)
        for slot, margin in enumerate(contact):
            common[slot] = min(common[slot], margin)
        # Every pivot angle in range; the 1-degree grid is supplemented by
        # the exact interior minimum if a corner can pass below its rest Z.
        dy, dz = (v-pivot)[...,1:].transpose(2,0,1)
        z = dz[...,None]*cos + dy[...,None]*sin + pivot[2]
        # derivative vanishes at atan2(dy,dz) modulo pi; only lower branch
        # (dy,dz both negative in the sampled range) is a minimum.
        critical = (np.arctan2(-dy,-dz) >= landmarks[0]) & (np.arctan2(-dy,-dz) <= landmarks[-1])
        low = np.minimum(z.min(2), np.where(critical, pivot[2]-np.hypot(dy,dz), np.inf))
        i,j = np.unravel_index(low.argmin(), low.shape)
        torso = min(torso, (float(low[i,j]), names[i], title))
        top = v[...,1].max(1)>9.8
        if include:
            selected.append(v[top])
        if include or not quick:
            cage.append(v[top]); samples.append(np.flatnonzero(top))
    checked = len(cage)
    torso_z = torso[0]
    assert torso_z > 2.25, torso
    for name, margin in zip(ls, common, strict=True):
        assert margin > (.030 if name.startswith('gajo') else .020), (name, margin)
    prefixes = [('gajo','gajos'), ('raíz','raíces'), ('v18_chain_','costura')]
    if pads:
        prefixes.append(('v18_pad_', 'placas'))
    if any(k.startswith('v17_vein_') for k in ls):
        prefixes.append(('v17_vein_', 'grietas'))
    ranges = [min(m for k,m in zip(ls,common) if k.startswith(prefix)) for prefix,_ in prefixes]
    print(f'841 poses + 504 mezclas · Z ≥ {torso_z:.3f} u · solapes '+ '/'.join(t for _,t in prefixes)+' '
          + '/'.join(f'{q:.3f}' for q in ranges)+' u', flush=True)

    def envelope(parts, ids=None):
        # Many stationary collar parcels recur in every pose. Strip exact
        # duplicates without averaging the extrema of any moving section.
        all_v = np.concatenate(parts)
        seen, first = np.unique(all_v.round(7), axis=0, return_index=True)
        tag = np.concatenate(ids)[first] if ids is not None else None
        return seen, seen.min(1), seen.max(1), tag

    def sweep(data, angles):
        v,lo,hi,tags = data
        worst = (.35,)
        fails = []
        for stance, pitch, yaw in angles:
            delta = F.fold(stance,pitch,yaw)
            # Inverting the common rigid rotation on the head leaves the
            # relative poses and SAT result exactly the same.
            h = F.rotate(F.head_in_body(stance,pitch,yaw),pivot,-delta)
            a,b = h.min(0)-.30,h.max(0)+.30
            k = np.flatnonzero((lo[:,0]<b[0])&(hi[:,0]>a[0])&(lo[:,1]<b[1])
                               &(hi[:,1]>a[1])&(lo[:,2]<b[2])&(hi[:,2]>a[2]))
            if len(k):
                d = sat(v[k],np.broadcast_to(h,(len(k),8,3)))
                i = int(d.argmin())
                case = (float(d[i]), stance, pitch, yaw, delta,
                        names[tags[k[i]]] if tags is not None else '')
                worst = min(worst, case)
                if case[0] <= .015:
                    fails.append(case)
        return worst, sorted(fails)

    x = itertools.product((0.,.5,1.), range(-90,91,15), range(-90,91,15))
    core, f1 = sweep(envelope(cage,samples),x)
    y = itertools.product((0.,.25,.5,.75,1.), np.linspace(-90,90,25), np.linspace(-90,90,25))
    dense, f2 = sweep(envelope(selected),y)
    print(f'Cabeza: {checked} poses × 507 orientaciones; 3.125 orientaciones sobre {len(selected)} poses de control. '
          f'Holgura mínima {min(core,dense)[0]:+.3f} u.', flush=True)
    assert not f1 and not f2, (f1[:12], f2[:12])
    assert F.fold(0,0,0) == 0., 'el ajuste altera el reposo neutral'


def visor_fit(geo, runtime):
    check_visor(geo, runtime)
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    assert json.loads(re.search(r'^const INLINE_FIT = (.+);$',html,re.M)[1]) == F.profile()
    tests = [dict(clip=n,t=.37*c['animation_length'],aim=aim) for n,c in runtime['animations'].items()
             for aim in ((0,0,0),(1.,0,0),(0.,67.5,-37.5),(1.,37.5,52.5))]
    run = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,check=True,
                         input=json.dumps(dict(geo=geo,clips=runtime,tests=tests,fit=F.profile())),
                         capture_output=True,text=True)
    for test,actual in zip(tests,json.loads(run.stdout)['poses'],strict=True):
        clip = T.prepare_clip(runtime['animations'][test['clip']])
        expected = P.matrices(F.wearer_pose(P.pose_at(geo,clip,test['t']),*test['aim']))
        assert all(np.allclose(expected[n], np.array(v).reshape(4,4), atol=1e-10, rtol=0)
                   for n,v in actual['byName'].items()), test
    print('Visor: 32 poses adicionales con ajuste al portador coinciden con el verificador')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--candidate', action='store_true')
    cli.add_argument('--fit-only', action='store_true')
    cli.add_argument('--quick', action='store_true', help='no cruza todos los blends con la rejilla de cabeza')
    a = cli.parse_args()
    geo = G.build_base()['minecraft:geometry'][0]
    atlas, glow, layout = S.map_surface(geo, paint=True)
    runtime = A.build(geo)
    if a.fit_only:
        fit_check(geo, runtime['animations'], a.quick)
        return
    oldbb = json.loads((BASELINE/'CAPA_v1.60.0.bbmodel').read_text())
    if a.candidate:
        model = B.build(geo, atlas, runtime)
    else:
        assert P.load(P.ARMOR_GEO) == geo and json.loads(A.ANIM.read_text()) == runtime
        assert np.array_equal(np.asarray(atlas), np.asarray(Image.open(P.ARMOR_TEX).convert('RGBA')))
        model = json.loads(B.DOC.read_text())
    protection(geo, atlas, glow, runtime, a.candidate)
    assert layout['density'][R.CLOTH] >= 3.30 and layout['cards'] >= 175, layout
    print(f"{layout['cards']} cartas UV, {layout['density'][R.CLOTH]:.2f} texels/u en el paño")
    visual(geo, atlas)
    check_editor(oldbb, model, geo, atlas, runtime)
    check_tracks(runtime, json.loads(OLD_CLIPS.read_text()), model)
    fit_check(geo, runtime['animations'], a.quick)
    if not a.candidate:
        visor_fit(geo, runtime)


if __name__ == '__main__':
    main()
