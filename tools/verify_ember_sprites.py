#!/usr/bin/env python3
"""Measure the effect of changing atlas frames with pose, size and lighting held fixed."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import cape_ember_sprites as E


def verify(samples, report):
    trace = np.loadtxt(samples)
    config = E.profile()
    count = config['steps']
    images = []
    for key in E.names():
        with Image.open(E.ASSETS / E.SPRITES / (key+'.png')) as im:
            images.append(np.asarray(im, dtype=float)/255)
    atlas = np.asarray(images)
    background = np.array([22,16,28], dtype=float)/255
    rows = ['fps\tcambio\tmax_salto_claves\tmax_salto_intermedios\tenergia_min\tenergia_max\tpares']
    for fps in (30,60,144):
        for pair in (0,1):
            selected = trace[(trace[:,1] == fps) & (trace[:,2] == pair)]
            route, _, _, life, p, old, new, opacity = selected[:,:8].T
            tint = selected[:,8:11].reshape(-1,1,1,3)
            # Stock particle vertex color and shader cutoff; use the same
            # positions/appearance on both sides to isolate the sprite swap.
            tint = np.floor(tint*255)/255
            alpha = (np.floor(opacity*255)/255).reshape(-1,1,1,1)
            def composite(sprite):
                rgba = atlas[sprite]
                a = rgba[...,3:]*alpha
                a *= a >= .1
                return background*(1-a) + tint*rgba[...,:3]*a
            before = composite(old.astype(int)*count)
            after = composite(new.astype(int))
            inside = route[1:] == route[:-1]
            assert set(life) == set(range(26,48)) and inside.any()
            jumps = [np.max(abs(np.diff(values,axis=0)[inside]))*255 for values in (before,after)]
            assert jumps[0] > 60 and jumps[1] <= .50*jumps[0], (fps,pair,jumps)
            # Avoid a dim gap or flare when moving through the transition.
            # Compare with the ideal smooth interpolation of the two rendered
            # endpoint textures under the same opacity (including cutoff).
            width = config['halfTicks']/life
            amount = np.clip((p-config['changes'][pair]+width)/(2*width),0,1)[:,None,None,None]
            amount = amount**2*(3-2*amount)
            goal = composite(pair*count)*(1-amount) + composite((pair+1)*count)*amount
            ratios = (after-background).sum(axis=(1,2,3))/(goal-background).sum(axis=(1,2,3))
            lo, hi = ratios.min(), ratios.max()
            assert lo>.95 and hi<1.08, (fps,pair,lo,hi)
            rows.append(f'{fps}\t{pair+1}\t{jumps[0]:.4f}\t{jumps[1]:.4f}\t{lo:.5f}\t{hi:.5f}\t{inside.sum()}')
            print(f'Brasas, {fps} FPS, cambio {pair+1}: Δ RGB máx {jumps[0]:.2f} → {jumps[1]:.2f}/255; '
                  f'energía {lo:.3f}–{hi:.3f} del fundido ideal.')
    report.write_text('\n'.join(rows)+'\n')


def compare_tint(before, after):
    a, b = np.loadtxt(before), np.loadtxt(after)
    # Progress, streak, phase, sprite, alpha, size and red retain .37 values.
    np.testing.assert_array_equal(a[:, :7], b[:, :7])
    quiet = a[:, 0] >= .58
    np.testing.assert_array_equal(a[quiet], b[quiet])
    warm = (a[:, 0] >= .14) & (a[:, 0] <= .22)
    changes = a[warm, 7:] - b[warm, 7:]
    assert len(changes) >= 48 and (changes.min(axis=0) > [.04, .17]).all(), changes.min(axis=0)
    print(f'Visibilidad de brasas: {len(warm)} muestras mantienen tiempos, tamaños e índices; '
          'el color destacado se enfría antes de la fase final.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples',type=Path)
    parser.add_argument('report',type=Path)
    parser.add_argument('--looks', nargs=2, type=Path, metavar=('BEFORE', 'AFTER'))
    args = parser.parse_args()
    verify(args.samples, args.report)
    if args.looks:
        compare_tint(*args.looks)
