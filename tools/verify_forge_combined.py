#!/usr/bin/env python3
"""Audit a continuous sprint → turn and crouch → stop → stand in Forge."""
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_contact import lap, original_dimensions
from cape_fit import fixed_wearer_pose, hood_moves
from preview_cloth import ARMOR_GEO, load, matrices, mod_version
from verify_forge_gaits import crop, table, text
from verify_forge_postures import ACTOR, read_boxes
from verify_forge_walk import pairs, points, read
from verify_v1660 import WornModel, contacts

SLOTS = ('pecho', 'curios')
STILLS = ((27, 'Carrera'), (52, 'Giro y frenada'), (63, 'Paso agachado'),
          (77, 'Al detenerse'), (103, 'De nuevo en pie'))


def timeline(data, slot):
    t = data['time']
    keys = data.dtype.names
    assert all(np.isfinite(data[k]).all() for k in keys if k != 'image'), (slot, 'traza inválida')
    assert len(t) > 115 and t[0] < 2 and t[-1] >= 109 and np.all(np.diff(t) >= 0), (slot, 'ruta incompleta')
    assert (data['ground'] == 1).all() and not any(data[k].any() for k in ('air', 'fall', 'swim')), (slot, 'no fue una maniobra en suelo seco')

    def span(lo, hi):
        mask = (t >= lo) & (t < hi)
        assert len(set(t[mask].astype(int))) >= .7 * (hi - lo), (slot, lo, hi, 'faltan ticks')
        return data[mask]

    run, entry, step, stop, stand, rest = (span(lo, hi) for lo, hi in (
        (30, 44), (49, 60), (60, 68), (81, 89), (89, 100), (101, 109)))
    assert (run['sprinting'] == 1).all() and run['run'].min() > .97, (slot, 'no llegó a correr')
    assert (step['crouching'] == 1).all() and step['sneak'].min() > .98 and step['leg_speed'].min() > .07, (slot, 'no hubo paso agachado')
    assert (stop['crouching'] == 1).all() and stop['leg_speed'].max() < .03, (slot, 'faltó freno agachado')
    assert not rest['crouching'].any() and (rest['sneak'] + rest['run'] + rest['walk']).max() < .002, (slot, 'no retomó reposo')
    for part, direction in ((entry, 1), (stand, -1)):
        w = part['sneak']
        assert np.count_nonzero((w > .01) & (w < .99)) >= 3, (slot, 'faltan pesos intermedios de Shift')
        assert (direction * np.diff(w) >= -.0001).all(), (slot, 'mezcla de Shift se reinició')
    stride = data['leg_pos'] * np.float32(.6662) / (2 * np.pi)
    np.testing.assert_allclose(data['stride'], stride, atol=.000005, rtol=0, err_msg=f'{slot}: reloj de la zancada')
    assert (np.diff(data['stride']) >= -1e-6).all() and np.ptp(data['seat_z']) < .006, (slot, 'reinicio de zancada o deriva de montura')
    use = pairs(t, 44, 85)
    assert use.sum() >= 28, (slot, 'faltan pares en giro y frenada')
    rate = np.linalg.norm(np.diff(points(data, 'tip'), axis=0)[use], axis=1) / np.diff(t)[use]
    assert 0.2 < np.quantile(rate, .90) and rate.max() < 6., (slot, 'punta inmóvil o latigazo', rate.max())
    return len(t), np.quantile(rate, .90), rate.max()


def fit(root, data, slot, rig, source):
    mesh = read_boxes(root / f'maniobra-{slot}-cubos.tsv')
    sampled = data[data['fit'] == 1]
    ticks = sampled['time'].astype(int)
    assert list(ticks) == sorted(mesh) and len(mesh) >= 55, (slot, 'faltan cuadros de malla')
    held = sampled[(ticks >= 49) & (ticks <= 67)]
    assert len(held) >= 13 and held['yaw'].min() > 54.5 and held['pitch'].max() < -34.5, (slot, 'faltó el giro en el render real')
    assert sampled['yaw'][0] < .05 and abs(sampled['yaw'][-1]) < .05, (slot, 'faltó barrer la mirada')
    roots = np.array([name.endswith('_seg0') for name in rig.names])
    fixed = rig.rigid & ~np.array([hood_moves(name) for name in rig.names])
    plate = np.array([name == 'v18_pad_1' for name in rig.names])
    reference = None
    worst = np.zeros(4)
    joins = np.full(3, np.inf)
    drift = 0.
    for tick, groups in mesh.items():
        label = (slot, tick)
        assert set(groups) == set(source) | set(ACTOR), (label, 'cubos incompletos')
        assert original_dimensions(groups, source, label) == len(rig.names)
        assert all(len(groups[name]) == 1 for name in ACTOR), label
        actors = {name: np.asarray(groups[name]) for name in ACTOR}
        live = np.array([groups[name].pop(0) for name in rig.names])
        if reference is None:
            reference = live[fixed]
        drift = max(drift, np.linalg.norm(live[fixed] - reference, axis=2).max())
        joins = np.minimum(joins, [*rig.joins(live), lap(live[roots], actors['body'])])
        limbs = np.concatenate([actors[k] for k in ('left_arm', 'right_arm', 'left_leg', 'right_leg')])
        hit = contacts(live[None, rig.cloth], limbs[None])[0]
        worst = np.maximum(worst, [lap(live[plate], actors['head']), lap(live[plate], actors['hat']),
                                   -hit[:2].min(), -hit[2:].min()])
    assert drift < .006 and (joins > [.038, .025, .018]).all(), (slot, 'se movió o se abrió el anclaje', drift, joins)
    assert worst[3] <= .05, (slot, 'cruce con pierna en maniobra', worst[3])
    return (len(mesh), *joins, drift, *worst)


def gallery(root, pictures, version):
    w, h = 222, 224
    board = Image.new('RGB', (5*(w+7)+18, 125+2*(h+38)+10), '#17121d')
    pen = ImageDraw.Draw(board)
    text(pen, (15, 10), f'De carrera a reposo agachado · v{version}', 28, bold=True)
    text(pen, (15, 53), 'Alex · cliente Forge, vista fija respecto del torso · misma secuencia en las dos ranuras', 16, '#d7c0d7')
    for j, (slot, paths) in enumerate(pictures.items()):
        y = 125+j*(h+38)
        text(pen, (13, y-22), slot.upper(), 14, bold=True)
        for i, ((_, label), path) in enumerate(zip(STILLS, paths, strict=True)):
            x = 12+i*(w+7)
            if j == 0:
                text(pen, (x+2, 78), label, 16, '#edc4db')
            board.paste(crop(path, w, h, 0, 1), (x, y))
    board.save(root/'maniobra-forge.jpg', quality=93, optimize=True)


def main(root):
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo, 0.))
    source = defaultdict(list)
    for name, box in zip(rig.names, rig.place(matrices(geo)), strict=True):
        source[name].append(box)
    results, pictures = [], {}
    for slot in SLOTS:
        data = read(root/f'maniobra-{slot}.tsv')
        count, p90, peak = timeline(data, slot)
        poses, seam, join, back, drift, head, hat, arm, leg = fit(root, data, slot, rig, source)
        results.append((slot, count, poses, *(f'{v:.6f}' for v in (p90, peak, seam, join, back, drift, head, hat, arm, leg))))
        visible = data[data['image'] != '-']
        assert len(visible) == len(STILLS), (slot, 'capturas incompletas')
        for sample, (at, _) in zip(visible, STILLS, strict=True):
            tick = int(sample['time'])
            assert at <= tick <= at + 2 and sample['image'] == f'maniobra-{slot}-{tick:03d}.png', (slot, at, sample)
        pictures[slot] = [root/name for name in visible['image']]
        print(f'{slot}: {count} cuadros, {poses} poses con malla; punta p90/pico {p90:.3f}/{peak:.3f}u/tick; '
              f'costura/raíz {seam:.3f}/{join:.3f}u, deriva {drift:.6f}u; placa/cabeza/capa exterior '
              f'{head:.3f}/{hat:.3f}u, paño/piernas {leg:.3f}u.', flush=True)
    table(root/'maniobra-forge.tsv', 'ranura cuadros poses punta_p90_u_tick punta_pico_u_tick '
          'costura_u raiz_u apoyo_u deriva_u placa_cabeza_u placa_capa_exterior_u pano_brazos_u pano_piernas_u', results)
    gallery(root, pictures, mod_version())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots', type=Path)
    main(parser.parse_args().shots)
