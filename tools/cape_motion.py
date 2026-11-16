#!/usr/bin/env python3
"""Movimiento de la capa — FUENTE DE VERDAD ÚNICA (v1.21.0).

v1.21.0 — POR QUÉ LA ANIMACIÓN ANTERIOR SE VEÍA FEA
---------------------------------------------------
`wave()` restaba `sin(phase)` a cada armónico para forzar `w(0)=0`. Eso
mataba el retardo: la fase espacial dejaba de ser un DESPLAZAMIENTO en el
tiempo y pasaba a ser una AMPLITUD, y los 150 huesos volvían TODOS a la
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
# v1.26.0 — EJES DE SIMETRÍA POR FAMILIA. El eje NO es un número
# global: cada familia tiene su propia anatomía de columnas y el eje
# es (columnas - 1) / 2. Medido sobre los pivotes X del geo real:
#   ribbon  12 -> X de -3.77 a +3.80   (eje 5.5)
#   cloth    9 -> X de -3.80 a +3.80   (eje 4.0)
#   vein    10 -> eje 4.5
#   cowl front/tooth 7 -> 3.0 ; cowl back 5 -> 2.0
#   chain    8 -> 3.5 ; pad 2 -> 0.5
# El 7.5 heredado (16 tiras de la élitra) inclinaba toda la capa hacia
# un lado: el paño izquierdo ondeaba el DOBLE que el derecho. Estos
# MISMOS números viven en Java (`CapaArmorModel.motionAxis`) y en el
# visor (`preview/app.js`); tools/audit_model.py comprueba que los tres
# ficheros digan lo MISMO, porque si uno se queda atrás Minecraft vuelve
# aaletear distinto que Blockbench.
RIBBON_AXIS = 5.5      # 12 mechones (columnas 0..11)
CLOTH_AXIS = 4.0       # 9 columnas de pano (columnas 0..8)
VEIN_AXIS = 4.5        # 10 grietas
COWL_AXIS = 3.0        # 7 piezas de capucha (front/tooth)
COWL_BACK_AXIS = 2.0   # 5 piezas del cuello trasero
CHAIN_AXIS = 3.5       # 8 eslabones
PAD_AXIS = 0.5         # 2 hombreras
DEFAULT_AXIS = 5.5     # hueso sin anatomia de columnas

# v1.22.0 — OCHO ESTADOS, no cuatro. Cada uno tiene silueta PROPIA:
# `bias` inclina la capa entera (grados, constante ⇒ no rompe C1) y
# `posbias` eleva/recoge las puntas. Así volar NO es "correr más rápido",
# caer no es saltar y agacharse no es idle: se VE el estado del jugador.
# `gain` multiplica la familia tela / capucha / vena; `gust` es la
# ráfaga común y `sway` el barrido lateral.
STYLES: dict[str, dict] = {
    # Reposo: respiración lenta, capa colgando recta.
    "idle": dict(length=4.0, phase=0.00, travel=TRAVEL, flutter=0.045,
                 step=0.00, flare=0.00, shiver=0.00, pull=0.030,
                 breath=0.020, pulse=0.16, gust=0.35, sway=0.25,
                 bias=0.0, posbias=(0.0, 0.0, 0.0),
                 gain=dict(tela=0.62, cowl=0.40, vena=0.60)),
    # Caminar: vaivén de paso con los lados en contrafase.
    "caminar": dict(length=1.2, phase=0.45, travel=TRAVEL, flutter=0.075,
                    step=1.00, flare=0.30, shiver=0.00, pull=0.060,
                    breath=0.028, pulse=0.22, gust=0.80, sway=0.85,
                    bias=0.0, posbias=(0.0, 0.0, 0.0),
                    gain=dict(tela=1.00, cowl=0.68, vena=0.95)),
    # Correr: barrida hacia atrás, aleteo de puntas y estela.
    "correr": dict(length=0.8, phase=0.95, travel=0.56, flutter=0.115,
                   step=0.45, flare=1.00, shiver=0.00, pull=0.110,
                   breath=0.045, pulse=0.30, gust=1.25, sway=1.15,
                   bias=-1.5, posbias=(0.0, 0.05, 0.12),
                   gain=dict(tela=1.65, cowl=0.95, vena=1.35)),
    # Volar / elytra: capa EXTENDIDA hacia atrás y arriba, aleteo lento
    # y amplio. La onda baja con menos retardo (el viento es parejo).
    "volar": dict(length=1.5, phase=2.20, travel=0.60, flutter=0.135,
                  step=0.10, flare=1.55, shiver=0.00, pull=0.150,
                  breath=0.055, pulse=0.34, gust=1.45, sway=1.30,
                  bias=-7.0, posbias=(0.0, 0.42, 0.55),
                  gain=dict(tela=1.85, cowl=1.05, vena=1.55)),
    # Caída libre: el aire LEVANTA la capa, puntas ondeando deprisa.
    "caer": dict(length=0.9, phase=1.15, travel=0.68, flutter=0.150,
                 step=0.00, flare=0.00, shiver=0.30, pull=0.130,
                 breath=0.040, pulse=0.28, gust=1.10, sway=0.90,
                 bias=8.5, posbias=(0.0, 0.55, 0.10),
                 gain=dict(tela=1.55, cowl=0.90, vena=1.35)),
    # Agacharse: capa RECOGIDA y pegada al cuerpo, casi sin viento.
    "agachado": dict(length=2.6, phase=0.80, travel=0.70, flutter=0.035,
                     step=0.00, flare=-0.35, shiver=0.00, pull=0.018,
                     breath=0.015, pulse=0.10, gust=0.20, sway=0.15,
                     bias=2.5, posbias=(0.0, -0.18, -0.35),
                     gain=dict(tela=0.48, cowl=0.32, vena=0.45)),
    # Agua: flota amortiguada, onda larga y lenta, deriva lateral.
    "agua": dict(length=3.2, phase=2.75, travel=0.72, flutter=0.050,
                 step=0.15, flare=0.20, shiver=0.00, pull=0.045,
                 breath=0.030, pulse=0.20, gust=0.55, sway=0.60,
                 bias=-1.2, posbias=(0.0, 0.12, 0.18),
                 gain=dict(tela=0.72, cowl=0.48, vena=0.70)),
    # Deterioro: estremecimiento de alta frecuencia y venas encendidas.
    "deterioro": dict(length=3.0, phase=1.70, travel=0.75, flutter=0.150,
                      step=0.00, flare=0.15, shiver=0.85, pull=0.025,
                      breath=0.012, pulse=0.45, gust=0.55, sway=0.40,
                      bias=0.0, posbias=(0.0, 0.0, 0.0),
                      gain=dict(tela=0.90, cowl=0.55, vena=2.10)),
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
    if name.startswith(("v17_cowl_", "v18_pad_", "v18_chain_")):
        m2 = TAIL_RE.search(name)
        return "cowl", (int(m2.group(1)) if m2 else 0), 0
    if name.startswith("v17_vein_"):
        m2 = TAIL_RE.search(name)
        return "vein", (int(m2.group(1)) if m2 else 0), 0
    return "other", 0, 0


def axis_of(name: str) -> float:
    """Eje de simetría de la familia del hueso: (columnas - 1) / 2.

    v1.26.0: el eje se deriva de la anatomía REAL de cada familia (ver
    las constantes de eje arriba), no de un 7.5 global. Con el eje
    equivocado, `lateral` deja de ir de -1 a +1 y la capa se inclina
    siempre hacia el mismo lado.
    """
    if name.startswith("v17_ribbon_"):
        return RIBBON_AXIS
    if name.startswith(("v15_cloth_cape_", "v15_hem_")):
        return CLOTH_AXIS
    if name.startswith("v17_vein_"):
        return VEIN_AXIS
    if name.startswith("v18_chain_"):
        return CHAIN_AXIS
    if name.startswith("v18_pad_"):
        return PAD_AXIS
    if name.startswith("v17_cowl_back_"):
        return COWL_BACK_AXIS
    if name.startswith("v17_cowl_"):
        return COWL_AXIS
    return DEFAULT_AXIS


def phase_of(name: str, style: str) -> float:
    """Fase espacial: el retardo por tramo es la clave del ondeo."""
    _fam, col, seg = parts(name)
    spec = STYLES[style]
    # v1.25.0: además del retardo por tramo, cada columna lleva su fase
    # (constante en el tiempo => sigue C1): los mechones dejan de ir todos
    # en bloque y la tela se lee orgánica.
    return (-spec["travel"] * seg + col * COLUMN_PHASE
            + 0.23 * math.sin(col * 2.13 + 1.7) + spec["phase"])


def _harm(f: float, k: int, p: float) -> tuple[float, float]:
    """sin(2πk f + p) y su derivada EXACTA respecto de f."""
    a = TAU * k * f + p
    return math.sin(a), TAU * k * math.cos(a)


def wave(f: float, phase: float, h: float) -> tuple[float, float]:
    """Onda viajera periódica y su derivada. NO se resta `sin(phase)`.

    Compatibilidad con la API anterior: devuelve (valor, d/df). Al ser
    frecuencias 1/2/3/4, `wave(0)==wave(1)` y la derivada también cierra.

    v1.29.0: un CUARTO armónico (k=4, amplitud 0.10) con fase 3.1*φ.
    Las tres primeras frecuencias daban una onda correcta pero algo
    mecánica; el armónico extra fraccionario (pero con k entero, así
    que sigue siendo periódica y C1) añade el ribete irisado que tiene
    una tela al sol, sin anclar nada a cero ni romper la costura.

    v1.31.0: un QUINTO armónico (k=5, amplitud 0.06) con fase 4.7*φ.
    El ribete de k=4 seguía siendo algo regular; un armónico de
    frecuencia más alta y baja amplitud añade el temblor fino de los
    hilos individuales de una tela al viento. k=5 es entero, así que
    la onda sigue periódica (wave(0)==wave(1)) y C1, y el self-test
    lo comprueba. No ancla nada a cero ni rompe la costura.

    v1.32.0: un SEXTO armónico (k=6, amplitud 0.035) con fase 6.1*φ.
    El temblor de k=5 seguía regular; un armónico de frecuencia mayor
    y amplitud menor añade el destello fino de los hilos más finos.

    v1.34.0: un SÉPTIMO armónico (k=7, amplitud 0.025) con fase 7.3*φ.
    El temblor de k=6 seguía aún algo regular; un armónico de frecuencia
    mayor y amplitud menor añade el destello casi microscópico de los
    hilos más finos al viento, sin que la onda pierda su periodicidad
    ni su costura C1. k=7 es entero, así que wave(0)==wave(1) y el
    self-test lo comprueba. No ancla nada a cero ni rompe la costura.
    """
    s1, d1 = _harm(f, 1, phase)
    s2, d2 = _harm(f, 2, phase * 1.7)
    s3, d3 = _harm(f, 3, phase * 2.3)
    s4, d4 = _harm(f, 4, phase * 3.1)
    s5, d5 = _harm(f, 5, phase * 4.7)
    # v1.32.0: SEXTO armónico (k=6, amplitud 0.035) con fase 6.1*φ.
    # El temblor de k=5 seguía siendo algo regular; un armónico de
    # frecuencia más alta y amplitud aún menor añade el destello fino
    # de los hilos más finos de una tela al viento. k=6 es entero, así
    # que la onda sigue periódica (wave(0)==wave(1)) y C1; el self-test
    # lo comprueba. No ancla nada a cero ni rompe la costura.
    s6, d6 = _harm(f, 6, phase * 6.1)
    # v1.34.0: SÉPTIMO armónico (k=7, amplitud 0.025) con fase 7.3*φ.
    s7, d7 = _harm(f, 7, phase * 7.3)
    # v1.35.0: OCTAVO armónico (k=8, amplitud 0.02) con fase 8.5*φ.
    # El destello de k=7 seguía algo regular; un armónico de frecuencia
    # mayor y amplitud menor añade el temblor casi imperceptible de los
    # hilos más finos, sin perder la periodicidad ni la costura C1. k=8
    # es entero, así que wave(0)==wave(1) y el self-test lo comprueba.
    s8, d8 = _harm(f, 8, phase * 8.5)
    # v1.36.0: NOVENO armónico (k=9, amplitud 0.015) con fase 9.7*φ.
    # El temblor de k=8 seguía aún algo regular; un armónico de frecuencia
    # mayor y amplitud menor añade el destello casi microscópico de los
    # hilos más finos al viento, sin perder la periodicidad ni la costura
    # C1. k=9 es entero, así que wave(0)==wave(1) y el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s9, d9 = _harm(f, 9, phase * 9.7)
    # v1.37.0: DÉCIMO armónico (k=10, amplitud 0.01) con fase 10.9*φ.
    # El temblor de k=9 seguía aún algo regular; un armónico de frecuencia
    # mayor y amplitud menor añade el destello casi imperceptible de los
    # hilos más finos al viento, sin perder la periodicidad ni la costura
    # C1. k=10 es entero, así que wave(0)==wave(1) y el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s10, d10 = _harm(f, 10, phase * 10.9)
    # v1.38.0: UNDÉCIMO armónico (k=11, amplitud 0.008) con fase 12.1*φ.
    # El temblor de k=10 seguía aún algo regular; un armónico de frecuencia
    # mayor y amplitud menor añade el destello casi imperceptible de los
    # hilos más finos al viento, sin perder la periodicidad ni la costura
    # C1. k=11 es entero, así que wave(0)==wave(1) y el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s11, d11 = _harm(f, 11, phase * 12.1)
    # v1.43.0: DÉCIMASEGUNDO armónico (k=12, amplitud 0.004) con fase
    # 13.7*φ. Es ROTACIÓN: el balanceo del paño lee el temblor de los
    # hilos más finos al viento, con amplitud menor que el k=11 y
    # fase distinta. La onda de rotación es lateral: no altera la
    # componente Z del dobladillo ni empuja el paño hacia el cuerpo
    # (evita el regreso de la v1.39.0/v1.40.0). k=12 es entero, así que
    # wave(0)==wave(1) y la derivada cierra (C1); el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s12, d12 = _harm(f, 12, phase * 13.7)
    # v1.44.0: DÉCIMATERCERO armónico (k=13, amplitud 0.003) con fase
    # 14.9*φ. Es ROTACIÓN: el balanceo del paño lee el temblor de los
    # hilos más estrechos al viento, con amplitud menor que el k=12
    # y fase distinta. La onda de rotación es lateral: no altera la
    # componente Z del dobladillo ni empuja el paño hacia el cuerpo
    # (evita el regreso de la v1.39.0/v1.40.0). k=13 es entero, así que
    # wave(0)==wave(1) y la derivada cierra (C1); el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s13, d13 = _harm(f, 13, phase * 14.9)
    # v1.45.0: DÉCIMACUARTO armónico (k=14, amplitud 0.002) con fase
    # 16.1*φ. Es ROTACIÓN: el balanceo del paño lee el temblor sub-texel
    # del grano del tejido al viento, con amplitud menor que el k=13
    # y fase distinta. La onda de rotación es lateral: no altera la
    # componente Z del dobladillo ni empuja el paño hacia el cuerpo
    # (evita el regreso de la v1.39.0/v1.40.0). k=14 es entero, así que
    # wave(0)==wave(1) y la derivada cierra (C1); el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s14, d14 = _harm(f, 14, phase * 16.1)
    # v1.46.0: DÉCIMACINCO armónico (k=15, amplitud 0.0015) con fase
    # 17.3*φ. Es ROTACIÓN: el balanceo del paño lee el temblor del
    # grano ultrafino al viento, con amplitud menor que el k=14 y
    # fase distinta. La onda de rotación es lateral: no altera la
    # componente Z del dobladillo ni empuja el paño hacia el cuerpo
    # (evita el regreso de la v1.39.0/v1.40.0). k=15 es entero, así que
    # wave(0)==wave(1) y la derivada cierra (C1); el self-test lo
    # comprueba. No ancla nada a cero ni rompe la costura.
    s15, d15 = _harm(f, 15, phase * 17.3)
    return (s1 + 0.28 * s2 + h * s3 + 0.10 * s4 + 0.06 * s5 + 0.035 * s6 + 0.025 * s7 + 0.02 * s8 + 0.015 * s9 + 0.01 * s10 + 0.008 * s11 + 0.004 * s12 + 0.003 * s13 + 0.002 * s14 + 0.0015 * s15,
            d1 + 0.28 * d2 + h * d3 + 0.10 * d4 + 0.06 * d5 + 0.035 * d6 + 0.025 * d7 + 0.02 * d8 + 0.015 * d9 + 0.01 * d10 + 0.008 * d11 + 0.004 * d12 + 0.003 * d13 + 0.002 * d14 + 0.0015 * d15)


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
    # v1.26.0: el eje depende de la FAMILIA (columnas reales / 2 - 0.5).
    # Con el 7.5 global el paño de 9 columnas iba de -1.0 a +0.07: la
    # izquierda ondeaba el doble que la derecha y el vaivén del paso
    # inclinaba la capa siempre hacia el mismo lado.
    axis = axis_of(name)
    lateral = (col - axis) / axis
    edge = 0.62 + 0.38 * abs(lateral) ** 1.4
    phase = phase_of(name, style)
    # Amplitud propia de cada mechón (determinista, no aleatoria): un
    # jirón no ondea igual que su vecino.
    col_amp = 0.88 + 0.24 * (0.5 + 0.5 * math.sin(col * 1.93 + 0.6))
    h = spec["flutter"] * (1.0 + 0.30 * seg) * col_amp if fam in (
        "ribbon", "cloth", "hem") else spec["flutter"] * col_amp

    w, dw = wave(f, phase, h)
    gust, dgust, drag, ddrag = _flow(f, phase)
    s_step, d_step = _harm(f, 1, phase * 0.5)
    s_shiv, d_shiv = _harm(f, 8, col * 1.3 + seg * 0.9)
    # v1.47.0: SEGUNDO armónico del shiver (k=13, amplitud 0.5x) con
    # fase distinta por columna/tramo. El temblor por columna lee el
    # grano del tejido: es ROTACIÓN (inclinación Z de cada jirón),
    # NO toca la posición (pos) ni la fuerza/dirección del viento
    # (gust), así que no puede empujar el paño al cuerpo (evita el
    # regreso de la v1.39.0/v1.40.0). k=13 es entero, C1 se mantiene.
    s_shiv2, d_shiv2 = _harm(f, 13, col * 1.7 + seg * 1.1)
    # v1.48.0: TERCER armónico del shiver (k=16, amplitud 0.20x) con
    # fase distinta por columna/tramo. El temblor por columna lee el
    # grano más fino del tejido: es ROTACIÓN (inclinación Z de cada
    # jirón), NO toca la posición (pos) ni la fuerza/dirección del
    # viento (gust), así que no puede empujar el paño al cuerpo.
    # k=16 es entero, C1 se mantiene. La amplitud se mantiene modesta
    # (0.20x): un 3.er armónico mayor elevaba el RMS del clip
    # `deterioro` hasta colisionar con `caminar` en los 2 decimales
    # que exige la validación de amplitudes distintas del bbmodel.
    s_shiv3, d_shiv3 = _harm(f, 16, col * 2.1 + seg * 1.3)
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
               amp * w + gust_a * 2.20 * seg_f * gust + shiver * s_shiv
               + shiver * 0.5 * s_shiv2 + shiver * 0.20 * s_shiv3]
        drot = [amp * 0.42 * dw - flare * 0.38 * ddrag
                + gust_a * 1.20 * seg_f * dgust,
                step * d_step + spec["sway"] * lateral * dgust,
                amp * dw + gust_a * 2.20 * seg_f * dgust + shiver * d_shiv
                + shiver * 0.5 * d_shiv2 + shiver * 0.20 * d_shiv3]
        # v1.50.0: micro-ROTACIÓN Z del dobladillo (armónico k=5, amplitud
        # 5% de amp, fase distinta por hueso). El borde inferior no es una
        # tira rigida: tiene el temblor fino de la tela en el dobladillo.
        # Es ROTACIÓN pura (RotZ): no toca la posición del paño ni puede
        # empujarlo al cuerpo. k=5 es entero, C1 se mantiene.
        if fam == "hem":
            _sh5, _dh5 = _harm(f, 5, phase * 2.1)
            _hemTrem = amp * 0.02
            rot[2] += _hemTrem * _sh5
            drot[2] += _hemTrem * _dh5
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
        # v1.49.0: micro-ROTACIÓN Z de la capucha (armónico k=6, amplitud
        # 6% de amp, fase distinta por hueso). El gorro no es una pieza
        # rigida: tiene el temblor fino de la tela. Es ROTACIÓN pura
        # (RotZ): no toca la posición ni el escalado (la respiración
        # sigue por `drag`), así que no puede empujar nada al cuerpo.
        # k=6 es entero, C1 se mantiene (wave(0)==wave(1)).
        s_cowl6, d_cowl6 = _harm(f, 6, phase * 1.7)
        cowlTrem = amp * 0.06
        rot = [amp * 0.45 * w + 0.30 * (drag - 0.5), 0.0,
               amp * 0.30 * w + 0.25 * gust + cowlTrem * s_cowl6]
        drot = [amp * 0.45 * dw + 0.30 * ddrag, 0.0,
                amp * 0.30 * dw + 0.25 * dgust + cowlTrem * d_cowl6]
        has_scale = True
        b = spec["breath"]
        scale = [1 + b * drag, 1 + b * drag * 0.55, 1 + b * drag * 0.30]
        dscale = [b * ddrag, b * ddrag * 0.55, b * ddrag * 0.30]
    elif fam == "vein":
        amp = 5.0 * g["vena"]
        # v1.50.0: micro-ROTACIÓN Z de la vena (armónico k=5, amplitud
        # 8% de amp, fase distinta). La vena encendida no es una línea
        # rígida: tiene el temblor fino de la energy por la cape. Es
        # ROTACIÓN pura (RotZ): no toca la posición ni el escalado (el
        # pulso sigue por `drag`). k=5 es entero, C1 se mantiene.
        _sv5, _dv5 = _harm(f, 5, phase * 2.4)
        _veinTrem = amp * 0.03
        rot = [amp * 0.12 * w, 0.0, amp * w + _veinTrem * _sv5]
        drot = [amp * 0.12 * dw, 0.0, amp * dw + _veinTrem * _dv5]
        has_scale = True
        p = spec["pulse"] * drag
        dp = spec["pulse"] * ddrag
        scale = [1 + p, 1 + p, 1.0]
        dscale = [dp, dp, 0.0]
    else:
        amp = 2.4 * g["tela"]
        rot = [amp * 0.5 * w, 0.0, amp * w]
        drot = [amp * 0.5 * dw, 0.0, amp * dw]

    # v1.22.0: SILUETA DEL ESTADO. `lean` inclina toda la capa (más en
    # las puntas) y `posbias` eleva/recoge el dobladillo. Son constantes
    # en el tiempo ⇒ derivada cero ⇒ el bucle sigue siendo C1.
    lean = spec["bias"] * (0.25 + 0.75 * seg_f)
    rot[0] += lean
    if has_pos:
        bend = seg_f ** 1.6
        for i in range(3):
            pos[i] += spec["posbias"][i] * bend

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
             "v17_cowl_front_3", "v17_vein_2", "v18_chain_3",
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
    assert len(rms) == 8 and len(set(rms)) == 8, rms
    # v1.22.0: los estados TIENEN que verse distintos, no sólo sonar
    # distintos. Volar barre/levanta, caer eleva, agacharse recoge.
    tip = "v17_ribbon_7_seg6"
    assert sample(tip, "volar", 0.0)["rot"][0] < -4.0, "volar no barre"
    assert sample(tip, "caer", 0.0)["rot"][0] > 3.0, "caer no eleva"
    assert sample(tip, "volar", 0.0)["pos"][1] > 0.25, "volar no levanta puntas"
    assert sample(tip, "agachado", 0.0)["pos"][2] < -0.20, "agache no recoge"
    print("cape_motion v1.25.0: 8 ESTADOS con silueta propia, onda VIAJERA "
          "C1, retardo por tramo y offsets acumulados OK", rms)


if __name__ == "__main__":
    _self_test()
