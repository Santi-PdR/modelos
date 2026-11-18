#!/usr/bin/env python3
"""Doce gajos trazados sobre la captura: dos capas, extremos escalonados.

El trazado registra proporciones en el plano de la cámara. El relieve en Z
se construye por capa; no es una lámina ni un canal de posición animado.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from cape_reference import lift

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'tools/reference_profile.json'
PROFILE_DATA = json.loads(PROFILE.read_text())
RIBBONS = 12
SEGS = 6
SEG_FRACTIONS = (0., .16, .33, .51, .69, .86, 1.)
Y_TOP, Y_BOT = 22.42, 1.30
HEIGHT = Y_TOP - Y_BOT

# Puntos en orden GEO (+X se refleja en pantalla). Paño granate por fuera,
# forro violeta largo por debajo. La última punta esculpida sobresale un
# poco de la última coordenada, como en el recorte de la referencia.
PATHS = (
    ((599, 212), (601, 251), (611, 281), (630, 294)),
    ((593, 218), (604, 288), (617, 346), (632, 412)),
    ((583, 210), (599, 259), (616, 317), (637, 365)),
    ((571, 222), (587, 286), (593, 354), (621, 415)),
    ((554, 216), (554, 277), (570, 338), (589, 398)),
    ((560, 221), (558, 300), (577, 404), (578, 468)),
    ((529, 223), (531, 264), (536, 308), (549, 348)),
    ((540, 222), (529, 308), (534, 410), (546, 486)),
    ((507, 217), (501, 273), (477, 341), (436, 388)),
    ((523, 222), (522, 314), (497, 406), (455, 475)),
    ((487, 210), (490, 249), (478, 291), (457, 305)),
    ((481, 217), (485, 265), (485, 332), (483, 379)),
)
WIDTHS = (1.54, 2.31, 2.48, 2.49, 2.3, 2.67, 2.45, 2.46, 2.72, 2.86, 1.53, 2.02)
DEPTH_BIAS = (.17, -.08, .26, -.11, .34, .04, .29, -.12, .39, -.15, .18, -.25)
# Separación del torso, 16 unidades de modelo = 1 bloque. Parte de la pose
# esculpida, no de la animación.
CLOTH_SETBACK = 2.02


def palette_at(t):
    """Paleta histórica del item plegado, que no se vuelve a pintar."""
    rows = PROFILE_DATA['palette']
    if t <= rows[0][0]:
        return tuple(rows[0][1])
    for (t0, c0), (t1, c1) in zip(rows, rows[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(a + (b - a) * f for a,b in zip(c0,c1))
    return tuple(rows[-1][1])


def layer(k: int) -> str:
    return 'outer' if k % 2 == 0 else 'inner'


def lateral(k):
    return (k - 5.5) / 5.5


def tip_t(k):
    # Alcance global para asignar una sección de la cadena de bisagras.
    return (PATHS[k][-1][1] - PATHS[k][0][1]) / 278.


def _fraction(k, t):
    return min(1., max(0., t / tip_t(k)))


def ribbon_z(k, t=0.):
    f = _fraction(k, t)
    return (1.71 + .47 * (layer(k) == 'outer') + DEPTH_BIAS[k]
            + .21 * (1 - abs(lateral(k))) + 1.12 * f
            + .11 * math.sin(4.2*f + 1.13*k))


def _path(k, t):
    p = PATHS[k]
    f = _fraction(k, t)
    s = (.0, .32, .67, 1.)
    i = min(2, max(0, sum(f >= x for x in s) - 1))
    q = (f - s[i]) / (s[i+1] - s[i])
    return tuple(a + (b-a) * q for a,b in zip(p[i], p[i+1]))


def ribbon_point(k, t):
    # La trayectoria se registra en la cara exterior, no en el eje de Z.
    x, y, _ = lift(*_path(k,t), ribbon_z(k,t) + CLOTH_SETBACK + .66)
    return x, y, ribbon_z(k,t)


def ribbon_x(k, t):
    return ribbon_point(k,t)[0]


def fan_x(k, t):
    return ribbon_x(k, min(t, tip_t(k)))


def silhouette(t):
    return max(abs(ribbon_x(k,t)) for k in range(RIBBONS) if t <= tip_t(k) + 1e-6)


def ribbon_w(k, t):
    f = _fraction(k, t)
    # Cuerpo ancho hasta la deshiladura; puntas de distinto ancho. La
    # última parte no es una vara larga: conserva la cara hasta el borde.
    r = 0.84 + .33 * math.sin(math.pi * min(1., f+.07))
    a = min(1., max(0., (f - (.57 + .045*(k%3))) / (.43 - .045*(k%3))))
    return .22 + (WIDTHS[k] * r - .22) * (1 - a*a)


def segment_bounds(k, n):
    return tuple(tip_t(k) * f for f in SEG_FRACTIONS[n:n+2])


def segment_geometry(k, n):
    t0, t1 = segment_bounds(k,n)
    tm = (t0+t1)/2
    x0, y0, z0 = ribbon_point(k,t0)
    x1, y1, z1 = ribbon_point(k,t1)
    dx, dy = x1-x0, y0-y1
    length = math.hypot(dx, dy)
    w = (ribbon_w(k,t0) + 2*ribbon_w(k,tm) + ribbon_w(k,t1)) / 4
    return dict(cx=(x0+x1)/2, cy=(y0+y1)/2, z=(z0+z1)/2,
                w=w*(.98 + .04*math.sin(k*1.7+n)),
                h=length*((1.28, 1.38, 1.45, 1.68, 1.74, 1.26)[n]),
                theta=-math.degrees(math.atan2(dx,dy)),
                bend=math.degrees(math.atan2(z1-z0,length)),
                twist=8.0*lateral(k) + 6.4*math.sin(k*1.18+n*.48),
                layer=layer(k))
