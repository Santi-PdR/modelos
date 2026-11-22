#!/usr/bin/env python3
"""Measure cape motion through real jumps and a ledge drop in the torso frame."""
import argparse
import base64
import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from cape_chain import LINKS
from cape_contact import lap, original_dimensions
from cape_fit import fixed_wearer_pose, hood_moves
from preview_cloth import ARMOR_GEO, load, matrices, mod_version
from verify_forge_postures import ACTOR, read_boxes
from verify_forge_walk import pairs, points, read
from verify_v1660 import WornModel, contacts

SLOTS = ('pecho', 'curios')
CASES = ('salto', 'salto-en-carrera', 'caida-del-borde')


@dataclass(frozen=True)
class Event:
    name: str
    start: int  # first rendered in-air sample
    land: int   # first rendered grounded sample


def events(data, slot):
    t, g, y = (data[c] for c in ('time', 'on_ground', 'height'))
    assert t[0] < 2 and t[-1] >= 169 and (np.diff(t) >= 0).all(), (slot, 'reloj roto')
    assert g[0] == g[-1] == 1 and set(g) == {0, 1}, (slot, 'ruta incompleta')
    start = np.flatnonzero(np.diff(g) < 0) + 1
    land = np.flatnonzero(np.diff(g) > 0) + 1
    assert len(start) == len(land) == len(CASES), (slot, 'hacen falta dos saltos y una caída', t[start], t[land])
    assert ((t[land] - t[start] > 9) & (t[land] - t[start] < 23)).all(), (slot, 'duración de vuelo', t[start], t[land])
    for i, (a, b) in enumerate(zip(start, land, strict=True)):
        if i < 2:
            assert 1.12 < y[a:b].max() < 1.40 and abs(y[b + 4]) < .05, (slot, 'el salto no fue a nivel', i)
        else:
            assert y[a] > -.2 and y[b+4] < -6.5 and data['vertical'][a:b].min() < -.64, (slot, 'no cayó del borde')
    assert np.max(data['speed'][start[0]:land[0]]) < .02 and data['speed'][start[1]] > .23, (
        slot, 'saltos quieto y en carrera no diferenciados')
    return [Event(name, a, b) for name, a, b in zip(CASES, start, land, strict=True)]


def metrics(data, event, slot):
    t = data['time']
    takeoff, touchdown = t[event.start], t[event.land]
    # Include easing into the motion and the first grounded recovery. Ignore
    # camera/world travel and samples with a skipped tick or tiny Δt.
    sample = pairs(t, takeoff - 1, touchdown + 8)
    settling = pairs(t, touchdown - 1.5, touchdown + 8)
    midair = slice(event.start, event.land)
    assert sample.sum() >= 26 and settling.sum() >= 11, (slot, event.name, 'faltan fracciones')
    dt = np.diff(t)
    swing = np.abs(np.diff(np.c_[data['top'], data['mid']], axis=0))
    hem = np.linalg.norm(np.diff(points(data, 'tip'), axis=0), axis=1)
    return dict(frames=int(sample.sum()), airtime=touchdown - takeoff,
                air=data['air'][midair].max(), fall=data['fall'][midair].max(), top=data['top'][midair].max(),
                hinge=(swing[sample, 0] / dt[sample]).max(), middle=(swing[sample, 1] / dt[sample]).max(),
                hem=(hem[sample] / dt[sample]).max(), landing=(hem[settling] / dt[settling]).max())


def landing_response(data, spans, slot):
    names = data.dtype.names
    assert 'aterrizaje_deg' in names and 'aterrizaje_eco' in names, (slot, 'faltan columnas de aterrizaje')
    pitch, heat, time = data['aterrizaje_deg'], data['aterrizaje_eco'], data['time']
    assert np.isfinite(pitch).all() and np.isfinite(heat).all(), (slot, 'impulso inválido')
    assert pitch.min() >= 0 and pitch.max() <= 5.5 + 1e-6 and heat.min() >= 0 and heat.max() <= 1 + 1e-6, (
        slot, 'envolvente del aterrizaje excedida', pitch.min(), pitch.max(), heat.min(), heat.max())
    for event in spans:
        touchdown = time[event.land]
        window = (time >= touchdown) & (time <= touchdown + 12)
        active = np.flatnonzero(window & (pitch > .05))
        lit = np.flatnonzero(window & (heat > .01))
        assert len(active) and len(lit), (slot, event.name, 'no se detectó un aterrizaje medible')
        pitch_age, light_age = time[active[0]] - touchdown, time[lit[0]] - touchdown
        assert pitch_age <= .8 and light_age - pitch_age >= 1.2, (
            slot, event.name, 'la luz no siguió al movimiento', pitch_age, light_age)
        assert pitch[window].max() > 1.0 and heat[window].max() > .15, (
            slot, event.name, 'respuesta de contacto demasiado débil', pitch[window].max(), heat[window].max())
        airborne = (time >= time[event.start]) & (time < touchdown)
        assert np.max(np.abs(pitch[airborne])) < 1e-7 and np.max(np.abs(heat[airborne])) < 1e-7, (
            slot, event.name, 'el eco apareció antes del contacto')
        rest = (time >= touchdown + 11) & (time <= touchdown + 13)
        assert rest.any() and np.max(np.abs(pitch[rest])) < .01 and np.max(np.abs(heat[rest])) < .01, (
            slot, event.name, 'el dobladillo no regresó a reposo')
        print(f'{slot} / {event.name}: aterrizaje {pitch_age:.2f} tics; luz +{light_age-pitch_age:.2f}; '
              f'picos {pitch[window].max():.2f}°/{heat[window].max():.2f}.', flush=True)


def report(root, slot, reference=False):
    data = read(root / f'saltos-{slot}.tsv')
    assert all(np.isfinite(data[c]).all() for c in data.dtype.names), (slot, 'muestra inválida')
    assert np.ptp(data['collar_z']) < .025, (slot, 'el asiento se movió en el salto')
    expected = data['leg_pos'] * np.float32(.6662) / (2 * np.pi)
    assert np.max(np.abs(data['stride'] - expected)) < 1e-5, (slot, 'reinicio de fase')
    spans = events(data, slot)
    if not reference:
        landing_response(data, spans, slot)
    result = {}
    for span in spans:
        row = metrics(data, span, slot)
        result[span.name] = row
        print(f'{slot} / {span.name}: {row["air"]:.1%} de AIR; {row["fall"]:.1%} de FALL; '
              f'ángulo superior {row["top"]:.2f}°; picos de bisagras {row["hinge"]:.2f}/{row["middle"]:.2f}°/tick, '
              f'punta {row["hem"]:.3f}u/tick (al aterrizar {row["landing"]:.3f}u/tick); {row["frames"]} pares.', flush=True)
    if reference:
        rest = result['salto']
        assert rest['air'] >= .96 and rest['top'] > 40 and rest['hinge'] > 14, (
            slot, 'no se reprodujo el latigazo de planeo en un salto quieto', rest)
    return data, spans, result


def verdict(data, spans, now, before, slot):
    assert data['air'].max() < 1e-8, (slot, 'sigue usando el clip de planeo en el suelo o el salto')
    assert data['fall'].min() >= 0 and data['fall'].max() <= 1, (slot, 'peso inválido')
    for event in spans[:2]:
        air = data[event.start:event.land]
        apex = (np.abs(air['vertical']) < .09) & (air['height'] > 1.)
        assert apex.any() and np.all((air['fall'][apex] > .16) & (air['fall'][apex] < .32)), (
            slot, event.name, 'el paño no respeta el ápice')
        assert .70 < now[event.name]['fall'] <= 1, (slot, event.name, 'se perdió la apertura al bajar')
    rest = now['salto']
    assert rest['top'] < 24 and rest['hinge'] < 8 and rest['hem'] < 5, (slot, 'latigazo en el salto quieto', rest)
    assert now['caida-del-borde']['fall'] > .93, (slot, 'se perdió la caída sostenida')
    for e in spans:
        touchdown = data['time'][e.land]
        recovering = (data['time'] >= touchdown) & (data['time'] < touchdown + 2)
        settled = (data['time'] >= touchdown + 7) & (data['time'] < touchdown + 9)
        assert np.all(data['fall'][recovering] > .35) and settled.any() and data['fall'][settled].max() < .005, (
            slot, e.name, 'el paño no se asienta progresivamente')
    for e in spans[1:]:
        grounded = (data['time'] >= data['time'][e.land] + 8) & (data['time'] < data['time'][e.land] + 11)
        assert grounded.any() and data['run'][grounded].max() > .94, (slot, e.name, 'no retomó la carrera')
    if before:
        assert rest['hinge'] < .52 * before['salto']['hinge'] and rest['hem'] < .75 * before['salto']['hem'], (
            slot, 'el salto normal no mejoró con respecto al JAR anterior', rest, before['salto'])
        for e in spans[1:]:
            a, b = now[e.name], before[e.name]
            assert a['hinge'] < .60 * b['hinge'] and a['landing'] < .90 * b['landing'], (
                slot, e.name, 'sigue el tirón en el salto con zancada o al aterrizar del borde', a, b)


def fit(root, slot, data, spans, rig, source):
    boxes = read_boxes(root / f'saltos-{slot}-cubos.tsv')
    chain_path = root/f'saltos-{slot}-cadena-fija.tsv'
    chain_base = read_boxes(chain_path) if chain_path.is_file() else None
    if chain_base is not None:
        assert set(chain_base) == set(boxes) and all(set(g) == set(LINKS) for g in chain_base.values()), slot
    chain_indices = [rig.names.index(n) for n in LINKS]
    ticks = np.array(sorted(boxes))
    for event in spans:
        a, b = (int(data['time'][i]) for i in (event.start, event.land))
        assert ((ticks >= a) & (ticks < b)).sum() >= 4 and ((ticks >= b) & (ticks <= b + 6)).sum() >= 2, (
            slot, event.name, 'faltan cubos de vuelo o de aterrizaje', a, b, ticks)
    roots = np.array([name.endswith('_seg0') for name in rig.names])
    flex_plates = tuple(map(int, mod_version().split('.'))) >= (1, 67, 38)
    fixed = rig.rigid & ~np.array([hood_moves(name) or flex_plates and name.startswith('v18_pad_') for name in rig.names])
    min_fit = np.full(3, np.inf)
    leg_hit, arm_hit, drift = 0., 0., 0.
    leg_detail = None
    cloth_indices = np.flatnonzero(rig.cloth)
    cloth_names = np.asarray(rig.names)[cloth_indices]
    limb_names = ('left_arm', 'right_arm', 'left_leg', 'right_leg')
    first = None
    for tick, group in boxes.items():
        label = (slot, tick)
        assert set(group) == set(source) | set(ACTOR), (label, 'cajas de la pose incompletas')
        assert original_dimensions(group, source, label) == len(rig.names)
        assert all(len(group[name]) == 1 for name in ACTOR), label
        live = np.array([group[name].pop(0) for name in rig.names])
        static = live.copy()
        if chain_base is not None:
            static[chain_indices] = np.concatenate([chain_base[tick][n] for n in LINKS])
        if first is None:
            first = static[fixed]
        drift = max(drift, np.linalg.norm(static[fixed] - first, axis=2).max())
        torso = np.array(group['body'])
        limbs = np.array([group[name][0] for name in limb_names])
        hit = contacts(live[None, rig.cloth], limbs[None])[0]
        arm_hit = max(arm_hit, -hit[:2].min())
        leg_contacts = hit[2:]
        worst = np.unravel_index(int(np.argmin(leg_contacts)), leg_contacts.shape)
        current_leg_hit = max(0., -float(leg_contacts[worst]))
        if current_leg_hit > leg_hit:
            leg_hit = current_leg_hit
            limb_index, cloth_index = worst
            garment_index = int(cloth_indices[cloth_index])
            garment_name = str(cloth_names[cloth_index])
            local_cube = int(np.count_nonzero(np.asarray(rig.names)[:garment_index] == garment_name))
            leg_detail = {
                'tick': int(tick),
                'limb': limb_names[limb_index + 2],
                'cape_bone': garment_name,
                'cube_in_bone': local_cube,
                'rig_cube_index': garment_index,
                'signed_sat_gap_u': float(leg_contacts[worst]),
            }
        min_fit = np.minimum(min_fit, [*rig.joins(live), lap(live[roots], torso)])
    assert (min_fit > [.038, .025, .018]).all() and drift < .006, (slot, 'deriva o costura en salto', min_fit, drift)
    # Keep the measured row even when leg contact exceeds the gate. The main
    # routine checks the limit only after both equipment slots are audited and
    # the TSV/gallery artifacts have been written.
    print(f'{slot}: {len(boxes)} poses de vuelo y suelo; costura/raíz/apoyo {min_fit[0]:.3f}/{min_fit[1]:.3f}/{min_fit[2]:.3f}u; '
          f'deriva {drift:.6f}u; cruces máximos en brazos/piernas {arm_hit:.4f}/{leg_hit:.4f}u.', flush=True)
    row = [slot, len(boxes), *(f'{v:.6f}' for v in (*min_fit, drift, arm_hit, leg_hit))]
    return row, leg_hit, leg_detail


def landing_geometry(root, slot, data, spans):
    live = read_boxes(root / f'saltos-{slot}-cubos.tsv')
    control_path = root / f'saltos-{slot}-dobladillo-fijo.tsv'
    assert control_path.is_file(), (slot, 'falta el control de bisagra inferior')
    control = read_boxes(control_path)
    assert control and all(tick in live for tick in control), (slot, 'control de dobladillo sin pose viva')
    expected_parts = set(control[next(iter(control))])
    assert all(set(parts) == expected_parts for parts in control.values()), (slot, 'control incompleto')
    differences = {}
    for tick, parts in control.items():
        assert set(parts) <= set(live[tick]), (slot, tick, 'control contiene huesos ajenos')
        rows = []
        for name, boxes in parts.items():
            actual = live[tick][name]
            assert len(actual) == len(boxes), (slot, tick, name, 'el control perdió cubos')
            rows.extend(np.max(np.abs(a - b)) for a, b in zip(actual, boxes, strict=True))
        differences[tick] = max(rows, default=0.)
    for event in spans:
        touchdown_time = float(data['time'][event.land])
        touchdown_tick = int(np.floor(touchdown_time + 1e-6))
        before = [difference for tick, difference in differences.items() if touchdown_tick - 3 <= tick < touchdown_tick]
        assert before and max(before) < .002, (slot, event.name, 'la bisagra movió el paño antes del contacto', before)
        ticks = np.array(sorted(t for t in differences if touchdown_tick <= t <= touchdown_tick + 13))
        assert len(ticks) >= 3, (slot, event.name, 'faltan poses de la bisagra')
        values = np.array([differences[int(t)] for t in ticks])
        assert values.max() > .08, (slot, event.name, 'la bisagra no movió la geometría del dobladillo', values)
        late = values[ticks >= touchdown_tick + 10]
        assert len(late) and late.max() < .015, (slot, event.name, 'el control de dobladillo no cerró', ticks, values)
        print(f'{slot} / {event.name}: A/B de bisagra en {len(ticks)} poses; máximo {values.max():.3f}u; '
              f'residuo tardío {late.max():.5f}u.', flush=True)


def motion_gallery(root):
    """Expose a compact Forge contact-sheet in Actions annotations as well as artifacts."""
    cw, ch = 288, 330
    margin, gap, heading = 12, 8, 42
    sheet = Image.new('RGB', (margin*2 + 2*cw + gap, heading + 2*(ch + 32)), '#17121d')
    pen = ImageDraw.Draw(sheet)
    pen.text((margin, 10), 'ALEX / SALTOS REALES EN FORGE · VISTA Y CONTACTO', fill='#f8eaf2')
    for col, title in enumerate(('ÁPICE', 'PRIMER CONTACTO')):
        pen.text((margin + col*(cw+gap), 28), title, fill='#e8c9e1')
    for row, slot in enumerate(SLOTS):
        y = heading + row*(ch + 32)
        pen.text((margin, y + 2), slot.upper(), fill='#f8eaf2')
        for col, phase in enumerate(('apice', 'contacto')):
            path = root / f'saltos-{slot}-{phase}.png'
            with Image.open(path) as photo:
                w, h = photo.size
                width = min(w, round(h * .62))
                crop = photo.crop(((w-width)//2, 0, (w+width)//2, h)).convert('RGB')
                crop = ImageOps.fit(crop, (cw, ch), Image.Resampling.LANCZOS)
            sheet.paste(crop, (margin + col*(cw+gap), y + 22))
    sheet.save(root / 'saltos-forge.jpg', quality=90, optimize=True)
    payload = None
    width, quality = 560, 68
    while width >= 96 and payload is None:
        preview = sheet.resize((width, round(width * sheet.height / sheet.width)), Image.Resampling.LANCZOS)
        for candidate_quality in (quality, max(12, quality - 12), max(8, quality - 24)):
            data = io.BytesIO()
            preview.save(data, 'JPEG', quality=candidate_quality, optimize=True)
            if len(data.getvalue()) <= 12_600:
                payload = data.getvalue()
                break
        width = round(width * .78)
        quality = max(24, quality - 7)
    if payload is None:
        raise AssertionError('no se pudo comprimir la lámina de saltos para Actions')
    encoded = base64.b64encode(payload).decode('ascii')
    # GitHub truncates annotation messages at 4096 chars; leave room for framing.
    chunk_size = 3_500
    for offset in range(0, len(encoded), chunk_size):
        index = offset // chunk_size
        print(f'::notice title=Saltos Forge galeria jpg {index:02}::{encoded[offset:offset+chunk_size]}')


def save(root, reports, fit_rows=()):
    fields = ('frames', 'airtime', 'air', 'fall', 'top', 'hinge', 'middle', 'hem', 'landing')
    with (root / 'saltos-forge.tsv').open('w', newline='') as f:
        out = csv.writer(f, delimiter='\t', lineterminator='\n')
        out.writerow(['version', 'ranura', 'prueba', *fields])
        for (version, slot), variants in reports.items():
            for name, row in variants.items():
                out.writerow([version, slot, name, row['frames'], *(f'{row[key]:.5f}' for key in fields[1:])])
    if fit_rows:
        with (root / 'costuras-saltos-forge.tsv').open('w', newline='') as f:
            out = csv.writer(f, delimiter='\t', lineterminator='\n')
            out.writerow(['ranura', 'cuadros', 'costura_u', 'raiz_u', 'apoyo_u', 'deriva_u', 'pico_brazo_u', 'pico_pierna_u'])
            out.writerows(fit_rows)


def gallery(root, baseline, curves, version):
    canvas = Image.new('RGB', (1400, 728), '#15111d')
    pen = ImageDraw.Draw(canvas)
    title = ImageFont.truetype('DejaVuSans-Bold.ttf', 30)
    label = ImageFont.truetype('DejaVuSans.ttf', 18)
    small = ImageFont.truetype('DejaVuSans.ttf', 14)
    white, quiet, before, after = '#f6ecf5', '#cebbd6', '#f4a4ca', '#97e2da'
    pen.text((24, 19), 'El manto en un salto normal', fill=white, font=title)
    pen.text((24, 59), 'Alex · capturas de Forge en tercera persona · v1.67.24 frente a ' + version, fill=quiet, font=label)
    for x, heading in ((24, 'EN EL ÁPICE'), (472, 'AL TOCAR SUELO'), (928, 'BISAGRA SUPERIOR RESPECTO DEL TORSO')):
        pen.text((x, 104), heading, fill=quiet, font=small)
    for j, slot in enumerate(SLOTS):
        y = 159 + 270*j
        pen.text((24, y-29), slot.upper(), fill=white, font=label)
        for k, pose in enumerate(('apice', 'contacto')):
            for i, (shots, tag, color) in enumerate(((baseline, 'v1.67.24', before), (root, version, after))):
                x = 24 + 448*k + 214*i
                with Image.open(shots / f'saltos-{slot}-{pose}.png') as photo:
                    crop = ImageOps.fit(photo.convert('RGB'), (204, 208), Image.Resampling.LANCZOS)
                canvas.paste(crop, (x, y))
                pen.text((x,y+216), tag, fill=color, font=small)
        x0, y0, w, h = 978, y+16, 391, 158
        for v in (0, 15, 30, 45):
            s = y0+h-v/50*h
            pen.line((x0,s,x0+w,s), fill='#3c3247', width=1)
            pen.text((x0-36,s-9), f'{v}°', fill=quiet, font=small)
        for t in (0, 5, 10, 15, 20):
            s = x0+(t+1)/22*w
            pen.text((s,y0+h+9), str(t), fill=quiet, font=small, anchor='mt')
        for (data, event), color in zip(curves[slot], (before, after), strict=True):
            t = data['time'] - np.floor(data['time'][event.start])
            visible = (t >= -1) & (t <= 21)
            xx = x0+(t+1)/22*w
            yy = y0+h-np.clip(data['top'],0,50)/50*h
            pen.line(list(zip(xx[visible], yy[visible], strict=True)), fill=color, width=3, joint='curve')
            x, z = xx[event.land], yy[event.land]
            pen.ellipse((x-4,z-4,x+4,z+4), fill=color)
        pen.text((x0, y0+h+33), 'Ticks desde el despegue  ·  ● primer cuadro en suelo', fill=quiet, font=small)
    pen.text((24, 697), 'La gráfica no incluye el desplazamiento de la cámara ni del jugador. Son dos recorridos independientes.',
             fill=quiet, font=small)
    canvas.save(root / 'comparacion-saltos-forge.jpg', quality=94, optimize=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('shots', type=Path)
    ap.add_argument('--baseline-shots', type=Path)
    args = ap.parse_args()
    summary, curves, fit_rows, leg_hits = {}, {}, [], []
    version = 'v' + mod_version()
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo, 0., slim=True))
    source = defaultdict(list)
    for name, cube in zip(rig.names, rig.place(matrices(geo)), strict=True):
        source[name].append(cube)
    for slot in SLOTS:
        before = None
        if args.baseline_shots:
            ref, old_events, before = report(args.baseline_shots, slot, reference=True)
            summary['v1.67.24', slot] = before
        data, spans, result = report(args.shots, slot)
        verdict(data, spans, result, before, slot)
        summary[version, slot] = result
        fit_row, leg_hit, leg_detail = fit(args.shots, slot, data, spans, rig, source)
        fit_rows.append(fit_row)
        leg_hits.append((slot, leg_hit, leg_detail))
        landing_geometry(args.shots, slot, data, spans)
        if args.baseline_shots:
            curves[slot] = ((ref, old_events[0]), (data, spans[0]))
    save(args.shots, summary, fit_rows)
    motion_gallery(args.shots)
    if args.baseline_shots:
        gallery(args.shots, args.baseline_shots, curves, version)
    failures = [(slot, round(hit, 6), detail) for slot, hit, detail in leg_hits if hit >= .05]
    if failures:
        raise AssertionError(('el nuevo recorrido del paño alcanza las piernas; máximo por ranura '
                              '(u, tick, pierna, cubo de manto y separación firmada)', failures))
