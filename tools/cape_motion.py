#!/usr/bin/env python3
"""Movimiento de la capa — FUENTE DE VERDAD ÚNICA (v1.21.0).

v1.21.0 — POR QUÉ LA ANIMACIÓN ANTERIOR SE VEÍA FEA
---------------------------------------------------
`wave()` restaba `sin(phase)` a cada armónico para forzar `w(0)=0`. Eso
mataba el retardo: la fase espacial dejaba de ser un DESPLAZAMIENTO en el
tiempo y pasaba a ser una AMPLITUD, y los 182 huesos volvían TODOS a la
pose neutra al principio y al final de cada clip. Resultado: un latido
global sincronizado, con un parón visible en la costura del bucle, en vez
de una tela por la que baja una onda. En el juego además
`CapaArmorModel.animateDeterioro()` reimplementaba una onda DISTINTA y
sobrescribía la de GeckoLib, así que Blockbench y Minecraft no coincidían.

AHORA:
  * **Onda viajera real**: `sin(2πf+φ) + 0.28 sin(4πf+1.7φ) + h sin(6πf+2.3φ)`.
    Todas las frecuencias son enteras ⇒ periódica ⇒ `w(0)=w(1)` y la
    derivada también coincide (C1 en la costura) SIN anclar nada a cero.
    La fase `φ = -0.62*tramo + col*0.19 + fase_clip` actúa como retardo
    temporal: la onda BAJA por cada jirón, desde el cuello a las puntas.
  * **Envolvente física**: la amplitud crece como `tramo^1.35`, las alas
    exteriores aletean más que el centro, una ráfaga común lenta (`gust`)
    barre toda la capa y un arrastre (`drag`) siempre positivo empuja la
    tela hacia atrás con el mismo retardo. Calibrada sobre el render de
    380 px: la punta se desplaza ~1 unidad, no 0.1 (antes era invisible).
  * **Posición real en las puntas**, con derivadas analíticas; GeckoLib
    también la recibe (antes sólo rotación ⇒ las puntas giraban en el sitio).
  * **Java ya NO reimplementa la onda**: GeckoLib aplica `sample()` y
    `CapaArmorModel` sólo SUMA la respuesta al giro/salto/sprint del
    portador leyendo la rotación ya animada del hueso.
  * Sin geometría de partículas: `spawnAura()` las emite en runtime.

Uso:  PYTHONPATH=tools python3 tools/cape_motion.py   (autotest)
"""

from __future__ import annotations

import math
import re

# --- Constantes compartidas con Java y JS (la CI comprueba que coinciden) --
TRAVEL = 0.62          # radianes de retardo por tramo de jirón
COLUMN_PHASE = 0.19    # desfase entre columnas
WAVE_SAMPLES = 11      # 12 muestras por hueso (0..WAVE_SAMPLES)
TAU = 2.0 * math.pi

# Cada clip tiene su propia fase, carácter y amplitudes. `gain` multiplica
# la familia: tela / capucha / vena / teja. `gust` es la ráfaga común y
# `sway` el barrido lateral; ninguno de los dos rompe el bucle.
STYLES: dict[str, dict] = {
    "idle": dict(length=4.0, phase=0.00, travel=TRAVEL, flutter=0.045,
                 step=0.00, flare=0.00, shiver=0.00, pull=0.030,
                 breath=0.020, pulse=0.16, gust=0.35, sway=0.25,
                 gain=dict(tela=0.62, cowl=0.40, vena=0.60, teja=0.55)),
    "caminar": dict(length=1.2, phase=0.45, travel=TRAVEL, flutter=0.075,
                    step=1.00, flare=0.30, shiver=0.00, pull=0.060,
                    breath=0.028, pulse=0.22, gust=0.80, sway=0.85,
                    gain=dict(tela=1.00, cowl=0.68, vena=0.95, teja=1.00)),
    "correr": dict(length=0.8, phase=0.95, travel=0.48, flutter=0.115,
                   step=0.45, flare=1.00, shiver=0.00, pull=0.110,
                   breath=0.045, pulse=0.30, gust=1.25, sway=1.15,
                   gain=dict(tela=1.65, cowl=0.95, vena=1.35, teja=1.45)),
    "deterioro": dict(length=3.0, phase=1.70, travel=TRAVEL, flutter=0.150,
                      step=0.00, flare=0.15, shiver=0.85, pull=0.025,
                      breath=0.012, pulse=0.45, gust=0.55, sway=0.40,
                      gain=dict(tela=0.90, cowl=0.55, vena=2.10, teja=0.75)),
}

RIBBON_RE = re.compile(r"^v17_ribbon_(\d+)_seg(\d+)$")
TAIL_RE = re.compile(r"_(\d+)$")
SECTION_SEG = {"top": 0, "mid": 3, "bottom": 6}


def parts(name: str) -> tuple[str, int, int]:
    """(familia, columna, tramo) REAL, no el índice del array."""
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


def _harm(f: float, k: int, p: float) -> tuple[float, float]:
    """sin(2πk f + p) y su derivada EXACTA respecto de f."""
    a = TAU * k * f + p
    return math.sin(a), TAU * k * math.cos(a)


def wave(f: float, phase: float, h: float) -> tuple[float, float]:
    """Onda viajera periódica y su derivada. NO se resta `sin(phase)`.

    Compatibilidad con la API anterior: devuelve (valor, d/df). Al ser
    frecuencias 1/2/3, `wave(0)==wave(1)` y la derivada también cierra.
    """
    s1, d1 = _harm(f, 1, phase)
    s2, d2 = _harm(f, 2, phase * 1.7)
    s3, d3 = _harm(f, 3, phase * 2.3)
    return s1 + 0.28 * s2 + h * s3, d1 + 0.28 * d2 + h * d3


def _flow(f: float, phase: float) -> tuple[float, float, float, float]:
    """Ráfaga común y arrastre (ambos periódicos), con derivadas."""
    g1, dg1 = _harm(f, 1, 0.55)
    g2, dg2 = _harm(f, 2, 1.10)
    gust = 0.72 * g1 + 0.28 * g2
    dgust = 0.72 * dg1 + 0.28 * dg2
    # drag = 0.5 - 0.5*cos(2πf + phase - 0.8), siempre en [0, 1].
    c, dc = _harm(f, 1, phase - 0.8 + math.pi / 2.0)
    drag = 0.5 - 0.5 * c
    ddrag = -0.5 * dc
    return gust, dgust, drag, ddrag


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
    edge = 0.62 + 0.38 * abs(lateral) ** 1.4
    phase = phase_of(name, style)
    h = spec["flutter"] * (1.0 + 0.30 * seg) if fam in (
        "ribbon", "cloth", "hem") else spec["flutter"]

    w, dw = wave(f, phase, h)
    gust, dgust, drag, ddrag = _flow(f, phase)
    s_step, d_step = _harm(f, 1, phase * 0.5)
    s_shiv, d_shiv = _harm(f, 8, col * 1.3 + seg * 0.9)
    s_pull, d_pull = _harm(f, 1, phase + 0.6)
    g = spec["gain"]

    rot = [0.0, 0.0, 0.0]
    drot = [0.0, 0.0, 0.0]
    pos = [0.0, 0.0, 0.0]
    dpos = [0.0, 0.0, 0.0]
    scale = [1.0, 1.0, 1.0]
    dscale = [0.0, 0.0, 0.0]
    has_pos = has_scale = False

    if fam in ("ribbon", "cloth", "hem"):
        amp = (1.60 + 8.50 * seg_f ** 1.35) * g["tela"] * edge
        flare = spec["flare"] * 6.0
        step = spec["step"] * 4.0 * lateral
        shiver = spec["shiver"] * 3.0 * (0.30 + 0.70 * seg_f)
        gust_a = spec["gust"]
        pull = spec["pull"]
        rot = [amp * 0.42 * w - flare * (0.62 + 0.38 * drag)
               + gust_a * 1.20 * seg_f * gust,
               step * s_step + spec["sway"] * lateral * gust,
               amp * w + gust_a * 2.20 * seg_f * gust + shiver * s_shiv]
        drot = [amp * 0.42 * dw - flare * 0.38 * ddrag
                + gust_a * 1.20 * seg_f * dgust,
                step * d_step + spec["sway"] * lateral * dgust,
                amp * dw + gust_a * 2.20 * seg_f * dgust + shiver * d_shiv]
        if fam == "ribbon":
            # v1.21.0: los 7 tramos son HERMANOS en el geo, así que una
            # rotación aislada sólo hacía vibrar cada cubo sobre su centro.
            # Un DESPLAZAMIENTO ACUMULADO (crece como tramo^1.6, con la
            # misma onda retardada) deforma el jirón como una curva: la
            # tela ondea de verdad en vez de ser un puñado de dados.
            has_pos = True
            bend = seg_f ** 1.6
            swing = (0.35 + 0.85 * g["tela"] + 3.0 * pull) * bend * edge
            pos = [swing * w + gust_a * 0.55 * bend * gust,
                   -0.28 * bend * drag,
                   flare * 0.10 * drag + 0.34 * bend * s_pull]
            dpos = [swing * dw + gust_a * 0.55 * bend * dgust,
                    -0.28 * bend * ddrag,
                    flare * 0.10 * ddrag + 0.34 * bend * d_pull]
    elif fam == "cowl":
        amp = 1.4 * g["cowl"]
        rot = [amp * 0.45 * w + 0.30 * (drag - 0.5), 0.0,
               amp * 0.30 * w + 0.25 * gust]
        drot = [amp * 0.45 * dw + 0.30 * ddrag, 0.0,
                amp * 0.30 * dw + 0.25 * dgust]
        has_scale = True
        b = spec["breath"]
        scale = [1 + b * drag, 1 + b * drag * 0.55, 1 + b * drag * 0.30]
        dscale = [b * ddrag, b * ddrag * 0.55, b * ddrag * 0.30]
    elif fam == "vein":
        amp = 5.0 * g["vena"]
        rot = [amp * 0.12 * w, 0.0, amp * w]
        drot = [amp * 0.12 * dw, 0.0, amp * dw]
        has_scale = True
        p = spec["pulse"] * drag
        dp = spec["pulse"] * ddrag
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
            mid = sample(name, style, 0.31)
            assert max(abs(x - y) for x, y in zip(a["drot"], mid["drot"])) > 0.05
    for style in STYLES:
        # v1.21.0: la onda YA NO ancla los huesos a cero en f=0. Antes
        # TODOS arrancaban en la pose neutra: era un latido con parón.
        assert max(abs(v) for v in sample(
            "v17_ribbon_7_seg5", style, 0.0)["rot"]) > 0.5, style
        # El retardo se VE desde el primer frame, no sólo a mitad de clip.
        a = sample("v17_ribbon_7_seg0", style, 0.0)["rot"]
        b = sample("v17_ribbon_7_seg5", style, 0.0)["rot"]
        assert max(abs(x - y) for x, y in zip(a, b)) > 1.0, (style, a, b)
    # La onda DEBE viajar: dos tramos del mismo jirón no están en fase.
    assert abs(phase_of("v17_ribbon_7_seg0", "caminar")
               - phase_of("v17_ribbon_7_seg4", "caminar")) > 2.0
    # La propagación se VE: el mismo jirón tiene poses distintas por tramo.
    a = sample("v17_ribbon_7_seg0", "caminar", 0.31)["rot"]
    b = sample("v17_ribbon_7_seg5", "caminar", 0.31)["rot"]
    assert max(abs(x - y) for x, y in zip(a, b)) > 1.0, (a, b)
    # Ningún clip puede generar partículas.
    assert not any("particle" in str(sample(n, s, 0.3))
                   for n in names for s in STYLES)
    rms = [round(math.sqrt(sum(v * v for v in sample(
        "v17_ribbon_7_seg5", s, 0.31)["rot"]) / 3), 4) for s in STYLES]
    assert len(set(rms)) == 4, rms
    print("cape_motion v1.21.0: onda VIAJERA (sin anclaje a cero), C1, "
          "retardo por tramo, rafaga/arrastre y 4 clips distintos OK", rms)


if __name__ == "__main__":
    _self_test()
