#!/usr/bin/env python3
"""Check lower ember births against the live Shift pose in both Forge slots."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def verify(shots):
    report = ['ranura\tzona\tn\tmarco_max_35\tmarco_max_36\tmedia_distancia_35\tmedia_distancia_36\tp90_distancia_35\tp90_distancia_36']
    for slot in ('pecho', 'curios'):
        with (shots/f'nacimiento-agachado-{slot}.tsv').open() as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        ticks = sorted({int(r['tick']) for r in rows})
        assert len(ticks) == 6 and min(np.diff(ticks)) >= 4, (slot, ticks)
        assert {r['zona'] for r in rows} == {'cuello', 'dobladillo', 'costado'}
        for band in ('dobladillo', 'costado'):
            candidates = [r for r in rows if r['zona'] == band]
            assert all(sum(int(r['tick']) == tick for r in candidates) == 27 for tick in ticks)
            data = np.array([[float(r[n]) for n in ('error_marco_35', 'error_marco_36', 'distancia_35', 'distancia_36')]
                             for r in candidates])
            assert np.isfinite(data).all() and (data >= 0).all()
            old, new = data[:, :2].max(axis=0)
            assert old > .25 and new < .004, (slot, band, old, new)
            mean = data[:, 2:].mean(axis=0)
            p90 = np.quantile(data[:, 2:], .90, axis=0)
            assert mean[1] < mean[0] and p90[1] < p90[0], (slot, band, mean, p90)
            print(f'{slot}, {band}: Δ marco máx {old:.4f} → {new:.5f} bloques; distancia media al paño '
                  f'{mean[0]:.3f} → {mean[1]:.3f} bloques, {len(data)} orígenes.')
            report.append(f'{slot}\t{band}\t{len(data)}\t{old:.7f}\t{new:.7f}\t{mean[0]:.6f}\t{mean[1]:.6f}\t{p90[0]:.6f}\t{p90[1]:.6f}')
        collar = [r for r in rows if r['zona'] == 'cuello']
        assert len(collar) == 6*27 and max(float(r['error_marco_36']) for r in collar) < .004, slot
    (shots/'nacimiento-agachado-resumen.tsv').write_text('\n'.join(report)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots', type=Path)
    verify(parser.parse_args().shots)
