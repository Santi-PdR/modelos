#!/usr/bin/env python3
"""Fixed-camera light A/B and the three actual particle sprites."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

import cape_bloom as B
import cape_reference as R
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label

SCENE = (20, 16, 27)
LINE = (77, 55, 79)


def panel(out):
    geo = P.load(P.ARMOR_GEO)
    hidden = P.effective_hidden(geo)
    size, frame, box = R.render_frame()

    def render(ambient, halo, scale):
        return P.render(geo, P.ARMOR_TEX, hidden, yaw=R.YAW, pitch=R.PITCH,
                        size=size*scale, frame=(*frame[:2], frame[2]*scale),
                        bg=SCENE, mannequin=True, ambient=ambient, emission=B.CORE,
                        tint=(.932,.69,.91), bloom=B.HALO if halo else None
                        ).crop(tuple(x*scale for x in box))

    image = Image.new('RGB', (1280, 938), BG)
    d = ImageDraw.Draw(image)
    label(d, (32,25), 'MANTLE OF THE BLIGHT STAR   /   v1.67.0', 18, ROSE, bold=True)
    label(d, (30,58), 'Luz que sigue las grietas', 53, bold=True)
    label(d, (33,128), 'Misma pose, cámara y emisión. Sólo cambia el halo.', 22, DIM)
    for i, (title, active) in enumerate((('01   SÓLO NÚCLEO', False), ('02   NÚCLEO + HALO', True))):
        x = 32 + i*386
        label(d, (x,178), title, 19, ROSE if active else DIM, bold=True)
        view = render(.40, active, 2).resize((365,588), Image.Resampling.LANCZOS)
        image.paste(view, (x,212))
        d.rectangle((x,212,x+364,799), outline=LINE)
    label(d, (33,819), 'LUZ BAJA   /   el magenta se extiende sólo sobre la tela', 20, DIM)

    x = 805
    d.rounded_rectangle((x,165,1247,800), radius=12, fill=(30,23,38), outline=LINE)
    label(d, (825,183), 'EL MISMO CORTE CON LUZ ALTA', 18, ROSE, bold=True)
    for i, (title, active) in enumerate((('NÚCLEO', False), ('+ HALO', True))):
        left = 825+i*202
        view = render(1, active, 2).crop((224,406,376,628))
        image.paste(view.resize((192,280), Image.Resampling.NEAREST), (left,249))
        label(d, (left,220), title, 17, DIM if not active else INK)
    label(d, (825,549), 'BRASA → DESTELLO → CENIZA', 18, ROSE, bold=True)
    for i, title in enumerate(('Rosa vivo', 'Magenta', 'Violeta')):
        left = 825 + i*133
        with Image.open(P.PARTICLE_DIR / f'capa_spark_{i}.png') as tex:
            sprite = tex.convert('RGBA').resize((96,96), Image.Resampling.NEAREST)
        d.rounded_rectangle((left,590,left+125,722), radius=8, fill=SCENE)
        image.paste(sprite, (left+14,592), sprite)
        label(d, (left+8,692), title, 17, DIM)
    label(d, (825,747), 'Tres sprites ampliados. Una partícula por chispa.', 16, DIM)
    d.line((32,870,1248,870), fill=LINE)
    label(d, (32,887), 'El halo no ilumina el mundo ni cambia el contorno. Render de diagnóstico, no captura de Minecraft.', 18, DIM)
    out.mkdir(exist_ok=True, parents=True)
    image.save(out/'capa_v1670_bloom.png', optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=P.ROOT/'docs')
    panel(ap.parse_args().out)
    print('v1.67.0: comparativa de halo y brasas')


if __name__ == '__main__':
    main()
