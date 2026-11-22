#!/usr/bin/env python3
"""Gate the live two-way return through neutral and standing against the verified .31."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_chain import LINKS
from cape_fit import fixed_wearer_pose, nape_piece, nape_shifts, profile
from preview_cloth import ARMOR_GEO, load, matrices, mod_version
from verify_forge_combined import SLOTS, fit, timeline
from verify_forge_crown import head_roof, sewn
from verify_forge_gaits import table, text
from verify_forge_nape import BAND, CHAIN, FRONT, Capture, chain_seam, cut, paired
from verify_forge_nape_return import TRACKS, frames, measure
from verify_forge_postures import read_boxes
from verify_forge_walk import read
from verify_v1660 import WornModel

TRIM = (CHAIN, BAND, FRONT)
PATCH = mod_version().rsplit('.', 1)[-1]
MESH_COLS = (f'ranura sentido tick tiempo yaw pitch peso_shift seccion_misma_pose_31_u2 seccion_{PATCH}_u2 '
             f'techo_{PATCH}_u costura_u tira_u avance_ajuste_u_tick salto_pose_u')
COLOR_COLS = (f'ranura sentido tick tiempo_31 tiempo_{PATCH} yaw_31 yaw_{PATCH} granate_31 granate_{PATCH} pelo_recuperado '
              f'granate_nuevo lado_granate_31 lado_granate_{PATCH} lado_pelo_recuperado lado_granate_nuevo')


# Vanilla switches the torso between two discrete poses. The archived .35
# has a 1.631327u adjustment at that switch in both slots and directions.
MAX_POSE_STEP = 1.65
MAX_ADJUSTMENT_SPEED = 2.3


def adjustment_motion(previous, sample):
    if previous is None:
        return 0., 0.
    dt = sample[0] - previous[0]
    assert np.isfinite(dt) and dt > 0, ('invalid Forge clock', previous[0], sample[0])
    delta = np.linalg.norm(sample[2] - previous[2], axis=1).max()
    # A pose step has magnitude, not a velocity: the interval between two
    # render samples around it depends on their unrelated partial ticks.
    return (0., delta) if sample[1] != previous[1] else (delta/dt, 0.)


def draw_metrics(root, reference, slot, direction, stem, rig, source, faults):
    trace = read(root/f'{stem}.tsv')
    _, _, peak, *_ = timeline(trace, stem)
    poses, seam, join, back, drift, head, hat, arm, leg = fit(root, trace, slot, rig, source, direction=direction)
    assert peak < 3.75 and min(seam-.038, join-.025, back-.018) > 0 and drift < .006 and leg <= .05, (stem,peak,seam,join,back,drift,leg)
    print(f'{stem}: {poses} poses con dimensiones originales; pico de punta {peak:.3f}u/tick, costura {seam:.3f}u, raíz {join:.3f}u, deriva {drift:.6f}u.', flush=True)
    model = read_boxes(root/f'{stem}-cubos.tsv')
    chain_path = root/f'{stem}-cadena-fija.tsv'
    chain_base = read_boxes(chain_path) if chain_path.is_file() else None
    if chain_base is not None:
        assert set(chain_base) == set(model) and all(set(g) == set(LINKS) for g in chain_base.values()), stem
    anchor = read_boxes(reference/f'{stem}-cubos.tsv')
    first = anchor[min(anchor)]
    data = {int(p['time']):p for p in trace[trace['fit'] == 1]}
    neighborhood = [t for t in sorted(model) if 80 <= t <= 91]
    assert len(neighborhood) >= 9 and any(87 <= t <= 89 for t in neighborhood), (stem,'faltan poses hasta el reposo agachado',neighborhood)
    step = profile()['bodyAngle']
    previous = None
    rows = []
    for tick, groups in sorted(model.items()):
        p = data[tick]
        aim = (-p['pitch'],p['yaw'],step if p['crouching'] else 0.)
        current = np.asarray(nape_shifts(*aim,p['sneak']))
        old = np.asarray(nape_shifts(*aim,legacy=True))
        # Isolate just the rigid stroke in this exact live pose. This is a
        # geometric counterfactual, not a claimed screenshot of .31.
        rigid = groups if chain_base is None else {**groups, **chain_base[tick]}
        control = {n: np.asarray(g) - current[k] + old[k] if (k := nape_piece(n)) is not None else g for n,g in rigid.items()}
        for n,g in rigid.items():
            if n.startswith(CHAIN):
                np.testing.assert_allclose(g-current[0],first[n],atol=.005,rtol=0,err_msg=f'{stem}/{tick}/{n}: cambio ajeno al ajuste')
        cut0, cut1 = cut(control,TRIM), cut(groups,TRIM)
        height, areas = head_roof(groups)
        sewn_edge, chain = sewn(groups), chain_seam(groups)
        sample = p['time'], p['crouching'], current
        rate, jump = adjustment_motion(previous, sample)
        previous = sample
        row = (slot,direction,tick,p['time'],p['yaw'],p['pitch'],p['sneak'],cut0,cut1,height,sewn_edge,chain,rate,jump)
        rows.append(row)
        if min(sewn_edge-.14,chain-.15) <= 0:
            faults.append((stem,tick,'unión del cuello o de la tira',round(sewn_edge,3),round(chain,3)))
        if not (rate <= MAX_ADJUSTMENT_SPEED and jump <= MAX_POSE_STEP):
            faults.append((stem,tick,'ajuste de la nuca: velocidad y salto de pose',round(rate,3),round(jump,3)))
        if 58 <= tick <= 91 and (height >= -.04 or sum(areas.values()) >= .05):
            faults.append((stem,tick,'cruce en la coronilla',round(height,3),round(sum(areas.values()),3)))
        if tick in neighborhood and (cut0 <= 5 or cut1 > 1.0):
            faults.append((stem,tick,'corte residual al centrar la cabeza',round(cut0,3),round(cut1,3)))
        if tick >= 94 and cut1 > .05:
            faults.append((stem,tick,'el ajuste cruza al ponerse de pie',round(cut1,3)))
    late = np.array([r[7:9] for r in rows if r[2] in neighborhood])
    print(f'{stem}: sección media t80–91 (misma pose) {late.mean(0)[0]:.3f} → {late.mean(0)[1]:.3f}u²; '
          f'unión tira mínima {min(r[11] for r in rows):.3f}u, velocidad del ajuste {max(r[12] for r in rows):.3f}u/tick, '
          f'salto al cambiar de pose {max(r[13] for r in rows):.3f}u.',flush=True)
    return rows


def color_metrics(root, ref, crops, track, slot, direction, faults):
    stem = f'{track}-{slot}'
    with (ref/f'{stem}-capturas.tsv').open() as file:
        old = {int(p['tick']): Capture(ref,p) for p in csv.DictReader(file,delimiter='\t')}
    live = frames(root,crops,track,slot,direction,neutral=True)
    a = {int(p['time']):p for p in read(ref/f'{stem}.tsv') if p['image'] != '-'}
    paired_ticks = sorted(old.keys() & live.keys())
    late_ticks = [t for t in paired_ticks if 79 <= t <= 83]
    neutral = [t for t in live if 87 <= t <= 89]
    assert len(late_ticks) >= 4 and max(late_ticks) == 83 and any(63 <= t <= 65 for t in paired_ticks) \
        and 77 in paired_ticks and neutral, (stem,paired_ticks,neutral)
    rows = []
    for tick in paired_ticks:
        b, cap, _ = live[tick]
        p = a[tick]
        paired(p,b)
        rear = measure(old[tick],cap,0)
        sides = [1 if c.eye[0] > 1 else -1 if c.eye[0] < 0 else 0 for c in (old[tick],cap)]
        if tick >= 77:
            assert sides == [direction]*2, (stem,tick,sides)
        side = measure(old[tick],cap,sides[0]) if sides[0] == sides[1] and sides[0] else ('-',)*4
        if side[0] != '-' and (side[1] > side[0]+220 or side[3] > 220):
            faults.append((stem,tick,'el granate se trasladó al lateral',side))
        if tick <= 77 and (direction == 1 or tick <= 65) and rear[1] > rear[0]+100:
            faults.append((stem,tick,'retroceso en el giro ya ajustado',rear))
        if tick == 77 and direction == -1 and not (rear[1] < .7*rear[0] and rear[2] > .25*rear[0]):
            faults.append((stem,tick,'no mejoró la frenada inversa',rear))
        rows.append((slot,direction,tick,p['time'],b['time'],p['yaw'],b['yaw'],*rear,*side))
    score = np.sum([r[7:11] for r in rows if r[2] in late_ticks],axis=0)
    if score[1] >= .50*score[0] or score[2] <= .35*score[0] or score[3] >= 700:
        faults.append((stem,'pelo al regresar',score.tolist()))
    for tick in neutral:
        p,c,_ = live[tick]
        cloth,hair = c.sample()
        if cloth.sum() > 700 or hair.sum() < .65*len(hair):
            faults.append((stem,tick,'reposo agachado con mancha en la nuca',int(cloth.sum()),int(hair.sum())))
        rows.append((slot,direction,tick,'-',p['time'],'-',p['yaw'],'-',int(cloth.sum()),'-','-','-','-','-','-'))
    print(f'{stem}: t79–83, {len(late_ticks)} pares: granate {score[0]} → {score[1]}, pelo recuperado {score[2]}, granate nuevo {score[3]}; '
          f'reposo agachado {neutral}.',flush=True)
    keys = (77,80 if 80 in late_ticks else late_ticks[0],83)
    return rows, [(f't{t}',old[t],live[t][1]) for t in keys] + [(f't{neutral[-1]} · centro',None,live[neutral[-1]][1])]


def gallery(path, slot, tracks):
    w,h = 235,201
    im = Image.new('RGB',(24+4*(w+6),96+len(tracks[0])*(h+28)), '#17121d')
    pen = ImageDraw.Draw(im)
    text(pen,(12,8),f'Alex · freno y retorno · {slot}',26,bold=True)
    text(pen,(12,45),'Forge, mismo recorrido. En el centro: toma nueva y comparación geométrica.',16,'#edc4db')
    for i, track in enumerate(tracks):
        for j,(t,old,new) in enumerate(track):
            x,y = 12+i*2*(w+6),91+j*(h+28)
            angle = '+55°' if i == 0 else '−55°'
            pair = f'.31 / .{PATCH}' if old else f'.{PATCH}'
            text(pen,(x,y-20),f'{angle} · {t} · {pair}',15,bold=True)
            for k,c in enumerate((old,new)):
                if c is not None:
                    with Image.open(c.path) as p:
                        im.paste(p.resize((w,h),Image.Resampling.LANCZOS),(x+k*(w+6),y))
    im.save(path,quality=95,optimize=True)


def verify(root, reference, out, crops):
    out.mkdir(parents=True,exist_ok=True)
    crops.mkdir(parents=True,exist_ok=True)
    geo = load(ARMOR_GEO)
    rig = WornModel(fixed_wearer_pose(geo,0.))
    source = defaultdict(list)
    for name, box in zip(rig.names,rig.place(matrices(geo)),strict=True):
        source[name].append(box)
    geometry, color, faults = [], [], []
    for slot in SLOTS:
        photos = []
        for track,direction in TRACKS:
            geometry.extend(draw_metrics(root,reference,slot,direction,f'{track}-{slot}',rig,source,faults))
            rows, frames_here = color_metrics(root,reference,crops,track,slot,direction,faults)
            color.extend(rows)
            photos.append(frames_here)
        gallery(out/f'retorno-{slot}.jpg',slot,photos)
    fmt = lambda rows: [[f'{x:.6f}' if isinstance(x,(float,np.floating)) else x for x in row] for row in rows]
    table(out/'retorno-malla.tsv',MESH_COLS,fmt(geometry))
    table(out/'retorno.tsv',COLOR_COLS,fmt(color))
    assert not faults, faults


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('shots','reference','out','crops'):
        ap.add_argument(name,type=Path)
    a = ap.parse_args()
    verify(a.shots,a.reference,a.out,a.crops)
