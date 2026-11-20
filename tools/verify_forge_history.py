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
from PIL import Image, ImageDraw, ImageFilter

from verify_forge_mount import emit, read
from verify_forge_seat import blue_floor, shirt_mask

VIEWS = ('diagonal', 'espejo', 'cenital')
WIDE_VIEWS = ('giro-amplio', 'giro-inverso')
SLOTS = ('pecho', 'curios')


def variants(view):
    return ('-v1280', '-v16713', '') if view in WIDE_VIEWS else ('-v1280', '-v16712', '')


def bounds(path):
    with path.open(newline='') as fd:
        values = {row[0]: np.array(tuple(map(float, row[1:]))).reshape(2, 3)
                  for row in list(csv.reader(fd, delimiter='\t'))[1:]}
    assert all(np.isfinite(b).all() and (b[1] >= b[0]).all() for b in values.values()), path
    return values


def geometry(root, view, slot, suffix=''):
    parts = bounds(root/f'historia-{view}-{slot}{suffix}.tsv')
    pads = [parts[f'v18_pad_{i}'] for i in range(2)]
    cowl = np.array([b for n,b in parts.items() if n.startswith('v17_cowl_back_')])
    roots = np.array([b for n,b in parts.items() if n.startswith('v17_ribbon_') and n.endswith('_seg0')])
    assert len(cowl) >= 5 and len(roots) == 12, (view, slot, suffix, len(cowl), len(roots))
    return np.array([pads[0][1,0], -pads[1][0,0], cowl[:,0,2].min(), cowl[:,1,1].max(),
                     roots[:,0,2].mean(), roots[:,1,1].max()])


def shirt_region(bare):
    skin = shirt_mask(bare) & ~blue_floor(bare) & (bare[...,1] > 92)
    _y, x = np.where(skin)
    assert len(x) > 500, 'sin camiseta visible'
    width = np.ptp(np.quantile(x,[.005,.995]))
    near = np.asarray(Image.fromarray((skin*255).astype('uint8')).filter(ImageFilter.MaxFilter(1+2*round(.10*width)))) > 0
    return near


def part_masks(stem, size):
    h,w = size
    sections = [Image.new('L',(w,h)) for _ in range(3)]
    draw = list(map(ImageDraw.Draw,sections))
    with stem.with_name(stem.name+'-caras').with_suffix('.tsv').open() as lines:
        for line in lines:
            name, *p = line.split()
            index = 0 if name == 'v18_pad_0' else 1 if name == 'v18_pad_1' else 2 if name.startswith('v17_cowl_back_') else -1
            if index < 0: continue
            quad = np.array(list(map(float,p))).reshape(4,2)*[w,h]
            assert np.isfinite(quad).all(), (name, quad)
            draw[index].polygon([tuple(v) for v in quad],fill=255)
    return [np.asarray(mask) > 0 for mask in sections]


def fabric_pixels(bare, worn):
    # Projection alone isn't a visible join. Keep only actual cloth pixels
    # in the F5 framebuffer that differ from the unequipped control.
    return ((np.abs(worn-bare).max(2) >= 18) & ~blue_floor(worn) & ~shirt_mask(worn)
              & (worn[...,1] < 97))

def visible_attachment(root, view, slot, suffix=''):
    stem = root/f'historia-{view}-{slot}{suffix}'
    worn = read(stem.with_suffix('.png'))
    bare = read(root/f'historia-{view}-sin-manto.png')
    assert worn.shape == bare.shape
    near = shirt_region(bare)
    fabric = fabric_pixels(bare,worn)
    metrics = []
    for mask in part_masks(stem,near.shape):
        visible = mask & fabric
        count = visible.sum()
        assert count >= 12, (view,slot,'pieza no visible en F5',count)
        metrics.append((int(count),float(near[visible].mean())))
    return metrics


def isolated_crown(stem, bare, near, suffix):
    # One withheld part, same light and registered pose. Other opaque pieces
    # inside the crown's projected quads cannot count as crown pixels.
    worn = read(stem.with_name(stem.name+suffix+'.png'))
    hidden = read(stem.with_name(stem.name+suffix+'-sin-cuello.png'))
    assert worn.shape == hidden.shape == bare.shape, stem
    mask = part_masks(stem.with_name(stem.name+suffix),near.shape)[2]
    assert mask.sum() >= 75, (stem,'proyección de cuello demasiado pequeña')
    real = mask & fabric_pixels(bare,worn) & (np.abs(worn-hidden).max(2) >= 15)
    return int(real.sum()), int((real & near).sum()), int(mask.sum())


def verify(root):
    errors = []
    for view in VIEWS:
        for slot in SLOTS:
            stem = root/f'historia-{view}-{slot}'
            with Image.open(stem.with_suffix('.png')) as image:
                size = image.size
            samples = [np.loadtxt(stem.with_name(stem.name+s+'-camara.tsv'))*size for s in ('-v1280','-v16712','')]
            assert all(m.shape == (8,2) and np.isfinite(m).all() for m in samples)
            drift = max(abs(m-samples[0]).max() for m in samples[1:])
            assert drift < .65, (view,slot,'cámara F5 no registrada',drift)
            old, prior, now = (geometry(root,view,slot,s) for s in ('-v1280','-v16712',''))
            assert 6.2 < old[0] < 6.9 and 6.2 < old[1] < 6.9, (view, slot, old)
            assert .8 < old[2] < 1.4 and 24 < old[3] < 26.1, (view, slot, old)
            assert 1.2 < old[4] < 2.9, (view, slot, old)
            if view == 'cenital':
                correct = prior[2]-now[2] > 1.18 and now[1] < 7.80 and now[2] < 3.15 and now[3] < 26.65 and now[4] < 3.55
            else:
                correct = (prior[1]-now[1] > 2.40 and prior[4]-now[4] > .34 and 6.0 < now[1] < 7.20
                           and now[2] < 4.31 and now[3] < 25.1 and now[4] < 3.82)
            values = ', '.join(f'{a:.2f}→{b:.2f}→{c:.2f}' for a,b,c in zip(old,prior,now,strict=True))
            before, metrics = [visible_attachment(root,view,slot,s) for s in ('-v16712','')]
            changes = [x-a for (_,a),(_,x) in zip(before,metrics,strict=True)]
            pixels = ', '.join(f'{a:.0%}→{x:.0%} ({p}px)' for (_,a),(p,x) in zip(before,metrics,strict=True))
            print(f'{view}/{slot} · registro {drift:.2f}px · v1.28.0→v1.67.12→prueba (u): '
                  f'extremos X D/I, Z/Y cuello, Z/Y raíces: {values} · píxeles proyectados '
                  f'cerca de la camiseta (placas y cuello): {pixels}',flush=True)
            # Require an improvement in the visible collar and preserve both
            # sleeve contacts, in addition to the body-space placement test.
            if not correct or any(x < .10 for _,x in metrics) or changes[2] < .10 or min(changes) < -.05:
                errors.append((view,slot,correct,[(n,round(f,3)) for n,f in metrics],np.round(changes,3).tolist()))
    assert not errors, errors


def study_wide_turn(root):
    """The published .13 and the live fit, each with its own hidden-crown control."""
    problems = []
    for view in WIDE_VIEWS:
        by_slot = []
        bare = read(root/f'historia-{view}-sin-manto.png')
        near = shirt_region(bare)
        for slot in SLOTS:
            stem = root/f'historia-{view}-{slot}'
            size = np.array(bare.shape[:2][::-1])
            versions = variants(view)
            pose_suffixes = (*versions, '-v16713-sin-cuello', '-sin-cuello')
            poses = [np.loadtxt(stem.with_name(stem.name+s+'-camara.tsv'))*size for s in pose_suffixes]
            assert all(m.shape == (8,2) and np.isfinite(m).all() for m in poses), stem
            drift = max(abs(m-poses[1]).max() for m in poses)
            assert drift < .65, (view,slot,'cámara F5 no registrada',drift)
            by_slot.append(poses[2])
            ref, base, now = (geometry(root,view,slot,s) for s in versions)
            p0, p1 = (bounds(stem.with_name(stem.name+s+'.tsv')) for s in versions[1:])
            for name in ('v18_pad_0', 'v18_pad_1', 'v17_cowl_return', 'v17_cowl_tooth_5'):
                np.testing.assert_allclose(p0[name],p1[name],rtol=0,atol=.015,err_msg=f'{stem}: {name} se movió')
            np.testing.assert_allclose(base[4:],now[4:],rtol=0,atol=.08,err_msg=f'{stem}: las raíces se movieron')
            assert .8 < ref[2] < 1.4 and 5.95 < base[2] < 6.05 and 4.1 < now[2] < 4.45, (stem, ref, base, now)
            assert 1.35 < now[3]-base[3] < 1.70, (stem,'el remate del cuello perdió altura o se levantó demasiado',base[3],now[3])
            a, b = (isolated_crown(stem,bare,near,s) for s in versions[1:])
            prev,n0,area0 = a
            current,n1,area1 = b
            assert prev >= 100 and current > 0, (view,slot,'el control oculto no aisló el cuello',a,b)
            retention = current/prev
            frac0,frac1 = n0/prev,n1/current
            oc0,oc1 = prev/area0,current/area1
            print(f'{view}/{slot} · registro {drift:.2f}px · Z histórico → v1.67.13 → actual '
                  f'{ref[2]:.2f} → {base[2]:.2f} → {now[2]:.2f}u; raíces {now[4]:.2f}u; '
                  f'cuello aislado {prev} → {current}px, cerca de camiseta {n0} → {n1}px ({frac0:.0%} → {frac1:.0%}); '
                  f'visible/proyectado {oc0:.0%} → {oc1:.0%}',flush=True)
            if (retention < .65 or frac1-frac0 < .15 or n1-n0 < .10*prev or oc1 < .82*oc0):
                problems.append((view,slot,a,b,'apoyo insuficiente, oclusión o pérdida de silueta'))
        assert abs(by_slot[0]-by_slot[1]).max() < .65, (view,'pecho y Curios no registrados')
    assert not problems, problems


def framing(image):
    mask = shirt_mask(image) & ~blue_floor(image)
    h,w = mask.shape
    ys,xs = np.where(mask)
    keep = (np.abs(xs-w/2) < .25*w) & (np.abs(ys-h/2) < .30*h)
    xs,ys = xs[keep],ys[keep]
    assert len(xs) > 500, 'no se ve la camiseta de referencia'
    x0,x1 = np.quantile(xs,[.005,.995]); y0,y1 = np.quantile(ys,[.005,.995]); d = x1-x0
    return (round(x0-.43*d),round(y0-.73*d),round(x1+.43*d),round(y1+.69*d))


def thumbnail(file, crop, title):
    with Image.open(file) as im:
        sample = im.convert('RGB').crop(crop)
    # Leave room in the 50-annotation budget for metrics and failures.
    for rate in (1,.86,.73,.62,.53,.44,.36,.30):
        buf = io.BytesIO()
        sample.resize((round(rate*sample.width),round(rate*sample.height)),Image.Resampling.NEAREST).save(
            buf,format='WEBP',quality=83,method=6)
        if len(buf.getvalue()) <= 1275:
            emit(title+' '+file.stem,buf.getvalue())
            return
    raise AssertionError(f'{file}: recorte demasiado grande')


def gallery(root, view):
    base = root/f'historia-{view}-sin-manto.png'
    if not base.is_file():
        return
    crop = framing(read(base))
    # Both historical slots and the bare control stay in the full artifact.
    # The ten wide-turn thumbnails must fit the same job annotation budget.
    suffixes = ('pecho-v1280','pecho-v16713','pecho','curios-v16713','curios') if view in WIDE_VIEWS else (
        'sin-manto', *(f'{slot}{s}' for slot in SLOTS for s in variants(view)))
    for suffix in suffixes:
        file = root/f'historia-{view}-{suffix}.png'
        if not file.is_file():
            continue
        thumbnail(file,crop,'Anclaje histórico')


def sweep_gallery(root):
    for slot in SLOTS:
        files = [root/f'giro-vivo-{slot}-{turn:+03d}.png' for turn in (48,60,68,79)]
        assert all(file.is_file() for file in files), (slot,'faltan fotogramas del giro')
        left,top,right,bottom = zip(*(framing(read(file)) for file in files),strict=True)
        crop = (min(left),min(top),max(right),max(bottom))
        for file in files:
            thumbnail(file,crop,'Recorrido F5')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots',type=Path)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--gallery',choices=VIEWS+WIDE_VIEWS)
    mode.add_argument('--recorrido',action='store_true',help='publicar recortes F5 de la secuencia de giro')
    mode.add_argument('--giro-amplio',action='store_true',help='comparar el cuello real en F5 con v1.67.13 y sus controles ocultos')
    args = ap.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
    elif args.recorrido:
        sweep_gallery(args.shots)
    elif args.giro_amplio:
        study_wide_turn(args.shots)
    else:
        verify(args.shots)
