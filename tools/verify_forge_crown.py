#!/usr/bin/env python3
"""Check the rear crown against the solid vanilla head and the actual pixels."""
import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_contact import lap
from cape_fit import profile, rear_tuck
from verify_forge_combined import SLOTS
from verify_forge_gaits import crop, table, text
from verify_forge_postures import read_boxes
from verify_forge_walk import read

EDGES = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))


def shorten(poly, axis, limit, sign):
    out = []
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        da,db = sign*(a[axis]-limit), sign*(b[axis]-limit)
        if da >= 0:
            out.append(a)
        if (da < 0) != (db < 0):
            out.append((da*b-db*a)/(da-db))
    return np.asarray(out).reshape(-1,2)


def roof_section(box):
    # Coordinates relative to a unit head cube. Raw ModelPart Y points
    # down: the top of the base skin (not of the transparent hat) is Y=0.
    hits = [(box[i,[0,2]]*box[j,1]-box[j,[0,2]]*box[i,1])/(box[j,1]-box[i,1])
            for i,j in EDGES if (box[i,1] < 0) != (box[j,1] < 0)]
    if len(hits) < 3:
        return 0.
    poly = np.asarray(hits)
    dx,dz = (poly-poly.mean(0)).T
    poly = poly[np.argsort(np.arctan2(dz,dx))]
    for axis in range(2):
        poly = shorten(shorten(poly,axis,0,1),axis,1,-1)
    x,z = poly.T
    return 32*abs(x @ np.roll(z,-1)-z @ np.roll(x,-1))  # 64u² face, shoelace / 2


def is_rear(name):
    return name.startswith('v17_cowl_back_')


def head_roof(groups):
    head, = groups['head']
    basis = head[[1,3,4]]-head[0]
    np.testing.assert_allclose(np.linalg.norm(basis,axis=1),[8]*3,atol=.004,rtol=0)
    inv = np.linalg.inv(basis)
    rear = {n:(np.asarray(b)-head[0]) @ inv for n,b in groups.items() if is_rear(n)}
    assert len(rear) == 5
    rise = max(-8*float(b[:,:,1].min()) for b in rear.values())
    area = {n:sum(roof_section(c) for c in boxes) for n,boxes in rear.items()}
    return rise,area


def sewn(groups):
    band = np.concatenate([g for n,g in groups.items() if is_rear(n)])
    lining = np.concatenate([g for n,g in groups.items() if n.startswith(('v17_cowl_front_', 'v17_cowl_tooth_'))
                             or n == 'v17_cowl_return'])
    half = band[:,:,0].mean(1) < 0
    return min(lap(band[half],lining),lap(band[~half],lining))


def hair_pixels(path, quad):
    with Image.open(path) as photo:
        rgb = np.asarray(photo.convert('RGB'),dtype=np.int16)
        points = np.asarray(quad)*photo.size
        # Ignore the one-pixel edge of the hat/sky. The decal in the control
        # is in the interior of this polygon, not an overlapping silhouette.
        center = points.mean(0)
        inner = Image.new('L',photo.size)
        ImageDraw.Draw(inner).polygon([tuple(p) for p in center + .93*(points-center)],fill=255)
    rgb = rgb[np.asarray(inner) > 0]
    r,g,b = rgb.T
    hair = (r >= 115) & (r-g >= 27) & (g-b >= 22)
    maroon = (r-g >= 17) & (b-g >= 8) & (g < 122)
    return len(rgb),int(hair.sum()),int(maroon.sum())


def report(root, baseline):
    out, pictures = [], []
    old_dir = baseline/'diagnostico-cuello'
    with (root/'maniobra-forge.tsv').open() as f:
        combined = {r['ranura']:r for r in csv.DictReader(f,delimiter='\t')}
    for slot in SLOTS:
        stem = f'maniobra-{slot}'
        trace = read(root/f'{stem}.tsv')
        mesh = read_boxes(root/f'{stem}-cubos.tsv')
        old = read_boxes(old_dir/f'{slot}-cubos.tsv')
        quads = {}
        for line in (root/f'{stem}-cabeza.tsv').read_text().splitlines():
            tick,label,*xy = line.split('\t')
            xy = np.asarray(xy,float).reshape(4,2)
            assert label == 'top' and (0 < xy).all() and (xy < 1).all(), (slot,tick,xy)
            quads[int(tick)] = xy
        assert len(quads) == 5 and combined[slot]['fuera_de_umbral'] == 'OK'
        assert float(combined[slot]['punta_pico_u_tick']) < 3.75, (slot,'se perdió el freno .29',combined[slot])
        fit = trace[trace['fit'] == 1]
        ticks = fit['time'].astype(int)
        lean = profile()['bodyAngle']
        expected = [rear_tuck(-p,y,lean) if c else 0 for c,p,y in zip(fit['crouching'],fit['pitch'],fit['yaw'])]
        np.testing.assert_allclose(fit['rear_tuck'],expected,atol=.004,rtol=0,err_msg=slot)
        held = [(t,mesh[t]) for t in ticks if 58 <= t <= 77]
        assert len(held) >= 17, (slot,'faltan poses del giro sostenido',ticks)
        for t,boxes in held:
            rise,area = head_roof(boxes)
            assert rise < -.04 and sum(area.values()) < .05 and sewn(boxes) > .14, (slot,t,rise,area,sewn(boxes))
        stills = fit[fit['image'] != '-'][2:4]
        for at,expected_at in zip(stills,(63,77),strict=True):
            tick = int(at['time'])
            control = old[expected_at]
            groups = mesh[tick]
            a0, parts0 = head_roof(control)
            a1, parts1 = head_roof(groups)
            assert sum(parts0.values()) > 2.5 and parts0['v17_cowl_back_1'] > 1.5, (slot,expected_at,parts0)
            assert a1 <= -.04 and sum(parts1.values()) <= .05, (slot,tick,a1,parts1)
            for name in ('v18_pad_0','v18_pad_1','v20_mount_seat','v17_cowl_return'):
                np.testing.assert_allclose(groups[name],control[name],atol=.005,rtol=0,err_msg=f'{slot}/{tick}: {name}')
            path = root/str(at['image'])
            count,hair,maroon = hair_pixels(path,quads[tick])
            seam = sewn(groups)
            print(f'{slot}: t={tick}, corona {a0:+.3f} → {a1:+.3f}u respecto al techo de la cabeza, '
                  f'corte {sum(parts0.values()):.3f} → {sum(parts1.values()):.3f}u², '
                  f'pelo {hair}/{count}px, granate {maroon}px, unión del borde {seam:.3f}u.',flush=True)
            assert count > 600 and hair >= .89*count and maroon <= max(4,.004*count), (slot,tick,count,hair,maroon)
            out.append((slot,expected_at,tick,*(f'{n:.6f}' for n in (a0,a1,sum(parts0.values()),sum(parts1.values()),seam)),
                        count,hair,maroon))
            pictures.append((old_dir/f'{slot}-{expected_at}-detalle.png',path))
    table(root/'maniobra-corona.tsv','ranura tick_base tick altura_base_u altura_u corte_base_u2 corte_u2 '
          'union_corona_u techo_px pelo_px granate_px',out)
    gallery(root,pictures)


def gallery(root, pictures):
    w,h=303,210
    sheet=Image.new('RGB',(4*(w+7)+18,120+2*(h+35)),'#17121d')
    pen=ImageDraw.Draw(sheet)
    text(pen,(13,8),'Borde posterior de la capucha · Alex en Forge',27,bold=True)
    text(pen,(13,47),'Giro sostenido y frenada agachada · recortes de las tomas reales',17,'#dbc1dc')
    for col,title in enumerate(('Paso · v1.67.29','Paso · v1.67.30','Freno · v1.67.29','Freno · v1.67.30')):
        text(pen,(13+col*(w+7),77),title,15,'#e4c3df')
    for row,slot in enumerate(SLOTS):
        y=120+row*(h+35)
        text(pen,(13,y-19),slot.upper(),14,bold=True)
        for j,(old,new) in enumerate(pictures[row*2:row*2+2]):
            with Image.open(old) as image:
                sheet.paste(image.resize((w,h),Image.Resampling.LANCZOS),(13+2*j*(w+7),y))
            sheet.paste(crop(new,w,h,.10,.55),(13+(2*j+1)*(w+7),y))
    sheet.save(root/'maniobra-corona.jpg',quality=95,optimize=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    parser.add_argument('--reference',type=Path,required=True)
    args=parser.parse_args()
    report(args.shots,args.reference)
