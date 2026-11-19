#!/usr/bin/env python3
"""Recover the supplied pixel art and animate it as a vanilla item sprite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'referencias/REFERENCIA_ICONO_v1676.png'
SOURCE_SHA = '5843b3c45a8f3a5a9630507a38236307a208cff1b391a18173d19bf92ab4d6d4'
ICON = ROOT / 'src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png'
META = ICON.with_suffix('.png.mcmeta')
# An exact 80 × 80 crop of the half-cell raster, including all the original
# sparks. A multiple of 16 keeps the vanilla atlas's four mip levels.
SIZE, COUNT, TICKS = 80, 16, 2
CROP = (7, 11, 87, 91)
# Pink specks on the checkerboard have partial coverage. Coordinates are
# in the source's 50 × 50 checkerboard, not in the cropped sprite.
MOTES = ((11,19), (35,22), (10,26), (37,26), (37,32), (37,35), (18,36),
         (38,37), (19,38), (19,39), (36,39), (34,40), (36,40), (18,41),
         (25,40), (25,43), (25,44))


def base_frame() -> Image.Image:
    """Sample inside each half-cell, not across the compressed pixel edges."""
    with Image.open(SOURCE) as source:
        assert source.size == (1024,1024)
        raw = np.asarray(source.convert('RGB'))
    center = np.rint((np.arange(100) + .5) * 1024/100).astype(int)
    taps = center[:,None] + np.arange(-2,3)
    rgb = np.rint(np.median(raw[taps[:,None,:,None], taps[None,:,None,:]], axis=(2,3)))
    y,x = np.indices(rgb.shape[:2]) // 2
    bg = np.where((x+y) % 2, 197, 141)
    delta = rgb - bg[...,None]
    mote = np.isin(y*50+x, [v*50+u for u,v in MOTES])
    cloth = (np.max(abs(delta),axis=2) > 18) & ~mote
    pink = np.clip((rgb[...,0] - rgb[...,1] - 4)/105, 0, 1)
    pink[pink < .105] = 0  # compression noise on adjacent gray tiles
    alpha = np.where(mote, pink, cloth)
    # Remove the gray matte from the pale, translucent sparks too.
    rgb[mote] = bg[mote,None] + delta[mote] / np.maximum(alpha[mote,None], 1e-6)
    rgba = np.dstack((np.where(alpha[...,None] > 0, np.clip(rgb,0,255), 0), 255*alpha))
    return Image.fromarray(np.rint(rgba).astype(np.uint8)).crop(CROP)


def frames() -> list[Image.Image]:
    base = base_frame()
    rgba = np.asarray(base).astype(float)
    y,x = np.indices((SIZE,SIZE))
    r,g,b,a = rgba.transpose(2,0,1)
    hue = (r > 105) & (r-g > 42) & (b-g > 11)
    # The reference's star, and only the existing pink seams below it.
    dx,dy = x-45.5, y-23.5
    star = ((abs(dx)+abs(dy) <= 8) & hue) * np.exp(-(dx*dx+dy*dy)/38)
    vein = hue & (a == 255) & (y >= 30) & (star == 0)
    mote = (a > 0) & (a < 255)
    light = np.maximum(rgba[...,:3], [255,234,251]) - rgba[...,:3]
    out = [base]
    for phase in np.arange(1,COUNT)/COUNT:
        envelope = np.sin(np.pi*phase)
        flash = max(0, np.cos(2*np.pi*(phase-.3125)))**2 * envelope
        flow = np.exp(-((y - (16 + 64*phase) + .14*(x-46))/9)**2)
        amount = (.76*flash*star + .46*envelope*flow*vein
                  + .30*mote*envelope*np.maximum(0, np.cos(2*np.pi*phase + y*.14)))
        colored = rgba.copy()
        colored[...,:3] += light * amount[...,None]
        out.append(Image.fromarray(np.rint(colored).astype(np.uint8)))
    return out


def metadata() -> dict:
    # The strip is clocked by the block/item atlas in the game, including
    # the hotbar. No stack state, overrides, BEWLR, or external pack needed.
    return {'animation': {'width': SIZE, 'height': SIZE, 'frametime': TICKS, 'interpolate': False}}


def first_frame(path: Path = ICON) -> Image.Image:
    """Return a still, not a vertically compressed contact sheet."""
    with Image.open(path) as texture:
        return texture.crop((0,0,texture.width,texture.width)).convert('RGBA')


def write() -> None:
    sheet = Image.new('RGBA', (SIZE, SIZE*COUNT))
    for index,image in enumerate(frames()):
        sheet.paste(image,(0,index*SIZE))
    sheet.save(ICON, optimize=True)
    META.write_text(json.dumps(metadata(), indent=2)+'\n')
    print(f'Icono: {COUNT} × {SIZE}px, {TICKS} ticks por cuadro, alfa independiente del checker.')


def verify() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    assert json.loads(META.read_text()) == metadata()
    with Image.open(ICON) as baked:
        assert baked.size == (SIZE,SIZE*COUNT) and baked.mode == 'RGBA'
        actual = np.asarray(baked).reshape(COUNT,SIZE,SIZE,4)
    generated = frames()
    expected = np.stack([np.asarray(f) for f in generated])
    np.testing.assert_array_equal(actual,expected)
    a = actual[0,...,3]
    assert first_frame().getbbox() == (9,3,71,79)
    assert (a == 255).sum() > 2750 and 15 <= ((a > 0) & (a < 255)).sum() <= 60
    assert not actual[:,a==0,:3].any(), 'checker or color outside the original sprite'
    assert np.all(actual[...,3] == a), 'outline changed during the pulse'
    # On a 16 logical pixel slot the pulse still changes the star visibly.
    low = np.array([np.asarray(f.resize((16,16),Image.Resampling.NEAREST)) for f in generated])
    spread = np.ptp(low[...,:3],axis=0).max(axis=2)
    assert spread[3:7,7:11].max() >= 28 and np.count_nonzero(spread > 8) >= 8
    assert np.ptp(actual[...,:3],axis=0)[a > 0].max() > 45
    print('Icono verificado: fuente original, silueta fija y pulso visible incluso a 16 px.', flush=True)


if __name__ == '__main__':
    write()
    verify()
