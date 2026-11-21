#!/usr/bin/env python3
"""Measure the .28 cloth polish against the exact .27 in real F5 routes."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from verify_forge_gaits import SLOTS, crop, gait, head_clearance, shoulder, table, text
from verify_forge_placement import FIXTURES, front_coverage
from verify_forge_walk import pairs, points, read

# Match player inputs in CapeWalkProbe, not the frame count or wall clock.
EVENTS = (('arranque', 20, 36), ('freno-carrera', 129, 150),
          ('correr-andar', 194, 207), ('freno-paso', 208, 225))
HOLDS = (('reposo', 230, 302, 72, 6), ('agachado', 318, 370, 52, 4))
ROUTES = ('pecho', 'curios', 'steve-pecho', 'steve-curios')


def rates(data, start, end):
    t = data['time']
    use = pairs(t, start, end)
    assert use.sum() >= 20, (start, end, 'faltan pares de tiempo en Forge', use.sum())
    dt = np.diff(t)[use]
    hem = np.linalg.norm(np.diff(points(data, 'tip'), axis=0)[use], axis=1) / dt
    run_rate = np.abs(np.diff(data['run'])[use]) / dt
    return np.array([np.quantile(hem, .90), hem.max(), run_rate.max()])


def transitions(root, reference):
    rows = []
    for route in ROUTES:
        file = f'paso-{route}.tsv'
        old, now = (read(d / file) for d in (reference, root))
        assert np.isfinite(now['clearance_pace']).all(), file
        t = now['time']
        use = pairs(t)
        speed = np.diff(now['clearance_pace'])[use] / np.diff(t)[use]
        assert speed.max() < .087 and speed.min() > -.055, (route, speed.min(), speed.max())
        settled = (t >= 221) & (t < 225)
        assert settled.any() and now['clearance_pace'][settled].max() < .27, (route, 'el dobladillo no se asienta')
        assert np.ptp(now['collar_z']) < .006, (route, 'se movió el asiento al cambiar el paso')
        for name, begin, end in EVENTS:
            a, b = (rates(d, begin, end) for d in (old, now))
            rows.append((route, name, *(f'{v:.4f}' for v in np.c_[a,b].ravel())))
            print(f'::notice title=Transiciones en Forge::{route}/{name}: punta p90 {a[0]:.3f} → {b[0]:.3f}u/tick; '
                  f'pico {a[1]:.3f} → {b[1]:.3f}u/tick; cambio de peso de carrera {a[2]:.3f} → {b[2]:.3f}/tick.', flush=True)
            if name == 'correr-andar':
                # The periodic motion of the walk is supposed to come back.
                # Test the change of its weight independently of that wave.
                assert b[2] < .81 * a[2] and b[1] <= a[1] + .18, (route, name, a, b)
            else:
                assert b[0] < .98 * a[0] and b[1] <= a[1] + .08, (route, name, a, b)
    table(root/'transiciones-forge.tsv', 'ruta fase punta_p90_base_u_tick punta_p90_u_tick '
          'punta_pico_base_u_tick punta_pico_u_tick cambio_carrera_base_tick cambio_carrera_tick', rows)


def cycle(data, start, stop, duration, crouched):
    d = data[(data['time'] >= start) & (data['time'] < stop)]
    assert len(d) >= 90 and np.ptp(d['time']) > duration - 2, ('falta un ciclo real', start, len(d))
    assert (d['crouching'] == crouched).all() and (d['sneak'] == int(crouched)).all(), start
    assert d['leg_speed'].max() < .012 and (d['walk'] + d['run']).max() < .002, start
    assert np.ptp(d['collar_z']) < .006, (start, 'deriva en la costura')
    phase = 2 * np.pi * (d['age'] % duration) / duration
    basis = np.c_[np.ones(len(d)), np.cos(phase), np.sin(phase), np.cos(2*phase), np.sin(2*phase)]
    angles = np.c_[d['bottom'], d['edge2'] - d['edge9']]
    c, _, rank, _ = np.linalg.lstsq(basis, angles, rcond=None)
    assert rank == 5 and np.isfinite(c).all(), start
    return np.r_[c[0,0], 2 * np.linalg.norm(c[1:3], axis=0)]


def quiet_and_gait(root, reference):
    quiet, stride = [], []
    for slot in SLOTS:
        name = f'paso-{slot}.tsv'
        old, now = (read(p/name) for p in (reference,root))
        assert now['time'][-1] >= 401 and old['time'][-1] >= 401, (slot, 'ruta de reposo incompleta')
        for label, start, stop, duration, _ in HOLDS:
            a, b = (cycle(d, start, stop, duration, label=='agachado') for d in (old, now))
            quiet.append((slot,label,*(f'{v:.4f}' for v in np.c_[a,b].ravel())))
            print(f'::notice title=Reposo y agachado en Forge::{slot}/{label}: ángulo medio del dobladillo {a[0]:.2f} → {b[0]:.2f}°; '
                  f'oscilación {a[1]:.2f} → {b[1]:.2f}°; alternancia de dos puntas {a[2]:.2f} → {b[2]:.2f}°.', flush=True)
            if label == 'reposo':
                assert 1.10*a[1] <= b[1] <= 3.55 and b[2] >= 1.45*a[2], (slot, label, a, b)
            else:
                assert a[0] - 3.1 <= b[0] <= a[0] - 2.4 and 1.5 <= b[1] < .81*a[1], (slot, label, a, b)
        for start in (310,382):
            weight = now['sneak'][(now['time'] >= start) & (now['time'] < start + 8)]
            assert np.count_nonzero((weight > .01) & (weight < .99)) >= 8, (slot, start, 'agachado sin mezcla')
        assert now['sneak'][now['time'] > 394].max() == 0, (slot, 'no volvió a reposo')
        for walking in (True, False):
            a, b = (gait(p/name, walking) for p in (reference,root))
            label = 'caminar' if walking else 'correr'
            np.testing.assert_allclose(b,a,atol=.14,rtol=.04,err_msg=f'{slot}: cambió la zancada estable ({label})')
            stride.append((slot,label,*(f'{v:.4f}' for v in np.c_[a,b].ravel())))
    table(root/'reposo-agachado-forge.tsv', 'ranura postura medio_base_deg medio_deg '
          'arco_base_deg arco_deg alternancia_base_deg alternancia_deg', quiet)
    table(root/'ritmo-forge.tsv', 'ranura marcha alternancia_base_deg alternancia_deg '
          'onda_base_deg onda_deg rebote_base_deg rebote_deg', stride)


def left_fit(root, reference):
    front, turns = [], []
    for fixture in FIXTURES:
        a, pa = shoulder(reference, fixture)
        b, pb = shoulder(root, fixture)
        fa, fb = (front_coverage(p, fixture) for p in (reference,root))
        print(f'::notice title=Hombrera izquierda en Forge::{fixture}: vuelo {a[0]:.3f} → {b[0]:.3f}u, '
              f'canto x99 {a[1]:.1f} → {b[1]:.1f}px, apoyos manga {a[2]:.3f} → {b[2]:.3f}u y tela {a[3]:.3f} → {b[3]:.3f}u.', flush=True)
        np.testing.assert_allclose(pb,pa,atol=.008,rtol=0,err_msg=f'{fixture}: cambió la otra hombrera')
        assert abs(b[0]-a[0]) < .19 and abs(b[1]-a[1]) <= 3, (fixture, 'se perdió el contorno frontal', a, b)
        assert (b[2:] >= [.80*a[2], .75*a[3]]).all() and (fb[:,0] >= .80*fa[:,0]).all(), (fixture, 'perdió apoyo frontal', a, b, fa, fb)
        front.append((fixture,*(f'{v:.4f}' for v in np.c_[a,b].ravel())))
    for slot in SLOTS:
        a, b = (head_clearance(p, slot) for p in (reference,root))
        for name in a:
            turns.append((slot,name,*(f'{v:.4f}' for v in np.c_[a[name],b[name]].ravel())))
            if name == 'giro':
                print(f'::notice title=Giro de cabeza en Forge::Alex {slot}: cajas de cabeza {a[name][0]:.3f} → {b[name][0]:.3f}u '
                      f'y capa exterior {a[name][1]:.3f} → {b[name][1]:.3f}u.', flush=True)
                assert a[name][0] > .75 and (b[name] < [.70*a[name][0], .84*a[name][1]]).all(), (slot, name, a[name], b[name])
            else:
                assert (b[name] <= a[name] + .05).all(), (slot, name, a[name], b[name])
    table(root/'hombrera-forge.tsv', 'montaje vuelo_base_u vuelo_u x99_base_px x99_px '
          'manga_base_u manga_u tela_base_u tela_u', front)
    table(root/'hombrera-mirada-forge.tsv', 'ranura postura cabeza_base_u cabeza_u capa_pelo_base_u capa_pelo_u', turns)


def turn_gallery(root, reference):
    w,h = 266,224
    board = Image.new('RGB', (4*(w+8)+16, 118+2*(h+41)+12), '#17121d')
    pen = ImageDraw.Draw(board)
    text(pen,(18,11),'Hombrera izquierda al girar · Forge F5',28,bold=True)
    text(pen,(18,51),'Alex · misma postura y cámara en cada pareja. De frente, la izquierda del portador queda a la derecha.',15,'#d3bfd6')
    for j, slot in enumerate(SLOTS):
        y = 118 + j*(h+41)
        text(pen,(12,y-19),slot.upper(),13,bold=True)
        for i,(shot,label) in enumerate(((f'posicion-alex-{slot}-frente.png','De frente'),
                                        (f'revision-alex-{slot}-giro-00.png','Giro hacia hombro'))):
            for k,(version, directory) in enumerate((('1.67.27',reference),('1.67.28',root))):
                x = 12 + (2*i+k)*(w+8)
                if j == 0:
                    text(pen,(x+2,77),f'{label} · v{version}',14, '#e7b9d6' if k==0 else '#a9dfd7', True)
                board.paste(crop(directory/shot,w,h,.05,.68), (x,y))
    board.save(root/'comparacion-giro-forge.jpg',quality=94,optimize=True)


def motion_gallery(root, reference, slot, name, title, track, segments):
    w,h = 227,305
    frames, delays = [], []
    for label, start, stop, period in segments:
        base = Image.new('RGB',(2*w+26,h+111), '#17121d')
        pen = ImageDraw.Draw(base)
        text(pen,(10,10),title,23,bold=True)
        text(pen,(10,42),f'Alex / {slot.upper()} · {label}',14,'#d3bfd6')
        text(pen,(10,68),'v1.67.27',15,'#e7b9d6',True)
        text(pen,(16+w,68),'v1.67.28',15,'#a9dfd7',True)
        paths = {t: [d/f'paso-{slot}-{track}-{t:03d}.png' for d in (reference,root)] for t in range(start,stop,period)}
        actual = [t for t,p in paths.items() if all(f.is_file() for f in p)]
        assert len(actual) >= len(paths)-2, (slot,label,'faltan capturas reales',actual)
        for t, next_tick in zip(actual,actual[1:]+[stop],strict=True):
            frame = base.copy()
            for i,path in enumerate(paths[t]):
                frame.paste(crop(path,w,h,0,1),(10+i*(w+6),90))
            frames.append(frame)
            delays.append((next_tick-t)*50)
    frames[0].save(root/f'comparacion-{name}-{slot}-forge.gif',save_all=True,
                   append_images=frames[1:],duration=delays,loop=0,optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('reference', type=Path)
    args = ap.parse_args()
    left_fit(args.shots, args.reference)
    quiet_and_gait(args.shots, args.reference)
    transitions(args.shots, args.reference)
    turn_gallery(args.shots, args.reference)
    for slot in SLOTS:
        motion_gallery(args.shots,args.reference,slot,'calma','Reposo y agachado · Forge F5','calma',
                       [(label.upper(),start,stop,period) for label,start,stop,_,period in HOLDS])
        motion_gallery(args.shots,args.reference,slot,'freno','Carrera, paso y frenada · Forge F5','cambio',
                       [('carrera → paso → reposo',192,218,2)])


if __name__ == '__main__':
    main()
