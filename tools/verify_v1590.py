#!/usr/bin/env python3
"""Regresión v1.59.0: base exacta, silueta, materiales, rig, clips y visor.

Sin cliente Minecraft: la holgura se mide contra torso/ropa y cabeza neutra
con muestreo de las ocho pistas, inflate, pivotes y un margen rotacional.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import itertools
import json
import re
import subprocess

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_motion as M
import cape_tracks as T
import preview_cloth as P
from cape_atlas_v1230 import build_clean_atlas
from present_v1590 import BACKUP, BASE_GEO, BASE_TEX, fit_frame


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_assets(atlas, glow, *, candidate):
    for line in (BACKUP / "SHA256SUMS.txt").read_text().splitlines():
        sha, name = line.split("  ", 1)
        # Respaldo exacto: incluye las fuentes, el GEO y los clips anteriores.
        assert digest(BACKUP / name) == sha, name
        if not candidate and name.startswith(("geo/", "textures/", "animations/")):
            live = P.ASSETS / name
            if live not in (P.ARMOR_TEX, P.ARMOR_GEO, A.ANIM):
                assert live.read_bytes() == (BACKUP / name).read_bytes(), name
    cur, old = np.asarray(atlas), np.asarray(Image.open(BASE_TEX).convert("RGBA"))
    mask = np.asarray(glow.convert("RGBA"))[..., 3] > 0
    original_mask = BASE_TEX.with_stem(BASE_TEX.stem + "_glowmask")
    assert np.array_equal(np.asarray(glow), np.asarray(Image.open(original_mask).convert("RGBA")))
    assert cur.shape == (128, 128, 4) and np.all(cur[..., 3] == 255)
    assert np.array_equal(cur[mask], old[mask]) and int(mask.sum()) == 3380, "alteración de energía"
    d = np.abs(cur[..., :3].astype(int) - old[..., :3]).max(axis=2)
    cloth, cowl = d[:96, :96], d[96:, :96]
    steel = np.r_[d[:16,96:].ravel(), d[64:96,96:].ravel()]
    assert (cloth > 0).sum() >= 5900 and (cloth >= 20).sum() >= 2400
    assert (cowl > 0).sum() >= 1450 and (steel >= 20).sum() >= 325
    print(f"RGB: {int((d>0).sum())} texels, {int((cloth>0).sum())} de tela/forro, "
          f"{int((steel>0).sum())} de acero; 3380 de energía intactos, alpha 255")


def geometry_change(old, new, atlas):
    size, bg = 460, (3, 9, 87)
    for yaw in (0, -32, 180):
        pitch = 0 if yaw == 0 else 9
        frame = fit_frame([old, new], yaw, pitch, size, margin=20)
        imgs = [np.asarray(P.render(g, a, P.effective_hidden(g), yaw=yaw, pitch=pitch,
                                   size=size, bg=bg, frame=frame))
                for g, a in ((old, BASE_TEX), (new, atlas))]
        m1, m2 = [(im != bg).any(axis=-1) for im in imgs]
        both = m1 & m2
        change = (np.abs(imgs[0].astype(int) - imgs[1].astype(int)).max(axis=-1)[both] >= 20).mean()
        silhouette = (m1 ^ m2).sum() / (m1 | m2).sum()
        assert change > .65 and silhouette > .20, (yaw, change, silhouette)
        print(f"Misma cámara {yaw:+}°: ΔRGB ≥20/255 en {change:.1%} de la superficie común; "
              f"silueta distinta en {silhouette:.1%} de la unión")
        if yaw == 0:
            x = int(round(size / 2 - frame[0] * frame[2]))
            y = int(round(size / 2 - (5.5 - frame[1]) * frame[2]))
            gaps = []
            widths = []
            for mask in (m1, m2):
                hits = np.flatnonzero(mask[y])
                gap = 0.0 if mask[y, x] else (hits[hits > x].min() - hits[hits < x].max() - 1) / frame[2]
                gaps.append(gap)
                widths.append(np.ptp(np.nonzero(mask)[1]) / frame[2])
            assert gaps[1] - gaps[0] > 3.0 and widths[1] - widths[0] > 1.6
            print(f"Ancho {widths[0]:.2f}→{widths[1]:.2f} u; hueco central a Y=5.5: {gaps[0]:.2f}→{gaps[1]:.2f} u")


def check_editor(old, bb, geo, atlas, runtime):
    for part in ("groups", "elements"):
        prev = {e['name']: e['uuid'] for e in old[part]}
        curr = {e['name']: e['uuid'] for e in bb[part]}
        assert all(curr.get(name) == uid for name, uid in prev.items()), f"UUID cambiado ({part})"
        assert len(set(curr.values())) == len(curr) == len(bb[part])
    assert len(bb["groups"]) == 225 and len(bb["elements"]) == 159
    hidden = P.effective_hidden(geo)
    assert {e["name"] for e in bb["elements"] if e["visibility"]} == {
        '{}_{}'.format(*G.legacy_element(b['name'], i)) for b in geo['bones']
        if b['name'] not in hidden for i in range(len(b.get('cubes', ())))}
    g_by_uid = {g["uuid"]: g for g in bb["groups"]}
    e_by_uid = {e["uuid"]: e for e in bb["elements"]}
    members = {}

    def walk(node, parent=None):
        g = g_by_uid[node["uuid"]]
        assert g["name"] not in members
        members[g["name"]] = parent, [e_by_uid[k] for k in node["children"] if isinstance(k, str)]
        for kid in node["children"]:
            if isinstance(kid, dict):
                walk(kid, g["name"])

    for root in bb["outliner"]:
        walk(root)
    ids = {g['name']: g for g in bb['groups']}
    for b in geo['bones']:
        name = b['name']
        parent, elements = members[name]
        pivot = np.asarray(b.get("pivot", (0, 0, 0))) * [-1, 1, 1]
        expected_basis = np.asarray(b.get("rotation", (0, 0, 0))) * [-1, -1, 1]
        assert parent == b.get('parent') and ids[name]['origin'] == list(pivot)
        assert ids[name]['rotation'] == list(expected_basis), name
        if elements:
            assert len(elements) == len(b['cubes'])
            for e, c in zip(elements, b['cubes']):
                x, y, z = c['origin']; w, h, d = c['size']
                assert np.allclose(e['from'], [-x-w,y,z], atol=5e-5, rtol=0)
                assert np.allclose(e['to'], [-x,y+h,z+d], atol=5e-5, rtol=0)
                assert c.get('inflate', 0) == e['inflate']
                assert np.allclose(e['rotation'], np.asarray(c.get('rotation', (0,0,0))) * [-1,-1,1], atol=5e-5)
                if 'pivot' in c:
                    assert e['origin'] == list(np.asarray(c['pivot']) * [-1,1,1])
                for fn, uv in c['uv'].items():
                    u, v = uv['uv']; uw, vh = uv['uv_size']
                    desired = [u, v, u+uw, v+vh]
                    if fn in ('up','down'):
                        desired = desired[2:] + desired[:2]
                    assert np.allclose(e['faces'][fn]['uv'], desired, atol=.00051, rtol=0)
    data = base64.b64decode(bb['textures'][0]['source'].split(',',1)[1])
    image = Image.open(io.BytesIO(data)).convert('RGBA')
    assert image.size == (128,128) and np.array_equal(np.asarray(image), np.asarray(atlas))
    assert bb == B.build(geo, atlas, runtime), "el export no es reproducible"
    print("Blockbench: 132 cubos visibles como en el GEO, 27 anclas ocultas, UV/signos/pivotes y UUIDs verificados")


def check_tracks(runtime, base, bb):
    clips, prev = runtime['animations'], base['animations']
    assert set(clips) == set(prev) == set(A.STYLE_BY_CLIP)
    out = {a['name']: a for a in bb['animations']}
    styles = dict(B.ANIMATION_SPECS)
    worst = 0.0
    for clip, style in A.STYLE_BY_CLIP.items():
        c, p = clips[clip], prev[clip]
        length = c['animation_length']
        assert c['loop'] and length == p['animation_length']
        assert {n:{k:v for k,v in t.items() if k in ('position','scale')}
                for n,t in c['bones'].items() if 'position' in t or 'scale' in t} == {
               n:{k:v for k,v in t.items() if k in ('position','scale')}
                for n,t in p['bones'].items() if 'position' in t or 'scale' in t}, (clip, 'cambió posición/escala')
        edit = out[next(k for k, v in styles.items() if v == style)]
        assert edit['length'] == length and edit['loop'] == 'loop'
        assert {v['name'] for v in edit['animators'].values()} == {n for n in c['bones'] if A.animated(n)}
        for animator in edit['animators'].values():
            name = animator['name']
            for ch, raw in c['bones'][name].items():
                keys = [k for k in animator['keyframes'] if k['channel'] == ch]
                times, values, _ease = T.prepare(raw)
                sign = {'rotation':[-1,-1,1], 'position':[-1,1,1], 'scale':[1,1,1]}[ch]
                vals = np.array(values) * sign
                actual = np.array([[float(k['data_points'][0][axis]) for axis in 'xyz'] for k in keys])
                assert [k['time'] for k in keys] == list(times) and np.array_equal(actual, vals)
                if ch != 'rotation':
                    assert all(k['interpolation'] == 'linear' for k in keys)
                    continue
                assert len(keys) == A.SAMPLES + 1 and times[0] == 0 and times[-1] == length
                assert np.array_equal(vals[0], vals[-1])
                assert all(k['interpolation'] == 'bezier' for k in keys)
                lt = np.array([k['bezier_left_time'] for k in keys]); lv = np.array([k['bezier_left_value'] for k in keys])
                rt = np.array([k['bezier_right_time'] for k in keys]); rv = np.array([k['bezier_right_value'] for k in keys])
                assert np.allclose(lv / lt, rv / rt, atol=.0030, rtol=0)
                assert np.allclose((lv / lt)[-1], (rv / rt)[0], atol=.0030, rtol=0)
                spans = np.diff(times)[:,None]
                assert np.allclose(rt[:-1], spans / 3, atol=1e-7, rtol=0)
                assert np.allclose(lt[1:], -spans / 3, atol=1e-7, rtol=0)
                for x in (.2,.4,.5,.6,.8):
                    # Mangos a tercios => t coincide con la fase del tramo.
                    v = ((1-x)**3*vals[:-1] + 3*x*(1-x)**2*(vals[:-1]+rv[:-1])
                         + 3*x*x*(1-x)*(vals[1:]+lv[1:]) + x**3*vals[1:])
                    worst = max(worst, float(np.abs(v - ((1-x)*vals[:-1] + x*vals[1:])).max()))
    assert worst < .8, worst
    rms = A.ribbon_rms(runtime)
    assert len({round(v, 2) for v in rms.values()}) == 8, rms
    print(f"8 RMS distintos: {', '.join(f'{k[10:]}={v:.3f}°' for k,v in rms.items())}; "
          f"máxima diferencia Bézier/bake entre muestras: {worst:.3f}°")


def separation(a, b):
    """Separating axis para pares de cubos orientados. Positivo = disjuntos."""
    e, f = [x[:,[1,3,4]] - x[:,0,None] for x in (a,b)]
    axes = np.concatenate((e,f,np.cross(e[:,:,None],f[:,None,:]).reshape(len(e),9,3)),axis=1)
    norm = np.linalg.norm(axes,axis=2,keepdims=True)
    axes = axes / np.where(norm > 1e-7,norm,1)
    pa, pb = (x @ axes.transpose(0,2,1) for x in (a,b))
    return np.where(norm[:,:,0]>1e-7,np.maximum(pa.min(1)-pb.max(1),pb.min(1)-pa.max(1)), -100).max(1)


def response(sx, sy, sz):
    """Sondeo de extremos simultáneos de la respuesta Java, no emulación de Minecraft."""
    def angles(name):
        m = M.RIBBON.fullmatch(name)
        if m:
            col, seg = map(int, m.groups())
            r = .35 + .65 * seg / 6
            side = abs(M.side_of(name, col))
            return (4.25 if sx > 0 else -2.41) * r, sy * r * (1+2.6*side), sz * (1.75*r+1.2*side)
        if name.startswith(('v17_cowl_','v18_')):
            return (.53 * sx, 0., .82 * sz)
        if name.startswith('v17_vein_'):
            return (1.50 * sx, .7 * sy, 2.45 * sz)
        return (0,0,0)
    return angles


def check_clearance(geo, clips):
    mats_identity = np.eye(4)
    hidden = P.effective_hidden(geo)
    data = [(b['name'], ci, P.cube_points(c, mats_identity)) for b in geo['bones']
            if b['name'] not in hidden for ci, c in enumerate(b.get('cubes',()))]
    vertices = np.array([v for _,_,v in data])
    names = [n for n,_,_ in data]
    ribbon = {}
    for i,(name, ci, _v) in enumerate(data):
        m = M.RIBBON.fullmatch(name)
        if m:
            col, seg = map(int, m.groups())
            ribbon[col, seg + ci] = i
    a, b = np.array([(ribbon[col,s],ribbon[col,s+1]) for col in range(12) for s in range(6)]).T
    torso, head = (float('inf'),), (float('inf'),)
    gap = -np.inf
    count = 0

    def measure(matrices, label):
        nonlocal torso, head, gap, count
        m = np.array([matrices[n] for n in names])
        points = vertices @ m[:,:3,:3].transpose(0,2,1) + m[:,None,:3,3]
        lo, hi = points.min(1), points.max(1)
        h = np.maximum.reduce((24-hi[:,1], lo[:,2]-4, lo[:,0]-4, -4-hi[:,0]))
        j, i = int(np.argmin(lo[:,2])), int(np.argmin(h))
        torso = min(torso, (float(lo[j,2]), label, names[j]))
        head = min(head, (float(h[i]), label, names[i]))
        gap = max(gap, float(separation(points[a], points[b]).max()))
        count += 1

    measure(P.matrices(geo),'bind')
    variants = [response(*sgn) for sgn in itertools.product((-1,1), repeat=3)]
    for name, clip in clips.items():
        prepared = T.prepare_clip(clip, set(names) | set(M.SECTIONS))
        for i, t in enumerate(np.linspace(0,clip['animation_length'],65)):
            measure(P.matrices(P.pose_at(geo, prepared, t)), f'{name}/{t:.3f}')
            if i % 8 == 0:
                for j, extra in enumerate(variants):
                    measure(P.matrices(P.pose_at(geo, prepared, t, extra)), f'{name}/{t:.3f}+rot{j}')
    assert torso[0] > 2.25 and head[0] > 0, (torso, head)
    assert gap < 0.09, ('gajo muestreado sin unión', gap)
    print(f"Holgura ({count} poses muestreadas): Z mínimo {torso[0]:.3f} u; "
          f"margen de cabeza neutra {head[0]:.3f} u; separación entre tramos (máx.) {gap:+.3f} u")


def check_visor(geo, runtime):
    html = (P.ROOT / 'docs/capa_v1170_visor.html').read_text()
    assert 'fetch(' not in html and '__VERSION__' not in html
    assert json.loads(re.search(r'^const INLINE_GEO = (.+);$',html,re.M)[1])['minecraft:geometry'][0] == geo
    assert json.loads(re.search(r'^const INLINE_ANIMATIONS = (.+);$',html,re.M)[1]) == runtime
    files = json.loads(re.search(r'^const INLINE_IMAGES = (.+);$',html,re.M)[1])
    for name, file in (('armor.png',P.ARMOR_TEX),
                       ('armor_glowmask.png',P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem+'_glowmask')),
                       ('capa_spark_1.png',P.PARTICLE_DIR/'capa_spark_1.png')):
        assert base64.b64decode(files[name].split(',',1)[1]) == file.read_bytes()
    filename = re.escape(B.DOC.name)
    rawbb = re.search(r'href="data:[^;]+;base64,([^"]+)" download="' + filename + r'"',html)[1]
    assert base64.b64decode(rawbb) == B.DOC.read_bytes()
    clips = runtime['animations']
    tests = [{'clip':name, 't':clip['animation_length']*f} for name,clip in clips.items() for f in (.0,.177,.409,.711)]
    js = subprocess.run(['node', 'tools/check_viewer_pose.js'], cwd=P.ROOT, check=True,
                        input=json.dumps(dict(geo=geo, clips=runtime, tests=tests)),
                        capture_output=True, text=True)
    answer = json.loads(js.stdout)
    hidden = P.effective_hidden(geo)
    assert set(answer['hidden']) == hidden
    prepared = {name:T.prepare_clip(clip) for name,clip in clips.items()}
    for q, got in zip(tests, answer['poses'], strict=True):
        posed = P.pose_at(geo, prepared[q['clip']], q['t'])
        matrices = P.matrices(posed)
        assert all(np.allclose(matrix,np.array(got['byName'][n]).reshape((4,4)),atol=1e-10,rtol=0)
                   for n,matrix in matrices.items())
        expected = P.collect(posed, hidden)[::37]
        for (pts, uv, _), face in zip(expected, got['sampleFaces'], strict=True):
            assert np.allclose(pts,face['pts'],atol=1e-10,rtol=0)
            assert np.allclose(uv,face['uvs'],atol=1e-10,rtol=0)
    print('Visor offline: atlas/GEO/clips/BBModel embebidos y 32 poses intermedias idénticas al muestreo Python')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--candidate',action='store_true')
    args = cli.parse_args()
    atlas, glow = build_clean_atlas()
    oldgeo, oldbb, oldanim = P.load(BASE_GEO), read(BACKUP / 'CAPA_v1.58.0.bbmodel'), read(A.BASE_ANIM)
    if args.candidate:
        geo = G.build()['minecraft:geometry'][0]
        runtime = A.build(geo)
        bb = B.build(geo,atlas,runtime)
    else:
        geo, runtime, bb = P.load(P.ARMOR_GEO), read(A.ANIM), read(B.DOC)
        assert geo == G.build()['minecraft:geometry'][0] and runtime == A.build(geo)
        assert np.array_equal(np.asarray(atlas),np.asarray(Image.open(P.ARMOR_TEX).convert('RGBA')))
    assert [b['name'] for b in geo['bones']] == [b['name'] for b in oldgeo['bones']]
    assert sum(len(b.get('cubes',())) for b in geo['bones']) == 270
    check_assets(atlas,glow,candidate=args.candidate)
    geometry_change(oldgeo,geo,atlas)
    check_editor(oldbb,bb,geo,atlas,runtime)
    check_tracks(runtime,oldanim,bb)
    check_clearance(geo,runtime['animations'])
    if not args.candidate:
        check_visor(geo,runtime)


if __name__ == '__main__':
    main()
