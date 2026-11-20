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
    jumped = (np.diff(data['stride']) < 0) & mask
    delta = np.abs(np.diff(data['top']))
    tip = np.column_stack([data[k] for k in ('tip_x', 'tip_y', 'tip_z')])
    transfer = np.linalg.norm(np.diff(tip, axis=0), axis=1)
    depth = data['collar_z'][in_walk]
    sway = np.ptp(depth)
    hinge = np.quantile(delta[mask]/dt[mask], .95)
    hem = np.quantile(transfer[mask]/dt[mask], .95)
    # v1.67.10 live baseline: 2.309u, 2 resets, 30.44–30.72°/tick and
    # 12.459–12.535u/tick. The mantle must also move, not just freeze.
    assert np.isfinite(tip).all() and mask.sum() >= 35, name
    assert sway < .26 and not jumped.any() and hinge < 10 and .02 < hem < 4.1, (name,sway,hinge,hem)
    assert np.max(np.abs(data['stride'] - data['leg_pos'] * np.float32(.6662) / (2 * np.pi))) < 2e-6, name
    assert (data['walk'][in_walk] >= .98).mean() > .95 and (data['run'][in_sprint] >= .98).mean() > .8, name
    assert (data['walk'][t < 17] < .01).all() and (data['run'][t > 147] < .01).all(), name
    transitions = []
    for label, start, end in (('arranque',18,36),('giro',70,94),('carrera',95,109),('freno',128,151)):
        select = (t[:-1] >= start) & (t[1:] < end) & (dt > .08) & (dt < 1.1)
        assert np.count_nonzero(select) >= 12, (name,label)
        max_turn = np.max(delta[select] / dt[select])
        transitions.append(f'{label} {max_turn:.1f}°/tick')
        assert max_turn < 25, (name,label,max_turn)
    print(f'{name}: {len(t)} cuadros y {int(mask.sum())} pares de paso estable; vaivén del asiento {sway:.3f}u; '
          f'reinicios de fase {int(jumped.sum())}; bisagra p95 {hinge:.2f}°/tick; extremo p95 {hem:.3f}u/tick. '
          f'Máximos en transición: {", ".join(transitions)}.',flush=True)


def upper_edge(root):
    from verify_forge_mount import read as image
    gain = {slot: [] for slot in ('pecho','curios')}
    for view in ('cenital','ajuste-medio','oblicua'):
        bare = image(root / f'{view}-sin-manto.png')
        anchor = np.loadtxt(root / f'{view}-v16710-borde.tsv', dtype=int)
        assert anchor.shape == (198,4), view

        def coverage(name):
            u,v,x,y = points = np.loadtxt(root / f'{name}-borde.tsv', dtype=int).T
            assert points.shape == (4,198) and np.array_equal(points[:2].T,anchor[:,:2]), name
            assert np.max(np.abs(points[2:].T - anchor[:,2:])) <= 1, (name,'se movió la cámara F5')
            assert min(x.min(),y.min()) >= 0 and x.max() < bare.shape[1] and y.max() < bare.shape[0], name
            rb,gb,bb = bare[y,x].T
            r,g,b = image(root / f'{name}.png')[y,x].T
            shirt = (gb-rb >= 19) & (bb-rb >= 19)
            cloth = (gb-g >= 16) & (np.maximum(r,b)-g >= 9)
            count = int(shirt.sum())
            assert count >= 30, (name,count)
            return float((cloth & shirt).sum() / count), count

        old, count = coverage(f'{view}-v16710')
        results = []
        for slot in gain:
            name = f'{view}-{slot}'
            now, _ = coverage(name)
            results.append(f'{slot} {now:.1%}')
            gain[slot].append(now - old)
            assert now >= .30 and now >= old - .10, (name,old,now)
        print(f'{view}: canto visible de la camiseta en {count} muestras; montura v1.67.10 {old:.1%} '
              f'→ {", ".join(results)}.',flush=True)
    assert all(max(values) >= .15 for values in gain.values()), ('sin mejora visible',gain)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('--motion-only', action='store_true',
                    help='omitir la comparativa de camiseta v1.67.10 si no se capturaron escenas históricas')
    args = ap.parse_args()
    for slot in ('pecho', 'curios'):
        name = 'paso-' + slot
        report(read(args.shots / (name + '.tsv')), name)
    if not args.motion_only:
        upper_edge(args.shots)
