#!/usr/bin/env python3
"""Atlas 128×128 de la capa equipada. No se usa para el item plegado.

v1.56: paño pintado desde cero, en carmesí de brasa y ciruela. Cada franja
vertical de 16 texels corresponde a un mechón; su cresta, sombra y galón
siguen la misma altura de UV desde el hombro hasta la punta. El cuello
usa paneles propios a densidad constante. Desgaste y costuras son RGB.

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

# De arriba abajo: triples (sombra profunda, cuerpo del pliegue, cresta).
# La base de la capa externa pasa de brasa a ciruela; el forro es frío.
OUTER_YARN = (
    (0,  ((52, 13, 32), (147, 36, 61), (224, 112, 116))),
    (20, ((49, 14, 34), (134, 38, 66), (206, 97, 117))),
    (33, ((32, 12, 38), (103, 43, 79), (170, 91, 132))),
    (47, ((22, 11, 34), (58, 30, 76), (117, 78, 131))),
)
INNER_YARN = (
    (0,  ((27, 13, 39), (88, 48, 104), (167, 110, 168))),
    (22, ((24, 12, 37), (71, 36, 92), (149, 95, 154))),
    (47, ((16, 9, 30), (45, 24, 67), (103, 65, 119))),
)
# RGB congelado de la textura v1.55.0 (sólo texels cubiertos por el glow).
ENERGY_RGB = Path(__file__).resolve().parent / "originals" / "capa_glow_rgb.png"


def _mix(a, b, q):
    return tuple(round(a[i] + (b[i] - a[i]) * q) for i in range(3))


def _yarn_at(rows, v):
    for (v0, p0), (v1, p1) in zip(rows, rows[1:]):
        if v <= v1:
            return tuple(_mix(a, b, (v - v0) / (v1 - v0)) for a, b in zip(p0, p1))
    return rows[-1][1]


def _drape(arr, v0, rows, *, lining=False) -> None:
    """Paño nuevo: pliegues sesgados de 4–7 texels y doble galón tejido en V."""
    for v in range(48):
        shadow, body, crest = _yarn_at(rows, v)
        tones = (shadow, _mix(shadow, body, 0.55), body, _mix(body, crest, 0.62), crest)
        for u in range(96):
            panel, x = divmod(u, 16)
            pleat = 6.0 + 1.4 * math.sin(v * 0.13 + panel * 1.21 + lining * 1.4)
            # La cara iluminada es ancha, la sombra termina en un canto
            # abrupto. No es una onda suave sobre el atlas anterior.
            d = x - pleat
            tone = (4 if -0.8 <= d <= 1.7 else 3 if -2.4 <= d <= 3.0
                    else 2 if -4.6 <= d <= 4.0 else 1 if -5.8 <= d <= 6.3 else 0)
            color = tones[tone]
            # Trabajo de telar a escala de juego: una arista pespunteada
            # y el galón atraviesan varias filas, no añaden ruido por píxel.
            if x in (1, 14) and (v + panel) % 5 < 3 and v < 42:
                color = _mix(shadow, crest, 0.47 if x == 1 else 0.32)
            braid_y = 14 + round(9 * (1 - abs((u + 0.5) / 48 - 1)))
            offset = v - braid_y - (3 if lining else 0)
            braid = (166, 121, 164) if lining else (218, 141, 114)
            if offset in (-1, 2, 6):
                color = _mix(color, shadow, 0.68)
            elif offset in (0, 1, 5):
                # Una pasada larga de hilo y otra fina, con el relieve
                # del pliegue todavía visible por debajo del bordado.
                color = _mix(color, braid, (0.52 if offset == 5 else 0.69) + 0.04 * tone)
            arr[v0 + v, u, :3] = color


def _paint_cowl_panels(arr) -> None:
    palettes = {
        "dorsal": ((52, 13, 32), (126, 34, 55), (184, 70, 87), (225, 134, 113)),
        "base": ((37, 13, 31), (93, 27, 47), (144, 60, 73), (173, 94, 88)),
        "faldon": ((43, 13, 37), (112, 31, 60), (169, 64, 96), (203, 114, 111)),
        "canto": ((33, 12, 29), (73, 24, 45), (107, 46, 68), (143, 71, 80)),
    }
    for name, (u0, v0, u1, v1) in COWL_TILES.items():
        shadow, body, crest, piping = palettes["faldon" if name == "estrella" else name]
        w, h = u1 - u0, v1 - v0
        for y in range(h):
            for x in range(w):
                xrel = (x + 0.5) / w
                crease = 1 - min(1.0, abs(xrel - 0.39) / 0.55)
                color = _mix(body, crest, crease * 0.92)
                color = _mix(color, shadow, 0.49 * (y / (h - 1)) + 0.19 * (1 - crease))
                if y in (1, 2):
                    color = _mix(piping, color, 0.11 + 0.18 * (1 - crease))
                elif y == 4:
                    color = shadow
                elif name != "canto" and 6 <= y <= 19 and x == w // 2 - 3 - y // 10:
                    if y % 4 < 2:
                        color = _mix(color, piping, 0.36)
                if name == "estrella":
                    # Estrella de ceniza bordada en el pliegue principal.
                    # Los cuatro rayos y su borde se leen a escala de juego.
                    dx, dy = abs(x - w // 2), abs(y - 13)
                    if (dx <= 1 and dy <= 6) or (dy <= 1 and dx <= 4) or dx + dy <= 4:
                        color = shadow
                    if (dx == 0 and dy <= 5) or (dy == 0 and dx <= 3) or dx + dy <= 2:
                        color = piping if x <= w // 2 else _mix(piping, crest, 0.52)
                    if dx + dy <= 1:
                        color = (223, 161, 133)
                arr[v0 + y, u0 + x, :3] = color


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
    _drape(atlas, 0, OUTER_YARN)
    _drape(atlas, 48, INNER_YARN, lining=True)
    _patches(atlas)
    _paint_cowl_panels(atlas)
    _wear_holes(atlas)

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
