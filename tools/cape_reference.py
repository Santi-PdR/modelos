#!/usr/bin/env python3
"""Registro de la captura original. Coordenadas absolutas en su PNG 1024×572.

Se registra con el portador como escala; NO se ajusta una cámara diferente
para cada versión. Sólo se traza la región observable de cada material; pelo,
brazo, ropa del portador, rejilla y motas no son parte del paño.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'referencias/REFERENCIA_CAPA.png'
SOURCE_SHA256 = '3a42a0feb6d468211eb6ae4c9c96f0c33c6f769063bc2805795b24dadfa07196'
YAW, PITCH, SCALE = 25., 10., 13.1
ORIGIN = 504., 490.
CROP = 387, 62, 672, 521

# Envolventes anotadas sobre REFERENCIA_CAPA.png. Las zonas negras profundas
# se subdividen por color más abajo para no aprender el pantalón ni el suelo.
MANTLE = ((473,203),(592,200),(615,230),(625,258),(637,281),(644,301),
          (629,294),(647,330),(649,352),(645,380),(645,404),(647,429),
          (635,415),(634,432),(619,416),(607,394),(603,441),(588,486),
          (580,481),(571,448),(560,438),(570,477),(565,497),(553,500),
          (541,465),(522,432),(521,417),(508,435),(492,457),(471,485),
          (457,486),(461,449),(473,420),(479,391),(475,373),(457,389),
          (427,406),(430,393),(448,354),(464,319),(475,282),(463,308),
          (450,319),(448,311),(462,282),(470,259),(470,234))
COWL = ((438,174),(449,173),(457,167),(462,156),(475,154),(481,146),
        (486,150),(498,145),(500,137),(510,140),(513,149),(521,151),
        (521,138),(535,142),(540,151),(547,154),(550,160),(563,164),
        (571,154),(581,153),(590,144),(601,147),(600,175),(591,195),
        (566,215),(544,222),(523,217),(504,205),(491,195),(470,189),(443,186))
LIP = ((465,181),(488,181),(500,194),(517,204),(532,217),(550,216),
       (567,207),(587,191),(596,181),(599,186),(581,203),(570,214),
       (551,226),(531,225),(510,215),(487,194),(465,191))
PADS = (((402,188),(427,186),(439,177),(457,179),(487,181),(490,226),
         (478,247),(467,252),(438,248),(434,231),(403,231)),
        ((593,181),(618,189),(618,205),(615,220),(597,219),(591,206)))

# Centros de los diez cortes más largos sobre el paño. Ancho/alto visual
# en la captura; NO incluye las partículas flotantes de la ilustración.
MARKS = ((498,229,4.4,24.), (514,257,3.5,15.), (522,290,4.8,19.),
         (474,344,4.3,23.), (556,250,3.4,19.), (591,240,4.7,18.),
         (585,297,4.8,15.), (616,372,5.2,19.), (547,391,4.7,25.),
         (537,430,4.2,20.))

COLLAR, CLOTH, SHOULDER, SEAM = 1, 2, 3, 4


def polygon(points, size):
    import numpy as np
    from PIL import Image, ImageDraw

    m = Image.new('1', size)
    ImageDraw.Draw(m).polygon(points, fill=1)
    return np.asarray(m, dtype=bool)


@lru_cache(maxsize=1)
def reference():
    """RGB de la captura + etiquetas conservadoras de las zonas observadas."""
    import numpy as np
    from PIL import Image

    im = Image.open(SOURCE).convert('RGB')
    a = np.asarray(im)
    r, g, b = np.moveaxis(a.astype(np.int16), -1, 0)
    tint = (r > g + 8) & (b >= g - 3) & (r > 25) & (g < 116)
    rose = (r >= 121) & (r - g >= 57) & (b - g >= 27) & (b >= 70)
    labels = np.zeros(a.shape[:2], np.uint8)
    for p in PADS:
        m = polygon(p, im.size)
        # La placa es carbón; no se considera paño el brazo, ni halo rosa.
        labels[m & (g < 74) & (b > r - 19) & ~rose] = SHOULDER
    labels[polygon(MANTLE, im.size) & tint] = CLOTH
    labels[polygon(COWL, im.size) & tint & ~rose] = COLLAR
    labels[polygon(LIP, im.size) & (r > g + 6) & (g < 95) & ~rose] = SEAM
    return a, labels, rose & (labels == CLOTH)


def basis(yaw=YAW, pitch=PITCH):
    t, p = math.radians(yaw), math.radians(pitch)
    s, c, sp, cp = math.sin(t), math.cos(t), math.sin(p), math.cos(p)
    return ((c, 0., s), (sp*s, cp, -sp*c), (-cp*s, sp, cp*c))


def projector(yaw=YAW, pitch=PITCH):
    import numpy as np
    return np.array(basis(yaw, pitch))


def pixel(v):
    """Puntos ya reflejados por GeckoLib/P.cube_points → píxeles del original."""
    import numpy as np
    q = np.asarray(v) @ projector().T
    return q[..., :2] * [SCALE, -SCALE] + ORIGIN


def lift(u, v, z):
    """Desproyección a (X,Y,Z) del GEO para un relieve Z elegido a mano."""
    (c, _, s), (sp_s, cp, sp_c), _ = basis()
    x = ((u - ORIGIN[0]) / SCALE - s * z) / c
    y = ((ORIGIN[1] - v) / SCALE - sp_s * x - sp_c * z) / cp
    return -x, y, z


def render_frame(crop=CROP):
    """Coord. de encuadre de preview_cloth, y caja del recorte dentro del lienzo."""
    x0, y0, x1, y1 = crop
    size = max(x1 - x0, y1 - y0)
    return size, ((size / 2 - (ORIGIN[0] - x0)) / SCALE,
                  ((ORIGIN[1] - y0) - size / 2) / SCALE, SCALE), (0, 0, x1-x0, y1-y0)
