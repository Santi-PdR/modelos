#!/usr/bin/env python3
"""Measure the actual rendered plate rims against both vanilla sleeves in F5."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from verify_forge_mount import gallery, read
from verify_forge_seat import blue_floor, shirt_mask

PREFIX = 'hombreras'


def visible_plate(root, slot, side, worn, bare, unplated):
    faces = np.loadtxt(root/f'{PREFIX}-{slot}-caras.tsv')
    assert faces.ndim == 2 and faces.shape[1] == 9 and np.isfinite(faces).all(), (slot, faces.shape)
    quads = faces[faces[:,0] == side,1:].reshape(-1,4,2)
    assert len(quads) >= 12, (slot, side, 'faltan caras de la hombrera')
    mask = Image.new('L',(worn.shape[1],worn.shape[0]))
    draw = ImageDraw.Draw(mask)
    for quad in quads:
        draw.polygon([tuple(p) for p in quad],fill=255)
    projected = np.asarray(mask.filter(ImageFilter.MaxFilter(3))) > 0
    # A projected box alone doesn't count: the rim must leave opaque cloth
    # pixels in the ordinary screenshot, and those pixels must disappear
    # when only the plates are hidden, not when the lining is removed.
    material = (worn[...,1] <= 95) & ~blue_floor(worn) & ~shirt_mask(worn)
    changed = (np.abs(worn-unplated).max(2) >= 12) & (np.abs(worn-bare).max(2) >= 18)
    return projected & material & changed


def seams(root, slot, worn, bare, unplated):
    shirt = shirt_mask(bare)
    _,xx = np.where(shirt)
    assert len(xx) > 600, 'no se ven las mangas de la referencia sin manto'
    left,right = xx.min(),xx.max()+1
    width = right-left
    output = []
    floor = blue_floor(worn)
    for side,lo,hi in ((1,.07,.21),(0,.79,.93)):
        mask = visible_plate(root,slot,side,worn,bare,unplated)
        points = []
        for x in range(left+round(lo*width),left+round(hi*width)):
            rear = np.flatnonzero(shirt[:,x])
            if not rear.size:
                continue
            y = int(rear[-1])
            start,stop = y-round(.045*width), y+round(.16*width)
            cloth = np.flatnonzero(mask[start:stop,x])
            rim = start+cloth[0] if cloth.size else stop
            points.append((max(0,rim-y-1),bool(cloth.size),int(floor[y+1:rim,x].sum())))
        assert len(points) >= .12*width, (slot,side,'la manga quedó fuera del recorte')
        d,found,air = np.asarray(points).T
        output.append((len(points),found.mean(),(d <= 1).mean(),np.quantile(d,.85),float(air.mean())))
    return width, output


def verify(root):
    bare = read(root/f'{PREFIX}-sin-manto.png')
    hidden = read(root/f'{PREFIX}-sin-placas.png')
    baseline = np.loadtxt(root/f'{PREFIX}-v16711.tsv')
    assert baseline.shape == (3,4) and np.isfinite(baseline).all()
    failures, before = [], None
    for slot in ('sin-placas','v16711','pecho','curios'):
        anchor = np.loadtxt(root/f'{PREFIX}-{slot}.tsv')
        assert anchor.shape == baseline.shape and np.max(abs(anchor-baseline)) < .55, (slot,'cámara desplazada')
        if slot == 'sin-placas':
            continue
        worn = read(root/f'{PREFIX}-{slot}.png')
        assert bare.shape == hidden.shape == worn.shape
        width, rows = seams(root,slot,worn,bare,hidden)
        for label,(n,found,joined,gap,air) in zip(('izquierda','derecha'),rows,strict=True):
            print(f'A 89,5°, {slot} {label}: {n} columnas, placa visible {found:.0%}, '
                  f'borde a ≤1px {joined:.0%}, separación p85 {gap:.1f}px, suelo {air:.2f}px/col.',flush=True)
        if before is None:
            before = rows
            continue
        for label,old,(n,found,joined,gap,air) in zip(('izquierda','derecha'),before,rows,strict=True):
            if found < .80 or joined < .55 or gap > max(2,.025*width):
                failures.append((slot,label,'el borde de la placa sigue lejos',found,joined,gap))
            if gap > old[3]+.4 or air > min(old[4]+.2,max(.45,.65*old[4])):
                failures.append((slot,label,'aparece suelo entre la manga y la placa',*old[3:],gap,air))
    assert min(row[1] for row in before) > .70 and max(row[3] for row in before) >= 2, (
        'la referencia v1.67.11 no reproduce la separación',before)
    assert not failures, failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    parser.add_argument('--gallery',action='store_true')
    args = parser.parse_args()
    if args.gallery:
        gallery(args.shots,PREFIX)
    else:
        verify(args.shots)
