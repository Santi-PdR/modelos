#!/usr/bin/env python3
"""Read the live F5 wade → swim → upright cycle, independently for both slots."""
import argparse
from pathlib import Path

import numpy as np

from verify_forge_walk import pairs, points, read

SLOTS = ('pecho', 'curios')


def cycle(root, slot):
    data = read(root / f'nado-ciclo-{slot}.tsv')
    t, stage, visual, swim, weight = (data[c] for c in ('time', 'stage', 'visual', 'swim_amount', 'clip_swim'))
    assert t[0] < 1 and (np.diff(t) >= 0).all(), (slot, 'se reinició el reloj del nado')
    assert set(stage) == {'wade', 'swim', 'exit'}, (slot, 'faltan posturas')
    wade = (stage == 'wade') & (t >= t[stage == 'wade'][-1] - 4)
    full = (stage == 'swim') & (swim == 1) & (visual == 1)
    up = (stage == 'exit') & (swim == 0) & (visual == 0)
    middle = (swim > .12) & (swim < .9)
    assert wade.sum() >= 4 and not visual[wade].any() and (swim[wade] == 0).all(), (slot, 'no vadeó de pie')
    assert full.sum() >= 8 and up.sum() >= 8 and np.ptp(t[up]) >= 9, (slot, 'faltan mesetas de nado/reposo')
    assert (middle & (stage == 'swim')).sum() >= 6 and (middle & (stage == 'exit')).sum() >= 6, (
        slot, 'faltan fracciones del nado')
    pair = pairs(t)
    assert pair.sum() >= 25 and np.isfinite(points(data, 'tip')).all(), (slot, 'sin medidas válidas de la punta')
    error = np.abs(weight - swim)
    print(f'{slot}: {len(t)} cuadros F5; clip al vadear {weight[wade].mean():.1%}; '
          f'con el cuerpo horizontal {weight[full].mean():.1%}; al erguirse {weight[up].mean():.1%}; '
          f'error máximo de peso {error.max():.1%}.', flush=True)
    return data, wade, full, up, error


def reference(root, slot):
    data, wade, full, up, error = cycle(root, slot)
    assert (data['clip_swim'][wade | full | up] >= .99).all() and error.max() >= .99, (
        slot, 'v1.67.23 no reprodujo el nado persistente en vertical')
    print(f'{slot}: v1.67.23 reprodujo el clip horizontal en las dos posturas de pie; '
          f'bisagra superior al vadear {data["top"][wade].mean():.2f}°.', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    args = ap.parse_args()
    for slot in SLOTS:
        reference(args.shots, slot)
