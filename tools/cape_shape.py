#!/usr/bin/env python3
"""Forma COMPARTIDA de la capa v1.17.0, derivada de la referencia.

`tools/reference_trace.py` mide el PNG del usuario y guarda
`tools/reference_profile.json`. Este módulo es la ÚNICA fuente de verdad de
la geometría del abanico de jirones: `armor_model_pipeline.py` lo usa para
colocar los cubos y `texture_pipeline.py` para DES-ABANICAR la referencia en
el atlas 96x48, de modo que cada cinta lleve exactamente los colores que le
corresponden en la captura.

La diferencia con v1.14/v1.15/v1.16: aquello era un CILINDRO de tiras
paralelas. La referencia es un ABANICO que nace estrecho en el cuello, se
abre hasta ~9 unidades a los lados y termina en PUNTAS a alturas distintas
(los jirones exteriores acaban ANTES que los centrales).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "tools" / "reference_profile.json"

# --- Parámetros medidos / compartidos -------------------------------------
RIBBONS = 16
SEGS = 6
# Tramos NO uniformes: los dos ultimos son cortos, para que la punta
# sea un remate rasgado y no una aguja de 5 unidades.
SEG_FRACTIONS = (0.0, 0.17, 0.34, 0.52, 0.70, 0.87, 1.0)
CANVAS_W, CANVAS_H = 96, 48
BAND_W = CANVAS_W / RIBBONS                  # 6.4 texels por cinta
BAND_H = CANVAS_H / SEGS                    # 8 texels por tramo

Y_TOP, Y_BOT = 23.0, 1.6                    # cuello -> puntas (unidades)
HEIGHT = Y_TOP - Y_BOT
X_NECK, X_TIP = 3.6, 9.4                   # apertura del abanico
W_TOP = 0.62                                # cintas se solapan arriba
W_MIN = 0.16                                # punta
THICK = 0.30

PROFILE_DATA = json.loads(PROFILE.read_text())


def palette_at(t: float) -> tuple[float, float, float]:
    """Color REAL medido en el PNG (interpolado entre filas de la mediana)."""
    rows = PROFILE_DATA["palette"]
    t = max(0.0, min(1.0, t))
    if t <= rows[0][0]:
        return tuple(float(v) for v in rows[0][1])
    for i in range(len(rows) - 1):
        t0, c0 = rows[i]
        t1, c1 = rows[i + 1]
        if t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            return tuple(c0[j] + (c1[j] - c0[j]) * f for j in range(3))
    return tuple(float(v) for v in rows[-1][1])


def _silhouette_raw(t: float) -> float:
    """Media anchura de la envolvente medida (unidades).

    v1.17.0 v1200: se usan los 31 puntos medidos, pero la COLA se
    recorta en t=0.867 y cierra suavemente a 6.6 unidades. Los ultimos
    puntos del PNG (5.17 en t=1.0) estan contaminados por el suelo de
    rejilla de Blockbench: usarlos literalmente hacia que todos los
    jirones convergiesen en un PICO, que la referencia no tiene.
    """
    pts = sorted((float(a), float(h))
                 for a, h in PROFILE_DATA["silhouette"] if a <= 0.867)
    smooth = []
    for i, (a, _h) in enumerate(pts):
        lo, hi = max(0, i - 1), min(len(pts), i + 2)
        smooth.append((a, sum(q[1] for q in pts[lo:hi]) / (hi - lo)))
    t = max(0.0, min(1.0, t))
    if t <= smooth[0][0]:
        return max(1.0, smooth[0][1])
    for i in range(len(smooth) - 1):
        t0, h0 = smooth[i]
        t1, h1 = smooth[i + 1]
        if t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            return max(1.0, h0 + (h1 - h0) * f)
    # Cola analitica: cierra, pero conserva un dobladillo ANCHO.
    last = smooth[-1]
    f = (t - last[0]) / max(1e-6, 1.0 - last[0])
    return max(1.0, last[1] * (1.0 - f) + 6.6 * f)


def silhouette(t: float) -> float:
    """Envolvente con el RECOGIDO del hombro medido en la captura.

    v1.17.0 v1210: al medir el render contra el PNG con la misma máscara,
    la campana se abria 1.7x demasiado pronto (t=0.2..0.7). El máximo de
    t~0.73 y el cierre de las puntas son correctos; lo que sobra es la
    apertura PREMATURA bajo la bufanda. Se estrecha un 17% con una media
    seno centrada en t=0.35, que vale CERO en el cuello y en el máximo.
    """
    h = _silhouette_raw(t)
    q = (max(0.0, min(1.0, t)) - 0.04) / 0.62
    if 0.0 < q < 1.0:
        h *= 1.0 - 0.17 * math.sin(math.pi * q)
    return h


def lateral(k: int) -> float:
    """-1 (izquierda) .. +1 (derecha) para la cinta k.

    v1.17.0 v1206: el espaciado uniforme hacia que los 16 jirones
    pareciesen un abanico generado por codigo. En la captura estan
    desigualmente repartidos: se anade una desviacion determinista,
    pequena y acotada, sin alterar la envolvente medida.
    """
    base = (k - (RIBBONS - 1) / 2.0) / ((RIBBONS - 1) / 2.0)
    return (base + 0.030 * math.sin(k * 2.83 + 0.4)
            + 0.014 * math.sin(k * 5.11 + 1.2))


def tip_t(k: int) -> float:
    """Los jirones exteriores acaban ANTES: el dobladillo es una V profunda."""
    # Casi TODOS los jirones llegan abajo: en la captura el dobladillo
    # conserva ~9 unidades de anchura y solo se deshilacha en puntas
    # desiguales. Antes los exteriores morian a t=0.8 y la capa acababa
    # en un pico que la referencia no tiene.
    base = 1.0 - 0.14 * abs(lateral(k)) ** 1.2
    return min(1.0, max(0.88, base + 0.060 * math.sin(k * 3.31 + 0.7)))


def ribbon_x(k: int, t: float) -> float:
    """Centro de la cinta k a la altura t (0 = cuello, 1 = puntas)."""
    a = lateral(k)
    # LA ENVOLVENTE MEDIDA DEL PNG, no un abanico lineal: la capa se abre
    # hasta t~0.73 y VUELVE A CERRARSE hacia las puntas (forma de campana).
    # Cerca del cuello se comprime para nacer bajo la bufanda.
    s = silhouette(min(1.0, max(0.0, t)))
    neck = 0.60 + 0.40 * min(1.0, max(0.0, t) / 0.35)
    # Deriva determinista por jiron: en la captura NO hay un abanico
    # perfectamente regular, las tiras estan rotas y desiguales.
    jitter = 0.16 * math.sin(k * 2.37 + 0.6)
    # TORCEDURA de la tela: crece hacia abajo, distinta por jiron.
    # Rompe la rectitud sin alterar la envolvente de campana medida.
    wrinkle = 0.32 * t * math.sin(k * 1.71 + t * 8.3 + 0.4)
    asym = 1.0 + 0.075 * a
    return a * s * neck * (1.0 + jitter) * asym + wrinkle


def ribbon_w(k: int, t: float) -> float:
    """Ancho de la cinta: masa de tela arriba, punta abajo."""
    f = min(1.0, t / tip_t(k))
    # Ancho CASI CONSTANTE (la referencia tiene ~15 tiras de 1-1.5
    # unidades separándose al abrirse) y una PUNTA final brusca.
    # En la captura los jirones se ENSANCHAN al bajar (0.6 -> 1.1
    # unidades) y solo en el ultimo 18% se rematan en punta corta.
    # Cada jiron tiene su propio grosor: en la captura NO son identicos.
    scale = 0.80 + 0.38 * (0.5 + 0.5 * math.sin(k * 2.71 + 1.2))
    if f <= 0.82:
        # Lobos anchos abajo: en la captura los jirones bajos son paño,
        # no tiras estrechas.
        # FINOS en el cuello, ANCHOS en los lobos bajos: en la captura
        # arriba los jirones son hebras y abajo son paño.
        # v1210: +14% de paño. La referencia tiene MUCHA más tela que
        # huecos (t=0.8: 48% de cobertura); el render anterior solo 19%.
        return (0.92 + 0.86 * f) * scale
    return (1.05 * ((1.0 - f) / 0.18) + 0.22) * scale


def ribbon_z(k: int) -> float:
    """Tres planos de profundidad solapados, sin Z-fighting."""
    return 2.30 + 1.05 * (0.5 + 0.5 * math.sin(k * 1.73 + 0.4))


def segment_bounds(k: int, n: int) -> tuple[float, float]:
    return tip_t(k) * SEG_FRACTIONS[n], tip_t(k) * SEG_FRACTIONS[n + 1]


def segment_geometry(k: int, n: int) -> dict:
    """Centro, tamaño, rotación Z y UV CONTINUA de un tramo de cinta."""
    t0, t1 = segment_bounds(k, n)
    tm = (t0 + t1) / 2.0
    x0, x1 = ribbon_x(k, t0), ribbon_x(k, t1)
    y0, y1 = Y_TOP - t0 * HEIGHT, Y_TOP - t1 * HEIGHT
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    dy, dx = y0 - y1, x1 - x0
    # Blockbench / GeckoLib NIEGAN X al importar. En espacio de pantalla el
    # desplazamiento es (-dx, -dy), así que la rotación Z debe ir con el
    # signo CONTRARIO: si no, el abanico se cierra hacia adentro.
    # CADA tramo se desvia un poco: en la captura los jirones no son
    # tablones rectos, sino telas rasgadas que cambian de direccion.
    theta = (-math.degrees(math.atan2(dx, dy))
             + 3.0 * math.sin(k * 1.83 + n * 2.41)
             + 2.1 * math.sin(k * 0.91 + n * 2.73))
    cx += 0.09 * math.sin(k * 2.11 + n * 1.37)
    cy += 0.07 * math.sin(k * 1.31 + n * 2.09)
    h = math.hypot(dx, dy) * 1.15   # solape: la cinta NO se parte en dados
    # Ancho MEDIO del tramo (no el del centro): asi el ultimo tramo afila
    # de verdad y la punta no vuelve a ser un rectangulo.
    w = (ribbon_w(k, t0) + 2.0 * ribbon_w(k, tm) + ribbon_w(k, t1)) / 4.0
    # Cada tramo se rasga a mano: anchura ligeramente distinta.
    w *= 0.96 + 0.08 * math.sin(k * 2.71 + n * 1.93)
    if n == SEGS - 1:
        w *= 0.90
    z = ribbon_z(k) - 0.05 + 0.055 * math.sin(k * 1.31 + n * 0.92)
    return dict(
        cx=cx, cy=cy, z=z, w=w, h=h, theta=theta,
        uv=[round(k * BAND_W, 4), round(t0 * CANVAS_H, 4)],
        uv_size=[round(BAND_W, 4), round((t1 - t0) * CANVAS_H, 4)],
    )


def reference_point(k: int, t: float) -> tuple[float, float]:
    """Dónde mirar en el RECORTE LIMPIO para el centro de la cinta k.

    Devuelve (x, y) en píxeles del recorte 310x375. Convierte las unidades
    del modelo al sistema de la captura usando el eje y la escala medidos.
    """
    p = PROFILE_DATA
    cx, ytop, ybot, ppu = (p["center_x"], p["y_top"], p["y_bottom"],
                           p["px_per_unit"])
    rx0, ry0 = p["roi"][0], p["roi"][1]
    x = cx + ribbon_x(k, t) * ppu - rx0
    y = ytop + t * (ybot - ytop) - ry0
    return x, y


def nearest_ribbon(t: float, xrel: float) -> int:
    """Cinta cuya línea central pasa más cerca de una marca de energía."""
    x = xrel * 8.6
    return min(range(RIBBONS), key=lambda k: abs(ribbon_x(k, min(t, tip_t(k))) - x))


def energy_marks() -> list[dict]:
    return PROFILE_DATA["energy_marks"]


def floating_motes() -> list[dict]:
    return PROFILE_DATA["floating_motes"]


def vein_marks(count: int = 10) -> list[dict]:
    """Subset de las grietas REALES del PNG que se convierte en VÓXELES 3D
    emisivos animados (no solo pintados en el atlas)."""
    marks = [m for m in PROFILE_DATA["energy_marks"] if not m["floating"]]
    step_n = max(1, len(marks) // max(1, count))
    return [marks[(i * step_n) % len(marks)] for i in range(count)]
