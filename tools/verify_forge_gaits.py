#!/usr/bin/env python3
"""Compare the .27 left shoulder and cloth gaits with the delivered .26 in Forge."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cape_contact import lap
from verify_forge_mount import read as pixels
from verify_forge_placement import FIXTURES, masks_for, read_contacts
from verify_forge_postures import PHASES, read_boxes
from verify_forge_walk import read

SLOTS = ('pecho', 'curios')
WIDE, SMALL = 'v18_pad_1', 'v18_pad_0'


def table(path, fields, rows):
    with path.open('w', newline='') as file:
        out = csv.writer(file, delimiter='\t', lineterminator='\n')
        out.writerow(fields.split())
        out.writerows(rows)


def shoulder(root, fixture):
    parts = {n:np.asarray(boxes) for n,boxes in read_contacts(root,fixture).items()}
    pad = parts[WIDE]
    center = parts['body'][:,:,0].mean()
    side = np.sign(pad[:,:,0].mean() - center)
    assert side == -1, (fixture, 'expected the wide plate on wearer left')
    sleeve, = [parts[s] for s in ('left_sleeve','right_sleeve') if side*(parts[s][:,:,0].mean()-center) > 0]
    lip = np.max(side * pad[:,:,0]) - np.max(side * sleeve[:,:,0])
    cloth = parts['v20_mount_shoulders']
    cloth = cloth[side*(cloth[:,:,0].mean(1)-center)>0]
    view = f'{fixture}-frente'
    worn, bare = (pixels(root/f'{view}{suffix}.png') for suffix in ('', '-sin-placas'))
    projected, = masks_for(root,view,(worn.shape[1],worn.shape[0]),(WIDE,))
    _, x = np.nonzero(projected & (np.abs(worn-bare).max(2)>=18))
    assert len(x) >= 100 and np.median(x) > worn.shape[1]/2, (fixture,'expected front F5 screen-right plate')
    return np.array([lip, np.quantile(x,.99), lap(pad,sleeve), lap(pad,cloth)]), parts[SMALL]


def check_shoulders(root, reference):
    rows = []
    for fixture in FIXTURES:
        old, small_old = shoulder(reference,fixture)
        new, small_new = shoulder(root,fixture)
        print(f'::notice title=Hombrera izquierda en Forge::{fixture}: vuelo {old[0]:.3f} → {new[0]:.3f}u; '
              f'canto frontal x99 {old[1]:.1f} → {new[1]:.1f}px; apoyo en manga {old[2]:.3f} → {new[2]:.3f}u; '
              f'unión con tela {old[3]:.3f} → {new[3]:.3f}u.',flush=True)
        np.testing.assert_allclose(small_new,small_old,atol=.008,rtol=0,err_msg=f'{fixture}: cambió la otra hombrera')
        assert .30 <= old[0]-new[0] <= .90, (fixture,'inset fuera de rango',old,new)
        assert old[1]-new[1] >= 1, (fixture,'el canto no se retrajo de frente',old,new)
        assert (new[2:] >= .80 * old[2:]).all(), (fixture,'perdió apoyo en manga o tela',old,new)
        rows.append((fixture,*(f'{v:.4f}' for v in np.c_[old,new].ravel())))
    table(root/'hombrera-forge.tsv', 'montaje vuelo_base_u vuelo_u x99_base_px x99_px '
          'manga_base_u manga_u tela_base_u tela_u', rows)


def head_clearance(root, slot):
    poses = read_boxes(root/f'revision-alex-{slot}-cubos.tsv')
    assert sorted(poses) == list(range(sum(phase[1] for phase in PHASES))), slot
    hits = {}
    start = 0
    for label,count,*_ in PHASES:
        hits[label] = np.maximum(0.,np.array([[lap(np.asarray(poses[i][WIDE]),np.asarray(poses[i][n]))
                                              for n in ('head','hat')] for i in range(start,start+count)]).max(0))
        start += count
    return hits


def check_look(root, reference):
    rows = []
    for slot in SLOTS:
        old, new = (head_clearance(path,slot) for path in (reference,root))
        for pose in old:
            a,b = old[pose],new[pose]
            # Closed collision boxes, not visible pixels (the skin overlay can
            # be transparent). Keep the existing margin in the audited poses.
            assert (b <= np.maximum([.05,.05],a+[.16,.18])).all(), (slot,pose,'nuevo cruce con la placa',a,b)
            rows.append((slot,pose,*(f'{v:.4f}' for v in np.c_[a,b].ravel())))
        print(f'::notice title=Giro de cabeza en Forge::Alex {slot}: reposo, mirada alta, cenital, giro, agachado y carrera '
              f'comparados con .26; máximo existente placa/cabeza {max(v[0] for v in old.values()):.3f} → '
              f'{max(v[0] for v in new.values()):.3f}u.',flush=True)
    table(root/'hombrera-mirada-forge.tsv','ranura postura cabeza_base_u cabeza_u capa_pelo_base_u capa_pelo_u',rows)


def gait(path, walking):
    data = read(path)
    lo,hi,mode = (35,70,'walk') if walking else (107,129,'run')
    d = data[(data['time'] >= lo) & (data['time'] < hi) & (data[mode] >= .98)]
    assert len(d) >= 35 and np.ptp(d['stride']) > 1.6, (path,mode,'faltan zancadas completas')
    phase = (d['stride'] % 1.) * 2 * np.pi
    # Fit to actual vanilla stride, not screenshot tick or game FPS. The
    # differential cancels common additive cloth inertia on the two tips.
    basis = np.c_[np.ones(len(d)), (d['time']-lo)/(hi-lo), np.cos(phase), np.sin(phase),
                  np.cos(2*phase), np.sin(2*phase)]
    delta = d['edge2'] - d['edge9']
    average = (d['edge2'] + d['edge9']) / 2
    y = np.c_[delta, average]
    assert np.isfinite(y).all(), path
    c, _, rank, _ = np.linalg.lstsq(basis,y,rcond=None)
    assert rank == basis.shape[1], path
    return np.array([np.linalg.norm(c[2:4,0]), np.linalg.norm(c[2:4,1]), np.linalg.norm(c[4:6,1])])


def check_gaits(root, reference):
    rows = []
    for slot in SLOTS:
        for walking in (True,False):
            name = 'caminar' if walking else 'correr'
            a,b = (gait(path/f'paso-{slot}.tsv',walking) for path in (reference,root))
            print(f'::notice title=Ritmo del paño en Forge::{slot}/{name}: alternancia entre lados {a[0]:.2f} → {b[0]:.2f}°; '
                  f'onda común una vez por zancada {a[1]:.2f} → {b[1]:.2f}°; '
                  f'rebote común dos veces {a[2]:.2f} → {b[2]:.2f}°.',flush=True)
            if walking:
                assert b[0] >= 1.45*a[0] and b[0] >= 2.8 and b[2] >= .85, (slot,name,a,b)
            else:
                assert b[1] <= .55*a[1] and b[2] >= .9 and b[2] >= 2*b[1], (slot,name,a,b)
            rows.append((slot,name,*(f'{v:.4f}' for v in np.c_[a,b].ravel())))
    table(root/'ritmo-forge.tsv', 'ranura marcha alternancia_base_deg alternancia_deg '
          'onda_base_deg onda_deg rebote_base_deg rebote_deg', rows)


def text(pen, xy, value, size=16, tone='#f2e6f2', bold=False):
    face = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    pen.text(xy,value,fill=tone,font=ImageFont.truetype(face,size))


def crop(path, width, height, top, bottom):
    with Image.open(path) as im:
        h = min(im.height,round(im.height*bottom)) - round(im.height*top)
        w = round(h*width/height)
        assert w <= im.width, (path,im.size)
        x = (im.width-w)//2
        y = round(im.height*top)
        return im.crop((x,y,x+w,y+h)).convert('RGB').resize((width,height),Image.Resampling.LANCZOS)


def shoulders_gallery(root, reference):
    w,h = 276,205
    canvas = Image.new('RGB',(4*(w+8)+16,128+2*(h+43)), '#17121d')
    pen = ImageDraw.Draw(canvas)
    text(pen,(24,18),'Hombrera izquierda · antes y después',30,bold=True)
    text(pen,(24,59),'Alex en Forge F5 · la pieza señalada queda a la derecha de la imagen frontal',18,'#d3bfd6')
    for j,slot in enumerate(SLOTS):
        y = 123+j*(h+43)
        text(pen,(17,y-22),slot.upper(),14,'#e3bddc',True)
        for i,(view,label) in enumerate((('frente','Frente'),('izquierda','Perfil izquierdo'))):
            for k,(version,path) in enumerate((('1.67.26',reference),('1.67.27',root))):
                x = 12+(i*2+k)*(w+8)
                if j == 0:
                    text(pen,(x+2,86),f'{label}  ·  v{version}',15,'#e7b9d6' if k == 0 else '#a9dfd7')
                photo = path/f'posicion-alex-{slot}-{view}.png'
                canvas.paste(crop(photo,w,h,.035,.585),(x,y))
    canvas.save(root/'comparacion-hombrera-forge.jpg',quality=94,optimize=True)


def gait_gallery(root, reference, slot):
    w,h = 226,250
    ranges = (range(40,64,2),range(106,130,2))
    motion = [[],[]]
    backdrop = Image.new('RGB',(2*w+28,2*(h+31)+92),'#17121d')
    pen = ImageDraw.Draw(backdrop)
    text(pen,(12,11),'Paso y carrera · Forge F5',24,bold=True)
    text(pen,(12,43),f'Alex / {slot.upper()}  ·  dos recorridos, cámara a tres cuartos',14,'#d3bfd6')
    for k, version in enumerate(('v1.67.26','v1.67.27')):
        text(pen,(12+k*(w+4),67),version,16,'#e7b9d6' if k == 0 else '#a9dfd7',True)
    for i, (ticks, label) in enumerate(zip(ranges,('CAMINAR','CORRER'),strict=True)):
        text(pen,(12,92+i*(h+31)),label,13,'#f2e6f2',True)
        for tick in ticks:
            photos = [p/f'paso-{slot}-ciclo-{tick:03d}.png' for p in (reference,root)]
            if all(p.is_file() for p in photos):
                motion[i].append((tick,[crop(p,w,h,0.,1.) for p in photos]))
        assert len(motion[i]) >= 10, (slot,label,'faltan fotogramas reales')
    # Use captured frames at matching route ticks. Any dropped frame stays
    # dropped; the animation neither interpolates it nor freezes one take.
    # Also align walk and run offsets in their independent timelines.
    walking = dict((tick-40,photos) for tick,photos in motion[0])
    running = dict((tick-106,photos) for tick,photos in motion[1])
    offsets = sorted(walking.keys() & running.keys())
    assert len(offsets) >= 9, (slot,'faltan pares de tomas')
    frames = []
    for tick in offsets:
        frame = backdrop.copy()
        for i, pair in enumerate((walking[tick],running[tick])):
            for k, photo in enumerate(pair):
                frame.paste(photo,(12+k*(w+4),113+i*(h+31)))
        frames.append(frame)
    dt = [50*(b-a) for a,b in zip(offsets,offsets[1:]+[24],strict=True)]
    frames[0].save(root/f'comparacion-marcha-{slot}-forge.gif',save_all=True,
                   append_images=frames[1:],duration=dt,loop=0,optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots', type=Path)
    parser.add_argument('reference', type=Path)
    args = parser.parse_args()
    check_shoulders(args.shots,args.reference)
    check_look(args.shots,args.reference)
    check_gaits(args.shots,args.reference)
    shoulders_gallery(args.shots,args.reference)
    for slot in SLOTS:
        gait_gallery(args.shots,args.reference,slot)


if __name__ == '__main__':
    main()
