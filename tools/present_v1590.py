#!/usr/bin/env python3
"""Placas comparables y ciclos desde los assets que lleva el mod."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import cape_animation_pipeline as animation
import cape_tracks as tracks
import preview_cloth as P

BACKUP = P.ROOT / "docs/respaldos/v1.58.0"
BASE_GEO = BACKUP / P.ARMOR_GEO.relative_to(P.ASSETS)
BASE_TEX = BACKUP / P.ARMOR_TEX.relative_to(P.ASSETS)
BASE_ANIM = animation.BASE_ANIM
BG = (22, 17, 28)
STAGE = (29, 23, 37)
INK, DIM, ROSE = (249, 237, 242), (197, 175, 198), (255, 172, 213)
TITLES = (
    ("Reposo", "Peso en el dobladillo"), ("Caminar", "Vaivén a contratiempo"),
    ("Esprintar", "Barrido hacia atrás"), ("Salto / planeo", "Apertura de los gajos"),
    ("Caída", "Remate levantado"), ("Agacharse", "Dobladillo recogido"),
    ("Agua", "Curva en S y deriva"), ("Deterioro", "Doble impulso"),
)


def label(draw, pos, s, size, color=INK, *, bold=False):
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        font = ImageFont.load_default(size=size)
    draw.text(pos, s, font=font, fill=color)


def fit_frame(geos, yaw, pitch, size, *, mannequin=False, margin=46):
    vertices = [f[0] for geo in geos for f in P.collect(geo, P.effective_hidden(geo))]
    if mannequin:
        vertices += [np.asarray(o) + P.CORNERS * s for o, s, _ in P.MANNEQUIN_BOXES]
    view = (P.R("x", pitch) @ P.R("y", yaw))[:3, :3]
    a = np.concatenate(vertices, axis=0) @ view.T
    lo, hi = a.min(axis=0), a.max(axis=0)
    return (*(lo[:2] + hi[:2]) / 2, (size - margin) / max(hi[:2] - lo[:2]))


def comparison(out: Path, newer: dict, atlas, ver: str):
    old = P.load(BASE_GEO)
    sheet = Image.new("RGB", (1200, 1190), BG)
    d = ImageDraw.Draw(sheet)
    label(d, (32, 25), "MANTLE OF THE BLIGHT STAR", 20, ROSE, bold=True)
    label(d, (30, 55), "Antes y después", 56, bold=True)
    label(d, (34, 125), "Modelo equipado · misma cámara, escala y luz en cada pareja", 21, DIM)
    size, yaw, pitch = 554, -13, 8
    frame = fit_frame([old, newer], yaw, pitch, size, mannequin=True)
    views = ((old, BASE_TEX, "v1.58.0   /   ANTES"), (newer, atlas, f"v{ver}   /   REDISEÑO"))
    for i, (model, texture, title) in enumerate(views):
        x = (32, 614)[i]
        label(d, (x+1, 179), title, 21, ROSE if i else DIM, bold=True)
        img = P.render(model, texture, P.effective_hidden(model), yaw=yaw, pitch=pitch,
                       size=size, frame=frame, bg=STAGE, mannequin=True)
        sheet.paste(img, (x, 216))
        d.rectangle((x, 216, x + size - 1, 769), outline=(70, 51, 77))
        # El encuadre del detalle es una ventana fija, no un autozoom.
        detail_yaw, detail_pitch = -27, 16
        view = P.R("x", detail_pitch) @ P.R("y", detail_yaw)
        target = view @ np.array([0, 21, 4.6, 1])
        hi = P.render(model, texture, P.effective_hidden(model), yaw=detail_yaw,
                      pitch=detail_pitch, size=size, bg=STAGE,
                      frame=(float(target[0]), float(target[1]), 31))
        sheet.paste(hi.crop((0, 145, size, 409)), (x, 829))
        d.rectangle((x, 829, x + size - 1, 1092), outline=(70, 51, 77))
    label(d, (34, 789), "DETALLE  /  CUELLO Y HOMBROS", 21, ROSE, bold=True)
    label(d, (34, 1110), "Cuello redondeado · cadena alta", 19, DIM)
    label(d, (616, 1110), "Solapas oblicuas · acero biselado · cadena en arco", 19)
    label(d, (34, 1153), "Render software · pose de reposo del rig (sin animar) · no es una captura del juego", 16, DIM)
    sheet.save(out, optimize=True)


def motion_sheet(out: Path, geo: dict, atlas, clips: dict, ver: str):
    # Cámara y escala fijas incluso al cambiar de estado.
    phases = (.25, .67)
    size, yaw, pitch = 246, -43, 9
    cfgs = [(tracks.prepare_clip(c), c["animation_length"]) for c in clips.values()]
    samples = [[P.pose_at(geo, data, length * f) for f in phases] for data, length in cfgs]
    frame = fit_frame([p for poses in samples for p in poses], yaw, pitch, size, mannequin=True, margin=19)
    sheet = Image.new("RGB", (2144, 798), BG)
    d = ImageDraw.Draw(sheet)
    label(d, (28, 23), f"OCHO POSES   /   v{ver}", 37, bold=True)
    label(d, (30, 75), "25 % → 67 % del ciclo · maniquí neutro · misma cámara y escala · sin FX", 20, DIM)
    for i, (poses, (title, line)) in enumerate(zip(samples, TITLES)):
        x, y = 28 + i % 4 * 528, 118 + i // 4 * 326
        label(d, (x, y), title, 25, ROSE, bold=True)
        label(d, (x, y+34), line, 17, DIM)
        for j, posed in enumerate(poses):
            img = P.render(posed, atlas, P.effective_hidden(geo), yaw=yaw, pitch=pitch,
                           size=size, frame=frame, mannequin=True, bg=STAGE)
            sheet.paste(img, (x + 253*j, y+58))
            label(d, (x + 253*j + 8, y+65), ("25 %", "67 %")[j], 15, DIM)
    sheet.save(out, optimize=True)


def motion_gif(out: Path, geo: dict, atlas, clips: dict, ver: str):
    # Los ciclos se sincronizan por fase en el GIF. El visor usa los segundos reales.
    size, yaw, pitch = 292, -46, 10
    selected = ["animation.moving", "animation.air", "animation.fall", "animation.deterioro"]
    indices = [1, 3, 4, 7]
    prepared = {k: tracks.prepare_clip(clips[k]) for k in selected}
    bounds = fit_frame([P.pose_at(geo, prepared[k], f*clips[k]["animation_length"])
                        for k in selected for f in (0,.2,.4,.6,.8)], yaw, pitch, size,
                       mannequin=True, margin=18)
    frames = []
    for j in range(32):
        board = Image.new("RGB", (632, 700), BG)
        d = ImageDraw.Draw(board)
        label(d, (18, 14), f"El paño en movimiento   /   v{ver}", 26, bold=True)
        for i, (k, ix) in enumerate(zip(selected, indices)):
            x, y = 18 + i%2 * 304, 54 + i//2 * 321
            t = j / 32 * clips[k]["animation_length"]
            img = P.render(P.pose_at(geo, prepared[k], t), atlas, P.effective_hidden(geo),
                           yaw=yaw, pitch=pitch, size=size, frame=bounds, bg=STAGE, mannequin=True)
            label(d, (x, y), TITLES[ix][0], 18, ROSE, bold=True)
            board.paste(img, (x, y+25))
        frames.append(board.quantize(192, dither=Image.Dither.NONE))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--candidate", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.candidate:
        from armor_model_pipeline import build
        from cape_atlas_v1230 import build_clean_atlas
        geo = build()["minecraft:geometry"][0]
        atlas, _ = build_clean_atlas()
        data = animation.build(geo)
    else:
        geo, atlas = P.load(P.ARMOR_GEO), P.ARMOR_TEX
        data = json.loads(animation.ANIM.read_text())
    ver = "1.59.0" if args.candidate else P.mod_version()
    comparison(args.out / f"capa_v{ver.replace('.', '')}_antes_despues.png", geo, atlas, ver)
    motion_sheet(args.out / "capa_v1170_estados.png", geo, atlas, data["animations"], ver)
    if args.gif:
        motion_gif(args.out / "capa_v1170_animaciones.gif", geo, atlas, data["animations"], ver)
    print(f"comparación y poses v{ver} en {args.out}")


if __name__ == "__main__":
    main()
