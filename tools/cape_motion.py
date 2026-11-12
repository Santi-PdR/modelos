#!/usr/bin/env python3
"""Movimiento de la capa — FUENTE DE VERDAD ÚNICA (rev. B / sin piezas volando).

Antes había cuatro ondas distintas: la del `.bbmodel`, la del
`animation.json` de GeckoLib (que además NO animaba ningún hueso `v17_*`),
la de `CapaArmorModel.java` (fase `i * 0.37`, es decir un índice global que
no tenía nada que ver con la columna ni el tramo) y la del visor JS. Cada
una inventaba su propia fase, así que la tela no ondeaba: vibraba.

Ahora `sample()` es la curva canónica y todos los consumidores la importan
(Python) o la replican con las MISMAS constantes (Java/JS, verificadas por
CI). Propiedades deliberadas:

  * **Onda periódica C1**: `wave(0) == wave(1) == 0` y la derivada también
    coincide. El bucle no pega un salto ni en Blockbench ni en GeckoLib.
  * **Retardo REAL por tramo**: `phase = -TRAVEL*seg + col*0.19 + fase`.
    La onda BAJA por cada jirón en vez de mover todos los cubos a la vez.
  * **Carácter por clip**: reposo = respiración lenta; caminar = vaivén de
    paso con los lados en contrafase; correr = capa barrida hacia atrás y
    aleteo de puntas; deterioro = estremecimiento de alta frecuencia.
  * **Sin geometría de partículas**: este módulo NO produce motas, ceniza ni
    keyframes `particle`. Las partículas las emite `spawnAura()` en runtime,
    desde el servidor, cuando la capa está equipada.

Uso:  PYTHONPATH=tools python3 tools/cape_motion.py   (autotest)
"""

from __future__ import annotations

import math
import re

# --- Constantes compartidas con Java y JS (la CI comprueba que coinciden) --
TRAVEL = 0.62          # radianes de retardo por tramo de jirón
COLUMN_PHASE = 0.19    # desfase entre columnas
WAVE_SAMPLES = 11      # 12 muestras por hueso (0..WAVE_SAMPLES)

# Cada clip tiene su propia fase, carácter y amplitudes. `gain` multiplica
# la familia: tela / capucha / vena / teja.
STYLES: dict[str, dict] = {
    "idle": dict(length=4.0, phase=0.00, travel=TRAVEL, flutter=0.055,
                 step=0.00, flare=0.00, shiver=0.00, pull=0.030,
                 breath=0.022, pulse=0.18,
                 gain=dict(tela=0.55, cowl=0.45, vena=0.55, teja=0.50)),
    "caminar": dict(length=1.2, phase=0.45, travel=TRAVEL, flutter=0.070,
                    step=1.00, flare=0.35, shiver=0.00, pull=0.055,
                    breath=0.030, pulse=0.22,
                    gain=dict(tela=1.00, cowl=0.80, vena=0.90, teja=1.00)),
    "correr": dict(length=0.8, phase=0.95, travel=0.48, flutter=0.110,
                   step=0.45, flare=1.00, shiver=0.00, pull=0.100,
                   breath=0.050, pulse=0.30,
                   gain=dict(tela=1.75, cowl=1.10, vena=1.30, teja=1.50)),
    "deterioro": dict(length=3.0, phase=1.70, travel=TRAVEL, flutter=0.160,
                      step=0.00, flare=0.15, shiver=1.00, pull=0.020,
                      breath=0.012, pulse=0.45,
                      gain=dict(tela=0.85, cowl=0.60, vena=2.20, teja=0.70)),
}

RIBBON_RE = re.compile(r"^v17_ribbon_(\d+)_seg(\d+)$")
TAIL_RE = re.compile(r"_(\d+)$")
SECTION_SEG = {"top": 0, "mid": 3, "bottom": 6}


def parts(name: str) -> tuple[str, int, int]:
    """(familia, columna, tramo) REAL, no el índice del array.

    Antes `CapaArmorModel` usaba `i * 0.37`: dos jirones contiguos podían
    caer en fases opuestas y la tela parecía un puñado de cubos sueltos.
    """
    m = RIBBON_RE.match(name)
    if m:
        return "ribbon", int(m.group(1)), int(m.group(2))
    if name.startswith("v15_cloth_cape_"):
        sec = name[len("v15_cloth_cape_"):].rsplit("_", 1)[0]
        col = int(TAIL_RE.search(name).group(1))
        return "cloth", col, SECTION_SEG.get(sec, 0)
    if name.startswith("v15_hem_"):
        return "hem", int(TAIL_RE.search(name).group(1)), 6
    if name.startswith(("v17_cowl_", "v17_yoke_", "v16_collar_", "v16_yoke_")):
        m2 = TAIL_RE.search(name)
        return "cowl", (int(m2.group(1)) if m2 else 0), 0
    if name.startswith(("v17_vein_", "v16_vein_")):
        m2 = TAIL_RE.search(name)
        return "vein", (int(m2.group(1)) if m2 else 0), 0
    if name.startswith(("v17_shingle_", "v16_tatter_", "v16_shred_",
                        "v16_fray_", "v16_hem_")):
        m2 = TAIL_RE.search(name)
        return "shingle", (int(m2.group(1)) if m2 else 0), 0
    return "other", 0, 0


def phase_of(name: str, style: str) -> float:
    """Fase espacial: el retardo por tramo es la clave del ondeo."""
    _fam, col, seg = parts(name)
    spec = STYLES[style]
    return -spec["travel"] * seg + col * COLUMN_PHASE + spec["phase"]


def wave(f: float, phase: float, h: float) -> tuple[float, float]:
    """Onda de 3 armónicos y su derivada EXACTA respecto de f.

    Se resta el valor en f=0 para que w(0)=w(1)=0: bucle sin salto.
    La derivada se usa para las tangentes Bézier (continuidad C1).
    """
    p, q, r = phase, phase * 1.7, phase * 2.3
    w = (0.75 * (math.sin(2 * math.pi * f + p) - math.sin(p))
         + 0.18 * (math.sin(4 * math.pi * f + q) - math.sin(q))
         + h * (math.sin(6 * math.pi * f + r) - math.sin(r)))
    dw = (0.75 * 2 * math.pi * math.cos(2 * math.pi * f + p)
          + 0.18 * 4 * math.pi * math.cos(4 * math.pi * f + q)
          + h * 6 * math.pi * math.cos(6 * math.pi * f + r))
    return w, dw


def _r(v: float) -> float:
    return round(v, 5)


def sample(name: str, style: str, f: float) -> dict:
    """Pose completa en `f` normalizado (0..1), con derivadas d/df.

    Devuelve rotación (grados), posición (unidades) y escala, más las
    derivadas analíticas de cada canal para las tangentes Bézier.
    """
    spec = STYLES[style]
    fam, col, seg = parts(name)
    seg_f = min(1.0, seg / 6.0)
    lateral = (col - 7.5) / 7.5
    phase = phase_of(name, style)
    h = spec["flutter"] * (1.0 + 0.30 * seg) if fam in (
        "ribbon", "cloth", "hem") else spec["flutter"]
    w, dw = wave(f, phase, h)
    two_pi_f = 2 * math.pi * f
    s2, c2 = math.sin(two_pi_f), math.cos(two_pi_f)
    s2p, c2p = math.sin(two_pi_f + phase), math.cos(two_pi_f + phase)
    g = spec["gain"]

    rot = [0.0, 0.0, 0.0]
    drot = [0.0, 0.0, 0.0]
    pos = [0.0, 0.0, 0.0]
    dpos = [0.0, 0.0, 0.0]
    scale = [1.0, 1.0, 1.0]
    dscale = [0.0, 0.0, 0.0]
    has_pos = has_scale = False

    if fam in ("ribbon", "cloth", "hem"):
        amp = (2.2 + 6.5 * seg_f) * g["tela"]
        flare = spec["flare"] * 4.0
        step = spec["step"] * 3.0 * lateral
        sh = spec["shiver"] * 3.0 * (0.30 + 0.70 * seg_f)
        sh_phase = col * 1.3 + seg * 0.9
        rot = [amp * 0.5 * w - flare * (0.5 + 0.5 * s2p),
               step * s2,
               amp * w + sh * math.sin(12 * math.pi * f + sh_phase)]
        drot = [amp * 0.5 * dw - flare * 0.5 * 2 * math.pi * c2p,
                step * 2 * math.pi * c2,
                amp * dw + sh * 12 * math.pi * math.cos(12 * math.pi * f + sh_phase)]
        if fam == "ribbon" and seg >= 4:
            has_pos = True
            pull = spec["pull"]
            pos = [pull * (0.4 + seg_f) * w,
                   -pull * seg_f * (0.5 - 0.5 * c2),
                   spec["flare"] * 0.10 * (0.5 + 0.5 * s2p)]
            dpos = [pull * (0.4 + seg_f) * dw,
                    -pull * seg_f * math.pi * s2,
                    spec["flare"] * 0.10 * 0.5 * 2 * math.pi * c2p]
    elif fam == "cowl":
        amp = 1.4 * g["cowl"]
        rot = [amp * 0.45 * w, 0.0, amp * 0.30 * w]
        drot = [amp * 0.45 * dw, 0.0, amp * 0.30 * dw]
        has_scale = True
        b = spec["breath"]
        pulse = b * (0.5 - 0.5 * c2)
        dpulse = b * math.pi * s2
        scale = [1 + pulse, 1 + pulse * 0.55, 1 + pulse * 0.30]
        dscale = [dpulse, dpulse * 0.55, dpulse * 0.30]
    elif fam == "vein":
        amp = 5.0 * g["vena"]
        rot = [amp * 0.12 * w, 0.0, amp * w]
        drot = [amp * 0.12 * dw, 0.0, amp * dw]
        has_scale = True
        p = spec["pulse"] * (0.5 - 0.5 * c2)
        dp = spec["pulse"] * math.pi * s2
        scale = [1 + p, 1 + p, 1.0]
        dscale = [dp, dp, 0.0]
    elif fam == "shingle":
        amp = 3.2 * g["teja"]
        rot = [amp * 0.40 * w, 0.0, amp * w]
        drot = [amp * 0.40 * dw, 0.0, amp * dw]
    else:
        amp = 2.4 * g["tela"]
        rot = [amp * 0.5 * w, 0.0, amp * w]
        drot = [amp * 0.5 * dw, 0.0, amp * dw]

    return {
        "rot": tuple(_r(v) for v in rot),
        "drot": tuple(_r(v) for v in drot),
        "pos": tuple(_r(v) for v in pos),
        "dpos": tuple(_r(v) for v in dpos),
        "scale": tuple(_r(v) for v in scale),
        "dscale": tuple(_r(v) for v in dscale),
        "has_pos": has_pos,
        "has_scale": has_scale,
    }


def _self_test() -> None:
    names = ("v17_ribbon_0_seg0", "v17_ribbon_7_seg4", "v17_ribbon_15_seg6",
             "v17_cowl_front_3", "v17_vein_2", "v17_shingle_5",
             "v15_cloth_cape_bottom_8")
    for style in STYLES:
        for name in names:
            a, b = sample(name, style, 0.0), sample(name, style, 1.0)
            for ch in ("rot", "pos", "scale"):
                assert max(abs(x - y) for x, y in zip(a[ch], b[ch])) < 1e-4, (
                    style, name, ch, a[ch], b[ch])
            # C1 en la COSTURA del bucle: la derivada también cierra.
            assert max(abs(x - y) for x, y in zip(
                a["drot"], b["drot"])) < 1e-3, (style, name, "drot")
            # La derivada no es constante: la curva tiene movimiento real.
            mid = sample(name, style, 0.31)
            assert max(abs(x - y) for x, y in zip(a["drot"], mid["drot"])) > 0.05
    # La onda DEBE viajar: dos tramos del mismo jirón no están en fase.
    assert abs(phase_of("v17_ribbon_7_seg0", "caminar")
               - phase_of("v17_ribbon_7_seg4", "caminar")) > 2.0
    # Ningún clip puede generar partículas.
    assert not any("particle" in str(sample(n, s, 0.3))
                   for n in names for s in STYLES)
    rms = [round(math.sqrt(sum(v * v for v in sample(
        "v17_ribbon_7_seg5", s, 0.31)["rot"]) / 3), 4) for s in STYLES]
    assert len(set(rms)) == 4, rms
    print("cape_motion: bucle C1, retardo por tramo y 4 clips distintos OK", rms)


if __name__ == "__main__":
    _self_test()
