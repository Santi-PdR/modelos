#!/usr/bin/env python3
"""Measure F5 data in body space so camera motion does not count as cape motion."""
import argparse
from pathlib import Path

import numpy as np


def read(path):
    return np.genfromtxt(path, names=True, dtype=None, encoding='utf-8', delimiter='\t')


TRANSITIONS = (('arranque',18,36),('giro',70,94),('carrera',95,109),('freno',128,151))
CHANGE = (('andar-correr',174,188),('correr-andar',193,207))


def points(data, name):
    return np.column_stack([data[f'{name}_{k}'] for k in 'xyz'])


def pairs(t, start=-np.inf, end=np.inf):
    dt = np.diff(t)
    return (t[:-1] >= start) & (t[1:] < end) & (dt > .08) & (dt < 1.1)


def report(data, name):
    t = data['time']
    dt = np.diff(t)
    in_walk = (t >= 35) & (t < 70)
    in_sprint = (t >= 107) & (t < 129)
    assert data['leg_speed'][in_walk].mean() > .36 and data['leg_speed'][in_sprint].mean() > .52, name
    mask = pairs(t,35,70)
    jumped = (np.diff(data['stride']) < -1e-6) & (mask if 'pace' not in data.dtype.names else pairs(t))
    delta = np.abs(np.diff(data['top']))
    tip = points(data,'tip')
    transfer = np.linalg.norm(np.diff(tip, axis=0), axis=1)
    depth = data['collar_z'][in_walk]
    sway = np.ptp(depth)
    hinge = np.quantile(delta[mask]/dt[mask], .95)
    hem = np.quantile(transfer[mask]/dt[mask], .95)
    # v1.67.10 live baseline: 2.309u, 2 resets, 30.44–30.72°/tick and
    # 12.459–12.535u/tick. The mantle must also move, not just freeze.
    assert np.isfinite(tip).all() and mask.sum() >= 35, name
    assert sway < .26 and not jumped.any() and hinge < 10 and .02 < hem < 4.1, (name,sway,hinge,hem)
    leg_pos = data['leg_pos']
    expected = leg_pos * np.float32(.6662) / (2 * np.pi)
    tolerance = 2e-6 + np.abs(expected) * np.finfo(np.float32).eps
    assert (np.abs(data['stride'] - expected) < tolerance).all(), name
    assert (data['walk'][in_walk] >= .98).mean() > .95 and (data['run'][in_sprint] >= .98).mean() > .8, name
    assert (data['walk'][t < 17] < .01).all() and (data['run'][(t > 147) & (t < 156)] < .01).all(), name
    transitions = []
    for label, start, end in TRANSITIONS:
        select = pairs(t,start,end)
        assert np.count_nonzero(select) >= 12, (name,label)
        max_turn = np.max(delta[select] / dt[select])
        transitions.append(f'{label} {max_turn:.1f}°/tick')
        assert max_turn < 25, (name,label,max_turn)
    print(f'{name}: {len(t)} cuadros y {int(mask.sum())} pares de paso estable; vaivén del asiento {sway:.3f}u; '
          f'reinicios de fase {int(jumped.sum())}; bisagra p95 {hinge:.2f}°/tick; extremo p95 {hem:.3f}u/tick. '
          f'Máximos en transición: {", ".join(transitions)}.',flush=True)


def continuity(data, name, baseline=None):
    def peaks(values, lo, hi):
        t = values['time']
        select = pairs(t,lo,hi)
        delta = np.diff(t)[select]
        slopes = np.abs(np.diff(np.c_[values['top'],values['mid']],axis=0)[select]) / delta[:,None]
        hem = np.linalg.norm(np.diff(points(values,'tip'),axis=0)[select],axis=1) / delta
        return np.r_[slopes.max(0),hem.max()]

    t = data['time']
    dt = np.diff(t)
    assert np.isfinite(points(data,'hood')).all() and np.isfinite(data['pace']).all(), name
    assert np.min(dt) >= 0 and t.max() >= 225, name
    sub_tick = pairs(t) & (np.floor(t[1:]) == np.floor(t[:-1]))
    across = pairs(t) & (np.floor(t[1:]) == np.floor(t[:-1])+1)
    assert sub_tick.sum() >= 80 and across.sum() >= 95, (name,'sub-tick sampling missing')
    valid = pairs(t)
    pace_slope = np.diff(data['pace'])[valid] / dt[valid]
    assert pace_slope.max() < .106 and pace_slope.min() > -.071, (name,'impulso de velocidad',pace_slope.min(),pace_slope.max())
    assert (data['run'][(t >= 185)&(t < 194)] > .98).mean() > .8, (name,'no cambió a carrera sin parar')
    assert (data['walk'][(t >= 202)&(t < 208)] > .98).mean() > .8, (name,'no volvió a andar sin parar')
    assert (data['run'][t >= 220] < .01).all() and (data['walk'][t >= 222] < .01).all(), name
    hood = points(data,'hood')
    crown = np.linalg.norm(np.ptp(hood[(t > 106)&(t < 128)],axis=0))
    assert .10 < crown < .68, (name,'amplitud capucha',crown)
    result = []
    for label, lo, hi in TRANSITIONS+CHANGE:
        p = peaks(data,lo,hi)
        base = peaks(baseline,lo,hi) if baseline is not None and (label,lo,hi) in TRANSITIONS else None
        result.append((name.removeprefix('paso-'),label, int(pairs(t,lo,hi).sum()), *p, *([-1.]*3 if base is None else base)))
        print(f'{name} / {label}: bisagras {p[0]:.2f}/{p[1]:.2f}°/tick, punta {p[2]:.3f}u/tick'
              + (f' (v1.67.20: {base[0]:.2f}/{base[1]:.2f}°, {base[2]:.3f}u)' if base is not None else ''),flush=True)
    print(f'{name}: {int(sub_tick.sum())} pares dentro del tick y {int(across.sum())} entre ticks; '
          f'arco de la capucha en carrera {crown:.3f}u.',flush=True)
    return result


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
    ap.add_argument('--baseline-shots', type=Path)
    args = ap.parse_args()
    table = []
    for name in ('paso-pecho','paso-curios','paso-steve-pecho','paso-steve-curios'):
        path = args.shots / (name + '.tsv')
        if 'steve' in name and not path.is_file() and args.baseline_shots is None:
            continue # historical recording
        data = read(path)
        report(data, name)
        if 'pace' in data.dtype.names:
            old = read(args.baseline_shots / path.name) if args.baseline_shots and 'steve' not in name else None
            table.extend(continuity(data,name,old))
    if table:
        with (args.shots/'continuidad-forge.tsv').open('w') as f:
            print('ruta\tfase\tpares\tarriba_deg_tick\tmedio_deg_tick\tpunta_u_tick\tbase_arriba\tbase_medio\tbase_punta',file=f)
            for *labels,a,b,c,d,e,g in table:
                print(*labels,*(f'{v:.3f}' for v in (a,b,c,d,e,g)),sep='\t',file=f)
    if not args.motion_only:
        upper_edge(args.shots)
