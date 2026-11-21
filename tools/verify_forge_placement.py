#!/usr/bin/env python3
"""Measure the original cloak in the live Forge wearer frame and in F5."""
from __future__ import annotations

import argparse
from collections import defaultdict
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from bbmodel_export import mod_version
from cape_contact import back_and_sleeves, original_dimensions, shoulder_seams
from cape_fit import fixed_wearer_pose
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


def front_coverage(root, fixture):
    name = f'{fixture}-frente'
    worn, control = (read(root/f'{name}{suffix}.png') for suffix in ('','-sin-placas'))
    names = ('v18_pad_0','v18_pad_1','left_sleeve','right_sleeve')
    plates, sleeves = np.split(masks_for(root,name,(worn.shape[1],worn.shape[0]),names),2)
    assert np.min(sleeves.sum(axis=(1,2)))>=180, (name,'las mangas no entraron en cuadro')
    # Count actual rendered plate pixels, not the plate's projected box.
    solid = plates & (np.abs(worn-control).max(2) >= 18)
    seam_zone = sleeves.copy()
    for zone, sleeve in zip(seam_zone, sleeves, strict=True):
        rows = np.flatnonzero(sleeve.any(1))
        for rise in range(1, max(1, round((rows[-1]-rows[0]+1)/3))+1):
            zone[:-rise] |= sleeve[rise:]
    match = (solid[:,None] & seam_zone[None]).sum(axis=(2,3))
    ix = match.argmax(axis=1)
    assert ix[0] != ix[1], (name,match,'las placas no están sobre mangas distintas')
    result = []
    for i,j in enumerate(ix):
        covered = solid[i] & seam_zone[j]
        shown = covered.sum()
        columns = covered.any(axis=0).sum() / sleeves[j].any(axis=0).sum()
        assert shown >= 40 and columns >= .39, (name, i, shown, columns, match.tolist())
        result.append((shown,columns))
    return np.asarray(result)


def front_fabric(root, fixture):
    """Isolate the fabric in the real draw; plate pixels are not cloth pixels."""
    name = f'{fixture}-frente'
    worn, control = (read(root/f'{name}{suffix}.png') for suffix in ('','-sin-tela-hombros'))
    assert worn.shape == control.shape, name
    mask, = masks_for(root,name,(worn.shape[1],worn.shape[0]),('v20_mount_shoulders',))
    solid = mask & (np.abs(worn-control).max(2) >= 8)
    left, right = np.split(solid, [worn.shape[1]//2], axis=1)
    count = np.asarray([left.sum(), right.sum()])
    assert min(count) >= 20, (name, 'no se distingue el ribete de tela en ambos hombros', count.tolist())
    return count


def nape_hair(path):
    pixels = read(path)
    h, w = pixels.shape[:2]
    r,g,b = pixels[round(.33*h):round(.59*h), w//2-round(.18*h):w//2+round(.18*h)].transpose(2,0,1)
    orange = (r >= 115) & (r-g >= 27) & (g-b >= 22)
    # Restrict to dark interruptions flanked by hair on the same scanline.
    inside = np.maximum.accumulate(orange,1) & np.maximum.accumulate(orange[:,::-1],1)[:,::-1]
    return orange, inside & (r < 95)


def nape_recovery(root, baseline):
    """Compare dark breaks inside Alex's orange hair in the same vanilla F5 pose."""
    with (root/'nuca-forge.tsv').open('w') as f:
        print('ranura\tpostura\tfranja_oscura_base_px\tdevueltos_al_pelo_px',file=f)
        for slot in ('pecho','curios'):
            for pose in ('cenital','agachado-cenital'):
                filename = f'revision-alex-{slot}-{pose}-00.png'
                _, old = nape_hair(baseline/filename)
                orange, _ = nape_hair(root/filename)
                total, recovered = old.sum(), (old & orange).sum()
                print(slot,pose,total,recovered,sep='\t',file=f)
                print(f'::notice title=Nuca en Forge::Alex {slot}/{pose}: {recovered}/{total} píxeles de la franja oscura '
                      'vuelven a mostrar pelo en F5.')
                assert total >= 30 and recovered >= .65*total, (filename,total,recovered)


def nape_retention(root, baseline):
    with (root/'nuca-forge.tsv').open('w') as f:
        print('ranura\tpostura\tpelo_base_px\tpelo_conservado_px\toscuros_nuevos_px',file=f)
        for slot in ('pecho','curios'):
            for pose in ('cenital','agachado-cenital'):
                filename = f'revision-alex-{slot}-{pose}-00.png'
                old, _ = nape_hair(baseline/filename)
                hair, dark = nape_hair(root/filename)
                count, kept, loss = old.sum(), (old & hair).sum(), (old & dark).sum()
                print(slot,pose,count,kept,loss,sep='\t',file=f)
                print(f'::notice title=Nuca en Forge::{slot}/{pose}: {kept}/{count} píxeles de pelo de la .22; '
                      f'{loss} oscuros nuevos en el interior.')
                assert count >= 160 and kept >= .90*count and loss <= max(9,.015*count), (filename,count,kept,loss)


def report(root, baseline=None, baseline_version='1.67.20'):
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo,0.))
    original = defaultdict(list)
    for name, cube in zip(rig.names, rig.place(matrices(geo)), strict=True):
        original[name].append(cube)
    front_rows, fabric_rows = [], []
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
        weave = shoulder_seams(parts,fixture)
        fabric = front_fabric(root,fixture)
        fabric_rows.append((fixture,*fabric,*weave.ravel()))
        print(f'::notice title=Tela frontal en Forge::{fixture}: {fabric.tolist()} px de tela sobre los hombros; '
              f'contacto con retornos {weave[:,0].round(3).tolist()}u y placas {weave[:,1].round(3).tolist()}u.')
        visible = front_coverage(root,fixture)
        coverage = [f'{px:.0f} px, {wide:.0%} del ancho' for px,wide in visible]
        if baseline is not None:
            old = front_coverage(baseline,fixture)
            ratio = (visible[:,0].sum()/old[:,0].sum())
            print(f'::notice title=Lectura frontal::{fixture}: {old[:,0].astype(int).tolist()} → '
                  f'{visible[:,0].astype(int).tolist()} píxeles de placa sobre las mangas ({ratio:.1%} de v{baseline_version}).')
            front_rows.append((fixture, *old[:,0].astype(int), *visible[:,0].astype(int)))
            # The flatter rim exposes fabric instead of maximizing dark plate
            # pixels. Keep both plates legible (front_coverage) and the total
            # coverage near the last delivered fit, with a separate fabric gate.
            if baseline_version == '1.67.20':
                minimum = 1.03 if '-alex-' in fixture else .97
            elif baseline_version == '1.67.22':
                minimum = .97
                old_fabric = front_fabric(baseline,fixture)
                np.testing.assert_allclose(visible[:,0],old[:,0],atol=8,rtol=.025,err_msg=fixture)
                np.testing.assert_allclose(fabric,old_fabric,atol=8,rtol=.045,err_msg=fixture)
            else:
                minimum = .85
                assert min(visible[:,0]/old[:,0]) >= .80, (fixture,'disminuyó demasiado una placa',visible,old)
            assert ratio >= minimum, (fixture,'lectura frontal',ratio)
        print(f'::notice title=Montaje fijo en Forge::{fixture}: órbita {drift[0]:.6f}u ({len(orbit)} vistas); '
              f'mirada {drift[1]:.6f}u ({len(aim)} poses); salto {drift[2]:.6f}u, {jump["lift"].max():.2f} bloques. '
              f'Placas sobre las mangas de frente: {" / ".join(coverage)}. '
              f'{cubes} cubos sin deformación; contacto paño/piel {body:.3f}u a través de {rays}/63 muestras, '
              f'costura {seam:.3f}u y apoyo sobre mangas {overlap.round(3).tolist()}u.')
    if baseline is not None:
        with (root/'lectura-frontal-forge.tsv').open('w') as f:
            print('fixture\tbase_compacta\tbase_ancha\tcompacta\tancha',file=f)
            for row in front_rows:
                print(*row,sep='\t',file=f)
    with (root/'tela-frontal-forge.tsv').open('w') as f:
        print('fixture\tizquierda_px\tderecha_px\tcompacta_retorno_u\tcompacta_placa_u\tancha_retorno_u\tancha_placa_u',file=f)
        for fixture,left,right,*seams in fabric_rows:
            print(fixture,left,right,*(f'{x:.3f}' for x in seams),sep='\t',file=f)
    if baseline is not None and baseline_version == '1.67.21':
        nape_recovery(root,baseline)
    if baseline is not None and baseline_version == '1.67.22':
        nape_retention(root,baseline)


def comparison(root, baseline, baseline_version='1.67.20'):
    cw,ch = 270,246
    columns = ('FRENTE','TRES CUARTOS','ESPALDA F5','CENITAL F5')
    board = Image.new('RGB',(cw*len(columns),46+(ch+24)*4),'#15101a')
    pen = ImageDraw.Draw(board)
    pen.text((10,10),'ALEX / FORGE 1.20.1 / MISMA CAMARA POR PAREJA',fill='#ffe4f0')
    for c,title in enumerate(columns):
        pen.text((c*cw+10,30),title,fill='#efc5da')
    for j,slot in enumerate(('pecho','curios')):
        views = (f'posicion-alex-{slot}-frente.png',f'posicion-alex-{slot}-diagonal.png',
                 f'posicion-alex-{slot}-espalda.png',f'revision-alex-{slot}-cenital-00.png')
        # Show the complete silhouette from behind; frame the collar and
        # sleeve joins more tightly elsewhere, identically in both versions.
        framing = ((.58,.31),(.62,.32),(1.,.50),(.48,.515))
        for i,(path,title) in enumerate(((baseline,f'BASE v{baseline_version}'),(root,f'AJUSTE v{mod_version()}'))):
            y = 46+(ch+24)*(j*2+i)
            pen.text((10,y+4),f'{slot.upper()} / {title}',fill='#ffe4f0')
            for c,name in enumerate(views):
                with Image.open(path/name) as raw:
                    w,h = raw.size
                    height, center = framing[c]
                    hh = round(h*height)
                    d = min(w,round(hh*cw/ch))
                    top = round(h*center)-hh//2
                    crop = raw.crop(((w-d)//2,top,(w+d)//2,top+hh)).convert('RGB')
                    board.paste(crop.resize((cw-6,ch),Image.Resampling.LANCZOS),(c*cw+3,y+19))
    board.save(root/'comparacion-alex-forge.jpg',quality=93,optimize=True)


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
    ap.add_argument('--baseline-shots', type=Path)
    ap.add_argument('--baseline-version', default='1.67.20')
    args = ap.parse_args()
    if args.gallery_only:
        gallery(args.shots)
        if args.baseline_shots:
            comparison(args.shots,args.baseline_shots,args.baseline_version)
    else:
        report(args.shots,args.baseline_shots,args.baseline_version)
