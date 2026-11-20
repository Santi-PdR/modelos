#!/usr/bin/env python3
"""Report what the real solid collar, shoulder plates and roots do in F5.

The old renderer is a reference for placement, not a collision-free target.
In particular the old collar may sit inside the player's second skin layer.
"""
import argparse
import csv
import io
from pathlib import Path

import numpy as np
from PIL import Image

from verify_forge_mount import emit, read
from verify_forge_seat import shirt_mask

VIEWS = ('diagonal', 'espejo', 'cenital')
SLOTS = ('pecho', 'curios')


def bounds(path):
    with path.open(newline='') as fd:
        values = {row[0]: np.array(tuple(map(float, row[1:]))).reshape(2, 3)
                  for row in list(csv.reader(fd, delimiter='\t'))[1:]}
    assert all(np.isfinite(b).all() and (b[1] >= b[0]).all() for b in values.values()), path
    return values


def geometry(root, view, slot, history):
    suffix = '-v1280' if history else ''
    parts = bounds(root/f'historia-{view}-{slot}{suffix}.tsv')
    pads = [parts[f'v18_pad_{i}'] for i in range(2)]
    cowl = np.array([b for n,b in parts.items() if n.startswith('v17_cowl_back_')])
    roots = np.array([b for n,b in parts.items() if n.startswith('v17_ribbon_') and n.endswith('_seg0')])
    assert len(cowl) >= 5 and len(roots) == 12, (view, slot, history, len(cowl), len(roots))
    return np.array([pads[0][1,0], -pads[1][0,0], cowl[:,0,2].min(), cowl[:,1,1].max(),
                     roots[:,0,2].mean(), roots[:,1,1].max()])


def verify(root):
    for view in VIEWS:
        for slot in SLOTS:
            old, now = (geometry(root,view,slot,hist) for hist in (True,False))
            assert 6.2 < old[0] < 6.9 and 6.2 < old[1] < 6.9, (view, slot, old)
            assert .8 < old[2] < 1.4 and 24 < old[3] < 26.1, (view, slot, old)
            assert 1.2 < old[4] < 2.9, (view, slot, old)
            values = ', '.join(f'{a:.2f}→{b:.2f}' for a,b in zip(old,now,strict=True))
            print(f'{view}/{slot} · v1.28.0→actual (u): extremos X D/I, Z/Y cuello, Z/Y raíces: {values}')


def gallery(root, view):
    base = root/f'historia-{view}-sin-manto.png'
    if not base.is_file():
        return
    img = read(base)
    mask = shirt_mask(img)
    h, w = mask.shape
    ys, xs = np.where(mask)
    keep = (np.abs(xs-w/2) < .25*w) & (np.abs(ys-h/2) < .30*h)
    xs, ys = xs[keep], ys[keep]
    assert len(xs) > 500, (view, 'no se ve la camiseta de referencia')
    x0,x1 = np.quantile(xs,[.005,.995]); y0,y1 = np.quantile(ys,[.005,.995]); d = x1-x0
    crop = (round(x0-.43*d),round(y0-.73*d),round(x1+.43*d),round(y1+.69*d))
    for suffix in ('sin-manto','pecho-v1280','pecho','curios-v1280','curios'):
        file = root/f'historia-{view}-{suffix}.png'
        if not file.is_file():
            continue
        with Image.open(file) as im:
            sample = im.convert('RGB').crop(crop)
        for rate in (1,.86,.73,.62,.53,.44,.36,.30):
            buf = io.BytesIO()
            sample.resize((round(rate*sample.width),round(rate*sample.height)),Image.Resampling.NEAREST).quantize(32).save(
                buf,format='PNG',optimize=True)
            if len(buf.getvalue()) <= 2450:
                break
        assert len(buf.getvalue()) <= 2450, file
        emit('Anclaje histórico '+file.stem,buf.getvalue())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots',type=Path)
    ap.add_argument('--gallery',choices=VIEWS)
    args = ap.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
    else:
        verify(args.shots)
