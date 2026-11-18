#!/usr/bin/env python3
"""Curvas de reposo para doce gajos, seis granate y seis de forro.

El ensanche a media altura, los distintos cortes y la apertura central
son geometría, no alfa. El ajuste de z describe el volumen EN REPOSO;
no interviene en los canales de movimiento del equipamiento.
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

Y_TOP, Y_BOT = 22.42, 1.30
HEIGHT = Y_TOP - Y_BOT
X_NECK, X_TIP = 4.15, 8.15
W_TOP, W_MIN = 2.20, 0.17
# Dobladillo partido: los dos jirones centrales terminan antes; las
# caídas largas viven a cada lado. Pequeña asimetría deliberada.
TAILS = (0.64, 0.70, 0.79, 0.89, 0.99, 0.70, 0.73, 0.91, 0.98, 0.84, 0.74, 0.66)
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
    """Abanico a media altura; después las puntas se recogen en dos colas."""
    t = max(0.0, min(1.0, t))
    bow = math.sin(math.pi / 2 * min(1.0, t / 0.59))
    return X_NECK + (X_TIP - X_NECK) * bow - 2.15 * _smooth(0.62, 1.0, t)


def tip_t(k: int) -> float:
    return TAILS[k]


def fan_x(k: int, t: float) -> float:
    """Envolvente de las doce franjas."""
    return lateral(k) * silhouette(t)


def ribbon_x(k: int, t: float) -> float:
    a = lateral(k)
    tt = max(0.0, min(1.0, t))
    crest = math.sin(2.7 * tt + k * 1.36 + 0.35) * 0.72 * tt
    # Abertura REAL en el centro bajo. No es un agujero pintado.
    cleft = math.copysign(2.02 * (1.0 - abs(a)) ** 1.75, a) * _smooth(0.28, 0.78, tt)
    return fan_x(k, tt) + cleft + crest


def ribbon_w(k: int, t: float) -> float:
    a = abs(lateral(k))
    local = max(0.0, min(1.0, t / tip_t(k)))
    belly = W_TOP + (0.85 + 0.52 * a) * math.sin(math.pi * min(1.0, local + 0.04))
    onset = (0.47, 0.52, 0.58)[k % 3]
    taper = 1.0 - _smooth(onset, 1.0, local)
    return W_MIN + (belly - W_MIN) * taper * (0.96 + 0.06 * math.sin(k * 1.77 + 0.2))


def ribbon_z(k: int, t: float = 0.0) -> float:
    """Lomo en volumen, con gajos externos sobre un forro retrasado."""
    tt = max(0.0, min(1.0, t))
    a = abs(lateral(k))
    root = 0.43 * (1.0 - _smooth(0.0, 0.34, tt))
    base = 1.76 + 1.40 * tt + 0.35 * (1.0 - a) - root
    offset = 0.53 if layer(k) == "outer" else -0.23
    curl = 0.19 * math.sin(k * 1.52 + tt * 5.1 + 0.3)
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
    h = math.hypot(dx, dy) * (1.42 if 1 <= n <= 4 else 1.34)
    w = (ribbon_w(k, t0) + 2.0 * ribbon_w(k, tm) + ribbon_w(k, t1)) / 4.0
    w *= 0.97 + 0.07 * math.sin(k * 2.71 + n * 1.93)
    if n == SEGS - 1:
        w *= 0.88
    # Un canto girado atrapa la luz; cambia el perfil sin añadir cubos.
    bend = math.degrees(math.atan2(ribbon_z(k, t1) - ribbon_z(k, t0), math.hypot(dx, dy)))
    twist = 12.0 * lateral(k) * math.sin(math.pi * min(1.0, (tm + 0.08) / 0.96))
    twist += 5.0 * math.sin(k * 1.28 + n * 0.42)
    layer_v = 0.0 if layer(k) == "outer" else 48.0
    stripe = (k // 2) * BAND_W
    return dict(
        cx=cx, cy=cy, z=z, w=w, h=h, theta=theta, twist=twist, bend=bend, layer=layer(k),
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
        k = 2 * (i % 6)          # siempre sobre un mechón EXTERNO
        t = tip_t(k) * (0.21 + 0.049 * i)
        out.append({"t": t, "k": k,
                    "x": ribbon_x(k, t) / 8.9,
                    "angle": 18.0 * math.sin(i * 1.7 + 0.3)})
    return out
