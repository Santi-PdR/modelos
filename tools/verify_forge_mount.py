#!/usr/bin/env python3
"""Read the Forge client's F5 and vanilla GUI screenshots, not the visor."""
from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image

import cape_icon as I


def read(path):
    with Image.open(path) as im:
        return np.array(im.convert('RGB'),dtype=np.int16)


def contact(bare, worn):
    assert bare.shape == worn.shape
    r,g,b = bare.transpose(2,0,1)
    # Pick the pale teal sleeves and jersey of the smoke client's vanilla
    # skin. The concrete and the soft entity shadow don't enter this mask.
    shirt = (g-r >= 19) & (b-r >= 19)
    assert shirt.any(), 'overhead scene did not capture the wearer'
    _,xx = np.where(shirt)
    left,right = xx.min(),xx.max()+1
    width = right-left
    center = (left+right)/2
    rear = np.where(shirt[:,round(center)])[0][-1]
    # Measure a band just aft of the torso, not the air behind the arms.
    # Bare already contains the entity shadow at exactly this camera pose.
    cols = slice(round(center-.213*width),round(center+.213*width))
    rows = slice(rear+round(.019*width),rear+round(.107*width))
    covered = bare[rows,cols,1] - worn[rows,cols,1] >= 16
    rail = max(1,covered.shape[1]//6)
    return covered.mean(), covered[:,:rail].mean(), covered[:,-rail:].mean()


def shoulder_rails(bare, worn, *, turned=False):
    """Measure each sleeve-to-pad bridge separately, including the first row.

    The torso-only test above passed the v1.67.6 build with visible holes
    at the sleeves. Here the thin strips begin on the *actual* edge of the
    tilted shirt. Reference and equipped shots use the same player pose.
    """
    def align(frame):
        return np.asarray(Image.fromarray(frame.astype(np.uint8)).rotate(-43,Image.Resampling.NEAREST),
                          dtype=np.int16) if turned else frame
    bare,worn = align(bare),align(worn)
    r,g,b = bare.transpose(2,0,1)
    shirt = (g-r >= 19) & (b-r >= 19)
    assert shirt.any()
    _,xx = np.where(shirt)
    width = xx.max() - xx.min() + 1
    center = xx.min() + width/2
    painted = g - worn[...,1] >= 16
    # Light grey concrete is grey-green even under the vanilla entity shadow.
    # Tests against the matching bare shirt alone miss holes *between* the
    # external tabs and the seat: check concrete in those inner strips too.
    wr,wg,wb = worn.transpose(2,0,1)
    floor = (abs(wr-wg) <= 2) & (wg-wb >= 3) & (wg-wb <= 16) & (wg >= 35)
    rails = []
    for direction in (-1,1):
        columns = [(x,direction*(x-center)/width)
                   for x in range(round(center-.43*width),round(center+.43*width))]
        edge = {x: np.flatnonzero(shirt[:,x])[-1]+1 for x,_ in columns if shirt[:,x].any()}
        outer = [(x,edge[x]) for x,f in columns if .32 <= f <= .41 and x in edge]
        assert len(outer) > .05*width, ('no se ve la manga exterior',turned,direction,len(outer),width)
        measured = np.stack([painted[y:y+max(3,round(.054*width)),x] for x,y in outer])
        # At 43° the head hides some of the shirt pixels along one seam.
        # Extrapolate the exposed sleeve edge under the head instead of
        # dropping columns (which would miss the hole being tested).
        rear = round(float(np.median([y for _,y in outer])))
        inner = []
        for x,f in columns:
            if .22 <= f <= .35:
                y = edge.get(x,rear)
                if abs(y-rear) > .027*width:
                    y = rear
                inner.append(floor[y:y+max(6,round(.106*width)),x])
        holes = np.stack(inner)
        opening = np.lib.stride_tricks.sliding_window_view(holes,(3,3)).all(axis=(-1,-2)).any()
        rails.append((float(measured.mean()),float(measured[:,:2].mean()),float(holes.mean()),bool(opening)))
    return rails


def upper_back(root, prefix):
    bare = read(root/f'{prefix}-sin-manto.png')
    key = f'{prefix}-sin-union'
    control = read(root/f'{key}.png')
    points = np.loadtxt(root/f'{key}.tsv', dtype=int)
    assert points.shape == (31*8,4)
    u,v,x,y = points.T
    h,w = bare.shape[:2]
    assert (0 <= x.min() < x.max() < w) and (0 <= y.min() < y.max() < h), 'contact strip outside the view'
    r,g,b = bare[y,x].T
    # Only samples on the exposed jersey count in the oblique view: the
    # head and sleeves can hide some, and replacing floor does not count.
    # For profile the probe is a cross-section of the solid bevel, so its
    # projection lies between the shirt and collar, not on the jersey.
    visible = (g-r >= 19) & (b-r >= 19) if prefix == 'oblicua' else np.ones(len(points),dtype=bool)
    assert visible.sum() >= 55 and np.ptp(u[visible]) >= 9, (key, 'no se ve la unión', int(visible.sum()))
    def cloth(im):
        r,g1,b = im[y,x].T
        return visible & (g-g1 >= 16) & (np.maximum(r,b)-g1 >= 10)
    prev = cloth(control)
    failures = []
    for slot in ('pecho','curios'):
        name = f'{prefix}-{slot}'
        resolved = np.loadtxt(root/f'{name}.tsv', dtype=int)
        assert np.array_equal(resolved[:,:2],points[:,:2]) and np.max(abs(resolved[:,2:]-points[:,2:])) <= 1, (name, 'cámara distinta')
        now = cloth(read(root/f'{name}.png'))
        old, new = prev.sum()/visible.sum(), now.sum()/visible.sum()
        # Demand a panel across the visible strip, not one clasp or tooth.
        rails = [now[visible & (u == col)].mean() for col in np.unique(u[visible])]
        joined = np.mean(np.asarray(rails) >= .7)
        print(f'{name}: unión visible en espalda alta {old:.1%} → {new:.1%}; ancho {joined:.1%} ({visible.sum()} muestras).',flush=True)
        if old > .55 or new < .84 or new-old < .28 or joined < .77:
            failures.append((name,old,new,joined))
    return failures


def hotbar(root):
    paths = sorted(root.glob('hotbar-[0-9][0-9].png'))
    assert len(paths) == I.COUNT+2, len(paths)
    pixels = np.stack([read(p) for p in paths])
    assert pixels.shape[1:] == (44,112,3)
    slot = pixels[:,6:38,40:72]
    bare = read(root/'hotbar-vacia.png')
    silhouette = np.median(np.abs(slot-bare[6:38,40:72]).max(axis=3),axis=0) >= 20
    area = int(silhouette.sum())
    spread = np.ptp(pixels,axis=0).max(axis=-1)
    change = spread[6:38,40:72]
    peak = int(change.max())
    seams = int((change[6:] >= 14).sum())
    # Check the crest moves vertically, not a single global change in tint.
    rest = np.min(slot, axis=0)
    energy = np.maximum(np.abs(slot-rest).max(axis=-1)-10,0)
    active = energy.sum((1,2)) >= 400
    centroids = (energy[active]*np.arange(32)[None,:,None]).sum((1,2))/energy[active].sum((1,2))
    assert len(centroids) >= 15 and np.ptp(centroids) >= 5, ('pulso fijo',centroids)
    # The player is standing still and unequipped: the rest of the hotbar
    # must not be what moves. These are actual game framebuffer pixels.
    outside = [spread[:6].max(),spread[38:].max(),spread[:,:40].max(),spread[:,72:].max()]
    assert max(outside) <= 4, outside
    assert peak >= 90 and seams >= 130, (peak,seams)
    assert len(np.unique(slot.reshape(len(slot),-1), axis=0)) >= 24
    target = np.asarray(I.first_frame().resize((32,32),Image.Resampling.NEAREST),dtype=np.int16)
    opaque = target[...,3] == 255
    # The nearest-neighbor sampling origin can round a physical pixel at
    # some framebuffer sizes. Compare only the original opaque artwork.
    err = min(np.median(np.abs(sample[opaque]-target[opaque,:3]).max(1))
              for frame in slot for x in (-1,0,1) for y in (-1,0,1)
              for sample in (np.roll(frame, (y,x), axis=(0,1)),))
    assert err <= 26, f'hotbar shape/colors did not match the shipped art: {err}'
    overlap = max(np.count_nonzero(sample & opaque)/np.count_nonzero(sample | opaque)
                  for x in (-1,0,1) for y in (-1,0,1)
                  for sample in (np.roll(silhouette, (y,x), axis=(0,1)),))
    assert overlap >= .87, overlap
    print(f'Hotbar de Forge: {area} px visibles a 2×, pulso Δ{peak}/255 en '
          f'{seams} px, recorrido {np.ptp(centroids):.1f}px; fondo estable.',flush=True)
    return pixels


def emit(title, data):
    encoded = base64.b64encode(data).decode('ascii')
    for i in range(0,len(encoded),1700):
        print(f'::notice title={title} {i//1700:02}::{encoded[i:i+1700]}')


def gallery(root, kind):
    # Thumbnail evidence also available where Actions' artifact storage
    # cannot be downloaded. Full-resolution shots stay in the artifact.
    if kind != 'hotbar':
        prefix = {'giro':'cenital-giro', 'perfil':'perfil', 'oblicua':'oblicua'}.get(kind,'cenital')
        if kind == 'bare':
            names = ('cenital-sin-manto','cenital-giro-sin-manto')
        elif kind == 'ajuste':
            names = ('ajuste-sin-manto', 'ajuste-v1678', 'ajuste-pecho', 'ajuste-curios')
        elif kind == 'perfil-base':
            names = ('oblicua-sin-manto','perfil-sin-manto')
        elif kind in ('perfil','oblicua'):
            names = tuple(f'{prefix}-{slot}' for slot in ('sin-union','pecho','curios'))
        else:
            names = (f'{prefix}-pecho',f'{prefix}-curios')
        for name in names:
            path = root/f'{name}.png'
            if not path.exists(): continue
            with Image.open(path) as im:
                x,y = im.width//2, im.height//2
                cut = im.crop((x-120,y-70,x+120,y+122)) if path.stem.startswith('cenital') else im.crop((x-128,y-80,x+128,y+130))
                # Each GitHub job step retains up to ten notices. Reserve
                # at most half of them for either slot, even in a busy shot.
                close = kind in ('oblicua','perfil','ajuste')
                cap = 2450 if kind == 'ajuste' else 3820 if close else 6350
                for width,colors in ((180,80),(160,64),(144,48),(128,40),(112,32),(96,28)):
                    buf = io.BytesIO()
                    small = cut.resize((width,round(width*.8)),Image.Resampling.NEAREST)
                    small.convert('RGB').quantize(colors=colors).save(buf,format='PNG',optimize=True)
                    if len(buf.getvalue()) <= cap: break
                assert len(buf.getvalue()) <= cap, name
                emit('Cenital '+path.stem,buf.getvalue())
    else:
        paths = sorted(root.glob('hotbar-[0-9][0-9].png'))[:I.COUNT]
        assert len(paths) == I.COUNT
        frames = [Image.fromarray(read(p).astype(np.uint8)) for p in paths]
        # Keep the native-resolution slot. The rest does not move, so use
        # a smaller margin around the real slot for check-run previews.
        frames = [f.crop((24,2,88,42)) for f in frames]
        full = np.concatenate([np.asarray(f) for f in frames])
        for colors in (96,64,48,32):
            palette = Image.fromarray(full).quantize(colors=colors)
            indexed = [f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
            buf = io.BytesIO()
            indexed[0].save(buf,format='GIF',save_all=True,append_images=indexed[1:],loop=0,duration=50*I.TICKS)
            data = buf.getvalue()
            if len(data) <= 12700: break
        (root/'hotbar-ciclo.gif').write_bytes(data)
        assert len(data) <= 12700, 'hotbar preview exceeds the annotation budget'
        emit('Ranura hotbar-ciclo',data)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots',type=Path)
    cli.add_argument('--gallery',choices=['cenital','giro','bare','oblicua','perfil','perfil-base','hotbar','ajuste'])
    args = cli.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
        return
    bare = read(args.shots/'cenital-sin-manto.png')
    center = []
    for slot in ('pecho','curios'):
        all_,left,right = contact(bare,read(args.shots/f'cenital-{slot}.png'))
        center.append(f'{slot} {all_:.1%} (márgenes {left:.1%}/{right:.1%})')
        assert all_ >= .93 and min(left,right) >= .85, 'suelo visible entre torso y unión del cuello'
    print('Anclaje cenital: ' + '; '.join(center),flush=True)
    failures = []
    for turned in (False,True):
        prefix = 'cenital-giro' if turned else 'cenital'
        control = read(args.shots/f'{prefix}-sin-manto.png') if turned else bare
        for name in ('pecho','curios'):
            key = f'{prefix}-{name}'
            rails = shoulder_rails(control,read(args.shots/f'{key}.png'),turned=turned)
            print(f'{key}: remates laterales {rails[0][0]:.1%}/{rails[1][0]:.1%}; '
                  f'junto a manga {rails[0][1]:.1%}/{rails[1][1]:.1%}; '
                  f'suelo interior {rails[0][2]:.1%}/{rails[1][2]:.1%}.',flush=True)
            if not all(total >= .78 and edge >= .55 and floor <= .04 and not opening
                       for total,edge,floor,opening in rails):
                failures.append((key,rails))
    high = [failure for prefix in ('oblicua','perfil') for failure in upper_back(args.shots,prefix)]
    hotbar(args.shots)
    assert not failures, ('hueco entre manga y remate',failures)
    assert not high, ('unión alta no visible',high)


if __name__ == '__main__':
    try:
        main()
    except (AssertionError,ValueError,FileNotFoundError) as exc:
        print(f'::error title=Anclaje y ranura en Forge::{exc}',flush=True)
        raise
