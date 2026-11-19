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
    rails = []
    for direction in (-1,1):
        result = []
        for x in range(round(center-.42*width),round(center+.42*width)):
            if not .32 <= direction*(x-center)/width <= .41 or not shirt[:,x].any():
                continue
            end = np.flatnonzero(shirt[:,x])[-1] + 1
            # Preserve the row adjacent to the sleeve. Its placement is
            # noisier when the sleeve bob and yaw straddle a physical pixel.
            result.append(painted[end:end+max(3,round(.054*width)),x])
        assert len(result) > .05*width
        measured = np.stack(result)
        rails.append((float(measured.mean()),float(measured[:,:2].mean())))
    return rails


def hotbar(root):
    paths = sorted(root.glob('hotbar-[0-9][0-9].png'))
    assert len(paths) == 18, len(paths)
    pixels = np.stack([read(p) for p in paths])
    assert pixels.shape[1:] == (44,112,3)
    slot = pixels[:,6:38,40:72]
    spread = np.ptp(pixels,axis=0).max(axis=-1)
    change = spread[6:38,40:72]
    peak = int(change.max())
    seams = int((change[6:] >= 14).sum())
    # The player is standing still and unequipped: the rest of the hotbar
    # must not be what moves. These are actual game framebuffer pixels.
    outside = [spread[:6].max(),spread[38:].max(),spread[:,:40].max(),spread[:,72:].max()]
    assert max(outside) <= 4, outside
    assert peak >= 55 and seams >= 38, (peak,seams)
    assert len(np.unique(slot.reshape(len(slot),-1), axis=0)) >= 10
    target = np.asarray(I.first_frame().resize((32,32),Image.Resampling.NEAREST),dtype=np.int16)
    opaque = target[...,3] == 255
    # The nearest-neighbor sampling origin can round a physical pixel at
    # some framebuffer sizes. Compare only the original opaque artwork.
    err = min(np.median(np.abs(sample[opaque]-target[opaque,:3]).max(1))
              for frame in slot for x in (-1,0,1) for y in (-1,0,1)
              for sample in (np.roll(frame, (y,x), axis=(0,1)),))
    assert err <= 26, f'hotbar shape/colors did not match the shipped art: {err}'
    print(f'Hotbar de Forge: pulso Δ{peak}/255, {seams} px de grietas animados, fondo estable y nuevo arte reconocido.',flush=True)
    return pixels


def emit(title, data):
    encoded = base64.b64encode(data).decode('ascii')
    for i in range(0,len(encoded),1700):
        print(f'::notice title={title} {i//1700:02}::{encoded[i:i+1700]}')


def gallery(root, kind):
    # Thumbnail evidence also available where Actions' artifact storage
    # cannot be downloaded. Full-resolution shots stay in the artifact.
    if kind != 'hotbar':
        prefix = 'cenital-giro' if kind == 'giro' else 'cenital'
        for name in ('pecho','curios'):
            path = root/f'{prefix}-{name}.png'
            if not path.exists(): continue
            with Image.open(path) as im:
                x,y = im.width//2, im.height//2
                cut = im.crop((x-120,y-70,x+120,y+122))
                # Each GitHub job step retains up to ten notices. Reserve
                # at most half of them for either slot, even in a busy shot.
                for width,colors in ((180,80),(160,64),(144,48),(128,40)):
                    buf = io.BytesIO()
                    small = cut.resize((width,round(width*.8)),Image.Resampling.NEAREST)
                    small.convert('RGB').quantize(colors=colors).save(buf,format='PNG',optimize=True)
                    if len(buf.getvalue()) <= 6350: break
                emit('Cenital '+path.stem,buf.getvalue())
    else:
        paths = sorted(root.glob('hotbar-[0-9][0-9].png'))[:I.COUNT]
        assert len(paths) == I.COUNT
        frames = [Image.fromarray(read(p).astype(np.uint8)) for p in paths]
        palette = Image.fromarray(np.concatenate([np.asarray(f) for f in frames])).quantize(colors=128)
        frames = [f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
        buf = io.BytesIO()
        frames[0].save(buf,format='GIF',save_all=True,append_images=frames[1:],loop=0,duration=50*I.TICKS)
        data = buf.getvalue()
        (root/'hotbar-ciclo.gif').write_bytes(data)
        emit('Ranura hotbar-ciclo',data)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots',type=Path)
    cli.add_argument('--gallery',choices=['cenital','giro','hotbar'])
    args = cli.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
        return
    bare = read(args.shots/'cenital-sin-manto.png')
    for name in ('cenital-pecho','cenital-curios'):
        all_,left,right = contact(bare,read(args.shots/f'{name}.png'))
        print(f'{name}: anclaje {all_:.1%}, márgenes {left:.1%}/{right:.1%}.',flush=True)
        assert all_ >= .93 and min(left,right) >= .85, 'suelo visible entre torso y unión del cuello'
    failures = []
    for turned in (False,True):
        prefix = 'cenital-giro' if turned else 'cenital'
        control = read(args.shots/f'{prefix}-sin-manto.png') if turned else bare
        for name in ('pecho','curios'):
            key = f'{prefix}-{name}'
            rails = shoulder_rails(control,read(args.shots/f'{key}.png'),turned=turned)
            print(f'{key}: remates laterales {rails[0][0]:.1%}/{rails[1][0]:.1%}; '
                  f'junto a manga {rails[0][1]:.1%}/{rails[1][1]:.1%}.',flush=True)
            if not all(total >= .78 and edge >= .55 for total,edge in rails):
                failures.append((key,rails))
    hotbar(args.shots)
    assert not failures, ('hueco entre manga y remate',failures)


if __name__ == '__main__':
    main()
