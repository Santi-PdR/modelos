#!/usr/bin/env python3
"""Compare articulated plates and .37 projections over the same live sleeves."""
from __future__ import annotations

import argparse
import csv
from itertools import product
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from cape_contact import lap
from cape_fit import fixed_wearer_pose
from preview_cloth import ARMOR_GEO, load, matrices
from verify_forge_gaits import table, text
from verify_forge_postures import read_boxes
from verify_v1660 import WornModel

PLATES = (('v18_pad_0', 'derecha', 'right_sleeve'), ('v18_pad_1', 'izquierda', 'left_sleeve'))
# Even grid on the faces of the main plate and rim, away from corners. The
# little tabs below the shoulder are meant to overlap the fabric/sleeve.
UV = (.1, .3, .5, .7, .9)
FACE_SAMPLES = np.array([p for p in product((0, *UV, 1), repeat=3)
                         if sum(v in (0, 1) for v in p) == 1])


def burial(plate, sleeve):
    """Mean buried depth (model pixels), not a measure of rendered pixels."""
    top = plate[:2]
    basis = top[:, [1, 3, 4]] - top[:, :1]
    points = (FACE_SAMPLES @ basis + top[:, :1]).reshape(-1, 3)
    axes = sleeve[[1, 3, 4]] - sleeve[0]
    fractions = (points - sleeve[0]) @ np.linalg.inv(axes)
    depth = np.minimum(fractions, 1 - fractions) * np.linalg.norm(axes, axis=1)
    return np.maximum(0, depth.min(axis=1))


def rigid_travel(base, live, label):
    assert base.shape == live.shape and np.isfinite([base, live]).all(), label
    np.testing.assert_allclose(np.linalg.norm(base[:, :, None]-base[:, None, :], axis=3),
                               np.linalg.norm(live[:, :, None]-live[:, None, :], axis=3),
                               atol=.004, rtol=0, err_msg=str(label))
    travel = np.linalg.norm(base-live, axis=2).max()
    assert travel < 2.65, (label, 'demasiado recorrido', travel)
    return travel


def verify(root):
    rig_data = fixed_wearer_pose(load(ARMOR_GEO), 0., slim=True)
    rig = WornModel(rig_data)
    boxes = rig.place(matrices(rig_data))
    original = {name: boxes[np.asarray(rig.names) == name] for name, _, _ in PLATES}
    rows, summary, images = [], [], {}
    for slot in ('pecho', 'curios'):
        stem = f'revision-alex-{slot}'
        with (root/f'{stem}-posturas.tsv').open() as f:
            trace = list(csv.DictReader(f, delimiter='\t'))
        live, control = (read_boxes(root/f'{stem}-{suffix}.tsv') for suffix in ('cubos', 'placas-fijas'))
        assert sorted(live) == sorted(control) == list(range(len(trace))), slot
        fast = [i for i, f in enumerate(trace) if f['phase'] == 'carrera']
        assert len(fast) == 24 and all(trace[i]['sprint'] == 'true' and float(trace[i]['speed']) >= .48 for i in fast), slot
        candidates = [i for i in fast if trace[i]['image'] != '-']
        assert len(candidates) == 5, slot
        pictures = []
        for name, side, arm in PLATES:
            signs = np.sign(original[name][0, :, 0].mean())
            score = []
            for i, entry in enumerate(trace):
                key = slot, side, i
                a, b = np.asarray(control[i][name]), np.asarray(live[i][name])
                assert a.shape == b.shape == original[name].shape and np.isfinite([a, b]).all(), key
                # Control must still be exactly the previous plate transform.
                gap = np.linalg.norm(a[:, :, None] - original[name][:, None, :], axis=3).min(2).max()
                assert gap < .007, (key, 'proyección fija distinta de .37', gap)
                shift = rigid_travel(a, b, key)
                if i not in fast:
                    assert shift < .006, (key, 'cambió una placa en una pose quieta', shift)
                strip = np.asarray(live[i]['v20_mount_shoulders'])
                strip = strip[np.sign(strip[:, :, 0].mean(axis=1)) == signs]
                seam = lap(b, strip)
                assert len(strip) == 1 and seam > .22, (key, 'abrió la costura', seam)
                for cover in ('head', 'hat'):
                    head = np.asarray(live[i][cover])
                    prior, after = max(0., lap(a, head)), max(0., lap(b, head))
                    assert after <= prior + .08, (key, cover, 'nuevo cruce', prior, after)
                sleeve, = live[i][arm]
                np.testing.assert_allclose(np.linalg.norm(sleeve[[1, 3, 4]]-sleeve[0], axis=1),
                                           (3.5, 12.5, 4.5), atol=.01, rtol=0)
                old, new = burial(a, sleeve), burial(b, sleeve)
                sample = [old.mean(), new.mean(), (old > .22).mean(), (new > .22).mean(), seam, shift]
                score.append(sample)
                rows.append((slot, side, i, entry['phase'], *(f'{v:.6f}' for v in sample)))
            motion = np.asarray(score)[fast]
            old, new, hidden0, hidden1 = motion.mean(0)[:4]
            assert old > .012 and new < .88 * old, (slot, side, 'no disminuyó el hundimiento', old, new)
            assert hidden1 < .92 * hidden0 and motion[:, 5].max() > .65, (slot, side, hidden0, hidden1)
            seam = motion[:, 4].min()
            summary.append((slot, side, len(fast), *(f'{v:.6f}' for v in (old, new, hidden0, hidden1, seam))))
            i = max(candidates, key=lambda k: score[k][0]-score[k][1])
            pictures.append((root / trace[i]['image'], score[i][5]))
            print(f'{slot}/{side}: 24 poses de carrera; profundidad media bajo la manga '
                  f'{old:.3f} → {new:.3f}u; muestras hundidas >.22u {hidden0:.1%} → {hidden1:.1%}; '
                  f'contacto mínimo con la costura {seam:.3f}u.', flush=True)
        images[slot] = pictures
    table(root/'hombreras-movimiento.tsv', 'ranura lado muestra fase profundidad_37_u profundidad_38_u '
          'enterrado_37 enterrado_38 costura_u movimiento_u', rows)
    table(root/'hombreras-resumen.tsv', 'ranura lado cuadros profundidad_37_u profundidad_38_u '
          'enterrado_37 enterrado_38 costura_min_u', summary)
    return images


def gallery(root, images):
    sheet = Image.new('RGB', (1100, 782), '#17121d')
    pen = ImageDraw.Draw(sheet)
    text(pen, (18, 12), 'Las hombreras durante la carrera', 27, bold=True)
    text(pen, (18, 50), 'Alex en Forge · capturas de la v1.67.38, no del control de malla .37.', 16, '#edc4db')
    for row, (slot, pairs) in enumerate(images.items()):
        y = 110 + 332 * row
        for col, (path, shift) in enumerate(pairs):
            x = 18 + 538 * col
            text(pen, (x, y-24), f'{slot.capitalize()} · muestra {col+1} · giro de placa ({shift:.2f}u)', 16)
            with Image.open(path) as im:
                sheet.paste(ImageOps.fit(im.convert('RGB'), (524, 306), Image.Resampling.LANCZOS), (x, y))
    sheet.save(root/'hombreras-en-carrera.jpg', quality=94, optimize=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots', type=Path)
    options = cli.parse_args()
    gallery(options.shots, verify(options.shots))
