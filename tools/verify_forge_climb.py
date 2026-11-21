#!/usr/bin/env python3
"""Isolate ladder support and the drop just after release in the real Forge client."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from preview_cloth import mod_version
from verify_forge_walk import pairs, points, read

SLOTS = ('pecho', 'curios')
PHASES = ('subida', 'pausa', 'desliz', 'caida')


def route(data, label):
    time, y, dy = (data[name] for name in ('time', 'height', 'step_y'))
    ladder, ground, shift = (data[name].astype(bool) for name in ('ladder', 'ground', 'shift'))
    stage = data['stage']
    assert np.all(np.diff(time) >= 0) and time[0] < 2 and time[-1] >= 132, (label, 'reloj del recorrido')
    assert all(np.isfinite(data[c]).all() for c in data.dtype.names if c != 'stage'), (label, 'muestra no finita')
    assert np.all((data['fall'] >= 0) & (data['fall'] <= 1)), (label, 'peso inválido')
    assert y.max() > 3.8 and ground[0] and ground[-1] and not ladder[0] and not ladder[-1], (
        label, 'no completó el recorrido', y[0], y.max(), y[-1])
    assert list(dict.fromkeys(stage)) == ['subida', 'pausa', 'desliz', 'salida'], (label, 'faltan fases')
    assert np.ptp(data['collar_z']) < .025, (label, 'se desplazó el asiento')
    assert (data['air'] == 0).all() and (data['swim'] == 0).all() and (data['run'] == 0).all(), (
        label, 'otro clip contaminó el ensayo en la escalera')
    supported = ladder & ~ground
    masks = ((stage == 'subida') & supported & (dy > .09) & (y > 1.2),
             (stage == 'pausa') & supported & shift & (np.abs(dy) < .01),
             (stage == 'desliz') & supported & ~shift & (dy < -.13),
             (stage == 'salida') & ~ladder & ~ground & (y > .06))
    for name, mask, count in zip(PHASES, masks, (16, 13, 8, 6), strict=True):
        assert mask.sum() >= count and np.ptp(time[mask]) > 1.5, (label, name, 'faltan fracciones', mask.sum())
    assert y[masks[0]].max() - y[masks[0]].min() > 2.5, (label, 'no subió la escalera')
    assert np.ptp(y[masks[1]]) < .30 and np.ptp(y[masks[2]]) > .55, (label, 'no se sostuvo o no resbaló en la escalera')
    assert data['vertical'][masks[-1]].min() < -.32, (label, 'no quedó en caída libre')
    return dict(zip(PHASES, masks, strict=True))


def report(root, slot, version, reference):
    data = read(root / f'escalera-{slot}.tsv')
    label = f'{version} {slot}'
    masks = route(data, label)
    rows = []
    for phase, use in masks.items():
        fall, top = data['fall'][use], data['top'][use]
        rows.append([version, slot, phase, int(use.sum()), fall.mean(), fall.max(), top.mean(), top.max()])
    supports = data['fall'][masks['subida'] | masks['pausa'] | masks['desliz']]
    assert data['fall'][masks['caida']].max() > .36, (label, 'el paño no se abre al soltar la escalera')
    if reference:
        assert supports.min() >= .219 and data['fall'][masks['desliz']].mean() > .24, (
            label, 'no se reprodujo el clip de caída en la escalera')
    else:
        verdict(data, masks, supports, label)
    by_phase = {r[2]: r for r in rows}
    print(f'{label}: FALL medio en subida / pausa / desliz / caída '
          + ' / '.join(f'{by_phase[phase][4]:.1%}' for phase in PHASES)
          + f'; pico de FALL tras soltarse {by_phase["caida"][5]:.1%}; {len(data)} cuadros F5.', flush=True)
    return data, masks, rows


def verdict(data, masks, supports, label):
    assert supports.max() < 1e-8, (label, 'se abrió en un tramo sostenido por la escalera', supports.max())
    time, fall = data['time'], data['fall']
    drop = np.flatnonzero(masks['caida'])
    landing = np.flatnonzero(data['ground'][drop[-1]:])[0] + drop[-1]
    # Read thresholds in the actual ladder/ground frames, not just on key input.
    settled = time >= time[landing] + 8
    assert settled.any() and fall[settled].max() < 1e-8, (label, 'se quedó abierta en el suelo')
    select = pairs(time, 80, time[landing] + 8)
    dt = np.diff(time)[select]
    slew = np.diff(fall)[select] / dt
    assert dt.size >= 35 and slew.max() <= .140001 and slew.min() >= -.160001, (
        label, 'perdió la transición gradual al salir de la escalera')
    assert np.linalg.norm(np.ptp(points(data, 'tip')[masks['subida']], axis=0)) > .1, (
        label, 'la punta quedó rígida durante la subida')


def save(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['version','ranura','fase','cuadros','caida_media','caida_pico','bisagra_media_deg','bisagra_pico_deg'])
        for row in rows:
            writer.writerow([*row[:4], *(f'{v:.6f}' for v in row[4:])])


def comparison(root, baseline, curves, version):
    canvas = Image.new('RGB', (1450, 724), '#15111d')
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('DejaVuSans-Bold.ttf', 30)
    medium = ImageFont.truetype('DejaVuSans.ttf', 18)
    small = ImageFont.truetype('DejaVuSans.ttf', 14)
    text, soft, old, new = '#f6ecf5', '#cebbd6', '#f4a4ca', '#97e2da'
    pen.text((24, 16), 'El manto al bajar de una escalera', fill=text, font=font)
    pen.text((24, 59), 'Alex en F5 · Forge 1.20.1 · v1.67.25 frente a ' + version, fill=soft, font=medium)
    for x, heading in ((24, 'DESLIZÁNDOSE CON APOYO'), (482, 'EN CAÍDA LIBRE'), (964, 'PESO DEL CLIP DE CAÍDA (FALL)')):
        pen.text((x, 102), heading, fill=soft, font=small)
    for j, slot in enumerate(SLOTS):
        y = 154 + 269*j
        pen.text((24, y-25), slot.upper(), fill=text, font=medium)
        for k, pose in enumerate(('desliz', 'caida')):
            for i, (shots, label, color) in enumerate(((baseline, 'v1.67.25', old), (root, version, new))):
                x = 24 + 458*k + 221*i
                with Image.open(shots / f'escalera-{slot}-{pose}.png') as frame:
                    crop = ImageOps.fit(frame.convert('RGB'), (212, 210), Image.Resampling.LANCZOS)
                canvas.paste(crop, (x, y))
                pen.text((x, y+214), label, fill=color, font=small)
        x0, y0, w, h = 1015, y+28, 404, 143
        t0, t1 = 8, 122

        def x(t):
            return x0 + (t - t0) / (t1 - t0) * w

        for mark in (0, .25, .50, .75, 1):
            sy = y0+h-mark*h
            pen.line((x0, sy, x0+w, sy), fill='#3c3247')
            pen.text((x0-9, sy), f'{mark:.0%}', fill=soft, font=small, anchor='rm')
        for tick, label in ((60, 'pausa'), (82, 'desliz'), (91, 'retroceso')):
            sx = x(tick)
            pen.line((sx, y0, sx, y0+h), fill='#696073')
            pen.text((sx-2, y0+h+9 if tick != 91 else y0+h+26), label, fill=soft, font=small, anchor='mt')
        for (data, mask), color in zip(curves[slot], (old, new), strict=True):
            time, fall = data['time'], data['fall']
            view = (time >= t0) & (time <= t1)
            pen.line(list(zip(x(time[view]), y0+h-fall[view]*h, strict=True)), fill=color, width=3)
            free = np.flatnonzero(mask['caida'])[0]
            sx, sy = x(time[free]), y0+h-fall[free]*h
            pen.ellipse((sx-4, sy-4, sx+4, sy+4), fill=color)
    pen.text((24, 689), '● Primer cuadro sin apoyo en la caída  ·  Misma secuencia de teclas en recorridos independientes.',
             fill=soft, font=small)
    canvas.save(root / 'comparacion-escalera-forge.jpg', quality=94, optimize=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots', type=Path)
    cli.add_argument('--baseline-shots', type=Path, help='capturas de v1.67.25 en las dos ranuras')
    args = cli.parse_args()
    version = 'v' + mod_version()
    rows, curves = [], {}
    for slot in SLOTS:
        if args.baseline_shots:
            old, old_masks, old_rows = report(args.baseline_shots, slot, 'v1.67.25', reference=True)
            rows.extend(old_rows)
        data, masks, current_rows = report(args.shots, slot, version, reference=False)
        rows.extend(current_rows)
        if args.baseline_shots:
            curves[slot] = ((old, old_masks), (data, masks))
    save(args.shots / 'escalera-forge.tsv', rows)
    if args.baseline_shots:
        comparison(args.shots, args.baseline_shots, curves, version)
