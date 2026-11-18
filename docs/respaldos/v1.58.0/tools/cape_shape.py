#!/usr/bin/env python3
"""v1.23.0 — FORMA DE LA CAPA: 12 MECHONES ANCHOS EN DOS CAPAS.

El usuario pidió REHACER la geometría: «deje de parecer hecha de tiras
finas y sueltas... 10 a 14 mechones anchos, planos y superpuestos en dos
capas (una interna morada oscura y una externa rojo carmesí) que se curven
orgánicamente y terminen en punta afilada para dar volumen».

Antes había 16 cintas de ~0.6-1.5 unidades con huecos negros: una élitra.
Ahora:

  * 12 mechones (``RIBBONS``), 6 externos carmesí + 6 internos morado,
    intercalados. Cada uno mide ~1.8 arriba y ~2.6 en la panza, con
    SOLAPE real entre vecinos: no queda ni una rendija de élitra.
  * Dos CAPAS con profundidad distinta (``ribbon_z``): la externa va
    delante en +Z (la que se ve desde atrás), la interna asoma por los
    bordes y por debajo.
  * Curva ORGÁNICA: x(t) y z(t) son curvas suaves propias de cada mechón;
    cada tramo se gira según la tangente local, así que el mechón se
    arquea en vez de ser un tablón recto.
  * PUNTA AFILADA: el ancho decae con ``smoothstep`` desde t=0.68 y el
    último tramo es una aguja de 0.10 unidades. La V de la referencia
    sigue: los mechones exteriores mueren antes (t~0.70) y los centrales
    llegan al dobladillo (t~1.0).

API pública que consumen armor_model_pipeline.py, texture_pipeline.py,
audit_model.py y el workflow: RIBBONS, SEGS, HEIGHT, Y_TOP, X_NECK,
palette_at, silhouette, lateral, tip_t, fan_x, ribbon_x, ribbon_w,
ribbon_z, segment_bounds, segment_geometry, nearest_ribbon, vein_marks.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "tools" / "reference_profile.json"

# --- Parámetros compartidos ------------------------------------------------
RIBBONS = 12                     # 10-14 pedidos: 12 (6 + 6 en dos capas)
SEGS = 6                        # 6 tramos + 1 punta = 7 huesos por mechón
SEG_FRACTIONS = (0.0, 0.16, 0.33, 0.51, 0.69, 0.86, 1.0)
CANVAS_W, CANVAS_H = 96, 48
BAND_W = CANVAS_W / (RIBBONS // 2)   # 16 texels por mechón y capa
BAND_H = CANVAS_H / SEGS

Y_TOP, Y_BOT = 23.0, 1.6
HEIGHT = Y_TOP - Y_BOT
X_NECK, X_TIP = 3.4, 8.9
W_TOP, W_MIN = 1.95, 0.10
THICK = 0.62

PROFILE_DATA = json.loads(PROFILE.read_text())


def palette_at(t: float) -> tuple[float, float, float]:
    """Color medido en el PNG de referencia (lo usa el item plegado)."""
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


def lateral(k: int) -> float:
    """-1 (mechón exterior izq) .. +1 (exterior der)."""
    return (k - (RIBBONS - 1) / 2.0) / ((RIBBONS - 1) / 2.0)


def layer(k: int) -> str:
    """Dos capas INTERCALADAS: externa carmesí, interna morado oscuro."""
    return "outer" if k % 2 == 0 else "inner"


def _smooth(a: float, b: float, x: float) -> float:
    q = max(0.0, min(1.0, (x - a) / (b - a)))
    return q * q * (3.0 - 2.0 * q)


def silhouette(t: float) -> float:
    """Semiancho de la capa: abre hasta t~0.75 y cierra en V al bajar."""
    t = max(0.0, min(1.0, t))
    return (X_NECK + 4.70 * min(1.0, t / 0.75) ** 0.80
            - 0.90 * max(0.0, (t - 0.75) / 0.25))


def tip_t(k: int) -> float:
    """V: las alas exteriores mueren a t~0.70, el centro baja a t~1.0."""
    a = abs(lateral(k))
    base = 1.0 - 0.34 * a ** 1.30
    wobble = 0.025 * math.sin(k * 2.13) + 0.018 * math.cos(k * 1.31)
    inner = 0.025 if layer(k) == "inner" else 0.0   # el forro asoma abajo
    return max(0.66, min(1.02, base + wobble + inner))


def fan_x(k: int, t: float) -> float:
    """Apertura radial suave; se conserva por compatibilidad con el audit."""
    return lateral(k) * silhouette(t)


def ribbon_x(k: int, t: float) -> float:
    """Centro X del mechón: curva ORGÁNICA, no recta radial."""
    a = lateral(k)
    tt = max(0.0, min(1.0, t))
    x = a * (X_NECK + (X_TIP - X_NECK) * tt ** 0.88)
    # Cada mechón serpentea con fase propia: pliegues, no tablones.
    x += (0.42 * math.sin(k * 1.83 + tt * 2.35)
          + 0.20 * math.cos(k * 0.91 + tt * 4.10)) * tt
    return x


def ribbon_w(k: int, t: float) -> float:
    """Ancho PLANO y SOLAPADO que afila hasta una punta real."""
    tt = max(0.0, min(1.0, t))
    base = W_TOP + 1.15 * tt
    # v1.23.0: el mechón se convierte en TRIÁNGULO desde t=0.52,
    # no en una aguja que aparece de golpe en el último tramo.
    taper = 1.0 - 0.94 * _smooth(0.52, 1.0, tt)
    w = max(W_MIN, base * taper)
    # Variación artesanal por mechón (sin ruido aleatorio).
    w *= 0.96 + 0.07 * math.sin(k * 2.71 + 0.4)
    return w


def ribbon_z(k: int, t: float = 0.0) -> float:
    """PROFUNDIDAD de las DOS CAPAS + curvatura 3D que envuelve el torso.

    Externa (carmesí) va en +Z y es la que se ve desde atrás; interna
    (morado) queda ~0.65 más cerca del cuerpo y asoma por los bordes y
    por las puntas. Ambas nacen pegadas a los hombros y caen hacia atrás.
    """
    tt = max(0.0, min(1.0, t))
    a = abs(lateral(k))
    base = 1.55 + 1.30 * tt + 0.40 * (1.0 - a) ** 1.3
    offset = 0.42 if layer(k) == "outer" else -0.24
    curl = 0.16 * math.sin(k * 1.73 + tt * 3.05 + 0.4)
    return base + offset + curl


def segment_bounds(k: int, n: int) -> tuple[float, float]:
    return tip_t(k) * SEG_FRACTIONS[n], tip_t(k) * SEG_FRACTIONS[n + 1]


def segment_geometry(k: int, n: int) -> dict:
    """Centro, tamaño, rotación tangencial y UV de un tramo de mechón."""
    t0, t1 = segment_bounds(k, n)
    tm = (t0 + t1) / 2.0
    x0, x1 = ribbon_x(k, t0), ribbon_x(k, t1)
    y0, y1 = Y_TOP - t0 * HEIGHT, Y_TOP - t1 * HEIGHT
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    dy, dx = y0 - y1, x1 - x0
    # Rotación Z = tangente local + una ligera onda de pliegue por tramo.
    theta = (-math.degrees(math.atan2(dx, dy))
             + 3.2 * math.sin(k * 1.83 + n * 2.41)
             + 1.8 * math.sin(k * 0.91 + n * 2.73))
    # Curva orgánica también en Z: los tramos bajos se echan hacia atrás.
    z = ribbon_z(k, tm) - 0.05 + 0.05 * math.sin(k * 1.31 + n * 0.92)
    h = math.hypot(dx, dy) * 1.22       # SOLAPE: no se parte en dados
    w = (ribbon_w(k, t0) + 2.0 * ribbon_w(k, tm) + ribbon_w(k, t1)) / 4.0
    w *= 0.97 + 0.06 * math.sin(k * 2.71 + n * 1.93)
    if n == SEGS - 1:
        w *= 0.88
    layer_v = 0.0 if layer(k) == "outer" else 48.0
    stripe = (k // 2) * BAND_W
    return dict(
        cx=cx, cy=cy, z=z, w=w, h=h, theta=theta, layer=layer(k),
        uv=[round(stripe + 0.5, 4), round(layer_v + t0 * CANVAS_H, 4)],
        uv_size=[round(BAND_W - 1.0, 4),
                 round((t1 - t0) * CANVAS_H * 1.1, 4)],
    )


def reference_point(k: int, t: float) -> tuple[float, float]:
    """Dónde mirar en el recorte limpio (compatibilidad con el audit)."""
    from reference_canvas import canvas as foto  # noqa: F401
    x = 48.0 + ribbon_x(k, t) * (96.0 / 17.80)
    y = t * 48.0
    return x, y


def nearest_ribbon(t: float, xrel: float) -> int:
    """Mechón cuya línea central pasa más cerca de ``xrel`` a la altura t."""
    target = xrel * 8.9
    return min(range(RIBBONS), key=lambda k: abs(ribbon_x(k, t) - target))


def energy_marks() -> list[dict]:
    """Posiciones de las grietas de energía (sólo documentación legacy)."""
    return [{"t": 0.18 + 0.07 * i, "x": -0.8 + 0.16 * i} for i in range(10)]


def floating_motes() -> list[dict]:
    """Las motas NO son geometría: las emite spawnAura() en runtime."""
    return []


def vein_marks(count: int = 10) -> list[dict]:
    """10 grietas neón sobre la capa externa, en alturas distintas."""
    out = []
    for i in range(count):
        t = 0.16 + 0.075 * i
        k = 2 * (i % 6)          # siempre sobre un mechón EXTERNO
        out.append({"t": t, "k": k,
                    "x": ribbon_x(k, t) / 8.9,
                    "angle": 18.0 * math.sin(i * 1.7 + 0.3)})
    return out
