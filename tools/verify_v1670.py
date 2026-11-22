#!/usr/bin/env python3
"""Verify the bloom (including adaptive exposure), embers and packaged assets."""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

import cape_bloom as B
import cape_nocturne as N
import cape_reference as R
import preview_cloth as P
from present_v1600 import NEUTRAL_PALETTE
from texture_pipeline import build_spark_sprites
from verify_v1620 import visor_material
from verify_v1630 import SPARKS, visor_embers
from verify_v1660 import preservation


def assets(geo, core):
    with Image.open(B.HALO) as image:
        halo = np.array(image)
        assert image.mode == 'RGB'
    assert np.array_equal(halo, np.asarray(B.build(geo, core))), 'el halo del mod no se reconstruye desde la máscara'
    hot = np.asarray(core)[..., 3] > 0
    spill = halo.max(axis=2)
    assert hot.sum() == 1848 and 10_000 < (spill > 0).sum() < 18_000
    assert spill.max() <= 114 and ((spill >= 16) & ~hot).sum() > 2500
    covered = 0
    for _, _, _, _, rect in B.faces(geo):
        here = hot[rect]
        if not here.any():
            continue
        band = spill[rect]
        covered += 1
        # At least one darker part of every luminous card must remain outside
        # the bright spill. Black guard pixels separate even adjacent cards.
        assert ((band <= 12) & ~here).any()
        y, x = rect
        assert not halo[y.start-1:y.stop+1, x.start-1].any()
        assert not halo[y.start-1:y.stop+1, x.stop].any()
        assert not halo[y.start-1, x.start:x.stop].any()
        assert not halo[y.stop, x.start:x.stop].any()
    assert covered == 58
    print(f'Halo generado: {covered} cartas de paño, {hot.sum()} texels de núcleo intactos, '
          f'{((spill>=16)&~hot).sum()} texels de halo visible fuera del núcleo.')

    max_alphas = []
    for path, generated in zip(SPARKS, build_spark_sprites(), strict=True):
        with Image.open(P.ASSETS/path) as actual:
            frame = np.array(actual)
            assert np.array_equal(frame, generated), path
        a = frame[..., 3]
        assert a.shape == (16, 16) and not (a[[0,15]].any() or a[:,[0,15]].any())
        assert 10 < ((a >= 32) & (a <= 81)).sum() < 40  # soft alpha visible at 80% lifetime opacity
        assert 10 < (a >= 128).sum() < 36
        max_alphas.append(a.max())
    assert max_alphas[0] > max_alphas[1] > max_alphas[2] > 192
    visor_embers()
    return Image.fromarray(halo)


def samples(geo, albedo, core, halo, java_samples=None, wake_classpath=None):
    # Check the *shipped* offline data first. Existing render/fit tests cover
    # the no-halo mode: A/B is a switch in the same software rasterizer.
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    images = json.loads(re.search(r'^const INLINE_IMAGES = (.+);$', html, re.M)[1])
    assert base64.b64decode(images['armor_halo.png'].split(',', 1)[1]) == B.HALO.read_bytes()
    visor_material(geo, albedo, core)

    p = N.profile()
    assert json.loads(re.search(r'^const INLINE_NOCTURNE = (.+);$', html, re.M)[1]) == p
    rows = np.loadtxt(java_samples).tolist() if java_samples else []
    for light, time, entity, d, e, i, packed in rows:
        dusk = N.darkness(p, light)
        edge, inner, _, _ = N.gains(p, dusk, time, entity)
        assert np.allclose((dusk, edge, inner), (d, e, i), atol=1e-12, rtol=0)
        lo, hi = (int(g*p['GAIN_UNITS']+.5) for g in (edge, inner))
        assert (lo | (hi << 16)) == int(packed)

    wake_rows = []
    if wake_classpath:
        route = [str(p[k]) for k in ('DEMO_START', 'DEMO_STOP', 'DEMO_SECONDS', 'DEMO_SPEED')]
        run = subprocess.run(['java', '-cp', wake_classpath, 'com.capatest.client.CapeHaloWakeTest', '--samples', *route],
                             cwd=P.ROOT, check=True, capture_output=True, text=True)
        wake_rows = [list(map(float, line.split())) for line in run.stdout.splitlines()]
        assert len(wake_rows) == 6*(40*p['DEMO_SECONDS'] + 1)
        for t, water, dusk, entity, edge, inner, packed in wake_rows:
            e, i, _, _ = N.gains(p, dusk, t, entity, N.demo_wake(p, t, water))
            assert np.allclose((edge, inner), (e, i), atol=1e-12, rtol=0)
            lo, hi = (int(g*p['GAIN_UNITS']+.5) for g in (e, i))
            assert (lo | (hi << 16)) == int(packed)

    size = 360
    ref = R.viewer_camera()
    frame = (*ref['center'], size*R.SCALE/max(ref['cropSize']))
    # Also keep a light, relatively matte view and a night view of the lining.
    cases = [('cueva', R.YAW, R.PITCH, .18), ('luz cercana', R.YAW, R.PITCH, .88),
             ('día', R.YAW, R.PITCH, 1), ('tres cuartos', -40, 16, .5), ('forro', 180., 8, .18)]
    tests = [dict(yaw=yaw, pitch=pitch, ambient=a, tint=(.932,.69,.91), mannequin=True,
                  bloom=enabled, dusk=N.darkness(p, 15*(a-.18)/.82), time=.61)
             for _,yaw,pitch,a in cases for enabled in (False,True)]
    wake_cases = [('arranque', .18, p['DEMO_START']+.20), ('frenada', .18, p['DEMO_STOP']+.42),
                  ('día', 1, p['DEMO_STOP']+.42), ('reposo', .18, p['DEMO_SECONDS'])]
    tests += [dict(yaw=R.YAW, pitch=R.PITCH, ambient=a, tint=(.932,.69,.91), mannequin=True,
                   bloom=True, dusk=N.darkness(p, 15*(a-.18)/.82), time=t, wake=enabled)
              for _, a, t in wake_cases for enabled in (False, True)]
    rgb = np.asarray(halo)[..., 0]
    y, x = np.unravel_index(np.argmax(np.where(np.asarray(core)[..., 3] == 0, rgb, 0)), rgb.shape)
    encode = lambda im: base64.b64encode(im.convert('RGBA').tobytes()).decode()
    packet = dict(geo=geo, reference=ref, size=size, atlasSize=512, tests=tests,
                  probe=[x+.5,y+.5], albedo=encode(albedo), emission=encode(core), halo=encode(halo),
                  nocturne=p, nocturneSamples=rows, wakeSamples=wake_rows)
    run = subprocess.run(['node','tools/check_viewer_raster.js'],cwd=P.ROOT,check=True,
                         input=json.dumps(packet),capture_output=True,text=True)
    rendered, energies = [], []
    for i, (test, result) in enumerate(zip(tests, json.loads(run.stdout), strict=True)):
        js = np.frombuffer(base64.b64decode(result['rgba']), np.uint8).reshape(size,size,4)
        assert np.all(js[...,3] == 255)
        assert np.allclose(result['frame'], frame, atol=1e-12, rtol=0)
        rgb = js[..., :3].astype(np.int16)
        rendered.append(rgb)
        # The A/B improvement is not a separate layer in the viewer; compare
        # both modes with an independent rasterization of the same depth test.
        player = [(o,s,c) for (o,s,_),c in zip(P.MANNEQUIN_BOXES, NEUTRAL_PALETTE, strict=True)]
        wake = N.demo_wake(p, test['time']) if test.get('wake') else (0, 0, 0)
        py = P.render(geo, albedo, P.effective_hidden(geo), frame=frame, size=size,
                      bg=(18,14,26), emission=core, yaw=test['yaw'], pitch=test['pitch'],
                      ambient=test['ambient'], tint=test['tint'], mannequin=player,
                      bloom=halo if test['bloom'] else None,
                      halo_gains=N.gains(p, test['dusk'], test['time'], wake=wake))
        diff = np.abs(rgb - np.asarray(py))
        assert (diff <= 1).mean() > .997, (test, diff.mean())
        if not i % 2:
            continue
        baseline = rendered[-2]
        delta = rgb - baseline
        assert delta.min() == 0, 'la luz de borde no debe oscurecer'
        assert not delta[(baseline == (18,14,26)).all(2)].any(), 'el halo salió del contorno'
        if i//2 >= len(cases):
            name = wake_cases[i//2 - len(cases)][0]
            pixels = int((delta.max(2) >= 2).sum())
            if name in ('día', 'reposo'):
                assert not delta.any(), (name, pixels)
            else:
                assert pixels > 200, (name, pixels)
            print(f'Pulso {name}: {pixels} píxeles cambian ≥2/255 a igual pose, sin extender la cobertura.')
            continue
        pixels = int((delta.max(2) >= 8).sum())
        name = cases[i//2][0]
        energies.append(int(delta.sum()))
        visible = pixels < 40 if name == 'forro' else pixels > 400
        assert visible, (test, pixels)
        print(f'{name}, {test["yaw"]:+.0f}°: {pixels} píxeles con halo ≥8/255; '
              'misma opacidad y fondo. JS/Python coinciden.')
    dark, lamp, day, _, _ = energies
    assert dark > 2.7 * max(lamp, day) > 0
    print(f'Cueva: {dark/day:.2f}× el aporte RGB del día, misma pose y fase. '
          'La mitad tapada no cambia en ninguno de los dos órdenes de dibujo.')
    if rows:
        print(f'{len(rows)} muestras de exposición, pulso y UV2 coinciden en Java/JS/Python.')
    if wake_rows:
        print(f'{len(wake_rows)} muestras de arranque/frenada, luz y agua coinciden en Java/JS/Python, incluso antes de cuantizar.')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--nocturne-samples', type=Path, help='muestras TSV de CapeNocturneTest --samples')
    cli.add_argument('--wake-classpath', help='classpath de CapeHaloWakeTest para cotejar el pulso de velocidad')
    args = cli.parse_args()
    preservation(changed=SPARKS)
    geo = P.load(P.ARMOR_GEO)
    with Image.open(P.ARMOR_TEX) as albedo, Image.open(B.CORE) as core:
        assert np.all(np.asarray(albedo)[..., 3] == 255)
        halo = assets(geo, core)
        samples(geo, albedo, core, halo, args.nocturne_samples, args.wake_classpath)


if __name__ == '__main__':
    main()
