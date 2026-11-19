#!/usr/bin/env python3
"""Extract the chosen pixel art and animate its existing pink fissures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'referencias/REFERENCIA_ICONO_v1677.png'
SOURCE_SHA = '0bc0ba2efea3bf9e03dbb3c266f34291b2b59af730044ded0f2e98ca38855e99'
PREVIOUS = ROOT / 'referencias/ICONO_V1677_PULSO.png'
PREVIOUS_SHA = '460273e99c6a60b532b18c4a36773be53000292a984965e44d12b69d68bcad17'
ICON = ROOT / 'src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png'
META = ICON.with_suffix('.png.mcmeta')
# Fill a 16-pixel slot without drawing past its border. A multiple of 16
# preserves the four mip levels of a normal vanilla item atlas.
SIZE, COUNT, TICKS = 64, 32, 1
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
    fabric = (a == 255) & (y >= 13)
    veins = (r >= 116) & (r-g >= 67) & (b-g >= 33) & fabric
    # Light can hit the reverse lining adjacent to a crack, not the void
    # between the frayed tips. The collar and exterior rim are unlit.
    inset = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
    dusk = np.maximum(rgba[...,:3],[176,63,142]) - rgba[...,:3]
    core = np.maximum(rgba[...,:3],[255,199,247]) - rgba[...,:3]
    length = y + .21*(x-32)
    # Use actual fissure pixels for three glints rather than painting dots
    # or a new star onto the reference artwork.
    yy,xx = np.where(veins)
    glints = []
    for gx,gy,delay in ((23,22,.25),(37,35,.47),(29,49,.69)):
        at = np.argmin((xx-gx)**2 + (yy-gy)**2)
        glints.append((np.exp(-((x-xx[at])**2+(y-yy[at])**2)/5.5),delay))
    out = [base]
    for phase in np.arange(1,COUNT)/COUNT:
        fade = np.sin(np.pi*phase)**1.7
        crest = 4 + 66*phase
        wave = np.exp(-((length-crest)/7.0)**2)
        tail = np.exp(-((length-crest+11)/12.0)**2)
        spark = sum(spot*np.exp(-((phase-delay)/.071)**2) for spot,delay in glints)
        intensity = np.clip(fade*(.13 + .79*wave + .19*tail + .61*spark),0,1)*veins
        bounce = Image.fromarray(np.rint(255*intensity).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.70))
        bounce = np.minimum(1.,np.asarray(bounce)/95.) * (fabric & (inset | veins))
        colored = rgba.copy()
        colored[...,:3] += .66*bounce[...,None]*dusk
        # Mix towards the hot rose core after the diffuse bounce, but never
        # go darker than the original. No alpha motion or enchantment glint.
        colored[...,:3] += intensity[...,None]*np.maximum(core - (colored[...,:3]-rgba[...,:3]),0.)
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
    assert hashlib.sha256(PREVIOUS.read_bytes()).hexdigest() == PREVIOUS_SHA
    with Image.open(PREVIOUS) as saved:
        old_strip = np.asarray(saved.convert('RGBA')).reshape(16,SIZE,SIZE,4)
    np.testing.assert_array_equal(actual[0], old_strip[0])
    old = np.asarray([np.asarray(Image.fromarray(frame).resize((16,16),Image.Resampling.NEAREST)) for frame in old_strip])
    count = np.count_nonzero(low[0,...,3])
    spread = np.ptp(low[...,:3],axis=0).max(axis=2)
    previous = np.ptp(old[...,:3],axis=0).max(axis=2)
    assert spread.max() >= 90 and np.count_nonzero(spread >= 14) >= 1.32*np.count_nonzero(previous >= 14)
    assert np.count_nonzero(spread[:3]) == 0, 'the collar must not flash'
    assert np.unique(low.reshape(COUNT,-1),axis=0).shape[0] >= 29
    # A travelling wave rather than a global opacity or color flash.
    delta = np.abs(low[...,:3].astype(int)-low[0,...,:3]).max(axis=-1)
    y = np.arange(16)
    centroid = [np.sum((d.sum(1))*y)/d.sum() for d in (delta[8],delta[23])]
    assert centroid[1]-centroid[0] >= 3., centroid
    print(f'Icono: {count}/256 px de silueta intacta a 1×; '
          f'{np.count_nonzero(previous >= 14)} → {np.count_nonzero(spread >= 14)} px de luz animada, '
          'núcleo rosa y rebote dentro de la tela.',flush=True)


if __name__ == '__main__':
    write()
    verify()
