#!/usr/bin/env python3
"""Detect visible trim setback in registered F5 screenshots.

The control wears the same item, with the complete v1.67.8 geometry and
lining. Unlike a shirt coverage test, look for the outer trim to actually
vacate the far side of each upper band and move toward the wearer.
"""
import argparse
from pathlib import Path

import numpy as np


SLOTS = ('pecho','curios')
# Bands on the wide plate, center of the collar, and compact plate. Units
# are widths of the slim model's bare shirt, even in the classic run.
# This keeps the bands on the same plates regardless of sleeve width.
BANDS = ((-.67,-.54),(-.18,.18),(.40,.465))


def shirt_mask(bare):
    r,g,b = bare.transpose(2,0,1)
    return (g-r >= 19) & (b-r >= 19)


def score(bare, previous, fitted, width):
    assert bare.shape == previous.shape == fitted.shape
    shirt = shirt_mask(bare)
    _,xx = np.where(shirt)
    assert len(xx) > 600, 'no se ve la camiseta del control F5'
    left,right = xx.min(),xx.max()+1
    center = (left+right)/2
    # The bare sleeves provide an independent fixed reference in screen
    # space. The depth of the model or a simulated camera isn't the score.
    rear = np.median([np.flatnonzero(shirt[:,x])[-1]
                      for x in range(round(left+.12*width),round(right-.12*width))])
    rows = np.arange(round(rear-.10*width),round(rear+.42*width))

    def trim(im):
        r,g,b = im.transpose(2,0,1)
        return (np.abs(im-bare).max(2) >= 18) & (g <= 70) & (r >= 36) & (r-g >= 20) & (b-g >= 5) & (r >= .9*b) & (b < 100)

    old,new = map(trim,(previous,fitted))
    reports = []
    for a,b in BANDS:
        cols = np.arange(round(center+a*width),round(center+b*width))
        base, candidate = (m[np.ix_(rows,cols)] for m in (old,new))
        a,b = (rows[np.where(m)[0]] for m in (base,candidate))
        assert min(len(a),len(b)) > 35, ('no se ve la pieza exterior', len(a),len(b))
        front,rearward = np.quantile(a,[.13,.75]) - np.quantile(b,[.13,.75])
        far = rows >= np.quantile(a,.75)
        linger = candidate[far].sum()/base[far].sum()
        reports.append((float(front/width),float(rearward/width),float(linger),len(b)/len(a)))
    # Check the slivers of blue concrete immediately behind each shoulder
    # return, inside the sleeve edges. Exclude the open sides and free hem.
    def floor(im):
        r,g,b = im.transpose(2,0,1)
        return (b-r >= 37) & (b-g >= 37) & (np.abs(r-g) <= 10)

    def joint(im):
        r,g,b = im.transpose(2,0,1)
        blue = floor(im)
        return blue,~blue & (np.abs(im-bare).max(2) >= 18) & (g <= 85) & (np.maximum(r,b)-g >= 7)

    layers = tuple(map(joint,(previous,fitted)))
    gaps = []
    span = round(.12*width)
    for lo,hi in ((-.375,-.155),(.155,.375)):
        strips = [(x,np.flatnonzero(shirt[:,x])[-1])
                  for x in range(round(center+lo*width),round(center+hi*width)) if shirt[:,x].any()]
        assert len(strips) >= .19*width, 'faltan mangas en F5'
        counts = [0,0]
        for x,last in strips:
            start,end = last-round(.025*width),last+1+span
            for i,(blue,material) in enumerate(layers):
                first = np.flatnonzero(material[start:end,x])
                # Don't count the floor *aft* of the plates when they advance.
                # A return overlapping the sleeve already closes this column.
                stop = min(end,start+first[0]+round(.016*width)) if len(first) else end
                counts[i] += int(blue[last+1:stop,x].sum())
        gaps.append(tuple(n/(len(strips)*span) for n in counts))
    return reports,gaps


def passes(reports):
    # This is a contraction about the seam, not a uniform translation. On
    # the small plate the visible front can stay pinned to the sleeve and
    # redistribute texels; the trailing edge must still visibly move in.
    return all(front >= -.040 and rear >= .043 and far <= .72 and .39 <= area <= 1.10
               for front,rear,far,area in reports)


def check(root: Path):
    from verify_forge_mount import read

    slim_bare = read(root/'ajuste-fino-sin-manto.png')
    _,cols = np.where(shirt_mask(slim_bare))
    assert cols.size, 'no se ve la camiseta de mangas finas'
    width = cols.max()+1-cols.min()
    failures = []
    for prefix,label in (('ajuste','clásico'),('ajuste-fino','fino')):
        bare = read(root/f'{prefix}-sin-manto.png')
        previous = read(root/f'{prefix}-v1678.png')
        anchor = np.loadtxt(root/f'{prefix}-v1678.tsv')
        assert anchor.shape == (3,4) and np.isfinite(anchor).all(), 'faltan las referencias de la cámara F5'
        control,_ = score(bare,previous,previous,width)
        assert not passes(control), 'la montura de v1.67.8 debe reprobar el ceñido'
        for slot in SLOTS:
            name = f'{prefix}-{slot}'
            actual = np.loadtxt(root/f'{name}.tsv')
            assert actual.shape == anchor.shape, (name,'faltan referencias de la cámara F5')
            delta = float(np.max(np.abs(actual-anchor)))
            assert delta < .55, (name,'la cámara se movió en píxeles',delta)
            report,gaps = score(bare,previous,read(root/f'{name}.png'),width)
            print(f'F5 76°, {label}, {slot}: hacia el torso {report[1][1]*width:.1f}px en cuello '
                  f'y {report[0][1]*width:.1f}/{report[2][1]*width:.1f}px en hombreras '
                  f'(cuartil trasero); suelo entre mangas y unión: '
                  + ' / '.join(f'{old:.1%} → {new:.1%}' for old,new in gaps) + '.',flush=True)
            if not passes(report):
                failures.append((name,'no se acercó el borde exterior completo',np.round(report,3).tolist()))
            if any(new > .025 for _,new in gaps):
                failures.append((name,'suelo visible junto al remate',gaps))
    assert not failures, failures


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots',type=Path)
    try:
        check(cli.parse_args().shots)
    except AssertionError as exc:
        message = str(exc).replace('%','%25').replace('\n','%0A')
        print(f'::error title=Ajuste visible en Forge::{message}',flush=True)
        raise SystemExit(1) from exc
