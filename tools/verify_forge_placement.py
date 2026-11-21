#!/usr/bin/env python3
"""Measure the original cloak in the live Forge wearer frame and in F5."""
from __future__ import annotations

import argparse
from collections import defaultdict
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_contact import back_and_sleeves, original_dimensions
from preview_cloth import ARMOR_GEO, load, matrices
from verify_v1660 import WornModel
from verify_forge_mount import emit, read

FIXTURES = tuple(f'posicion-{skin}-{slot}' for skin in ('steve','alex') for slot in ('pecho','curios'))
VIEWS = (('espalda','ESPALDA'),('frente','FRENTE'),('diagonal','TRES CUARTOS'),
         ('izquierda','PERFIL'),('arriba','CENITAL'),('salto','SALTO'))


def masks_for(root, name, size, names):
    masks = {part:Image.new('L',size) for part in names}
    drawing = {part:ImageDraw.Draw(mask) for part,mask in masks.items()}
    for line in (root/f'{name}-caras.tsv').read_text().splitlines():
        bone,*xy = line.split()
        if bone in drawing:
            quad = np.asarray(xy,float).reshape(4,2)*size
            assert np.isfinite(quad).all(), name
            drawing[bone].polygon(list(map(tuple,quad)),fill=255)
    return np.asarray([np.asarray(masks[name])>0 for name in names])


def read_contacts(root, fixture):
    parts = defaultdict(list)
    for row in (root/f'{fixture}-encastre.tsv').read_text().splitlines():
        bone,*xyz = row.split()
        parts[bone].append(np.asarray(xyz,float).reshape(8,3))
    return parts


def report(root):
    geo = load(ARMOR_GEO)
    rig = WornModel(geo)
    original = defaultdict(list)
    for name, cube in zip(rig.names, rig.place(matrices(geo)), strict=True):
        original[name].append(cube)
    for fixture in FIXTURES:
        rows = np.genfromtxt(root/f'{fixture}-recorrido.tsv',names=True,delimiter='\t',dtype=None,encoding='utf-8')
        orbit, aim, jump = (rows[rows['mode']==m] for m in ('orbit','aim','jump'))
        assert len(orbit)==7 and np.ptp(orbit['camera_yaw'])>=180 and np.ptp(orbit['camera_pitch'])>=120, fixture
        assert np.abs(orbit['pitch']).max()<.02 and np.abs(orbit['yaw']).max()<.02, fixture
        assert len(aim)==49 and np.ptp(aim['camera_yaw'])==np.ptp(aim['camera_pitch'])==0, fixture
        assert aim['pitch'].min()<=-88.98 and aim['pitch'].max()>=88.98, fixture
        assert aim['yaw'].min()<=-68 and aim['yaw'].max()>=68, fixture
        assert jump['lift'].max()>.65 and abs(jump['lift'][-1])<.01, fixture
        drift = [v['drift'].max() for v in (orbit,aim,jump)]
        assert np.isfinite(drift).all() and max(drift)<.006, (fixture,drift,'cambió la montura en coordenadas del torso')
        parts = read_contacts(root,fixture)
        cubes = original_dimensions(parts, original, fixture)
        body, rays, seam, overlap = back_and_sleeves(parts, fixture)
        name = f'{fixture}-frente'
        worn, control = (read(root/f'{name}{suffix}.png') for suffix in ('','-sin-placas'))
        names = ('v18_pad_0','v18_pad_1','left_sleeve','right_sleeve')
        plates, sleeves = np.split(masks_for(root,name,(worn.shape[1],worn.shape[0]),names),2)
        assert np.min(sleeves.sum(axis=(1,2)))>=180, (name,'las mangas no entraron en cuadro')
        # A rigid pauldron may sit just *above* the sleeve in a front view
        # instead of covering a tall fraction of its side. Check the seam
        # strip and one model pixel above it, using the actual silhouette.
        # back_and_sleeves already requires their boxes to touch in depth.
        solid = plates & (np.abs(worn-control).max(2) >= 18)
        seam_zone = sleeves.copy()
        for zone, sleeve in zip(seam_zone, sleeves, strict=True):
            rows = np.flatnonzero(sleeve.any(1))
            for rise in range(1, max(1, round((rows[-1]-rows[0]+1)/3))+1):
                zone[:-rise] |= sleeve[rise:]
        match = (solid[:,None] & seam_zone[None]).sum(axis=(2,3))
        ix = match.argmax(axis=1)
        assert ix[0] != ix[1], (name,match,'las placas no están sobre mangas distintas')
        coverage = []
        for i,j in enumerate(ix):
            covered = solid[i] & seam_zone[j]
            shown = covered.sum()
            columns = covered.any(axis=0).sum() / sleeves[j].any(axis=0).sum()
            assert shown >= 40 and columns >= .39, (name, i, shown, columns, match.tolist())
            coverage.append(f'{shown} px, {columns:.0%} del ancho')
        print(f'::notice title=Montaje fijo en Forge::{fixture}: órbita {drift[0]:.6f}u ({len(orbit)} vistas); '
              f'mirada {drift[1]:.6f}u ({len(aim)} poses); salto {drift[2]:.6f}u, {jump["lift"].max():.2f} bloques. '
              f'Placas sobre las mangas de frente: {" / ".join(coverage)}. '
              f'{cubes} cubos sin deformación; contacto paño/piel {body:.3f}u a través de {rays}/63 muestras, '
              f'costura {seam:.3f}u y apoyo sobre mangas {overlap.round(3).tolist()}u.')


def gallery(root):
    cw,ch = 218,220
    image = Image.new('RGB',(cw*len(VIEWS),44+(ch+21)*len(FIXTURES)),'#15101a')
    pen = ImageDraw.Draw(image)
    pen.text((10,9),'MANTLE OF THE BLIGHT STAR  /  ENCASTRE EN FORGE',fill='#ffe4f0')
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
    for width in (980,840,700,560,420,350,300,240):
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
