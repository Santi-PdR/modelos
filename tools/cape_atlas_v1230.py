#!/usr/bin/env python3
"""Atlas 128×128 de la capa equipada. No se usa para el item plegado.

Paño repintado a partir de las capturas de Blockbench: granate profundo
arriba, forro violeta y cantos desgastados. Las 12 franjas mantienen sus
UV originales; cada una tiene pliegues y roturas de distinta trayectoria.
Los parches del cuello son tela, sin galones ni emblemas.

Los parches metálicos y el diseño de energía anterior se conservan. La
máscara de brillo se genera con los trazos originales; el RGB de todo
texel con glow se conserva, incluso en el halo que antes dependía del
color del paño. Alfa del atlas fijo a 255.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from cape_shape import tip_t
from cloth_spec import COWL_TILES

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

# Sombra, cuerpo y cresta. La referencia iluminada da granate (~70,18,32)
# y violeta (~64,29,69); los RGB del atlas compensan la sombra del cubo.
# Los picos de rojo quedan aparte de los rosas del neón.
CRIMSON_PLEATS = (
    (0,  ((36, 6, 17), (128, 26, 40), (185, 48, 57))),
    (13, ((31, 6, 16), (110, 20, 35), (171, 44, 55))),
    (24, ((28, 6, 21), (100, 18, 35), (165, 41, 54))),
    (33, ((23, 6, 24), (77, 23, 51), (140, 48, 77))),
    (47, ((16, 7, 22), (48, 20, 47), (100, 49, 86))),
)
VIOLET_PLEATS = (
    (0,  ((16, 7, 23), (49, 23, 61), (98, 60, 110))),
    (17, ((19, 7, 28), (52, 23, 66), (103, 62, 119))),
    (31, ((24, 9, 35), (79, 37, 95), (135, 79, 145))),
    (47, ((17, 7, 27), (67, 32, 81), (116, 66, 130))),
)
# Trayectorias a mano en UV (0..15). Se escalonan en y de forma distinta
# para el forro: no aparece la misma raya atravesando todos los jirones.
FOLD_ROWS = (0, 8, 16, 24, 32, 40, 47)
FOLD_SPINES = (
    (10, 9, 5, 8, 5, 7, 9),
    (4, 5, 9, 10, 7, 4, 5),
    (8, 10, 7, 4, 6, 9, 7),
    (6, 4, 5, 9, 10, 6, 8),
    (11, 9, 8, 5, 6, 9, 6),
    (5, 8, 6, 10, 8, 5, 8),
)
# El violeta asoma a distinta altura bajo las crestas granate. Los
# jirones exteriores más cortos conservan una caída más roja.
VIOLET_BREAK = (33, 29, 22, 28, 24, 32)
# RGB congelado de la textura v1.55.0 (sólo texels cubiertos por el glow).
ENERGY_RGB = Path(__file__).resolve().parent / "originals" / "capa_glow_rgb.png"


def _mix(a, b, q):
    return tuple(round(a[i] + (b[i] - a[i]) * q) for i in range(3))


def _tones_at(stops, y):
    for (lo, a), (hi, b) in zip(stops, stops[1:]):
        if y <= hi:
            return tuple(_mix(c0, c1, (y - lo) / (hi - lo)) for c0, c1 in zip(a, b))
    return stops[-1][1]


def _paint_shreds(atlas: np.ndarray, *, lining: bool) -> None:
    """Bloques de color en zigzag, cresta quebrada y desgaste en RGB."""
    stops = VIOLET_PLEATS if lining else CRIMSON_PLEATS
    y_base = 48 if lining else 0
    for panel in range(6):
        u = 16 * panel
        hand = -1 if (panel + lining) % 2 else 1
        spine = np.interp(np.arange(48), FOLD_ROWS, FOLD_SPINES[(panel + 2 * lining) % 6])
        tip = 48 * tip_t(2 * panel + int(lining))
        for y, ridge in enumerate(spine):
            depth = min(1.0, y / tip)
            stain = (panel * 7 + y // 4 + y // 9) % 5 - 2
            # La cresta termina en una arista estrecha; cada lado pierde
            # anchura de forma distinta al acercarse al extremo real del UV.
            spread = 4.9 - 1.3 * depth + 0.43 * stain
            tear = max(0.0, (depth - 0.73) / 0.27)
            near, face, light = _tones_at(stops, y)
            tones = (near, _mix(near, face, 0.38), face, _mix(face, light, 0.56), light)
            if not lining and y >= VIOLET_BREAK[panel] - 4:
                a, b, c = _tones_at(VIOLET_PLEATS, y)
                violet = (a, _mix(a, b, 0.38), b, _mix(b, c, 0.56), c)
            else:
                violet = None
            for x in range(16):
                d = hand * (x - ridge)
                # La sombra continúa al otro lado del pliegue. Las cuñas
                # descentradas evitan tanto el ruido fino como los galones.
                tone = 0
                if -spread - 1.7 <= d <= spread + 2.0 - tear * 2:
                    tone = 1
                if -spread + 0.7 <= d <= spread - tear * 1.8:
                    tone = 2
                if -2.8 + 0.16 * stain <= d <= 1.0 - tear * 0.6:
                    tone = 3
                if -1.4 < d <= 0.25 and (y + panel * 3) % 13 < 10:
                    tone = 4
                # Una segunda cara del pliegue sólo asoma por tramos.
                if 4.2 + 0.22 * stain <= d <= 5.6 + 0.25 * stain and (y + panel * 5) % 19 < 12:
                    tone = 2
                color = tones[tone]
                if violet is not None:
                    onset = VIOLET_BREAK[panel] + 0.62 * d + 0.56 * stain
                    fade = min(1.0, max(0.0, (y - onset) / 7))
                    color = _mix(color, violet[tone], fade)
                if x == 0 or x == 15:
                    color = _mix(near, color, 0.18)
                atlas[y_base + y, u + x, :3] = color


def _paint_cowl_panels(atlas: np.ndarray) -> None:
    """Granate de la bufanda: crestas asimétricas, sin bordado ni filete."""
    palette = {
        "dorsal": ((28, 5, 14), (83, 13, 27), (141, 35, 45)),
        "base": ((25, 5, 14), (71, 11, 24), (120, 27, 39)),
        "faldon": ((29, 6, 19), (91, 16, 32), (149, 37, 49)),
        "canto": ((17, 6, 15), (56, 11, 23), (86, 21, 34)),
        # Identificador UV histórico; el panel central ya no lleva estrella.
        "estrella": ((30, 5, 18), (96, 17, 31), (152, 37, 46)),
    }
    for i, (name, (u0, v0, u1, v1)) in enumerate(COWL_TILES.items()):
        shadow, body, light = palette[name]
        w, h = u1 - u0, v1 - v0
        for y in range(h):
            t = y / (h - 1)
            fold = w * (0.42 + 0.10 * math.sin(t * 4.4 + i * 0.9))
            for x in range(w):
                d = (x + 0.5 - fold) / w
                # El canto oscuro y la luz en diagonal dan forma a cada
                # paño sin imprimir líneas claras por todo el cuello.
                crease = max(0.0, 1.0 - abs(d + t * 0.07) * 3.7)
                color = _mix(body, light, crease * (0.69 - 0.36 * t))
                if abs(d) > 0.29 or y > 20 + (x + i) % 4:
                    color = _mix(color, shadow, 0.52)
                if 0.14 < d < 0.25 and 0.19 < t < 0.81:
                    color = _mix(color, shadow, 0.32)
                atlas[v0 + y, u0 + x, :3] = color


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


def _frayed_edges(atlas: np.ndarray) -> None:
    """Mordidas estrechas, en lugar de lunares. No perforan el canal alfa."""
    image = Image.fromarray(atlas)
    draw = ImageDraw.Draw(image)
    for lining in (False, True):
        base = 48 if lining else 0
        dark = (14, 7, 24, 255) if lining else (18, 5, 16, 255)
        for panel in range(6):
            start = 16 * panel
            tip = min(47, int(48 * tip_t(2 * panel + int(lining))))
            # Alterna lado y altura para que la rotura siga la caída del
            # jirón y no parezca una costura horizontal entre piezas.
            for y, side, length in ((tip - 9, panel % 2, 6), (tip - 3, 1 - panel % 2, 5)):
                rim = start if side == 0 else start + 15
                inward = 1 if side == 0 else -1
                y += base
                draw.polygon(((rim, y - 2), (rim + inward * 2, y + 1),
                              (rim + inward * 4, y + 3), (rim + inward, y + 4),
                              (rim, min(y + length, base + 47))), fill=dark)
            x, y = start + (3 + 3 * panel) % 10, base + tip - 2
            draw.line(((x, y), (x + 1, y - 3), (x + 3, y - 5)), fill=dark, width=1)
    atlas[...] = np.asarray(image)


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
    atlas = np.empty((SIZE, SIZE, 4), dtype=np.uint8)
    atlas[...] = (26, 10, 36, 255)
    _paint_shreds(atlas, lining=False)
    _paint_shreds(atlas, lining=True)
    _patches(atlas)
    _paint_cowl_panels(atlas)
    _frayed_edges(atlas)

    core, hot, halo = _neon_masks()
    halo2 = np.asarray(Image.fromarray(core).filter(ImageFilter.MaxFilter(5)))
    glow = np.empty_like(atlas)
    glow[...] = (255, 130, 225, 0)
    glow[(halo2 > 0) & (halo == 0), 3] = 48
    glow[halo > 0, 3] = 118
    glow[core > 0, 3] = 240
    glow[hot > 0, 3] = 255

    # Restaurar también el RGB bajo el halo de 2 texels (alpha 48), no
    # sólo las líneas principales: el re-render multiplica por ese RGB.
    with Image.open(ENERGY_RGB) as image:
        energy = np.asarray(image.convert("RGBA"))
    emissive = glow[..., 3] > 0
    assert np.array_equal(energy[..., 3] == 255, emissive), "cambió la cobertura del neón"
    atlas[emissive, :3] = energy[emissive, :3]
    assert (atlas[..., 3] == 255).all(), "atlas con texel transparente"
    return Image.fromarray(atlas), Image.fromarray(glow)
