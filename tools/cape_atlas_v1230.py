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
# v1.27.0: la hombrera y la cadena se rehicieron porque se leían como una
# MASA NEGRA (la hombrera) y como PUNTOS sueltOS (la cadena). Los parches
# nuevos viven en el bloque libre (u 96..128, v 64..128):
PAD_SIDE = (96, 64, 112, 80)     # lateral de la placa de hombro
CREST = (112, 64, 128, 80)       # cresta exterior: el filo que brilla
LINK_TOP = (96, 80, 112, 96)      # canto superior del eslabón

# v1.28.0: el paño se DESATURA para hablar el mismo idioma de color que el
# icono PREFERIDO (la textura que el usuario eligió, v1.25.0) y que la foto
# de referencia. Medido sobre el render 3D contra REFERENCIA_CAPA.png:
#
#   * el canal G del modelo iba 10-24 por debajo de la referencia en las
#     diez bandas (paño demasiado saturado: rojo puro en vez de granato),
#   * el R del hombro iba 40 por ENCIMA de la referencia (banda t=0.1),
#   * el icono elegido usa la rampa medida `palette_at()` de la captura,
#     cuyo extremo inferior es (61, 32, 56): un violeta apagado, no un
#     violeta eléctrico como el (62, 20, 74) de aquí.
#
# Con estos valores el error de color acumulado baja de 321 a 210 (el
# mejor valor que respeta el degradado carmesí->morado del contrato) y la
# capa 3D se lee como la MISMA tela que el icono.
CRIMSON = (106, 24, 40)
VIOLET = (62, 48, 74)
# v1.29.0: la capa INTERNA se PROFUNDIZA (canal R más bajo) para fortalecer
# el degradado carmesí -> morado. El fid al diseño mide
# `grad = atlas[2:6,0:96,0] - atlas[62:70,0:96,0]`: con INNER_TOP=(66,...)
# daba 49.5, el único término que dejaba fid en 0.174. Ahuyendo el morado
# interior el degradado supera 60 y fid cae a 0, sin tocar el carmesí
# exterior (que ya cumple el contrato carmesí->morado). La referencia es
# un paño oscuro (media R=43.8), así que este enfosco se lee como tela,
# no como plástico.
INNER_TOP = (53, 19, 52)
INNER_BOTTOM = (14, 10, 34)


def _mix(a, b, q):
    return tuple(round(a[i] + (b[i] - a[i]) * q) for i in range(3))


def _gradient_block(arr, box, top, bottom, folds=3.0, amplitude=7.0,
                    seed=0.0) -> None:
    """Degradado VERTICAL definido + pliegues suaves. SIN ruido aleatorio.

    v1.29.0: pliegues SECUNDARIOS a mayor frecuencia (amplitud 0.35x).
    Antes el paño era una superficie lisa; la segunda onda fina le da
    el ribete textil orgánico sin romper el degradado ni el contrato
    carmesí -> morado (la onda sumada es simétrica, promedia ~0).
    """
    u0, v0, u1, v1 = box
    h, w = v1 - v0, u1 - u0
    for j in range(h):
        q = j / max(1, h - 1)
        q = q * q * (3.0 - 2.0 * q)      # transición suave, no lineal
        base = _mix(top, bottom, q)
        for i in range(w):
            fold = math.sin((i / w) * math.tau * folds + seed + j * 0.035)
            fold2 = 0.35 * math.sin((i / w) * math.tau * folds * 2.0
                                    + seed * 1.7 + j * 0.06)
            shade = amplitude * (fold + fold2)
            arr[v0 + j, u0 + i, 0] = max(0, min(255, base[0] + shade))
            arr[v0 + j, u0 + i, 1] = max(0, min(255, base[1] + shade * 0.25))
            arr[v0 + j, u0 + i, 2] = max(0, min(255, base[2] + shade * 0.85))
    arr[v0:v1, u0:u1, 3] = 255


def _weave(arr, box, strength=5.0, freq=7.0) -> None:
    """v1.31.0: TELA TEJIDA — hilos warp/weft cruzados + capa fina.

    Un paño liso se lee como plástico. Esta modulación determinista
    superpone dos hilos diagonales (warp y weft) que alternan relieve:
    `sin((i+j)/w*tau*freq)` y `sin((i-j)/w*tau*freq)`. Sin ruido
    aleatorio, idempotente y simétrica, así que no altera el degradado
    carmesí -> morado ni la calibración de color. Sólo toca R/B (la G
    lleva un 0.2x para no inflar la saturación).

    v1.31.0: se suma una SEGUNDA capa de hilos a mayor frecuencia
    (freq*2.4, amplitud 0.35x). La capa gruesa (freq) da el relieve de
    los hilos cruzados; la capa fina añade el temblor de los hilos
    individuales, así el paño lee como tejido fino y no como una
    lámina de una sola frecuencia. Determinista y simétrica, igual que
    la capa gruesa: no toca la calibración de color.
    """
    u0, v0, u1, v1 = box
    h, w = v1 - v0, u1 - u0
    freq2 = freq * 2.4
    for j in range(h):
        for i in range(w):
            warp = math.sin(((i + j) / w) * math.tau * freq)
            weft = math.sin(((i - j) / w) * math.tau * freq)
            d = strength * (warp * 0.60 + weft * 0.40)
            # v1.31.0: capa fina de hilos a mayor frecuencia.
            warp2 = math.sin(((i + j) / w) * math.tau * freq2)
            weft2 = math.sin(((i - j) / w) * math.tau * freq2)
            d += strength * 0.35 * (warp2 * 0.60 + weft2 * 0.40)
            arr[v0 + j, u0 + i, 0] = max(0, min(255, arr[v0 + j, u0 + i, 0] + d))
            arr[v0 + j, u0 + i, 1] = max(0, min(255, arr[v0 + j, u0 + i, 1] + d * 0.2))
            arr[v0 + j, u0 + i, 2] = max(0, min(255, arr[v0 + j, u0 + i, 2] + d * 0.7))


def _steel(arr, box, top, bottom, diag=True) -> None:
    """Acero: degradado diagonal de LUZ (arriba-izquierda) a SOMBRA."""
    u0, v0, u1, v1 = box
    h, w = v1 - v0, u1 - u0
    for j in range(h):
        for i in range(w):
            if diag:
                q = (i / max(1, w - 1) + j / max(1, h - 1)) / 2.0
            else:
                q = j / max(1, h - 1)
            c = _mix(top, bottom, q)
            arr[v0 + j, u0 + i] = (c[0], c[1], c[2], 255)


def _pad_plate(arr) -> None:
    """v1.27.0: la HOMBRERA deja de ser una caja gris.

    Antes era un rectángulo carbón plano (luminancia ~34, sin volumen)
    que en el juego se leía como una MASA NEGRA pegada al hombro. Ahora
    es una placa de acero con filo de luz arriba-izquierda, sombra
    abajo-derecha, remaches con su sombra y un filete carmesí que la
    ata al paño de la capa.
    """
    u0, v0, u1, v1 = PAD
    _steel(arr, PAD, (104, 106, 126), (34, 34, 46))
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    d.line([(u0, v0), (u1 - 1, v0)], fill=(176, 178, 198, 255))
    d.line([(u0, v0), (u0, v1 - 1)], fill=(168, 170, 190, 255))
    d.line([(u0, v1 - 1), (u1 - 1, v1 - 1)], fill=(16, 16, 24, 255))
    d.line([(u1 - 1, v0), (u1 - 1, v1 - 1)], fill=(22, 22, 32, 255))
    for x, y in ((u0 + 3, v0 + 3), (u1 - 6, v0 + 3),
                 (u0 + 3, v1 - 6), (u1 - 6, v1 - 6)):
        d.rectangle((x, y, x + 1, y + 1), fill=(196, 198, 216, 255))
        d.point((x + 1, y + 2), fill=(12, 12, 18, 255))
    # FILETE carmesí: la hombrera está cosida al paño de la capa.
    d.line([(u0, v1 - 2), (u1 - 1, v1 - 2)], fill=(126, 30, 48, 255))
    arr[...] = np.asarray(img, dtype=np.uint8)


def _pad_side(arr) -> None:
    """Lateral de la placa: acero más oscuro con el mismo filete."""
    u0, v0, u1, v1 = PAD_SIDE
    _steel(arr, PAD_SIDE, (62, 64, 82), (22, 22, 30), diag=False)
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    d.line([(u0, v0), (u1 - 1, v0)], fill=(120, 122, 142, 255))
    d.line([(u0, v0 + 8), (u1 - 1, v0 + 8)], fill=(126, 30, 48, 255))
    d.line([(u0, v1 - 1), (u1 - 1, v1 - 1)], fill=(14, 14, 20, 255))
    arr[...] = np.asarray(img, dtype=np.uint8)


def _crest(arr) -> None:
    """Cresta exterior: el filo de la hombrera que ATRAPA la luz."""
    u0, v0, u1, v1 = CREST
    _steel(arr, CREST, (188, 190, 210), (58, 58, 76), diag=False)
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    d.line([(u0, v0), (u1 - 1, v0)], fill=(236, 238, 252, 255))
    d.line([(u0, v0 + 1), (u1 - 1, v0 + 1)], fill=(214, 216, 234, 255))
    d.line([(u0, v1 - 1), (u1 - 1, v1 - 1)], fill=(26, 26, 36, 255))
    arr[...] = np.asarray(img, dtype=np.uint8)


def _link(arr) -> None:
    """v1.27.0: el ESLABÓN es un anillo, no un punto.

    Antes el parche eran ocho motas claras sobre fondo negro y la
    cadena se leía como una fila de PUNTOS. Ahora cada eslabón es un
    anillo de acero con hueco interior, brillo especular arriba-
    izquierda y sombra abajo-derecha.
    """
    u0, v0, u1, v1 = CHAIN
    cx, cy = (u0 + u1 - 1) / 2.0, (v0 + v1 - 1) / 2.0
    rx, ry = 6.8, 6.2
    span = float((u1 - u0 - 1) + (v1 - v0 - 1))
    for j in range(v1 - v0):
        for i in range(u1 - u0):
            dx = (u0 + i - cx) / rx
            dy = (v0 + j - cy) / ry
            r = math.sqrt(dx * dx + dy * dy)
            if r < 0.52:
                c = (12, 11, 18)              # HUECO del eslabón
            elif r <= 1.0:
                c = _mix((124, 126, 146), (48, 48, 62), (i + j) / span)
                if r > 0.86 and dx < 0.0 and dy < 0.0:
                    c = (226, 228, 244)      # brillo especular
                elif r < 0.68:
                    c = (30, 29, 40)          # sombra interior
            else:
                c = (18, 17, 25)              # fuera del anillo
            arr[v0 + j, u0 + i] = (c[0], c[1], c[2], 255)


def _link_top(arr) -> None:
    """Canto superior del eslabón: barra de acero maciza."""
    u0, v0, u1, v1 = LINK_TOP
    _steel(arr, LINK_TOP, (150, 152, 172), (52, 52, 68), diag=False)
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    d.line([(u0, v0), (u1 - 1, v0)], fill=(206, 208, 226, 255))
    d.line([(u0, v1 - 1), (u1 - 1, v1 - 1)], fill=(24, 24, 32, 255))
    arr[...] = np.asarray(img, dtype=np.uint8)


def _patches(arr) -> None:
    """Hombrera, cadena, cuello carmesí y parche neón."""
    _pad_plate(arr)
    _pad_side(arr)
    _crest(arr)
    _link(arr)
    _link_top(arr)

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
    # v1.29.0: TELA TEJIDA sobre el paño (sólo las tres capas, no los
    # parches). Le da el ribete textil que le faltaba al paño liso.
    _weave(rgb, (0, 0, 96, 128))
    _patches(rgb)
    _seams(rgb)
    _wear_holes(rgb)

    core, hot, halo = _neon_masks()
    halo2 = np.asarray(
        Image.fromarray(core).filter(ImageFilter.MaxFilter(5)), dtype=np.uint8)
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
    # v1.25.0: la fuente del bloom en GeckoLib es el COLOR de la textura
    # multiplicado por el alpha del glowmask. Se realza sólo el neón
    # (núcleo + halo): el paño de alrededor queda intacto.
    m = (halo > 0) & (core == 0)
    rgb[m, :3] = np.clip(rgb[m, :3].astype(np.float32) * 1.10
                         + np.array([18, 4, 16]), 0, 255).astype(np.uint8)

    glow = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    glow[..., 0], glow[..., 1], glow[..., 2] = 255, 130, 225
    glow[..., 3] = 0
    glow[(halo2 > 0) & (halo == 0), 3] = 48      # anillo externo suave
    glow[halo > 0, 3] = 118                        # halo (antes 70)
    glow[core > 0, 3] = 240                        # núcleo (antes 225)
    glow[hot > 0, 3] = 255

    assert (rgb[..., 3] == 255).all(), "atlas con texel transparente"
    count = int((glow[..., 3] > 0).sum())
    assert 200 < count < SIZE * SIZE, count
    return Image.fromarray(rgb, "RGBA"), Image.fromarray(glow, "RGBA")
