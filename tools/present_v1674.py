"""Same-frame lateral drag A/B and the Java response after each reversal."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cape_bloom as B
import cape_nocturne as N
import cape_tracks as T
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, STAGE, fit_frame, label

LINE = (77, 55, 79)
EARLY = (168, 155, 236)


def plate(out, geo, moving, times, angles, profile, clip_pose):
    sheet = Image.new('RGB', (1040, 1000), BG)
    draw = ImageDraw.Draw(sheet)
    label(draw, (28,24), 'MANTLE OF THE BLIGHT STAR   /   v1.67.4', 17, ROSE, bold=True)
    label(draw, (25,54), 'El paño se queda atrás', 47, bold=True)
    label(draw, (29,115), 'Paso lateral · misma pose, cámara y halo en las dos vistas.', 20, DIM)
    size, yaw, pitch = 510, 0, 9
    track = T.prepare_clip(moving)
    frame_index = 16  # 0.80 s into the first one-second leg
    phase = times[frame_index]
    poses = [clip_pose(geo, track, phase, motion, 0, 0, 0, profile)
             for motion in (np.zeros_like(angles[frame_index]), angles[frame_index])]
    frame = fit_frame(poses, yaw, pitch, size, mannequin=True, margin=132)
    ambient = .40
    light = N.profile()
    options = dict(yaw=yaw, pitch=pitch, size=size, bg=STAGE, mannequin=True,
                   ambient=ambient, emission=B.CORE, tint=(.932,.69,.91), bloom=B.HALO,
                   halo_gains=N.gains(light, N.darkness(light, 15*(ambient-.18)/.82), phase))
    for i, (name, model) in enumerate(zip(('A   SIN ARRASTRE', 'B   CON ARRASTRE'), poses, strict=True)):
        x = (29, 296)[i]
        label(draw, (x,167), name, 18, DIM if i == 0 else ROSE, bold=True)
        image = P.render(model, P.ARMOR_TEX, P.effective_hidden(model), frame=frame, **options)
        sheet.paste(image.crop((129,0,381,size)), (x,196))
        draw.rectangle((x,196,x+251,705), outline=LINE if i == 0 else ROSE)

    label(draw, (585,167), 'LAS PUNTAS · DETALLE', 18, ROSE, bold=True)
    # Both crops keep the same magnification and vertical reference line.
    view = P.R('x', pitch) @ P.R('y', yaw)
    tip = view @ np.array([1.2, 1.9, 6, 1])
    for i, model in enumerate(poses):
        x = 585 + i * 215
        image = P.render(model, P.ARMOR_TEX, P.effective_hidden(model),
                         frame=(tip[0], tip[1], frame[2]*4), **options)
        sheet.paste(image.crop((155,175,355,345)), (x,196))
        draw.rectangle((x,196,x+199,365), outline=LINE)
        for y in range(201, 364, 9):
            draw.line((x+100,y,x+100,y+3), fill=DIM, width=1)
        label(draw, (x+13,207), 'A' if i == 0 else 'B', 19, INK, bold=True)
    label(draw, (585,394), 'La costura no se desplaza.', 24, bold=True)
    label(draw, (585,434), 'El collar y la montura siguen al torso.\nEl arrastre empieza debajo de la unión\ny se nota más en el extremo libre.', 19, DIM)
    label(draw, (585,529), 'A los 100 ms de la inversión,', 23, bold=True)
    label(draw, (585,566), 'el tramo superior ya vuelve,\npero el último todavía sigue la ida.', 19, DIM)
    label(draw, (29,730), 'Inclinación añadida · muestras del filtro Java', 22, bold=True)
    plot(draw, times, angles)
    label(draw, (29,964), 'Simulación sobre el modelo equipado; no es una captura de Minecraft.', 16, DIM)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)


def plot(draw, times, angles):
    draw.rounded_rectangle((29,767,1010,947), 9, fill=STAGE, outline=LINE)
    x, mid, w, h = 85, 851, 894, 43
    for v, text in ((1, '+1°'), (0, '0°'), (-1, '−1°')):
        y = mid-h*v
        draw.line((x,y,x+w,y), fill=LINE)
        label(draw, (43,y-10), text, 14, DIM)
    for s, text in ((0, '0 s'), (1, '1 s · Inversión'), (2, '2 s')):
        a = x+w*s/2
        draw.line((a,793,a,913), fill=LINE)
        label(draw, (a-14 if s != 1 else a-53,918), text, 14, DIM)
    for seg, name, color, left in ((0,'Tramo 1',EARLY,715),(-1,'Punta',ROSE,856)):
        draw.line([(x+w*t/2, mid-h*r) for t,r in zip(times,angles[:,seg,1],strict=True)],
                  fill=color, width=3, joint='curve')
        draw.line((left,789,left+24,789), fill=color, width=3)
        label(draw, (left+31,779), name, 15, INK)
