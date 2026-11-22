#!/usr/bin/env python3
"""Bake the two spark transitions from the three unchanged 16×16 key sprites."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'src/main/resources/assets/capatest'
JAVA = ROOT / 'src/main/java/com/capatest/client/CapeEmber.java'
MANIFEST = 'particles/capa_spark.json'
SPRITES = 'textures/particle/'
KEYS = tuple(f'capa_spark_{i}' for i in range(3))


def profile():
    java = JAVA.read_text()
    def number(key):
        return float(re.search(r'\b'+key+r'\s*=\s*([.\d]+)', java)[1])
    return dict(steps=int(number('SPRITE_STEPS')), halfTicks=number('SPRITE_HALF_TICKS'),
                changes=[number('FIRST_CHANGE'),number('SECOND_CHANGE')])


def frames():
    """Ordered atlas keys, with pair and fraction for each generated frame."""
    steps = profile()['steps']
    for pair in (0,1):
        yield KEYS[pair], pair, 0
        for tick in range(1,steps):
            yield f'capa_spark_mix_{pair}{pair+1}_{tick:02d}', pair, tick
    yield KEYS[-1], 1, steps


def names():
    return [name for name,_,_ in frames()]


def extras():
    return {SPRITES+name+'.png' for name in names() if name not in KEYS}


def manifest():
    return {'textures': ['capatest:'+name for name in names()]}


def mix(a, b, step, steps):
    # Premultiply before mixing the edge; straight RGB interpolation would
    # bleed the hidden RGB of transparent pixels into visible ones.
    la, lb = (steps-step)*a[3], step*b[3]
    opacity = la+lb
    if opacity == 0:
        return (0,0,0,0)
    def rounded(numerator, denominator):
        return (2*numerator+denominator)//(2*denominator)
    return tuple(rounded(la*a[i]+lb*b[i], opacity) for i in range(3)) + (rounded(opacity, steps),)


def bake(assets=ASSETS, *, check=False):
    from PIL import Image
    directory = assets/SPRITES
    keys = []
    for name in KEYS:
        with Image.open(directory/(name+'.png')) as im:
            assert im.mode == 'RGBA' and im.size == (16,16), name
            keys.append(list(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata()))
    steps = profile()['steps']
    for name, pair, tick in frames():
        if tick in (0,steps):
            continue  # never rewrite the original PNGs
        pixels = [mix(a,b,tick,steps) for a,b in zip(keys[pair],keys[pair+1],strict=True)]
        out = directory/(name+'.png')
        if check:
            with Image.open(out) as im:
                found = list(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata())
                assert im.size == (16,16) and im.mode == 'RGBA' and found == pixels, out
        else:
            im = Image.new('RGBA',(16,16))
            im.putdata(pixels)
            im.save(out)
    desc = assets/MANIFEST
    if check:
        assert json.loads(desc.read_text()) == manifest(), desc
        actual = {p.relative_to(assets).as_posix() for p in directory.glob('capa_spark_mix_*.png')}
        assert actual == extras(), actual ^ extras()
    else:
        desc.write_text(json.dumps(manifest(),indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    bake(check=parser.parse_args().check)
    print(f'{len(names())} cuadros de brasa: {len(KEYS)} originales + {len(extras())} intermedios premultiplicados.')
