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
    return ('-v1280', '', '-cuello') if view in WIDE_VIEWS else ('-v1280', '-v16712', '')


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


def visible_attachment(root, view, slot, suffix=''):
    stem = root/f'historia-{view}-{slot}{suffix}'
    worn = read(stem.with_suffix('.png'))
    bare = read(root/f'historia-{view}-sin-manto.png')
    assert worn.shape == bare.shape
    skin = shirt_mask(bare) & ~blue_floor(bare) & (bare[...,1] > 92)
    _y, x = np.where(skin)
    assert len(x) > 500, (view, slot, 'sin camiseta visible')
    width = np.ptp(np.quantile(x,[.005,.995]))
    near = np.asarray(Image.fromarray((skin*255).astype('uint8')).filter(ImageFilter.MaxFilter(1+2*round(.10*width)))) > 0
    h,w = skin.shape
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
    # Projection alone isn't a visible join. Keep only actual cloth pixels
    # in the F5 framebuffer that differ from the unequipped control.
    fabric = ((np.abs(worn-bare).max(2) >= 18) & ~blue_floor(worn) & ~shirt_mask(worn)
              & (worn[...,1] < 97))
    metrics = []
    for mask in sections:
        visible = (np.asarray(mask)>0) & fabric
        count = visible.sum()
        # At large turns the near sleeve may hide the opposite plate.
        # Report its visibility, rather than treating an occlusion as a hole.
        if view not in WIDE_VIEWS or mask is sections[2]:
            assert count >= 12, (view,slot,'pieza no visible en F5',count)
        metrics.append((int(count),float(near[visible].mean()) if count else 0.))
    return metrics


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
    """Registered A/B for the still collar. Report the look; don't assume a fix."""
    for view in WIDE_VIEWS:
        by_slot = []
        for slot in SLOTS:
            stem = root/f'historia-{view}-{slot}'
            with Image.open(stem.with_suffix('.png')) as image:
                size = image.size
            versions = variants(view)
            poses = [np.loadtxt(stem.with_name(stem.name+s+'-camara.tsv'))*size for s in versions]
            assert all(m.shape == (8,2) and np.isfinite(m).all() for m in poses), stem
            drift = max(abs(m-poses[1]).max() for m in poses)
            assert drift < .65, (view,slot,'cámara F5 no registrada',drift)
            by_slot.append(poses[1])
            ref, base, trial = (geometry(root,view,slot,s) for s in versions)
            p0, p1 = (bounds(stem.with_name(stem.name+s+'.tsv')) for s in versions[1:])
            for name in ('v18_pad_0', 'v18_pad_1', 'v17_cowl_return', 'v17_cowl_tooth_5'):
                np.testing.assert_allclose(p0[name],p1[name],rtol=0,atol=.015,err_msg=f'{stem}: {name} se movió en la sonda')
            np.testing.assert_allclose(base[3:],trial[3:],rtol=0,atol=.08,err_msg=f'{stem}: altura de cuello o raíces cambiaron')
            assert .8 < ref[2] < 1.4 and 1.25 < base[2]-trial[2] < 1.50, (stem, ref, base, trial)
            counts = [visible_attachment(root,view,slot,s)[2] for s in versions]
            cloth = ' → '.join(f'{f:.0%} ({n}px)' for n,f in counts)
            print(f'{view}/{slot} · registro {drift:.2f}px · referencia → actual → sonda: '
                  f'Z delantero del cuello {ref[2]:.2f} → {base[2]:.2f} → {trial[2]:.2f}u; '
                  f'raíces {base[4]:.2f}u; píxeles en la proyección del cuello cerca de camiseta {cloth}',flush=True)
        assert abs(by_slot[0]-by_slot[1]).max() < .65, (view,'pecho y Curios no registrados')


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
    # Both historical slots and the bare control stay in the full artifact.
    # The ten wide-turn thumbnails must fit the same job annotation budget.
    suffixes = ('pecho-v1280','pecho','pecho-cuello','curios','curios-cuello') if view in WIDE_VIEWS else (
        'sin-manto', *(f'{slot}{s}' for slot in SLOTS for s in variants(view)))
    for suffix in suffixes:
        file = root/f'historia-{view}-{suffix}.png'
        if not file.is_file():
            continue
        with Image.open(file) as im:
            sample = im.convert('RGB').crop(crop)
        # Leave room in the 50-annotation budget for metrics and failures.
        for rate in (1,.86,.73,.62,.53,.44,.36,.30):
            buf = io.BytesIO()
            sample.resize((round(rate*sample.width),round(rate*sample.height)),Image.Resampling.NEAREST).save(
                buf,format='WEBP',quality=83,method=6)
            if len(buf.getvalue()) <= 1275:
                break
        assert len(buf.getvalue()) <= 1275, file
        emit('Anclaje histórico '+file.stem,buf.getvalue())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots',type=Path)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--gallery',choices=VIEWS+WIDE_VIEWS)
    mode.add_argument('--giro-amplio',action='store_true',help='auditar la sonda de cuello sin asumir un cambio de ajuste')
    args = ap.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
    elif args.giro_amplio:
        study_wide_turn(args.shots)
    else:
        verify(args.shots)
