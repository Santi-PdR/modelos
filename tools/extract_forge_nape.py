#!/usr/bin/env python3
"""Keep the lossless crop, camera registration and nearby mesh of the Forge control."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from verify_forge_combined import SLOTS, timeline
from verify_forge_gaits import table
from verify_forge_postures import ACTOR
from verify_forge_walk import read


def extract(root, out, prefix='maniobra', stills_only=False):
    out.mkdir(parents=True, exist_ok=True)
    photos = []
    for slot in SLOTS:
        stem = f'{prefix}-{slot}'
        trace = read(root/f'{stem}.tsv')
        timeline(trace, slot)
        stills = trace[trace['image'] != '-'][2:4]
        wanted = {int(s['time']) for s in stills}
        screen = {}
        for line in (root/f'{stem}-cabeza.tsv').read_text().splitlines():
            tick, plane, *uv = line.split('\t')
            assert plane == 'top' and len(uv) == 8, line
            screen[int(tick)] = uv
        for shot, target in zip(stills, (63,77), strict=True):
            tick = int(shot['time'])
            assert target <= tick <= target+2 and shot['fit'] == shot['crouching'] == 1, (slot,shot)
            with Image.open(root/str(shot['image'])) as im:
                w,h = im.size
                # A lossless crop only; its offset is kept in full viewport pixels.
                x0,y0 = w//2 - round(.26*h), round(.105*h)
                x1,y1 = w//2 + round(.26*h), round(.56*h)
                name = f'{slot}-{tick}-nuca.png'
                im.crop((x0,y0,x1,y1)).save(out/name,optimize=True)
            photos.append((slot,tick,name,w,h,x0,y0,*screen[tick]))
        if not stills_only:
            wanted |= set(range(58,84)) & set(trace[trace['fit']==1]['time'].astype(int))
        rows = []
        for line in (root/f'{stem}-cubos.tsv').read_text().splitlines():
            tick, bone, coords = line.split('\t',2)
            if int(tick) not in wanted:
                continue
            box = np.fromstring(coords,sep='\t').reshape(8,3)
            if bone in ACTOR or box[:,1].max() > 17.5:
                rows.append(line)
        assert {int(line.split('\t',1)[0]) for line in rows} == wanted, slot
        (out/f'{slot}-cubos.tsv').write_text('\n'.join(rows)+'\n')
    table(out/'capturas.tsv','ranura tick imagen ancho alto x0 y0 ax ay bx by cx cy dx dy',photos)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--prefix',default='maniobra')
    parser.add_argument('--stills-only',action='store_true')
    args = parser.parse_args()
    extract(args.shots,args.out,args.prefix,args.stills_only)
