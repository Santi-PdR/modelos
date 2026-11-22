#!/usr/bin/env python3
"""Audit a continuous sprint → turn and crouch → stop → stand in Forge."""
import argparse
import csv
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
    # The first render can wait for the server's daylight packet, while
    # the script is still warming up. Require the start-of-run still and
    # explicit tick coverage within every measured part, not an idle prefix.
    assert 0 <= t[0] < 27 and t[-1] >= 109 and np.all(np.diff(t) >= 0), (
        slot, 'ruta incompleta', len(t), float(t[0]), float(t[-1]))
    # The second equip can inherit an airborne sample while the teleport
    # settles. The measurement starts on the established sprint at t=24.
    airborne = (data['ground'] != 1) | (data['air'] > 0) | (data['fall'] > 0) | (data['swim'] > 0)
    assert not np.any(airborne & (t >= 24)), (slot, 'no fue una maniobra en suelo seco', t[airborne].tolist()[:16])

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
    p90, peak = float(np.quantile(rate, .90)), float(rate.max())
    a = np.flatnonzero(use)[rate.argmax()]
    return len(t), p90, peak, t[a], t[a+1]-t[a], *(float(abs(data[k][a+1]-data[k][a])) for k in ('top', 'mid'))


def landmarks(data, stem, *, extended=False):
    visible = data[data['image'] != '-']
    assert len(visible) >= len(STILLS), (stem,'capturas incompletas')
    picked = []
    for at, _ in STILLS:
        shot = next(r for r in visible if at <= int(r['time']) <= at+2)
        t = int(shot['time'])
        assert shot['image'] == f'{stem}-{t:03d}.png', (stem,t,shot)
        picked.append(shot)
    extra = set(visible['time'].astype(int)) - {int(p['time']) for p in picked}
    assert not extra or extended and extra <= set(range(78,84)) | set(range(87,90)), (stem,extra)
    return picked


def fit(root, data, slot, rig, source, *, direction=1):
    stem = f'{"maniobra" if direction == 1 else "giro-inverso"}-{slot}'
    mesh = read_boxes(root / f'{stem}-cubos.tsv')
    sampled = data[data['fit'] == 1]
    ticks = sampled['time'].astype(int)
    assert list(ticks) == sorted(mesh) and len(mesh) >= 55, (slot, 'faltan cuadros de malla')
    held = sampled[(ticks >= 49) & (ticks <= 67)]
    assert len(held) >= 13 and (direction*held['yaw']).min() > 54.5 and held['pitch'].max() < -34.5, (stem, 'faltó el giro en el render real')
    assert abs(sampled['yaw'][0]) < .05 and abs(sampled['yaw'][-1]) < .05, (stem, 'faltó barrer la mirada')
    roots = np.array([name.endswith('_seg0') for name in rig.names])
    # The chain has a local render stroke, but original_dimensions above
    # the contact checks still requires the unscaled box for every link.
    trim = tuple(map(int, mod_version().split('.'))) >= (1, 67, 31)
    flex_plates = tuple(map(int, mod_version().split('.'))) >= (1, 67, 38)
    fixed = rig.rigid & ~np.array([hood_moves(name) or trim and name.startswith('v18_chain_')
                                 or flex_plates and name.startswith('v18_pad_') for name in rig.names])
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
    return (len(mesh), *joins, drift, *worst)


def gallery(root, pictures, version):
    w, h = 234, 202
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


def previous_rows(path):
    if path is None:
        return {}
    with path.open() as f:
        rows = {r['ranura']: r for r in csv.DictReader(f, delimiter='\t')}
    assert set(rows) == set(SLOTS), 'faltan ranuras del control .28'
    for slot, r in rows.items():
        recorded = timeline(read(path.parent/f'maniobra-{slot}.tsv'), slot)
        assert r['fuera_de_umbral'] == 'punta' and recorded[2] > 6
        np.testing.assert_allclose(recorded[1:3], [float(r[k]) for k in ('punta_p90_u_tick','punta_pico_u_tick')], atol=1e-6, rtol=0)
    return rows


def main(root, diagnostic=False, reference=None, extended=False):
    baseline = previous_rows(reference)
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo, 0.))
    source = defaultdict(list)
    for name, box in zip(rig.names, rig.place(matrices(geo)), strict=True):
        source[name].append(box)
    results, comparison, pictures, faults = [], [], {}, []
    for slot in SLOTS:
        data = read(root/f'maniobra-{slot}.tsv')
        count, p90, peak, tick, dt, top, mid = timeline(data, slot)
        poses, seam, join, back, drift, head, hat, arm, leg = fit(root, data, slot, rig, source)
        faults_here = []
        if p90 <= .2 or peak >= 6.:
            faults_here.append('punta')
        if drift >= .006 or min(seam - .038, join - .025, back - .018) <= 0:
            faults_here.append('costura/montura')
        if leg > .05:
            faults_here.append('piernas')
        if baseline:
            old = baseline[slot]
            old_p90, old_peak = (float(old[k]) for k in ('punta_p90_u_tick','punta_pico_u_tick'))
            t, floor = data['time'], data['crouch_floor']
            if (floor.max() < 40 or floor.max() > 49.50001 or (floor[(t < 50) | (t >= 66)] != 0).any()
                    or not ((data['sneak'] >= .999) & (floor > 8)).any() or np.any((floor > 0) & (data['top'] < floor-.36))):
                faults_here.append('retención del giro de la bisagra')
            if peak >= .75 * old_peak:
                faults_here.append('reducción del pico')
            if head > float(old['placa_cabeza_u']) + .06 or hat > float(old['placa_capa_exterior_u']) + .06:
                faults_here.append('holgura de hombrera')
            comparison.append((slot, *(f'{v:.6f}' for v in (old_p90, p90, old_peak, peak, 100*(1-peak/old_peak)))))
            print(f'{slot}: pico de punta .28 → candidata: {old_peak:.3f} → {peak:.3f}u/tick; '
                  f'retención máxima {floor.max():.2f}°, sin cambiar la mezcla de Shift.', flush=True)
        faults.extend(f'{slot}: {case}' for case in faults_here)
        result = (p90, peak, tick, dt, top, mid, seam, join, back, drift, head, hat, arm, leg)
        results.append((slot, count, poses, *(f'{v:.6f}' for v in result), ','.join(faults_here) or 'OK'))
        chosen = landmarks(data,f'maniobra-{slot}',extended=extended)
        pictures[slot] = [root/p['image'] for p in chosen]
        print(f'{slot}: {count} cuadros, {poses} poses con malla; punta p90/pico {p90:.3f}/{peak:.3f}u/tick; '
              f'pico en t={tick:.2f}, intervalo {dt:.3f}, bisagras Δ{top:.2f}/{mid:.2f}°; '
              f'costura/raíz {seam:.3f}/{join:.3f}u, deriva {drift:.6f}u; placa/cabeza/capa exterior '
              f'{head:.3f}/{hat:.3f}u, paño/piernas {leg:.3f}u.', flush=True)
    table(root/'maniobra-forge.tsv', 'ranura cuadros poses punta_p90_u_tick punta_pico_u_tick '
          'pico_t pico_delta_t pico_delta_top_deg pico_delta_mid_deg costura_u raiz_u apoyo_u deriva_u '
          'placa_cabeza_u placa_capa_exterior_u pano_brazos_u pano_piernas_u fuera_de_umbral', results)
    if baseline:
        table(root/'maniobra-comparacion.tsv', 'ranura p90_base_u_tick p90_u_tick pico_base_u_tick pico_u_tick reduccion_pico_pct', comparison)
    gallery(root, pictures, mod_version())
    if faults:
        message = 'Fuera de umbral: ' + '; '.join(faults)
        if not diagnostic:
            raise SystemExit(message)
        print(f'::warning title=Diagnóstico de maniobra::{message}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shots', type=Path)
    parser.add_argument('--diagnostico', action='store_true', help='Guardar las mediciones incluso si superan el umbral; no certifica la maniobra.')
    parser.add_argument('--reference', type=Path, help='TSV del diagnóstico .28 y sus trazas en el mismo directorio')
    parser.add_argument('--extended', action='store_true', help='La ruta registra también el retorno hasta reposo agachado.')
    args = parser.parse_args()
    main(args.shots, args.diagnostico, args.reference, args.extended)
