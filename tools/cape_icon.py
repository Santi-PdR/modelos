#!/usr/bin/env python3
"""Extract the chosen pixel art and animate its existing pink fissures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'referencias/REFERENCIA_ICONO_v1677.png'
SOURCE_SHA = '0bc0ba2efea3bf9e03dbb3c266f34291b2b59af730044ded0f2e98ca38855e99'
PREVIOUS = ROOT / 'referencias/ICONO_V1676_BACKUP.png'
ICON = ROOT / 'src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png'
META = ICON.with_suffix('.png.mcmeta')
# Fill a 16-pixel slot without drawing past its border. A multiple of 16
# preserves the four mip levels of a normal vanilla item atlas.
SIZE, COUNT, TICKS = 64, 16, 2
ART_SIZE = (56, 62)


def base_frame() -> Image.Image:
    with Image.open(SOURCE) as source:
        assert source.size == (1024,1024)
        raw = np.asarray(source.convert('RGB'))
    # Median from the centres of half-cells. Neither the rescaled tile
    # borders nor the nearly neutral checker colors belong to the drawing.
    axis = (np.arange(SIZE)*16 + 8)
    taps = axis[:,None] + np.arange(-2,3)
    rgb = np.median(raw[taps[:,None,:,None], taps[None,:,None,:]], axis=(2,3)).astype(np.uint8)
    art = (rgb.max(2) < 158) | ((np.ptp(rgb,axis=2) > 27) & (rgb[...,1] < 154))
    rgba = np.dstack((np.where(art[...,None],rgb,0), 255*art)).astype(np.uint8)
    image = Image.fromarray(rgba)
    assert image.getbbox() == (9,6,54,61), 'the source silhouette changed'
    sprite = Image.new('RGBA',(SIZE,SIZE))
    # A little extra width on the display raster: 13–14 px at GUI scale 1.
    sprite.paste(image.crop(image.getbbox()).resize(ART_SIZE,Image.Resampling.NEAREST), (4,1))
    return sprite


def frames() -> list[Image.Image]:
    base = base_frame()
    rgba = np.asarray(base).astype(float)
    y,x = np.indices((SIZE,SIZE))
    r,g,b,a = rgba.transpose(2,0,1)
    veins = (r >= 127) & (r-g >= 72) & (b-g >= 39) & (a == 255) & (y >= 13)
    light = np.maximum(rgba[...,:3],[255,133,242]) - rgba[...,:3]
    out = [base]
    for phase in np.arange(1,COUNT)/COUNT:
        breath = np.sin(np.pi * phase)**2
        sweep = np.exp(-((y+.17*(x-32) - (10+64*phase))/8.8)**2)
        amount = breath*(.18+.63*sweep)*veins
        colored = rgba.copy()
        colored[...,:3] += light * amount[...,None]
        out.append(Image.fromarray(np.rint(colored).astype(np.uint8)))
    return out


def metadata() -> dict:
    # The item atlas advances this strip in hotbar/inventory. No custom
    # renderer, stack state, resource pack or alternate model overrides.
    return {'animation': {'width': SIZE, 'height': SIZE, 'frametime': TICKS, 'interpolate': False}}


def first_frame(path: Path = ICON) -> Image.Image:
    with Image.open(path) as texture:
        return texture.crop((0,0,texture.width,texture.width)).convert('RGBA')


def write() -> None:
    sheet = Image.new('RGBA', (SIZE, SIZE*COUNT))
    for index,image in enumerate(frames()):
        sheet.paste(image,(0,index*SIZE))
    sheet.save(ICON, optimize=True)
    META.write_text(json.dumps(metadata(), indent=2)+'\n')
    print(f'Icono: {COUNT} cuadros de {SIZE}px, {TICKS} ticks/cuadro, pulso sobre la referencia nueva.')


def verify() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    assert json.loads(META.read_text()) == metadata()
    with Image.open(ICON) as baked:
        assert baked.size == (SIZE,SIZE*COUNT) and baked.mode == 'RGBA'
        actual = np.asarray(baked).reshape(COUNT,SIZE,SIZE,4)
    generated = frames()
    np.testing.assert_array_equal(actual,np.stack([np.asarray(f) for f in generated]))
    a = actual[0,...,3]
    assert first_frame().getbbox() == (4,1,60,63)
    assert set(np.unique(a)) == {0,255}
    assert not actual[:,a==0,:3].any(), 'checker outside the artwork'
    assert np.all(actual[...,3] == a), 'outline changed during the pulse'
    low = np.array([np.asarray(f.resize((16,16),Image.Resampling.NEAREST)) for f in generated])
    prev = np.asarray(first_frame(PREVIOUS).resize((16,16),Image.Resampling.NEAREST))
    count = np.count_nonzero(low[0,...,3])
    assert count >= 1.14*np.count_nonzero(prev[...,3]), (count,np.count_nonzero(prev[...,3]))
    spread = np.ptp(low[...,:3],axis=0).max(axis=2)
    assert spread.max() >= 60 and np.count_nonzero(spread >= 14) >= 13
    assert np.count_nonzero(spread[:3]) == 0, 'the collar must not flash'
    print(f'Icono: {count}/256 píxeles de silueta a escala 1, sin damero y con animación sólo en las grietas.', flush=True)


if __name__ == '__main__':
    write()
    verify()
