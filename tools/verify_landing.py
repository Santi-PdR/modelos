#!/usr/bin/env python3
"""Independent checks for the landing hem echo and its shared light budget.

The samples come from the real Java classes. Only the contact detector, the
hem envelope and the UV2 gains are exercised here. Geometry is measured
separately from the Forge jump artifacts.
"""
import argparse
import csv
import math
import sys
from pathlib import Path

HITCH = dict(start=.16, full=.84)
PITCH = dict(limit=5.5, peak=3.0, end=9.0)
HEAT = dict(start=1.6, peak=4.4, end=11.0)
ROOM = .55          # CapeNocturne.WAKE_LIMIT
EDGE_SHARE = .72
INNER_SHARE = .90
UNIT = 1 / 4096     # CapeNocturne.GAIN_UNITS
COLUMNS = ('lift', 'age', 'dusk', 'wake', 'pitch', 'heat', 'edge', 'inner', 'hem_edge', 'hem_inner')


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pulse(t, start, peak, end):
    return smooth(min((t - start) / (peak - start), (end - t) / (end - peak)))


def strength(lift):
    return smooth((lift - HITCH['start']) / (HITCH['full'] - HITCH['start'])) if lift > HITCH['start'] else 0.


def load(path):
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        assert tuple(reader.fieldnames) == COLUMNS, (path, reader.fieldnames)
        rows = [{key: float(value) for key, value in row.items()} for row in reader]
    assert rows, path
    return rows


def envelope(rows):
    lifts = sorted({row['lift'] for row in rows})
    peak_pitch, peak_heat, lag = 0., 0., 1e9
    for lift in lifts:
        band = sorted((row for row in rows if row['lift'] == lift and row['dusk'] == 1 and row['wake'] == 0),
                      key=lambda row: row['age'])
        assert band, lift
        impulse = strength(lift)
        seen_cloth = seen_light = None
        for row in band:
            age = row['age']
            cloth = PITCH['limit'] * impulse * pulse(age, 0, PITCH['peak'], PITCH['end']) if impulse else 0.
            light = impulse * pulse(age, HEAT['start'], HEAT['peak'], HEAT['end'])
            assert abs(row['pitch'] - cloth) < 1e-9, (lift, age, 'cabeceo', row['pitch'], cloth)
            assert abs(row['heat'] - light) < 1e-9, (lift, age, 'calor', row['heat'], light)
            if row['pitch'] > 0:
                assert age > 0 and age < PITCH['end'], (lift, age, 'el dobladillo se movió fuera de su ventana')
                seen_cloth = age if seen_cloth is None else seen_cloth
            if row['heat'] > 0:
                assert age > HEAT['start'] and age < HEAT['end'], (lift, age, 'la luz se salió de su ventana')
                seen_light = age if seen_light is None else seen_light
            peak_pitch = max(peak_pitch, row['pitch'])
            peak_heat = max(peak_heat, row['heat'])
        if impulse:
            assert seen_cloth is not None and seen_light is not None, (lift, 'sin respuesta')
            lag = min(lag, seen_light - seen_cloth)
        else:
            assert seen_cloth is None and seen_light is None, (lift, 'respuesta con un paso mínimo')
    assert abs(peak_pitch - PITCH['limit']) < 1e-9 and abs(peak_heat - 1) < 1e-9, (peak_pitch, peak_heat)
    assert lag >= 1.4, ('la luz no llega después del paño', lag)
    return peak_pitch, peak_heat, lag


def budget(rows):
    exact = dark = bright = 0
    worst_edge = worst_inner = 0.
    for row in rows:
        delta_edge = row['hem_edge'] - row['edge']
        delta_inner = row['hem_inner'] - row['inner']
        room = ROOM * row['dusk'] * row['dusk']
        mix = min(1., row['heat'])
        assert -1e-12 <= delta_edge <= EDGE_SHARE * mix * room + UNIT, ('borde', row)
        assert -1e-12 <= delta_inner <= INNER_SHARE * mix * room + UNIT, ('interior', row)
        assert row['hem_edge'] < 1.95 and row['hem_inner'] < 1.95, ('sin margen en la escala 4096', row)
        if row['dusk'] == 0:
            assert delta_edge == 0 and delta_inner == 0, ('eco de día', row)
            bright += 1
        elif row['wake'] == 0:
            assert abs(delta_edge - EDGE_SHARE * mix * room) <= UNIT, ('borde exacto', row)
            assert abs(delta_inner - INNER_SHARE * mix * room) <= UNIT, ('interior exacto', row)
            dark += 1
        else:
            exact += 1
        worst_edge = max(worst_edge, delta_edge)
        worst_inner = max(worst_inner, delta_inner)
    return dark, exact, bright, worst_edge, worst_inner


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('samples', type=Path)
    args = cli.parse_args()
    rows = load(args.samples)
    peak_pitch, peak_heat, lag = envelope(rows)
    dark, braking, bright, worst_edge, worst_inner = budget(rows)
    print(f'{len(rows)} muestras: cabeceo máximo {peak_pitch:.2f}°; calor máximo {peak_heat:.3f}; '
          f'la luz llega {lag:.2f} tics después del paño.', flush=True)
    print(f'{dark} muestras oscuras sin freno reproducen su cuota exacta, {braking} conviven con el freno '
          f'y {bright} de día no cambian; eco máximo +{worst_edge:.4f}/+{worst_inner:.4f}.', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
