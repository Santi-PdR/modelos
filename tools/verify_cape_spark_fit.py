#!/usr/bin/env python3
"""Compare Java's birth points to the authored ribbons (software diagnostic, not Forge)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cape_animation_pipeline as A
import cape_bloom as B
import cape_tracks as T
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label

SCALE = .9375  # vanilla player render size
FEET = (float(np.float32(1.501)) - 1.5) * SCALE


def root(swimming):
    shift = np.array([0, FEET - swimming, .3 * swimming]) * 16
    return P.R('x', -90) @ P.T(shift) @ np.diag([SCALE, SCALE, SCALE, 1])


def measure(geo, clip, swimming, data):
    # Probe jitter extrema and centers against the ribbons across the clip.
    # Sampling faces slightly overstates the distance, even if a point is on the mesh.
    hidden = {b['name'] for b in geo['bones'] if not b['name'].startswith('v17_ribbon_')}
    track, transform = T.prepare_clip(clip), root(swimming)
    u = np.linspace(0, 1, 5)[:, None, None]
    v = np.linspace(0, 1, 5)[None, :, None]
    results = []
    for f in np.linspace(0, 1, 25):
        posed = P.pose_at(geo, track, clip['animation_length'] * f)
        faces = P.collect(posed, hidden)
        points = np.concatenate([(q[0] + u*(q[1]-q[0]) + v*(q[3]-q[0])).reshape(-1, 3) for q, _, _ in faces])
        points = (points @ transform[:3, :3].T + transform[:3, 3]) / 16
        distance = np.linalg.norm(data[:, :, None, :] - points, axis=-1).min(axis=-1)
        results.append(distance)
    return np.array(results)


def plate(output, geo, poses, results):
    # An orthographic source-data view, deliberately without wing models or a
    # simulated current. Outline symbols mark possible births, not four extra particles.
    sheet = Image.new('RGB', (1090, 910), BG)
    draw = ImageDraw.Draw(sheet)
    label(draw, (30, 24), 'MANTLE OF THE BLIGHT STAR   /   v1.67.2', 19, ROSE, bold=True)
    label(draw, (28, 54), 'Las brasas siguen al paño', 47, bold=True)
    label(draw, (31, 117), 'Mismo manto y misma pose. Sólo cambia el origen de las brasas.', 20, DIM)
    label(draw, (31, 163), 'ANTES   ·   HITBOX VERTICAL', 18, DIM, bold=True)
    label(draw, (557, 163), 'AHORA   ·   POSTURA + CAÍDA DEL PAÑO', 18, ROSE, bold=True)
    for i, (swimming, title, clip, centers) in enumerate(poses):
        phase = .27
        posed = P.pose_at(geo, T.prepare_clip(clip), clip['animation_length'] * phase)
        transform = root(swimming)
        # Insert a parent with exactly the same affine projection as the points.
        name = 'diagnostic_player_pose'
        posed['bones'] = [dict(name=name, pivot=[0,0,0], scale=[SCALE]*3, rotation=[90,0,0],
                               offset=transform[:3,3].tolist())] + [dict(b, parent=b.get('parent') or name) for b in posed['bones']]
        bounds = P.effective_hidden(posed)
        yaw, pitch = (-64, 25) if not swimming else (-65, 25)
        size = 503
        view = (P.R('x', pitch) @ P.R('y', yaw))[:3, :3]
        body = [(np.array(o) + P.CORNERS * s) @ transform[:3,:3].T + transform[:3,3]
                for o, s, _ in P.MANNEQUIN_BOXES]
        verts = np.concatenate([p for p, _, _ in P.collect(posed, bounds)] + body
                               + [centers[:, [0, 2]].reshape(-1, 3) * 16])
        vv = verts @ view.T
        cx, cy = (vv.min(axis=0) + vv.max(axis=0))[:2] / 2
        scale = min(13.0, 450 / np.ptp(vv[:, 0]), 196 / np.ptp(vv[:, 1]))
        camera = (cx, cy, scale)
        canvas = P.render(posed, P.ARMOR_TEX, bounds, yaw=yaw, pitch=pitch, size=size, frame=camera,
                          bg=(29,23,37), mannequin=True, mannequin_pose=[transform]*6,
                          ambient=.90, emission=B.CORE, bloom=B.HALO, tint=(.94,.72,.93))
        y0 = 201 + i * 333
        for j, column in enumerate((0, 2)):
            view_img = canvas.copy()
            pen = ImageDraw.Draw(view_img)
            for px, py, _ in centers[:, column] @ view.T * 16:
                x, y = size/2 + (px-cx)*scale, size/2 - (py-cy)*scale
                pen.ellipse((x-6,y-6,x+6,y+6), outline=ROSE, width=2)
                pen.ellipse((x-1,y-1,x+1,y+1), fill=INK)
            left = 30 + 526*j
            draw.rectangle((left,y0,left+502,y0+298), fill=(29,23,37))
            sheet.paste(view_img.crop((0,145,503,358)), (left,y0+42))
            draw.rectangle((left,y0,left+502,y0+298), outline=(77,55,79))
            label(draw, (left+13, y0+12), title, 18, INK, bold=True)
            max_gap = results[i][:, :, column].max()
            label(draw, (left+13, y0+268), f'Distancia máxima al paño: {max_gap:.2f} bloques'.replace('.', ','), 16, DIM)
    label(draw, (31, 856), 'Círculos: puntos posibles de nacimiento. Diagnóstico de clips; sin alas, no es una captura de Minecraft.', 16, DIM)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=Path, help='CapeSparkFrameTest --samples (TSV)')
    parser.add_argument('--plate', type=Path)
    args = parser.parse_args()
    rows = [s.split('\t') for s in args.samples.read_text().splitlines()]
    geo = P.load(P.ARMOR_GEO)
    clips = json.loads(A.ANIM.read_text())['animations']
    poses, results = [], []
    for swimming, state, title, clip_name in [(False, 'AIR', 'Planeo con élitros', 'air'), (True, 'SWIM', 'Nado horizontal', 'swim')]:
        data = np.array([[float(x) for x in row[1:]] for row in rows if row[0] == state])
        points = data[:,1:].reshape(-1, 3, 3)
        clip = clips['animation.'+clip_name]
        assert len(points) == 108 and np.count_nonzero(data[:,0]) == 4
        distances = measure(geo, clip, swimming, points)
        maxima = distances.max(axis=(0,1))
        assert maxima[2] < .33 and maxima[2] < .58*maxima[0], maxima
        assert distances[:,:,2].mean() < .86*distances[:,:,1].mean(), maxima
        print(f'{state}: {len(points)*len(distances)} muestras; máximo vertical/giro solo/ajustado {maxima.round(3)} bloques')
        poses.append((swimming, title, clip, points[data[:,0] == 1]))
        results.append(distances)
    if args.plate:
        plate(args.plate, geo, poses, results)


if __name__ == '__main__':
    main()
