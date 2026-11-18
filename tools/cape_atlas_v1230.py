#!/usr/bin/env python3
"""Atlas 128×128 de la capa equipada. No se usa para el item plegado.

Paño equipado: doblez envolvente en el cuello granate y caras violetas
anchas en los jirones, con roturas mates. Cada franja cae a su propio
ritmo según la altura de su punta. Sólo se pintan las UV existentes,
sin galones, emblemas ni cambios de silueta.

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

# Sombra, cuerpo y cresta. Burdeos en las primeras caras; a media
# caída las caras frías tienen más azul que rojo, sin competir en
# saturación con el rosa protegido.
CRIMSON_PLEATS = (
    (0,  ((33, 6, 18), (128, 26, 48), (178, 49, 71))),
    (14, ((30, 6, 17), (117, 24, 41), (168, 46, 66))),
    (26, ((25, 5, 17), (100, 18, 39), (145, 40, 61))),
    (37, ((22, 6, 23), (77, 17, 46), (125, 38, 68))),
    (47, ((17, 6, 22), (55, 16, 41), (102, 34, 64))),
)
VIOLET_PLEATS = (
    (0,  ((21, 8, 34), (56, 26, 82), (108, 60, 143))),
    (14, ((25, 11, 40), (64, 28, 97), (120, 68, 155))),
    (27, ((27, 11, 44), (83, 40, 122), (138, 81, 179))),
    (36, ((24, 10, 40), (93, 48, 137), (147, 91, 192))),
    (47, ((19, 8, 34), (72, 34, 106), (127, 69, 162))),
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
VIOLET_BREAK = (0.60, 0.56, 0.47, 0.52, 0.48, 0.65)
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
    """Pliegues sesgados con una segunda cara de tela fría, no de neón."""
    y_base = 48 if lining else 0
    for panel in range(6):
        u = 16 * panel
        hand = -1 if (panel + lining) % 2 else 1
        spine = np.interp(np.arange(48), FOLD_ROWS, FOLD_SPINES[(panel + 2 * lining) % 6])
        tip = 48 * tip_t(2 * panel + int(lining))
        for y, ridge in enumerate(spine):
            depth = min(1.0, y / tip)
            # Variación por bloques grande, sin un patrón de ruido por texel.
            step = (y // 5 + panel * 3 + y // 11) % 5 - 2
            spread = 5.05 - 0.85 * depth + 0.34 * step
            taper = max(0.0, (depth - 0.78) / 0.22)
            warm = _fold_tones(CRIMSON_PLEATS, y)
            cold = _fold_tones(VIOLET_PLEATS, y)
            for x in range(16):
                d = hand * (x - ridge)
                tone = 0
                if -spread - 1.6 <= d <= spread + 2.3 - taper:
                    tone = 1
                if -spread + 0.25 <= d <= spread + 0.6 - taper * 1.3:
                    tone = 2
                if -3.35 + 0.23 * step <= d < 0.85 - taper * 0.6:
                    tone = 3
                if -2.3 < d <= -0.55 and (y + panel * 4) % 18 < 12:
                    tone = 4
                # Surco quebrado que separa dos caras anchas del pliegue.
                if 2.25 + 0.47 * step < d < 3.65 + 0.47 * step and (y + panel * 7) % 23 < 13:
                    tone = 1
                if not lining:
                    # La cara fría asoma en diagonal y en distinto punto
                    # de cada faldón. La cresta granate cede más tarde.
                    onset = tip * VIOLET_BREAK[panel] - 0.72 * d + 0.42 * step
                    if tone >= 3 and panel in (0, 1, 5):
                        onset += 2.8
                    fade = min(1.0, max(0.0, (y - onset) / 7.0))
                    color = _mix(warm[tone], cold[tone], fade)
                else:
                    color = cold[tone]
                if x in (0, 15):
                    color = _mix((19, 6, 23), color, 0.40)
                atlas[y_base + y, u + x, :3] = color


# Sombra, cuerpo, luz; y punto más bajo del doblez en texels. Los paneles
# comparten UV dentro de cada parche: el quiebre se coloca en la parte
# central que realmente muestrean, incluidas las piezas más cortas.
COWL_FOLDS = {
    "dorsal": ((23, 5, 15), (71, 14, 29), (153, 41, 61), 8.0),
    "base": ((21, 4, 13), (66, 11, 24), (141, 32, 50), 5.2),
    "faldon": ((26, 5, 17), (79, 14, 31), (162, 45, 66), 7.2),
    "canto": ((17, 5, 15), (48, 9, 22), (89, 21, 40), 6.0),
    # Nombre del UV histórico: ahora es tela lisa doblada, no un emblema.
    "estrella": ((27, 5, 18), (82, 15, 32), (167, 48, 70), 9.5),
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
            lip = low - 7.3 * abs(side + 0.13) ** 2.15 + 1.30 * side
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
                if y > 19.5 - 4.1 * abs(side - 0.1):
                    color = _mix(color, shadow, 0.31)
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
