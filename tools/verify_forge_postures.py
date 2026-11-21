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
from cape_fit import fixed_wearer_pose, hood_moves
from preview_cloth import ARMOR_GEO, load, matrices
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


def report(root, slot, rig, source):
    fixture = f'revision-alex-{slot}'
    with (root/f'{fixture}-posturas.tsv').open() as f:
        trace = list(csv.DictReader(f, delimiter='\t'))
    boxes = read_boxes(root/f'{fixture}-cubos.tsv')
    n = sum(phase[1] for phase in PHASES)
    assert len(trace) == n and sorted(boxes) == list(range(n)), fixture
    assert np.all(np.diff([int(r['tick']) for r in trace]) > 0), fixture
    names = np.asarray(rig.names)
    collar = np.char.startswith(names, 'v17_cowl_') | np.char.startswith(names, 'v19_cuellito_')
    plates = np.char.startswith(names, 'v18_pad_')
    roots = np.char.endswith(names, '_seg0')
    hood = np.array([hood_moves(n) for n in names])
    unmoving = rig.rigid & ~hood
    expected = set(source) | set(ACTOR)
    rows, images = [], []
    i = 0
    baseline = None
    for phase, count, pitch, yaw, vanilla, label in PHASES:
        motion = []
        photos = []
        for frame in range(count):
            label_sample = (fixture, phase, frame)
            r = trace[i]
            assert int(r['sample']) == i and r['phase'] == phase, label_sample
            assert r['pose'] == ('CROUCHING' if phase.startswith('agachado') else 'STANDING'), (label_sample, r)
            assert (r['sprint'] == 'true') == (phase == 'carrera'), r
            assert float(r['speed']) >= .48 if phase == 'carrera' else float(r['speed']) <= .025, r
            np.testing.assert_allclose([float(r['pitch']), float(r['yaw'])], [pitch,yaw], atol=.02, rtol=0)
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
            stroke = np.linalg.norm(local-baseline,axis=2)
            drift = stroke[unmoving].max()
            assert drift < .006, (label_sample, 'la montura cambió en coordenadas del torso', drift)
            contact = contacts(local[None],actors[None])[0]
            hit = [max(0.,-contact[k,m].min()) for k,m in (
                (2,collar),(2,plates),(3,collar),(2,rig.cloth),(slice(4,6),rig.cloth),
                (slice(6,8),rig.cloth),(slice(8,10),rig.cloth))]
            seam, root_join = rig.joins(local)
            back = lap(local[roots], actors[:1])
            motion.append([drift,seam,root_join,back,stroke[hood].max(),*hit])
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
        hits = [f'{np.count_nonzero(col > .05)}/{count} ({col.max():.3f}u)' for col in a[:,5:].T]
        crown = a[:,4].max()
        row = [slot,phase,count,f'{a[:,0].max():.6f}',*[f'{v:.3f}' for v in a[:,1:4].min(0)],f'{crown:.3f}',*hits]
        rows.append(row)
        print(f'::notice title=Posturas Alex en Forge::{slot}/{phase}: unión mínima de raíz {row[5]}u; '
              f'contacto paño/torso {row[6]}u; recorrido capucha {crown:.3f}u; cuello/cabeza {hits[0]}, '
              f'placas/cabeza {hits[1]}, paño/brazos {hits[4]}, paño/piernas {hits[6]}.', flush=True)
        assert (a[:,1:4].min(0) > [.038,.025,.018]).all(), (fixture,phase,'se abrió el paño',row)
        assert crown < .80 and (phase != 'carrera' or crown > .13), (fixture,phase,'recorrido capucha',crown)
        assert a[:,-1].max() < .05, (fixture,phase,'intersección nueva con pierna',row)
        if phase in ('cenital','agachado-cenital'):
            assert a[:,6].max() <= .05, (fixture,phase,'placa en la nuca',row)
        elif phase == 'giro':
            assert a[:,6].max() <= 1.06, (fixture,phase,'creció el cruce de la placa',row)
    return rows, images


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


def run(root):
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo,0.))
    source = defaultdict(list)
    for name, cube in zip(rig.names,rig.place(matrices(geo)),strict=True):
        source[name].append(cube)
    rows, pictures = [], {}
    for slot in ('pecho','curios'):
        measured, images = report(root,slot,rig,source)
        rows.extend(measured)
        pictures[slot] = images
    with (root/'revision-alex-forge.tsv').open('w') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerow(('ranura','postura','cuadros','deriva_rigida_max_u','costura_min_u','raiz_min_u',
                         'solape_paño_torso_min_u','recorrido_capucha_max_u',*METRICS))
        writer.writerows(rows)
    gallery(root,pictures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots',type=Path)
    run(parser.parse_args().shots)
