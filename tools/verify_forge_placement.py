#!/usr/bin/env python3
"""Measure the original cloak in the live Forge wearer frame and in F5."""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from verify_forge_mount import emit, read

FIXTURES = tuple(f'posicion-{skin}-{slot}' for skin in ('steve','alex') for slot in ('pecho','curios'))
VIEWS = (('espalda','ESPALDA'),('frente','FRENTE'),('arriba','DESDE ARRIBA'),
         ('izquierda','PERFIL MIRANDO ARRIBA'),('abajo','DESDE ABAJO'),('salto','SALTO'))


def plate_masks(root, name, size):
    masks = [Image.new('L',size) for _ in range(2)]
    drawing = list(map(ImageDraw.Draw,masks))
    for line in (root/f'{name}-caras.tsv').read_text().splitlines():
        bone,*xy = line.split()
        if bone not in ('v18_pad_0','v18_pad_1'):
            continue
        quad = np.asarray(xy,float).reshape(4,2)*size
        assert np.isfinite(quad).all(), name
        drawing[int(bone[-1])].polygon(list(map(tuple,quad)),fill=255)
    return np.asarray([np.asarray(m)>0 for m in masks])


def report(root):
    for fixture in FIXTURES:
        rows = np.genfromtxt(root/f'{fixture}-recorrido.tsv', names=True, delimiter='\t')
        assert len(rows)>=60 and np.isfinite(rows['root_z']).all(), fixture
        assert rows['pitch'].min()<=-89 and rows['pitch'].max()>=89, fixture
        assert rows['yaw'].min()<=-68 and rows['yaw'].max()>=68, fixture
        assert rows['lift'].max()>.65 and abs(rows['lift'][-1])<.01, fixture
        aimed_up = rows[rows['pitch']<=0]
        drift = aimed_up['seat_drift'].max()
        assert drift < .006, (fixture,drift,'seat followed the head or jump')
        # Bone-local measurements before projection: the pinned seat alone
        # isn't enough if the visible ribbons still slide far to the rear.
        straight_up = aimed_up[(aimed_up['pitch']<-65)&(abs(aimed_up['yaw'])<.01)]
        ribbon, collar = straight_up['root_z'].max(), straight_up['collar_z'].max()
        assert ribbon < 7.0 and collar < 9.0, (fixture,ribbon,collar,'cloth lifted off the torso')
        visible = []
        for view in ('espalda','frente','arriba'):
            name = f'{fixture}-{view}'
            worn = read(root/f'{name}.png')
            hidden = read(root/f'{name}-sin-placas.png')
            masks = plate_masks(root,name,(worn.shape[1],worn.shape[0]))
            diff = np.abs(worn-hidden).max(2)>=15
            counts = np.count_nonzero(masks&diff,axis=(1,2))
            assert min(counts)>=50, (name,counts,'original plate missing in F5')
            visible.append(f'{view} {counts[0]}/{counts[1]}')
        print(f'::notice title=Colocación original en Forge::{fixture}: {len(rows)} poses; asiento {drift:.6f}u; '
              f'Z máxima mirando arriba, raíz {ribbon:.3f}u y cuello {collar:.3f}u; salto {rows["lift"].max():.2f} bloques; '
              f'píxeles de ambas placas {"; ".join(visible)}.')


def gallery(root):
    cw,ch = 218,220
    image = Image.new('RGB',(cw*len(VIEWS),44+(ch+21)*len(FIXTURES)),'#15101a')
    pen = ImageDraw.Draw(image)
    pen.text((10,9),'MANTLE OF THE BLIGHT STAR  /  MODELO ORIGINAL EQUIPADO EN FORGE',fill='#ffe4f0')
    for col,(_,label) in enumerate(VIEWS):
        pen.text((col*cw+10,28),label,fill='#efc5da')
    for row,fixture in enumerate(FIXTURES):
        y = 44+row*(ch+21)
        pen.text((10,y+2),fixture.removeprefix('posicion-').replace('-',' / ').upper(),fill='#ffe4f0')
        for col,(view,_) in enumerate(VIEWS):
            with Image.open(root/f'{fixture}-{view}.png') as raw:
                im = raw.convert('RGB')
            w,h = im.size
            # Camera is centered on the torso, not the former mount. Keep
            # the feet, complete free cloth and hat in the F5 view.
            d = min(w,round(h*cw/ch))
            im = im.crop(((w-d)//2,0,(w+d)//2,h))
            image.paste(im.resize((cw-4,ch),Image.Resampling.LANCZOS),(col*cw+2,y+17))
    image.save(root/'colocacion-original-forge.jpg',quality=91,optimize=True)
    for width in (980,840,700,560,420):
        data = io.BytesIO()
        image.resize((width,round(width*image.height/image.width)),Image.Resampling.LANCZOS).save(
            data,'JPEG',quality=68,optimize=True)
        if len(data.getvalue()) <= 12_600:
            emit('Colocación original galeria jpg',data.getvalue())
            break


if __name__=='__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('--gallery-only', action='store_true')
    args = ap.parse_args()
    (gallery if args.gallery_only else report)(args.shots)
