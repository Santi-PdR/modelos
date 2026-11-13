#!/usr/bin/env python3
"""v1.23.0 — ATLAS LIMPIO Y EMISSIVE, CREADO A MANO.

El usuario pidió: «Limpia el ruido de la textura dejando un degradado
definido de rojo carmesí a morado oscuro con agujeros de desgaste en las
puntas, y añade grietas y bordes en rosa/magenta neón con renderizado
brillante (emissive / fullbright)».

El atlas anterior era el PNG de la referencia recortado: traía la cabeza
blanca del maniquí, el arnés, el checkerboard y ruido de compresión que,
una vez mapeado a cubos, se leía como motas y cuadrados.

Este módulo pinta un atlas 128x128 NUEVO y determinista:

  * u=0..96, v=0..48   : capa EXTERNA. Degradado carmesí -> violeta.
  * u=0..96, v=48..96  : capa INTERNA. Morado oscuro, más frío y apagado.
  * u=0..96, v=96..128 : puntas / desgaste.
  * u=96..128          : parches para hombreras carbón, cadena, cuello
                         carmesí oscuro y el parche NEÓN de las grietas 3D.
  * Grietas y bordes neón: trazos con HALO + NÚCLEO + CENTRO BLANCO,
    dibujados con ImageDraw (sin ruido aleatorio). Se exporta además un
    ``*_glowmask.png`` cuya ALFA enciende exactamente esos texels: el
    ``AutoGlowingGeoLayer`` de GeckoLib los renderiza a luz llena.
  * Agujeros de desgaste: muescas y boquetes oscuros irregulares en el
    tercio inferior, alineados con los bordes de cada mechón.

Todo el atlas es OPACO (alpha=255): los agujeros son COLOR, no transparencia,
para que ningún UV de la geometría pueda samplear un texel vacío.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 128

# Parches reservados (u0, v0, u1, v1)
PAD = (96, 0, 112, 16)
CHAIN = (112, 0, 128, 16)
COLLAR = (96, 16, 128, 40)
NEON = (96, 40, 128, 64)

CRIMSON = (142, 24, 40)
VIOLET = (62, 20, 74)
INNER_TOP = (66, 16, 58)
INNER_BOTTOM = (24, 9, 40)


def _mix(a, b, q):
    return tuple(round(a[i] + (b[i] - a[i]) * q) for i in range(3))


def _gradient_block(arr, box, top, bottom, folds=3.0, amplitude=7.0,
                    seed=0.0) -> None:
    """Degradado VERTICAL definido + pliegues suaves. SIN ruido aleatorio."""
    u0, v0, u1, v1 = box
    h, w = v1 - v0, u1 - u0
    for j in range(h):
        q = j / max(1, h - 1)
        q = q * q * (3.0 - 2.0 * q)      # transición suave, no lineal
        base = _mix(top, bottom, q)
        for i in range(w):
            fold = math.sin((i / w) * math.tau * folds + seed + j * 0.035)
            shade = amplitude * fold
            arr[v0 + j, u0 + i, 0] = max(0, min(255, base[0] + shade))
            arr[v0 + j, u0 + i, 1] = max(0, min(255, base[1] + shade * 0.25))
            arr[v0 + j, u0 + i, 2] = max(0, min(255, base[2] + shade * 0.85))
    arr[v0:v1, u0:u1, 3] = 255


def _patches(arr) -> None:
    """Hombreras carbón, cadena oscura, cuello carmesí y parche neón."""
    # --- hombreras: carbón con vetas horizontales y remaches -------------
    u0, v0, u1, v1 = PAD
    for j in range(v1 - v0):
        for i in range(u1 - u0):
            v = 34 + 5 * math.sin(j * 0.9) + 3 * math.sin(i * 1.7 + j * 0.4)
            arr[v0 + j, u0 + i] = (int(v), int(v + 1), int(v + 6), 255)
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    for x, y in ((99, 3), (109, 3), (99, 12), (109, 12)):
        d.rectangle((x, y, x + 1, y + 1), fill=(86, 88, 100, 255))

    # --- cadena: eslabones oscuros con realce metálico -------------------
    u0, v0, u1, v1 = CHAIN
    arr[v0:v1, u0:u1] = (20, 20, 27, 255)
    img.paste(Image.fromarray(arr[v0:v1, u0:u1], "RGBA"), (u0, v0))
    d = ImageDraw.Draw(img)
    for row in range(4):
        y = 1 + row * 4
        for col in range(2):
            x = u0 + 1 + col * 7
            d.rectangle((x, y, x + 6, y + 2), outline=(50, 52, 64, 255))
            d.point((x + 3, y + 1), fill=(84, 86, 102, 255))
    arr[...] = np.asarray(img, dtype=np.uint8)

    # --- cuello alto: carmesí OSCURO con pliegues verticales -------------
    u0, v0, u1, v1 = COLLAR
    for j in range(v1 - v0):
        q = j / max(1, v1 - v0 - 1)
        base = _mix((84, 15, 27), (48, 10, 21), q)
        for i in range(u1 - u0):
            fold = 6.0 * math.sin(i * 0.85 + j * 0.06)
            arr[v0 + j, u0 + i] = (max(0, int(base[0] + fold)),
                                   max(0, int(base[1] + fold * 0.2)),
                                   max(0, int(base[2] + fold * 0.5)), 255)
    img2 = Image.fromarray(arr, "RGBA")
    ImageDraw.Draw(img2).line((u0, v1 - 2, u1, v1 - 2),
                              fill=(26, 6, 12, 255), width=2)
    arr[...] = np.asarray(img2, dtype=np.uint8)

    # --- parche NEÓN para las grietas 3D ---------------------------------
    u0, v0, u1, v1 = NEON
    for j in range(v1 - v0):
        for i in range(u1 - u0):
            q = 1.0 - min(1.0, abs(i - (u1 - u0) / 2) / ((u1 - u0) / 2))
            c = _mix((196, 28, 128), (255, 214, 246), q ** 2)
            arr[v0 + j, u0 + i] = (c[0], c[1], c[2], 255)


def _wear_holes(arr) -> None:
    """Agujeros de desgaste en las PUNTAS: muescas + boquetes irregulares."""
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    dark = (9, 5, 16, 255)
    for layer_v in (0, 48):
        y_base = layer_v + 48
        for k in range(6):
            u = k * 16 + 3 + (k * 5) % 7
            depth = 3 + (k * 7) % 5
            d.polygon([(u, y_base - 1), (u + 3, y_base - 1),
                       (u + 2, y_base - depth), (u + 1, y_base - depth + 2)],
                      fill=dark)
    holes = [(11, 40, 2, 2), (27, 43, 2, 2), (45, 38, 3, 2),
             (61, 45, 2, 3), (77, 41, 2, 2), (91, 44, 2, 2),
             (16, 88, 2, 2), (50, 91, 2, 2), (84, 87, 2, 2)]
    for u, v, w, h in holes:
        d.ellipse((u - w, v - h, u + w, v + h), fill=dark)
    arr[...] = np.asarray(img, dtype=np.uint8)


def _neon_paths():
    """Pocos trazos, FINOS y quebrados: grietas, no una telaraña."""
    edges, cracks = [], []
    # Bordes de mechón: guiones cortos y discontinuos (desgastados).
    for k in range(6):
        u0 = k * 16
        for u in (u0 + 1, u0 + 14):
            for seg in range(2):
                v0 = 4 + seg * 21 + (k * 3) % 6
                edges.append([(u, v0), (u + (seg % 2), v0 + 3),
                              (u, v0 + 5 + (k + seg) % 3)])
    # Grietas diagonales, 10 en total, repartidas por el paño.
    for i in range(10):
        u = 6 + (i * 17) % 82
        v = 8 + (i * 11) % 32
        du, dv = 4 + (i % 3) * 2, 6 + (i % 4) * 2
        cracks.append([(u, v), (u + du * 0.5, v + dv * 0.55),
                       (u + du, v + dv)])
    # 4 ramificaciones cortas.
    for i in range(4):
        u = 16 + (i * 23) % 70
        v = 24 + (i * 9) % 16
        cracks.append([(u, v), (u + 3, v + 2), (u + 6, v + 1)])
    # Unas pocas grietas también en la capa INTERNA (morado oscuro).
    for i in range(4):
        u = 10 + (i * 21) % 76
        v = 56 + (i * 13) % 30
        cracks.append([(u, v), (u + 3, v + 3), (u + 5, v + 5)])
    return edges, cracks


def _seams(arr) -> None:
    """Costura oscura de 1 texel entre mechones: se LEEN como capas."""
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    for k in range(6):
        u = k * 16
        for v0, v1 in ((2, 18), (23, 38), (41, 47)):
            d.line((u, v0, u, v1), fill=(28, 8, 30, 255), width=1)
    arr[...] = np.asarray(img, dtype=np.uint8)


def _neon_masks():
    core = Image.new("L", (SIZE, SIZE), 0)
    hot = Image.new("L", (SIZE, SIZE), 0)
    dc, dh = ImageDraw.Draw(core), ImageDraw.Draw(hot)
    edges, cracks = _neon_paths()
    for p in edges:
        dc.line(p, fill=255, width=1, joint="curve")
    for p in cracks:
        dc.line(p, fill=255, width=2, joint="curve")
        dh.line(p, fill=255, width=1, joint="curve")
    # El parche NEÓN entero emite (es la textura de las grietas 3D).
    u0, v0, u1, v1 = NEON
    dc.rectangle((u0, v0, u1 - 1, v1 - 1), fill=255)
    dh.rectangle((u0 + 12, v0 + 4, u1 - 13, v1 - 5), fill=255)
    halo = core.filter(ImageFilter.MaxFilter(3))
    return (np.asarray(core, dtype=np.uint8),
            np.asarray(hot, dtype=np.uint8),
            np.asarray(halo, dtype=np.uint8))


def build_clean_atlas():
    """Devuelve (atlas RGBA, glowmask RGBA) 128x128, deterministas."""
    rgb = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    rgb[...] = (26, 10, 36, 255)

    # Dos capas de tela + franja de puntas.
    _gradient_block(rgb, (0, 0, 96, 48), CRIMSON, VIOLET,
                    folds=6.0, amplitude=8.0, seed=0.4)
    _gradient_block(rgb, (0, 48, 96, 96), INNER_TOP, INNER_BOTTOM,
                    folds=6.0, amplitude=5.0, seed=1.7)
    _gradient_block(rgb, (0, 96, 96, 128), (22, 9, 38), (12, 6, 24),
                    folds=6.0, amplitude=3.0, seed=2.2)
    _patches(rgb)
    _seams(rgb)
    _wear_holes(rgb)

    core, hot, halo = _neon_masks()
    # HALO: magenta oscuro alrededor del trazo.
    m = (halo > 0) & (core == 0)
    rgb[m, 0] = np.maximum(rgb[m, 0].astype(int), 122).astype(np.uint8)
    rgb[m, 1] = np.maximum(rgb[m, 1].astype(int), 18).astype(np.uint8)
    rgb[m, 2] = np.maximum(rgb[m, 2].astype(int), 96).astype(np.uint8)
    # NÚCLEO: rosa/magenta neón.
    m = core > 0
    rgb[m] = (244, 74, 190, 255)
    # CENTRO BRILLANTE: casi blanco rosado.
    m = hot > 0
    rgb[m] = (255, 204, 240, 255)

    # GLOWMASK: GeckoLib sólo lee el ALFA. El RGB queda coherente por si
    # alguna herramienta lo inspecciona.
    glow = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    glow[..., 0], glow[..., 1], glow[..., 2] = 255, 120, 220
    glow[..., 3] = 0
    glow[halo > 0, 3] = 70
    glow[core > 0, 3] = 225
    glow[hot > 0, 3] = 255

    assert (rgb[..., 3] == 255).all(), "atlas con texel transparente"
    count = int((glow[..., 3] > 0).sum())
    assert 200 < count < SIZE * SIZE, count
    return Image.fromarray(rgb, "RGBA"), Image.fromarray(glow, "RGBA")
