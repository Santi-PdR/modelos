#!/usr/bin/env python3
"""Measure F5 data in body space so camera motion does not count as cape motion."""
import argparse
from pathlib import Path

import numpy as np


def read(path):
    return np.genfromtxt(path, names=True, dtype=None, encoding='utf-8', delimiter='\t')


def report(data, name):
    t = data['time']
    dt = np.diff(t)
    in_walk = (t >= 35) & (t < 70)
    in_sprint = (t >= 107) & (t < 129)
    assert data['leg_speed'][in_walk].mean() > .36 and data['leg_speed'][in_sprint].mean() > .52, name
    mask = in_walk[1:] & in_walk[:-1] & (dt > .08) & (dt < 1.1)
    jumped = (np.diff(data['clip_tick']) < 0) & mask
    delta = np.abs(np.diff(data['top']))
    tip = np.column_stack([data[k] for k in ('tip_x', 'tip_y', 'tip_z')])
    transfer = np.linalg.norm(np.diff(tip, axis=0), axis=1)
    depth = data['collar_z'][in_walk]
    print(f'{name}: {len(t)} cuadros y {np.count_nonzero(mask)} pares en paso estable; '
          f'vaivén del asiento {np.ptp(depth):.3f}u; reinicios de fase {jumped.sum()}; '
          f'cambio de bisagra p95 {np.quantile(delta[mask]/dt[mask], .95):.2f}°/tick; '
          f'movimiento del extremo p95 {np.quantile(transfer[mask]/dt[mask], .95):.3f}u/tick; '
          f'velocidad de andar/estirar {data["leg_speed"][in_walk].mean():.2f}/{data["leg_speed"][in_sprint].mean():.2f}', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    args = ap.parse_args()
    for slot in ('pecho', 'curios'):
        name = 'paso-' + slot
        report(read(args.shots / (name + '.tsv')), name)
