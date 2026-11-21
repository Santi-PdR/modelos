#!/usr/bin/env python3
"""Measure cape motion through real jumps and a ledge drop in the torso frame."""
import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from verify_forge_walk import pairs, points, read

SLOTS = ('pecho', 'curios')
CASES = ('salto', 'salto-en-carrera', 'caida-del-borde')


@dataclass(frozen=True)
class Event:
    name: str
    start: int  # first rendered in-air sample
    land: int   # first rendered grounded sample


def events(data, slot):
    t, g, y = (data[c] for c in ('time', 'on_ground', 'height'))
    assert t[0] < 2 and t[-1] >= 169 and (np.diff(t) >= 0).all(), (slot, 'reloj roto')
    assert g[0] == g[-1] == 1 and set(g) == {0, 1}, (slot, 'ruta incompleta')
    start = np.flatnonzero(np.diff(g) < 0) + 1
    land = np.flatnonzero(np.diff(g) > 0) + 1
    assert len(start) == len(land) == len(CASES), (slot, 'hacen falta dos saltos y una caída', t[start], t[land])
    assert ((t[land] - t[start] > 9) & (t[land] - t[start] < 23)).all(), (slot, 'duración de vuelo', t[start], t[land])
    for i, (a, b) in enumerate(zip(start, land, strict=True)):
        if i < 2:
            assert 1.12 < y[a:b].max() < 1.40 and abs(y[b + 4]) < .05, (slot, 'el salto no fue a nivel', i)
        else:
            assert y[a] > -.2 and y[b+4] < -6.5 and data['vertical'][a:b].min() < -.64, (slot, 'no cayó del borde')
    assert np.max(data['speed'][start[0]:land[0]]) < .02 and data['speed'][start[1]] > .23, (
        slot, 'saltos quieto y en carrera no diferenciados')
    return [Event(name, a, b) for name, a, b in zip(CASES, start, land, strict=True)]


def metrics(data, event, slot):
    t = data['time']
    takeoff, touchdown = t[event.start], t[event.land]
    # Include easing into the motion and the first grounded recovery. Ignore
    # camera/world travel and samples with a skipped tick or tiny Δt.
    sample = pairs(t, takeoff - 1, touchdown + 8)
    settling = pairs(t, touchdown - 1.5, touchdown + 8)
    midair = slice(event.start, event.land)
    assert sample.sum() >= 26 and settling.sum() >= 11, (slot, event.name, 'faltan fracciones')
    dt = np.diff(t)
    swing = np.abs(np.diff(np.c_[data['top'], data['mid']], axis=0))
    hem = np.linalg.norm(np.diff(points(data, 'tip'), axis=0), axis=1)
    return dict(frames=int(sample.sum()), airtime=touchdown - takeoff,
                air=data['air'][midair].max(), fall=data['fall'][midair].max(), top=data['top'][midair].max(),
                hinge=(swing[sample, 0] / dt[sample]).max(), middle=(swing[sample, 1] / dt[sample]).max(),
                hem=(hem[sample] / dt[sample]).max(), landing=(hem[settling] / dt[settling]).max())


def report(root, slot, reference=False):
    data = read(root / f'saltos-{slot}.tsv')
    assert all(np.isfinite(data[c]).all() for c in data.dtype.names), (slot, 'muestra inválida')
    assert np.ptp(data['collar_z']) < .025, (slot, 'el asiento se movió en el salto')
    expected = data['leg_pos'] * np.float32(.6662) / (2 * np.pi)
    assert np.max(np.abs(data['stride'] - expected)) < 1e-5, (slot, 'reinicio de fase')
    spans = events(data, slot)
    result = {}
    for span in spans:
        row = metrics(data, span, slot)
        result[span.name] = row
        print(f'{slot} / {span.name}: {row["air"]:.1%} de AIR; {row["fall"]:.1%} de FALL; '
              f'ángulo superior {row["top"]:.2f}°; picos de bisagras {row["hinge"]:.2f}/{row["middle"]:.2f}°/tick, '
              f'punta {row["hem"]:.3f}u/tick (al aterrizar {row["landing"]:.3f}u/tick); {row["frames"]} pares.', flush=True)
    if reference:
        rest = result['salto']
        assert rest['air'] >= .96 and rest['top'] > 40 and rest['hinge'] > 14, (
            slot, 'no se reprodujo el latigazo de planeo en un salto quieto', rest)
    return data, spans, result


def write(root, version, rows):
    fields = ('frames', 'airtime', 'air', 'fall', 'top', 'hinge', 'middle', 'hem', 'landing')
    with (root / 'saltos-forge.tsv').open('w', newline='') as f:
        out = csv.writer(f, delimiter='\t', lineterminator='\n')
        out.writerow(['version', 'ranura', 'prueba', *fields])
        for slot, variants in rows.items():
            for name, row in variants.items():
                out.writerow([version, slot, name, row['frames'], *(f'{row[key]:.5f}' for key in fields[1:])])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    args = ap.parse_args()
    write(args.shots, 'v1.67.24', {slot: report(args.shots, slot, reference=True)[2] for slot in SLOTS})
