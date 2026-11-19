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
# are widths of the bare player's shirt; no framebuffer size assumption.
BANDS = ((-.67,-.54),(-.18,.18),(.40,.465))


def shirt_mask(bare):
    r,g,b = bare.transpose(2,0,1)
    return (g-r >= 19) & (b-r >= 19)


def score(bare, previous, fitted, reference_width=None):
    assert bare.shape == previous.shape == fitted.shape
    shirt = shirt_mask(bare)
    _,xx = np.where(shirt)
    assert len(xx) > 600, 'no se ve la camiseta del control F5'
    left,right = xx.min(),xx.max()+1
    center = (left+right)/2
    width = reference_width or right-left
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
        front,mid,rearward = np.quantile(a,[.13,.5,.75]) - np.quantile(b,[.13,.5,.75])
        far = rows >= np.quantile(a,.75)
        linger = candidate[far].sum()/base[far].sum()
        reports.append((float(front/width),float(mid/width),float(rearward/width),float(linger),len(b)/len(a)))
    # Check the slivers of blue concrete immediately behind each shoulder
    # return, inside the sleeve edges. Exclude the open sides and free hem.
    def floor(im):
        r,g,b = im.transpose(2,0,1)
        return (b-r >= 37) & (b-g >= 37) & (np.abs(r-g) <= 10)

    old_blue,new_blue = map(floor,(previous,fitted))
    gaps = []
    for a,b in ((-.375,-.155),(.155,.375)):
        strips = [(x,np.flatnonzero(shirt[:,x])[-1])
                  for x in range(round(center+a*width),round(center+b*width)) if shirt[:,x].any()]
        assert len(strips) >= .19*width, 'faltan mangas en F5'
        windows = np.array([(y,x) for x,last in strips for y in range(last+1,last+1+round(.12*width))])
        y,x = windows.T
        gaps.append((old_blue[y,x].mean(),new_blue[y,x].mean()))
    return width,reports,gaps


def passes(reports):
    return all(front >= -.040 and middle >= need and rear >= .045 and far <= .72 and .47 <= area <= 1.10
               for (front,middle,rear,far,area),need in zip(reports,(.045,.035,.019),strict=True))


def check(root: Path):
    from verify_forge_mount import read

    reference = None
    for prefix,label in (('ajuste','clásico'),('ajuste-fino','fino')):
        bare = read(root/f'{prefix}-sin-manto.png')
        previous = read(root/f'{prefix}-v1678.png')
        anchor = np.loadtxt(root/f'{prefix}-v1678.tsv')
        assert anchor.shape == (3,4) and np.isfinite(anchor).all(), 'faltan las referencias de la cámara F5'
        reference,control,_ = score(bare,previous,previous,reference)
        assert not passes(control), 'la montura de v1.67.8 debe reprobar el ceñido'
        for slot in SLOTS:
            name = f'{prefix}-{slot}'
            actual = np.loadtxt(root/f'{name}.tsv')
            assert actual.shape == anchor.shape and np.max(np.abs(actual-anchor)) < .55, (name,'la cámara se movió')
            width,report,gaps = score(bare,previous,read(root/f'{name}.png'),reference)
            print(f'F5 76°, {label}, {slot}: hacia el torso {report[1][2]*width:.1f}px en cuello '
                  f'y {report[0][2]*width:.1f}/{report[2][2]*width:.1f}px en hombreras '
                  f'(cuartil trasero); suelo entre mangas y unión: '
                  + ' / '.join(f'{old:.1%} → {new:.1%}' for old,new in gaps) + '.',flush=True)
            assert passes(report), (name,'no se acercó el borde exterior completo',report)
            assert all(new <= max(.025,old+.012) for old,new in gaps), (name,'se abrió un hueco junto al remate',gaps)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots',type=Path)
    check(cli.parse_args().shots)
