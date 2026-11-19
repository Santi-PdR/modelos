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


def hotbar(root):
    paths = sorted(root.glob('hotbar-[0-9][0-9].png'))
    assert len(paths) == 18, len(paths)
    pixels = np.stack([read(p) for p in paths])
    assert pixels.shape[1:] == (44,112,3)
    slot = pixels[:,6:38,40:72]
    spread = np.ptp(pixels,axis=0).max(axis=-1)
    change = spread[6:38,40:72]
    star = int(change[4:13,13:23].max())
    seams = int((change[13:25] >= 14).sum())
    # The player is standing still and unequipped: the rest of the hotbar
    # must not be what moves. These are actual game framebuffer pixels.
    outside = [spread[:6].max(),spread[38:].max(),spread[:,:40].max(),spread[:,72:].max()]
    assert max(outside) <= 4, outside
    assert star >= 26 and seams >= 18, (star,seams)
    assert len(np.unique(slot.reshape(len(slot),-1), axis=0)) >= 10
    target = np.asarray(I.first_frame().resize((32,32),Image.Resampling.NEAREST),dtype=np.int16)
    opaque = target[...,3] == 255
    # The nearest-neighbor sampling origin can round a physical pixel at
    # some framebuffer sizes. Compare only the original opaque artwork.
    err = min(np.median(np.abs(sample[opaque]-target[opaque,:3]).max(1))
              for frame in slot for x in (-1,0,1) for y in (-1,0,1)
              for sample in (np.roll(frame, (y,x), axis=(0,1)),))
    assert err <= 26, f'hotbar shape/colors did not match the shipped art: {err}'
    print(f'Hotbar de Forge: estrella Δ{star}/255, {seams} px de grietas animados, fondo estable y arte reconocido.',flush=True)
    return pixels


def emit(title, data):
    encoded = base64.b64encode(data).decode('ascii')
    for i in range(0,len(encoded),1700):
        print(f'::notice title={title} {i//1700:02}::{encoded[i:i+1700]}')


def gallery(root, kind):
    # Thumbnail evidence also available where Actions' artifact storage
    # cannot be downloaded. Full-resolution shots stay in the artifact.
    if kind == 'cenital':
        for path in sorted(root.glob('cenital-*.png')):
            if path.stem == 'cenital-sin-manto': continue
            with Image.open(path) as im:
                x,y = im.width//2, im.height//2
                cut = im.crop((x-120,y-70,x+120,y+122)).resize((180,144),Image.Resampling.NEAREST)
                buf = io.BytesIO()
                cut.convert('RGB').quantize(colors=96).save(buf,format='PNG',optimize=True)
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
    cli.add_argument('--gallery',choices=['cenital','hotbar'])
    args = cli.parse_args()
    if args.gallery:
        gallery(args.shots,args.gallery)
        return
    bare = read(args.shots/'cenital-sin-manto.png')
    for name in ('cenital-pecho','cenital-curios'):
        all_,left,right = contact(bare,read(args.shots/f'{name}.png'))
        print(f'{name}: anclaje {all_:.1%}, márgenes {left:.1%}/{right:.1%}.',flush=True)
        assert all_ >= .93 and min(left,right) >= .85, 'suelo visible entre torso y unión del cuello'
    hotbar(args.shots)


if __name__ == '__main__':
    main()
