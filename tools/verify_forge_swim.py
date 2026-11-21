#!/usr/bin/env python3
"""Measure the live F5 wade → swim → upright cycle in both equipment slots."""
import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from verify_forge_walk import pairs, points, read

SLOTS = ('pecho', 'curios')
POSES = (('de-pie-en-agua', 'DE PIE EN AGUA'), ('nado-horizontal', 'NADO HORIZONTAL'),
         ('fin-del-nado', 'REGRESO A VERTICAL'))


def cycle(root, slot):
    data = read(root / f'nado-ciclo-{slot}.tsv')
    t, stage, visual, swim, weight = (data[c] for c in ('time', 'stage', 'visual', 'swim_amount', 'clip_swim'))
    assert t[0] < 1 and (np.diff(t) >= 0).all(), (slot, 'se reinició el reloj del nado')
    assert list(dict.fromkeys(stage)) == ['wade', 'swim', 'exit'], (slot, 'faltan posturas')
    wade = (stage == 'wade') & (t >= t[stage == 'wade'][-1] - 2.5)
    full = (stage == 'swim') & (swim == 1) & (visual == 1)
    up = (stage == 'exit') & (swim == 0) & (visual == 0)
    middle = (swim > .12) & (swim < .9)
    assert wade.sum() >= 4 and not visual[wade].any() and (swim[wade] == 0).all(), (slot, 'no vadeó de pie')
    assert full.sum() >= 8 and up.sum() >= 8 and np.ptp(t[up]) >= 9, (slot, 'faltan mesetas de nado/reposo')
    assert (middle & (stage == 'swim')).sum() >= 6 and (middle & (stage == 'exit')).sum() >= 6, (
        slot, 'faltan fracciones del nado')
    tip = points(data, 'tip')
    angles = np.c_[data['top'], data['mid']]
    pair = pairs(t)
    assert pair.sum() >= 25 and np.isfinite(tip).all() and np.isfinite(angles).all(), (slot, 'sin medidas válidas')
    error = np.abs(weight - swim)
    # Ignore the teleport/equipment warmup. Measure consecutive F5 samples
    # throughout the actual swimming entry and withdrawal, in torso space.
    active = (stage[1:] == 'swim') | (stage[1:] == 'exit')
    select = pair & active
    dt = np.diff(t)[select]
    hinge_slope = np.max(np.abs(np.diff(angles, axis=0)[select]) / dt[:, None], axis=0)
    tip_slope = np.max(np.linalg.norm(np.diff(tip, axis=0)[select], axis=1) / dt)
    return data, wade, full, up, error, (*hinge_slope, tip_slope)


def report(root, slot, baseline=False):
    data, wade, full, up, error, speeds = cycle(root, slot)
    weight, top = data['clip_swim'], data['top']
    if baseline:
        assert (weight[wade | full | up] >= .99).all() and error.max() >= .99, (
            slot, 'v1.67.23 no reprodujo el nado persistente en vertical')
    else:
        # Floating-point tolerance only: no second transition or queue in
        # the water. These rows have no wet/dry cut, forced pose or teleport.
        assert error.max() < 2e-6, (slot, 'el paño no sigue la interpolación del cuerpo', error.max())
        assert data['clip_run'][wade | full | up].max() < .005, (slot, 'pose de carrera en la piscina')
        assert np.ptp(data['collar_z'][data['stage'] != 'wade']) < .25, (slot, 'se movió el asiento del cuello')
        assert np.ptp(top[full]) > .05, (slot, 'nado congelado')
    mode = 'v1.67.23' if baseline else 'ajuste'
    print(f'{slot} {mode}: {len(data)} cuadros; clip al vadear {weight[wade].mean():.1%}; '
          f'en horizontal {weight[full].mean():.1%}; de nuevo de pie {weight[up].mean():.1%}; '
          f'error máximo del peso {error.max():.3%}; bisagra al vadear {top[wade].mean():.2f}°. '
          f'Entrada/salida: picos {speeds[0]:.2f}/{speeds[1]:.2f}°/tick, punta {speeds[2]:.3f}u/tick.', flush=True)
    return [mode, slot, len(data), *(f'{weight[mask].mean():.7f}' for mask in (wade, full, up)), f'{error.max():.8f}',
            *(f'{top[mask].mean():.4f}' for mask in (wade, full, up)), *(f'{v:.4f}' for v in speeds)]


def comparison(root, baseline, version, baseline_slots):
    w, h = 308, 205
    rows = [(slot, shots, ver) for slot in SLOTS
            for shots, ver in (([(baseline, '1.67.23')] if slot in baseline_slots else []) + [(root, version)])]
    sheet = Image.new('RGB', (w * 3, 58 + len(rows) * (h + 32)), '#19141f')
    pen = ImageDraw.Draw(sheet)
    pen.text((12, 10), 'EL PAÑO AL VADEAR Y NADAR / ALEX, F5 EN FORGE', fill='#f8eaf2')
    for i, (_, label) in enumerate(POSES):
        pen.text((i * w + 12, 36), label, fill='#f0bed9')
    for i, (slot, shots, ver) in enumerate(rows):
        suffix = '-curios' if slot == 'curios' else ''
        row = 58 + i * (h + 32)
        pen.text((12, row + 2), f'{slot.upper()} / v{ver}', fill='#f8eaf2')
        for k, (name, _) in enumerate(POSES):
            with Image.open(shots / f'{name}{suffix}.png') as img:
                crop = ImageOps.fit(img.convert('RGB'), (w - 12, h), Image.Resampling.LANCZOS)
            sheet.paste(crop, (k * w + 6, row + 21))
    sheet.save(root / 'comparacion-nado-forge.jpg', quality=94, optimize=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('--baseline-shots', type=Path, help='referencia de pecho, o de ambas ranuras si se grabaron')
    args = ap.parse_args()
    version = next(line.split('=', 1)[1].strip() for line in Path('gradle.properties').read_text().splitlines()
                   if line.startswith('mod_version='))
    baseline_slots = set()
    if args.baseline_shots:
        baseline_slots.add('pecho')
        if (args.baseline_shots / 'nado-ciclo-curios.tsv').is_file():
            baseline_slots.add('curios')
    rows = []
    for slot in SLOTS:
        if slot in baseline_slots:
            rows.append(report(args.baseline_shots, slot, baseline=True))
        candidate = report(args.shots, slot)
        candidate[0] = 'v' + version
        rows.append(candidate)
    with (args.shots / 'nado-forge.tsv').open('w', newline='') as f:
        out = csv.writer(f, delimiter='\t', lineterminator='\n')
        out.writerow(['version', 'ranura', 'cuadros', 'nado_vertical', 'nado_horizontal', 'nado_al_erguirse',
                      'error_max_peso', 'bisagra_vertical_deg', 'bisagra_horizontal_deg', 'bisagra_al_erguirse_deg',
                      'pico_sup_deg_tick', 'pico_med_deg_tick', 'pico_punta_u_tick'])
        out.writerows(rows)
    if args.baseline_shots:
        comparison(args.shots, args.baseline_shots, version, baseline_slots)
