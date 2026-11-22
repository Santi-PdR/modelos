#!/usr/bin/env python3
"""Measure actual vanilla skin/cloth intersections from the Forge pose audit.

Contact with a closed cube is diagnostic, not a count of visible clipped pixels:
the hat and sleeve textures can be transparent. Never silently discard hits.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_contact import lap, original_dimensions
from cape_fit import fixed_wearer_pose, hood_aim, hood_moves, nape_piece, nape_shifts, profile, sprint_edge_offset
from preview_cloth import ARMOR_GEO, load, matrices, mod_version
from verify_v1660 import WornModel, contacts

# name, rendered ticks collected, head pitch/yaw, untouched vanilla F5 camera
PHASES = (
    ('reposo', 8, 8, 0, True, 'ESPALDA F5'),
    ('cenital', 8, 79, 22, True, 'CENITAL F5'),
    ('mirada-alta', 8, -64, 0, False, 'MIRADA ARRIBA'),
    ('giro', 8, -35, 55, False, 'GIRO DE CABEZA'),
    ('agachado', 12, 0, 0, False, 'AGACHADO'),
    ('agachado-cenital', 8, 79, 22, True, 'AGACHADO F5'),
    ('carrera', 24, 0, 0, False, 'CARRERA'),
)
ACTOR = ('body', 'jacket', 'head', 'hat', 'left_arm', 'right_arm', 'left_sleeve',
         'right_sleeve', 'left_leg', 'right_leg')
METRICS = ('cuello_cabeza', 'placas_cabeza', 'cuello_capa_exterior', 'pano_cabeza',
           'pano_brazos', 'pano_mangas', 'pano_piernas')


def read_boxes(path):
    out = defaultdict(lambda: defaultdict(list))
    for line in path.read_text().splitlines():
        sample, bone, *xyz = line.split('\t')
        out[int(sample)][bone].append(np.asarray(xyz, dtype=float).reshape(8, 3))
    return out


def report(root, slot, rig, source, *, nape=False):
    fixture = f'revision-alex-{slot}'
    with (root/f'{fixture}-posturas.tsv').open() as f:
        trace = list(csv.DictReader(f, delimiter='\t'))
    boxes = read_boxes(root/f'{fixture}-cubos.tsv')
    control_path = root/f'{fixture}-sin-holgura-brazos.tsv'
    paired = control_path.is_file()
    control = read_boxes(control_path) if paired else {}
    n = sum(phase[1] for phase in PHASES)
    assert len(trace) == n and sorted(boxes) == list(range(n)), fixture
    if paired:
        assert sorted(control) == list(range(n-PHASES[-1][1],n)), (fixture,'muestras A/B de carrera ausentes')
    assert np.all(np.diff([int(r['tick']) for r in trace]) > 0), fixture
    names = np.asarray(rig.names)
    collar = np.char.startswith(names, 'v17_cowl_') | np.char.startswith(names, 'v19_cuellito_')
    plates = np.char.startswith(names, 'v18_pad_')
    roots = np.char.endswith(names, '_seg0')
    hood = np.array([hood_moves(n) for n in names])
    # The sleeve hinge is checked against the old pose in verify_forge_shoulders.
    flex_plates = (root/f'{fixture}-placas-fijas.tsv').is_file()
    unmoving = rig.rigid & ~hood & ~(plates if flex_plates else np.zeros_like(plates))
    expected = set(source) | set(ACTOR)
    offsets = {n for n in source if sprint_edge_offset(n,rig.by[n].get('parent')) is not None}
    free = rig.cloth & ~roots
    rows, images, arms = [], [], []
    i = 0
    baseline = None
    for phase, count, pitch, yaw, vanilla, label in PHASES:
        motion = []
        photos = []
        # The audit waits at least seven ticks. Here the neutral crouch is
        # settled; when sprint is measured (15 ticks later) it has released.
        shifts = nape_shifts(-pitch,yaw,profile()['bodyAngle'] if phase.startswith('agachado') else 0.)
        stroke_fit = np.array([shifts[k] if (k := nape_piece(n)) is not None else (0,0,0) for n in names]) if nape else 0.
        for frame in range(count):
            label_sample = (fixture, phase, frame)
            r = trace[i]
            assert int(r['sample']) == i and r['phase'] == phase, label_sample
            assert r['pose'] == ('CROUCHING' if phase.startswith('agachado') else 'STANDING'), (label_sample, r)
            assert (r['sprint'] == 'true') == (phase == 'carrera'), r
            assert float(r['speed']) >= .48 if phase == 'carrera' else float(r['speed']) <= .025, r
            np.testing.assert_allclose([float(r['pitch']), float(r['yaw'])], [pitch,yaw], atol=.02, rtol=0)
            if paired:
                # The test never asks a tilted torso to do the upright fold.
                wanted = 0. if phase.startswith('agachado') else hood_aim(-pitch,yaw,0.)
                np.testing.assert_allclose(float(r['pliegue']),wanted,atol=.03,rtol=0,err_msg=str(label_sample))
            assert (r['vanilla'] == 'true') == vanilla, r
            if vanilla:
                np.testing.assert_allclose([float(r['camera_pitch']),float(r['camera_yaw'])], [pitch,yaw], atol=.02, rtol=0)
            group = boxes[i]
            assert set(group) == expected, (label_sample, sorted(set(group)^expected))
            assert all(len(group[name]) == 1 for name in ACTOR), label_sample
            assert original_dimensions(group, source, label_sample) == len(names)
            local = np.array([group[name].pop(0) for name in names])
            actors = np.array([group[k][0] for k in ACTOR])
            # Prevent an armour model or fat sleeve placeholder from passing as Alex.
            for k, dims in ((0,(8,12,4)), (2,(8,8,8)), (3,(9,9,9)), (4,(3,12,4)), (5,(3,12,4))):
                np.testing.assert_allclose(np.linalg.norm(actors[k,[1,3,4]]-actors[k,0],axis=1), dims, atol=.01, rtol=0)
            if baseline is None:
                baseline = local.copy()
            # Subtract the declared translation only. A stretched/detached
            # link or any moved plate still fails the original checks.
            center = local-stroke_fit[:,None,:] if nape else local
            stroke = np.linalg.norm(center-baseline,axis=2)
            drift = stroke[unmoving].max()
            assert drift < .006, (label_sample, 'la montura cambió en coordenadas del torso', drift)
            contact = contacts(local[None],actors[None])[0]
            hit = [max(0.,-contact[k,m].min()) for k,m in (
                (2,collar),(2,plates),(3,collar),(2,rig.cloth),(slice(4,6),rig.cloth),
                (slice(6,8),rig.cloth),(slice(8,10),rig.cloth))]
            if paired and phase == 'carrera':
                ablation = control[i]
                assert set(ablation) == offsets, (label_sample,set(ablation)^offsets)
                before = local.copy()
                for bone in offsets:
                    mask = names == bone
                    b = np.asarray(ablation[bone])
                    delta = local[mask] - b
                    np.testing.assert_allclose(delta,np.broadcast_to(delta[0,0],delta.shape),atol=.002,rtol=0)
                    assert .08 < np.linalg.norm(delta[0,0]) <= 1.34, (label_sample,bone,delta[0,0])
                    before[mask] = b
                a = contacts(before[None],actors[None,4:6])[0]
                arms.append((max(0.,-a[:,rig.cloth].min()),hit[4],
                             max(0.,-a[:,free].min()),max(0.,-contact[4:6,free].min())))
            seam, root_join = rig.joins(local)
            back = lap(local[roots], actors[:1])
            hood_motion = np.linalg.norm(local[hood]-baseline[hood],axis=2).max()
            motion.append([drift,seam,root_join,back,stroke[hood].max(),hood_motion,*hit])
            if r['image'] != '-':
                assert r['image'] == f'{fixture}-{phase}-{frame:02d}.png', label_sample
                path = root/r['image']
                with Image.open(path) as photo:
                    assert min(photo.size) >= 460, label_sample
                photos.append((hit[4] if phase == 'carrera' else 0.,path))
            i += 1
        assert len(photos) == (5 if phase == 'carrera' else 1), (fixture, phase)
        # Show the largest measured arm overlap among the saved race frames.
        images.append((label,max(photos, key=lambda item:item[0])[1]))
        a = np.array(motion)
        hits = [f'{np.count_nonzero(col > .05)}/{count} ({col.max():.3f}u)' for col in a[:,6:].T]
        crown = a[:,4].max()
        raw_crown = a[:,5].max()
        row = [slot,phase,count,f'{a[:,0].max():.6f}',*[f'{v:.3f}' for v in a[:,1:4].min(0)],f'{raw_crown:.3f}',*hits]
        rows.append(row)
        print(f'::notice title=Posturas Alex en Forge::{slot}/{phase}: unión mínima de raíz {row[5]}u; '
              f'contacto paño/torso {row[6]}u; recorrido capucha {raw_crown:.3f}u; cuello/cabeza {hits[0]}, '
              f'placas/cabeza {hits[1]}, paño/brazos {hits[4]}, paño/piernas {hits[6]}.', flush=True)
        assert (a[:,1:4].min(0) > [.038,.025,.018]).all(), (fixture,phase,'se abrió el paño',row)
        limit = {'mirada-alta':5.7,'giro':1.35}.get(phase,.80) if paired else .80
        assert crown < limit and (phase != 'carrera' or crown > .13), (fixture,phase,'recorrido capucha',crown)
        if paired and phase == 'mirada-alta':
            assert 2. < crown and (a[:,[6,8]].max(0) < [2.40,2.92]).all(), (fixture,phase,'cruce de cuello',row)
        assert a[:,-1].max() < .05, (fixture,phase,'intersección nueva con pierna',row)
        if phase in ('cenital','agachado-cenital'):
            assert a[:,7].max() <= .05, (fixture,phase,'placa en la nuca',row)
        elif phase == 'giro':
            assert a[:,7].max() <= 1.06, (fixture,phase,'creció el cruce de la placa',row)
    return rows, images, np.asarray(arms)


def sleeves(slot, a):
    assert a.shape == (24,4), (slot,a.shape)
    peak, mean = a.max(0),a.mean(0)
    assert peak[3] < .90*peak[2] and mean[3] < .80*mean[2], (slot,'cruce de tramos libres',peak,mean)
    assert mean[1] < .98*mean[0], (slot,'no bajó el cruce de paño/brazos',mean)
    print(f'::notice title=Holgura de carrera en Forge::{slot}: mismas 24 poses; paño libre/brazos '
          f'{peak[2]:.3f} → {peak[3]:.3f}u pico, {mean[2]:.3f} → {mean[3]:.3f}u promedio; '
          f'paño completo {peak[0]:.3f} → {peak[1]:.3f}u pico.',flush=True)
    return [slot,len(a),*(f'{v:.3f}' for v in (*peak,*mean))]


def gallery(root, pictures):
    cw, ch = 222, 238
    sheet = Image.new('RGB', (cw*len(PHASES), 49+(ch+27)*len(pictures)), '#16111d')
    pen = ImageDraw.Draw(sheet)
    pen.text((11,10), 'ALEX / MANTLE OF THE BLIGHT STAR / POSTURAS REALES EN FORGE', fill='#ffe2f3')
    for col, (_,_,_,_,_,title) in enumerate(PHASES):
        pen.text((col*cw+10,32), title, fill='#e8c9e1')
    for row, (slot, images) in enumerate(pictures.items()):
        y = 49+row*(ch+27)
        pen.text((11,y+4), slot.upper(), fill='#ffe2f3')
        for col, (_, path) in enumerate(images):
            with Image.open(path) as im:
                w, h = im.size
                # Center on the wearer; keep the hem and the top of the head.
                width = min(w, round(h*cw/ch))
                frame = im.crop(((w-width)//2,0,(w+width)//2,h)).convert('RGB')
                sheet.paste(frame.resize((cw-6,ch), Image.Resampling.LANCZOS), (col*cw+3,y+21))
    sheet.save(root/'revision-alex-forge.jpg', quality=94,optimize=True)


def comparison(root, before, after):
    columns = ('MIRADA ARRIBA','CENITAL F5','CARRERA')
    w,h = 269,237
    sheet = Image.new('RGB',(w*len(columns),55+4*(h+24)),'#19141f')
    pen = ImageDraw.Draw(sheet)
    pen.text((9,8),'ALEX / MANTLE OF THE BLIGHT STAR / PRUEBAS REALES EN FORGE',fill='#f8eaf2')
    for i,label in enumerate(columns):
        pen.text((w*i+9,32),label,fill='#f0bed9')
    for i,slot in enumerate(('pecho','curios')):
        for j,(images,version) in enumerate(((before,'1.67.22'),(after,mod_version()))):
            top = 55+(2*i+j)*(h+24)
            pen.text((9,top+2),f'{slot.upper()} / v{version}',fill='#f8eaf2')
            for k,label in enumerate(columns):
                with Image.open(dict(images[slot])[label]) as photo:
                    x,y = photo.size
                    ht,center = ((.51,.30),(.49,.49),(1.,.50))[k]
                    dy = round(y*ht)
                    dx = min(x,round(dy*w/h))
                    cy = round(y*center)
                    crop = photo.crop(((x-dx)//2,cy-dy//2,(x+dx)//2,cy-dy//2+dy)).convert('RGB')
                    sheet.paste(crop.resize((w-6,h),Image.Resampling.LANCZOS),(k*w+3,top+20))
    sheet.save(root/'comparacion-gestos-forge.jpg',quality=94,optimize=True)


def peak(text):
    return float(text.split('(')[-1].removesuffix('u)'))


def run(root, reference=None):
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo,0.))
    source = defaultdict(list)
    for name, cube in zip(rig.names,rig.place(matrices(geo)),strict=True):
        source[name].append(cube)
    rows, pictures, base_pictures, pairs = [], {}, {}, []
    for slot in ('pecho','curios'):
        measured, images, arms = report(root,slot,rig,source,nape=tuple(map(int, mod_version().split('.'))) >= (1, 67, 32))
        pairs.append(sleeves(slot,arms))
        rows.extend(measured)
        pictures[slot] = images
        if reference:
            old, base_pictures[slot], _ = report(reference,slot,rig,source)
            for earlier, now in zip(old,measured,strict=True):
                pose = now[1]
                if pose == 'mirada-alta':
                    assert all(peak(now[i]) < factor*peak(earlier[i]) for i,factor in ((8,.70),(10,.75))), (earlier,now)
                if pose in ('cenital','agachado-cenital'):
                    assert all(peak(now[i]) <= peak(earlier[i])+.045 for i in (8,10)), (earlier,now)
                if pose == 'giro':
                    assert peak(now[8]) <= peak(earlier[8])+.03, (earlier,now)
    with (root/'holgura-brazos-forge.tsv').open('w') as f:
        print('ranura\tcuadros\tpico_total_sin_u\tpico_total_con_u\tpico_libre_sin_u\tpico_libre_con_u'
              '\tmedia_total_sin_u\tmedia_total_con_u\tmedia_libre_sin_u\tmedia_libre_con_u',file=f)
        for row in pairs:
            print(*row,sep='\t',file=f)
    with (root/'revision-alex-forge.tsv').open('w') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerow(('ranura','postura','cuadros','deriva_rigida_max_u','costura_min_u','raiz_min_u',
                         'solape_paño_torso_min_u','recorrido_capucha_max_u',*METRICS))
        writer.writerows(rows)
    gallery(root,pictures)
    if reference:
        comparison(root,base_pictures,pictures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    parser.add_argument('--baseline-shots',type=Path,help='capturas y cubos de Forge v1.67.22')
    args = parser.parse_args()
    run(args.shots,args.baseline_shots)
