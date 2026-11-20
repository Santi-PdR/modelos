#!/usr/bin/env python3
"""Measure the actual rendered plate rims against both vanilla sleeves in F5."""
import argparse
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from verify_forge_mount import emit, read
from verify_forge_seat import blue_floor, shirt_mask

PREFIX = 'hombreras'


def plate_quads(root, stem, side):
    faces = np.loadtxt(root/f'{stem}-caras.tsv')
    assert faces.ndim == 2 and faces.shape[1] == 9 and np.isfinite(faces).all(), (stem, faces.shape)
    quads = faces[faces[:,0] == side,1:].reshape(-1,4,2)
    assert len(quads) >= 12, (stem, side, 'faltan caras de la hombrera')
    return quads


def visible_plate(quads, worn, bare, unplated):
    assert worn.shape == bare.shape == unplated.shape
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


def sleeve_rim(image):
    # Track the cyan test skin, not sparse pixels from the blue floor, sparks
    # or a colour fringe. At this angle a sleeve is tens of pixels tall.
    aqua = shirt_mask(image) & (image[...,1] > 95) & (np.abs(image[...,2]-image[...,1]) < 30)
    run = aqua[:-2] & aqua[1:-1] & aqua[2:]
    solid = np.zeros_like(aqua)
    solid[:-2] |= run
    solid[1:-1] |= run
    solid[2:] |= run
    height = solid.sum(axis=0)
    columns = np.flatnonzero(height >= max(6, .35*height.max()))
    assert solid.sum() > 600 and len(columns) > 60, 'no se ven ambas mangas'
    return solid, int(columns[0]), int(columns[-1])+1


def seams(root, slot, worn, bare, unplated):
    _,ref_left,ref_right = sleeve_rim(bare)
    width = ref_right-ref_left
    # Read the rim of the sleeve in this draw. Small vanilla idle rolls can
    # move its outermost column even with the torso and camera registered.
    shirt,left,right = sleeve_rim(worn)
    assert max(abs(left-ref_left),abs(right-ref_right)) < .045*width, (
        slot,'mangas sin registrar',(ref_left,ref_right),(left,right))
    output = []
    floor = blue_floor(worn)
    # The outer half of each sleeve, away from the return over the interior.
    # Exclude the last rasterized texel at each silhouette edge.
    near,far = round(.015*width),round(.09*width)
    for side,cols in ((1,range(left+near,left+far)),(0,range(right-far,right-near))):
        mask = visible_plate(plate_quads(root,f'{PREFIX}-{slot}',side),worn,bare,unplated)
        points = []
        for x in cols:
            rear = np.flatnonzero(shirt[:,x])
            if not rear.size:
                continue
            y = int(rear[-1])
            start,stop = y-round(.045*width), y+round(.16*width)
            cloth = np.flatnonzero(mask[start:stop,x])
            rim = start+cloth[0] if cloth.size else stop
            points.append((max(0,rim-y-1),bool(cloth.size),int(floor[y+1:rim,x].sum())))
        assert len(points) >= max(6,.06*width), (
            slot,side,'la manga quedó fuera del recorte',(left,right),width,len(points))
        d,found,air = np.asarray(points).T
        _,plate_cols = np.where(mask)
        overhang = max(0,left-plate_cols.min() if side == 1 else plate_cols.max()-right+1) if plate_cols.size else np.inf
        output.append((len(points),found.mean(),(d <= 1).mean(),np.quantile(d,.85),float(air.mean()),overhang))
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
        for label,(n,found,joined,gap,air,overhang) in zip(('izquierda','derecha'),rows,strict=True):
            print(f'A 89,5°, {slot} {label}: {n} columnas, placa visible {found:.0%}, '
                  f'borde a ≤1px {joined:.0%}, separación p85 {gap:.1f}px, suelo {air:.2f}px/col, '
                  f'extremo {overhang}px fuera de la manga.',flush=True)
        if before is None:
            before = rows
            continue
        for label,old,now in zip(('izquierda','derecha'),before,rows,strict=True):
            _,found,joined,gap,air,overhang = now
            if found < .80 or joined < .50 or gap > max(2,.031*width):
                failures.append((slot,label,'el borde de la placa sigue lejos',found,joined,gap))
            if gap > old[3]+.5 or air > min(old[4]+.25,max(.5,.65*old[4])):
                failures.append((slot,label,'queda suelo entre la manga y la placa',old[3:5],now[3:5]))
            if overhang > max(2,.05*width) or (label == 'izquierda' and overhang > .40*old[5]):
                failures.append((slot,label,'extremo aún fuera de la manga',old[5],overhang))
    assert before[0][1] >= .75 and before[0][5] >= .13*width, (
        'la referencia v1.67.11 no reproduce el extremo separado',before)
    assert not failures, failures


def gallery(root):
    path = root/f'{PREFIX}-sin-manto.png'
    if not path.is_file():
        return
    shirt,left,right = sleeve_rim(read(path))
    y,_ = np.where(shirt[:,left:right])
    width = right-left
    cut = (int(left-.235*width),int(y.min()-.34*width),
           int(right-1+.16*width),int(y.max()+.37*width))
    for slot in ('sin-manto','v16711','pecho','curios'):
        path = root/f'{PREFIX}-{slot}.png'
        if not path.is_file():
            continue
        with Image.open(path) as image:
            patch = image.convert('RGB').crop(cut)
        for rate,colors in ((1,80),(1,48),(1,32),(.88,32),(.76,24),(.65,16),(.55,12)):
            buf = io.BytesIO()
            thumb = patch.resize((round(patch.width*rate),round(patch.height*rate)),Image.Resampling.NEAREST)
            thumb.quantize(colors=colors).save(buf,format='PNG',optimize=True)
            if len(buf.getvalue()) <= 2450:
                break
        assert len(buf.getvalue()) <= 2450, slot
        emit('Cenital '+path.stem,buf.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    parser.add_argument('--gallery',action='store_true')
    args = parser.parse_args()
    if args.gallery:
        gallery(args.shots)
    else:
        verify(args.shots)
