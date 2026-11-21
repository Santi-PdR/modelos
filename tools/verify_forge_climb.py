#!/usr/bin/env python3
"""Isolate ladder support and the drop just after release in the real Forge client."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from verify_forge_walk import points, read

SLOTS = ('pecho', 'curios')
PHASES = ('subida', 'pausa', 'desliz', 'caida')


def route(data, label):
    time, y, dy = (data[name] for name in ('time', 'height', 'step_y'))
    ladder, ground, shift = (data[name].astype(bool) for name in ('ladder', 'ground', 'shift'))
    stage = data['stage']
    assert np.all(np.diff(time) >= 0) and time[0] < 2 and time[-1] >= 132, (label, 'reloj del recorrido')
    assert np.isfinite(y).all() and np.isfinite(points(data, 'tip')).all(), (label, 'muestra no finita')
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
    by_phase = {r[2]: r for r in rows}
    print(f'{label}: FALL medio en subida / pausa / desliz / caída '
          + ' / '.join(f'{by_phase[phase][4]:.1%}' for phase in PHASES)
          + f'; pico de FALL tras soltarse {by_phase["caida"][5]:.1%}; {len(data)} cuadros F5.', flush=True)
    return data, masks, rows


def save(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['version','ranura','fase','cuadros','caida_media','caida_pico','bisagra_media_deg','bisagra_pico_deg'])
        for row in rows:
            writer.writerow([*row[:4], *(f'{v:.6f}' for v in row[4:])])


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots', type=Path)
    args = cli.parse_args()
    results = [report(args.shots, s, 'v1.67.25', reference=True)[2] for s in SLOTS]
    save(args.shots / 'escalera-forge.tsv', [row for result in results for row in result])
