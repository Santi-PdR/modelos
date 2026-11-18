#!/usr/bin/env python3
"""Atlas 128×128 de la capa equipada. No se usa para el item plegado.

Paño de sarga granate y forro mineral malva, pintados por gajo. Las
vetas de hilo siguen el pliegue, y las roturas muestran un borde pálido
antes de caer a sombra. Acero azulado quemado en hombreras y cadena.

El diseño de energía anterior se conserva. La
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

# Sombra, cuerpo y cresta. Burdeos en las primeras caras; a media
# caída las caras frías tienen más azul que rojo, sin competir en
# saturación con el rosa protegido.
CRIMSON_PLEATS = (
    (0,  ((37, 5, 20), (119, 22, 42), (201, 68, 89))),
    (15, ((44, 8, 25), (141, 31, 54), (219, 80, 98))),
    (25, ((32, 6, 26), (112, 23, 52), (192, 61, 95))),
    (36, ((24, 8, 30), (82, 18, 56), (144, 46, 97))),
    (47, ((14, 6, 22), (57, 13, 44), (118, 38, 76))),
)
VIOLET_PLEATS = (
    (0,  ((23, 12, 39), (53, 34, 84), (113, 77, 148))),
    (15, ((26, 11, 46), (72, 42, 107), (130, 86, 173))),
    (25, ((30, 13, 50), (87, 48, 127), (151, 104, 193))),
    (38, ((26, 12, 43), (94, 54, 139), (165, 115, 202))),
    (47, ((17, 8, 29), (75, 35, 110), (137, 88, 172))),
)
# Trayectorias a mano en la anchura de cada UV (0..15). El forro
# desplaza la trayectoria para que sus crestas no calquen las de arriba.
FOLD_ROWS = (0, 8, 16, 24, 32, 40, 47)
FOLD_SPINES = (
    (12, 10, 6, 4, 5, 8, 6),
    (4, 6, 9, 11, 10, 8, 10),
    (10, 10, 8, 5, 5, 8, 9),
    (5, 4, 7, 9, 6, 5, 7),
    (10, 11, 9, 8, 5, 7, 10),
    (7, 5, 6, 9, 11, 9, 7),
)
# Fracción de la altura REAL de cada jirón, no una banda horizontal.
# Algunos faldones cortos todavía muestran más granate que violeta.
VIOLET_BREAK = (0.72, 0.53, 0.42, 0.45, 0.40, 0.66)
# RGB congelado de la textura v1.55.0 (sólo texels cubiertos por el glow).
ENERGY_RGB = Path(__file__).resolve().parent / "originals" / "capa_glow_rgb.png"


def _mix(a, b, q):
    return tuple(round(a[i] + (b[i] - a[i]) * q) for i in range(3))


def _tones_at(stops, y):
    for (lo, a), (hi, b) in zip(stops, stops[1:]):
        if y <= hi:
            return tuple(_mix(c0, c1, (y - lo) / (hi - lo)) for c0, c1 in zip(a, b))
    return stops[-1][1]


def _fold_tones(stops, y):
    shadow, body, crest = _tones_at(stops, y)
    return shadow, _mix(shadow, body, 0.49), body, _mix(body, crest, 0.45), crest


def _paint_shreds(atlas: np.ndarray, *, lining: bool) -> None:
    """Sarga interrumpida, crestas anchas y contracanto en cada gajo."""
    y_base = 48 if lining else 0
    for panel in range(6):
        u = 16 * panel
        hand = -1 if (panel + lining) % 2 else 1
        spine = np.interp(np.arange(48), FOLD_ROWS, FOLD_SPINES[(panel + 2 * lining) % 6])
        tip = 48 * tip_t(2 * panel + int(lining))
        for y, ridge in enumerate(spine):
            depth = min(1.0, y / tip)
            step = (y // 6 + panel * 3) % 5 - 2
            spread = 5.7 - 1.38 * depth + 0.31 * step
            warm = _fold_tones(CRIMSON_PLEATS, y)
            cold = _fold_tones(VIOLET_PLEATS, y)
            for x in range(16):
                d = hand * (x - ridge)
                tone = 0
                if -spread - 1.0 <= d <= spread + 1.9:
                    tone = 1
                if -spread <= d <= spread - 0.6:
                    tone = 2
                if -3.9 + 0.3 * step <= d <= -0.5:
                    tone = 3
                if -2.9 + 0.24 * step < d <= -1.6 and (y + panel * 6) % 22 < 16:
                    tone = 4
                # Giro del canto: recorte roto, con una cara visible por
                # detrás. No repite una raya continua de arriba a abajo.
                if 0.4 < d < 1.55 + 0.35 * step and y > 7 + (panel * 3) % 12:
                    tone = 1
                if lining:
                    color = cold[tone]
                else:
                    onset = tip * VIOLET_BREAK[panel] + 0.85 * d + 0.48 * step
                    fade = min(1.0, max(0.0, (y - onset) / 6.0))
                    color = _mix(warm[tone], cold[tone], fade)
                if tone > 1 and (x + hand * (y // 2) + panel) % 6 == 0 and y % 9 < 7:
                    # Dos texels de sarga, sólo en las caras anchas.
                    color = _mix(color, cold[4] if lining else warm[4], .12)
                if x in (0, 15):
                    color = _mix((22, 7, 29), color, .25 + .12 * (y % 6 < 3))
                atlas[y_base + y, u + x, :3] = color


# Sombra, cuerpo, luz; y punto más bajo del doblez en texels. Los paneles
# comparten UV dentro de cada parche: el quiebre se coloca en la parte
# central que realmente muestrean, incluidas las piezas más cortas.
COWL_FOLDS = {
    "dorsal": ((26, 6, 21), (98, 17, 42), (195, 64, 91), 6.7),
    "base": ((21, 5, 18), (81, 13, 37), (157, 49, 72), 5.3),
    "faldon": ((29, 7, 25), (109, 22, 47), (208, 78, 102), 7.6),
    "canto": ((15, 6, 20), (52, 11, 30), (111, 32, 56), 6.0),
    "estrella": ((26, 6, 21), (100, 19, 45), (191, 64, 95), 7.3),
}


def _fold_edge(color, shadow, light, distance, weight):
    """Sombreado del doblez: ascenso graduado, quiebre y valle mate."""
    if -5.6 < distance < -0.4:
        q = (distance + 5.6) / 5.2
        # Planos anchos discretos para que el doblez no se lea como hilo.
        return _mix(color, light, (0.18 + 0.62 * round(q * 5) / 5) * weight)
    if -0.4 <= distance < 0.9:
        return _mix(color, light, 0.75 * weight)
    if 0.9 <= distance < 5.0:
        q = (5.0 - distance) / 4.1
        return _mix(color, shadow, (0.21 + 0.61 * round(q * 4) / 4) * weight)
    return color


def _paint_cowl_panels(atlas: np.ndarray) -> None:
    """Pliegue ancho que envuelve el cuello y se pierde por debajo."""
    for name, (u0, v0, u1, v1) in COWL_TILES.items():
        shadow, body, crest, low = COWL_FOLDS[name]
        w, h = u1 - u0, v1 - v0
        for x in range(w):
            side = 2.0 * (x + 0.5) / w - 1
            # Curva con fondo redondeado, no un segundo galón en V.
            lip = low - 5.3 * abs(side + 0.23) ** 2.05 + 3.10 * side
            # La caída secundaria no es paralela; se apaga hacia un borde.
            second = low + 7.7 - 4.1 * abs(side - 0.18) ** 1.65 + 1.3 * side
            fold_weight = 0.98 - 0.48 * abs(side + 0.08)
            inner_weight = 0.71 * max(0.0, 1.0 - abs(side - 0.09) * 1.35)
            for y in range(h):
                depth = y / (h - 1)
                color = _mix(body, shadow, 0.08 + 0.22 * depth + 0.32 * side ** 2)
                color = _fold_edge(color, shadow, crest, y - lip, fold_weight)
                if name not in ("base", "canto"):
                    color = _fold_edge(color, shadow, crest, y - second, inner_weight)
                if y > 13.6 + 5.4 * side - 1.8 * side * side:
                    lining = _mix((36, 14, 58), color, 0.44)
                    color = _mix(color, lining, 0.33 + 0.40 * depth)
                if name != "canto" and (x + y // 2) % 7 == 0 and 3 < y < 17:
                    color = _mix(color, crest, 0.19)
                # Fragmentos de hilo expuesto, cortos y diagonales.
                if name in ("faldon", "estrella") and 8 <= y <= 12 and x in (y - 1, y, 28 - y // 2):
                    color = _mix(color, (231, 111, 131), 0.24)
                if abs(side + 0.15 * math.sin(y * 0.24)) > 0.59:
                    color = _mix(color, shadow, 0.49)
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
    """Acero de tormenta: biseles interiores, remaches y arañazos mates."""
    u, v, _, _ = PAD
    _steel(arr, PAD, (102, 101, 134), (31, 28, 46))
    image = Image.fromarray(arr)
    draw = ImageDraw.Draw(image)
    def trace(pts, color):
        draw.line([(u+x, v+y) for x, y in pts], fill=(*color, 255))
    trace([(1, 12), (1, 5), (4, 2), (12, 2)], (160, 160, 188))
    trace([(3, 12), (11, 12), (13, 10), (13, 4)], (28, 22, 35))
    trace([(4, 10), (8, 6), (11, 6)], (67, 39, 70))
    trace([(7, 8), (9, 5)], (157, 133, 155))
    trace([(8, 8), (10, 6)], (35, 25, 45))
    for x, y in ((4, 4), (11, 4), (4, 11), (11, 10)):
        draw.point((u + x + 1, v + y + 1), fill=(24, 22, 36, 255))
        draw.point((u + x, v + y), fill=(201, 185, 200, 255))
    arr[...] = np.asarray(image)


def _pad_side(arr) -> None:
    u, v, _, _ = PAD_SIDE
    _steel(arr, PAD_SIDE, (96, 88, 118), (19, 15, 33), diag=False)
    for y, color in ((2, (155, 149, 181)), (4, (51, 39, 63)), (9, (93, 36, 67)),
                     (10, (60, 18, 38)), (13, (18, 14, 29))):
        arr[v + y, u + 1:u + 15, :3] = color
    for k in (4, 10):
        arr[v + 6:v + 8, u + k, :3] = (142, 117, 152)
        arr[v + 8, u + k + 1, :3] = (28, 19, 40)


def _crest(arr) -> None:
    u, v, _, _ = CREST
    _steel(arr, CREST, (169, 162, 193), (52, 44, 77), diag=False)
    arr[v + 3, u + 1:u + 15, :3] = (188, 181, 204)
    arr[v + 5, u + 2:u + 14, :3] = (61, 42, 70)
    arr[v + 11, u + 3:u + 13, :3] = (101, 52, 90)


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
                c = _mix((133, 125, 153), (47, 39, 63), (i + j) / span)
                if r > 0.86 and dx < 0.0 and dy < 0.0:
                    c = (222, 211, 235)      # brillo especular
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


# (centro u, fracción v, dirección) de la rotura en las 6 franjas.
TEARS = ((5, .78, 1), (9, .88, -1), (6, .73, 1), (9, .81, 1), (10, .76, -1), (6, .84, -1))


def _frayed_edges(atlas: np.ndarray) -> None:
    """Muescas y hebras partidas. La sombra es RGB, nunca un recorte alfa."""
    for lining in (False, True):
        base = 48 if lining else 0
        for panel in range(6):
            start = panel * 16
            band = atlas[base:base + 48, start:start + 16]
            tile = Image.fromarray(band.copy())
            draw = ImageDraw.Draw(tile)
            tip = min(47, int(48 * tip_t(2 * panel + int(lining))))
            x, reach, hand = TEARS[(panel + 2 * lining) % 6]
            y = round(tip * reach)
            if lining:
                hand *= -1
            dark = (13, 6, 23, 255)
            thread = (89, 46, 110, 255) if lining or panel in (2, 3, 4) else (105, 24, 57, 255)
            draw.polygon(((x - hand, y - 5), (x + hand, y - 3),
                          (x + hand, y - 1), (x + 2 * hand, y + 1),
                          (x + hand, y + 4), (x - hand, y + 2), (x - hand, y)),
                         fill=dark)
            # Un lado retiene el hilo al que le pega la luz; el otro
            # desaparece en sombra. Sin repetir un pespunte regular.
            draw.line(((x + 2 * hand, y - 3), (x + 2 * hand, y - 1),
                       (x + 3 * hand, y + 1)), fill=thread, width=1)
            side = 15 if (panel + lining) % 2 else 0
            inside = -1 if side else 1
            cut = tip - 4
            draw.polygon(((side, cut - 4), (side + 3 * inside, cut),
                          (side + 2 * inside, cut + 2), (side, cut + 4)), fill=dark)
            band[...] = np.asarray(tile)


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
