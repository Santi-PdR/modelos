#!/usr/bin/env python3
"""Measure worn details using same-view, same-wearer Forge controls."""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from verify_forge_mount import emit, read

VIEWS = ('espalda', 'frente', 'izquierda', 'derecha', 'arriba', 'abajo')
FIXTURES = tuple(f'yugo-{skin}-{slot}' for skin in ('steve', 'alex') for slot in ('pecho', 'curios'))


def regions(root, name, size):
    w, h = size
    masks = [Image.new('L', size) for _ in range(3)]
    draw = list(map(ImageDraw.Draw, masks))
    for line in (root / f'{name}-caras.tsv').read_text().splitlines():
        n, *coords = line.split()
        i = 0 if n == 'v18_pad_0' else 1 if n == 'v18_pad_1' else 2
        quad = np.asarray(coords, float).reshape(4, 2) * [w, h]
        assert np.isfinite(quad).all(), name
        draw[i].polygon([tuple(p) for p in quad], fill=255)
    return np.asarray([np.asarray(m) > 0 for m in masks])


def report(root):
    for fixture in FIXTURES:
        data = np.genfromtxt(root / f'{fixture}-recorrido.tsv', names=True, delimiter='\t')
        assert len(data) >= 35 and np.isfinite(data['drift']).all()
        assert data['pitch'].min() <= -89 and data['pitch'].max() >= 89
        assert data['yaw'].min() <= -70 and data['yaw'].max() >= 70
        assert data['lift'].max() > .65 and abs(data['lift'][-1]) < .01
        assert data['drift'].max() < .006, fixture
        visibility = []
        for view in VIEWS:
            name = f'{fixture}-{view}'
            worn, no_pads, no_yoke = [read(root / f'{name}{s}.png') for s in ('', '-sin-placas', '-sin-yugo')]
            masks = regions(root, name, (worn.shape[1], worn.shape[0]))
            changes = np.abs(worn - no_pads).max(2) >= 15
            yoke = np.abs(worn - no_yoke).max(2) >= 15
            p0, p1 = (int(np.count_nonzero(changes & m)) for m in masks[:2])
            collar = int(np.count_nonzero(yoke & masks[2]))
            visibility.append(f'{view} {p0}/{p1}/{collar}')
            assert collar >= 24, (name, p0, p1, collar, 'no se distingue la tela fija')
            if view in ('frente', 'arriba', 'espalda'):
                assert min(p0, p1) >= 70, (name, p0, p1, 'placa tapada')
            elif view != 'abajo':
                # The far sleeve can be occluded from a true profile.
                assert max(p0, p1) >= 62, (name, p0, p1)
        print(f'::notice title=Yugo equipado en Forge::{fixture}: {len(data)} muestras, '
              f'cambio máximo {data["drift"].max():.6f}u, salto {data["lift"].max():.2f} bloques. '
              f'Píxeles visibles placa izq/der/yugo: {"; ".join(visibility)}')


def gallery(root, path):
    cell_w, cell_h = 208, 164
    views = (*VIEWS, 'salto')
    image = Image.new('RGB', (cell_w * len(views), 39 + (cell_h+20)*len(FIXTURES)), '#15101a')
    draw = ImageDraw.Draw(image)
    draw.text((12, 10), 'MANTLE OF THE BLIGHT STAR   /   YUGO FIJO EN FORGE', fill='#f6dded')
    for j, view in enumerate(views):
        draw.text((j*cell_w+12, 25), view.upper(), fill='#eec6dd')
    for i, fixture in enumerate(FIXTURES):
        y = 39 + (cell_h+20)*i
        for j, view in enumerate(views):
            x = j*cell_w
            name = f'{fixture}-{view}'
            native = Image.open(root / f'{name}.png').convert('RGB')
            bounds_name = name if view != 'salto' else f'{fixture}-espalda'
            mask = regions(root, bounds_name, native.size).any(0)
            py, px = np.where(mask)
            w, h = native.size
            cx = (px.min()+px.max())/2 if len(px) else w/2
            cy = (py.min()+py.max())/2 if len(py) else h/2
            width = max(170, np.ptp(px)*1.36 if len(px) else 0, (np.ptp(py)+32)*1.3 if len(py) else 0)
            height = width*cell_h/cell_w
            # Keep the head and the top of the skirt in the same crop, even
            # for a small front projection. The jump uses the locked camera.
            if view not in ('arriba','abajo'):
                cy -= height*.08
            box = (cx-width/2, cy-height/2, cx+width/2, cy+height/2)
            crop = native.crop(tuple(map(round,box))).resize((cell_w-4,cell_h-4),Image.Resampling.LANCZOS)
            image.paste(crop, (x+2,y+17))
        draw.text((11, y+2), fixture.removeprefix('yugo-').replace('-', '  /  ').upper(), fill='#ffe2ef')
    image.save(path, quality=88, optimize=True)
    # Compact proof also available if Actions storage isn't reachable.
    preview = image.resize((1092, 582), Image.Resampling.LANCZOS)
    for quality in (81, 75, 66, 59):
        data = io.BytesIO()
        preview.save(data, 'JPEG', quality=quality, optimize=True)
        if len(data.getvalue()) < 55_000:
            break
    emit('Yugo fijo galeria jpg', data.getvalue())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('--gallery-only', action='store_true')
    args = ap.parse_args()
    if not args.gallery_only:
        report(args.shots)
    gallery(args.shots, args.shots / 'yugo-fijo-forge.jpg')
