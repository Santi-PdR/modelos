#!/usr/bin/env python3
"""Coreografía rotacional del paño equipado. Grados en espacio GeckoLib.

Las tres bisagras construyen la silueta del estado; los gajos reaccionan
con retardo desde la costura y los faldones del cuello casi no se mueven.
Sin traslaciones, escala, viento nuevo ni FX en estas curvas. Los canales
espaciales preexistentes se conservan por separado en el bake.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    length: float
    pitch: tuple[float, float, float]  # corona, mitad y dobladillo
    flex: tuple[float, float, float]
    roll: tuple[float, float, float]
    spread: float                    # abre o recoge ambos lados
    ripple: float                    # acento local en los gajos
    phase: float = 0.0


STYLES = {
    "idle":       Style(3.60, (1.2, 0.9, -0.4), (1.1, 1.7, 2.0), (.3, 1.0, 1.35), 0.4, 2.3),
    "caminar":    Style(1.00, (12, 6, -2), (2.6, 4.4, 4.5), (1.4, 2.6, 4.8), 2.0, 5.2, .4),
    "correr":     Style(0.72, (32, 14, -5), (3.8, 4.6, 6.2), (1.0, 2.3, 4.4), -6.0, 8.4, .8),
    "volar":      Style(1.35, (51, 12, -2), (4.0, 5.5, 5.8), (1.1, 1.9, 3.2), 14.0, 12.0, 1.5),
    "caer":       Style(0.90, (21, 21, 27), (3.7, 5.6, 8.2), (1.5, 3.0, 5.0), 6.0, 10.3, 2.0),
    "agachado":   Style(2.60, (10, -6, -7), (1.3, 1.1, 1.9), (.3, .7, 1.2), -14.0, 2.5, .3),
    "agua":       Style(3.20, (14, 9, -14), (3.1, 4.5, 5.5), (1.5, 5.5, 12.0), 4.0, 6.9, 2.3),
    "deterioro":  Style(3.00, (8, 4, 11), (2.3, 3.4, 5.6), (1.1, 3.4, 4.3), 5.5, 9.0, 1.1),
}
SECTIONS = ("cape_top", "cape_mid", "cape_bottom")
RIBBON = re.compile(r"v17_ribbon_(\d+)_seg(\d+)")


def side_of(name: str, column: int) -> float:
    """Cada familia usa su propio centro, no el de los 12 jirones."""
    if name.startswith("v17_ribbon_"):
        axis = 5.5
    elif name.startswith("v15_cloth_"):
        axis = 4.0
    elif name.startswith("v17_vein_"):
        axis = 4.5
    elif name.startswith("v17_cowl_back_"):
        axis = 2.0
    elif name.startswith("v18_chain_"):
        axis = 3.5
    elif name.startswith("v18_pad_"):
        axis = 0.5
    else:
        axis = 3.0
    return (column - axis) / axis


def beat(angle: float) -> float:
    """Dos impulsos por vuelta: el primero más fuerte, el segundo un eco."""
    return .56 * ((1.0 + math.cos(angle)) / 2) ** 3 + .44 * ((1.0 - math.cos(angle)) / 2) ** 3


def sample(name: str, style: str, f: float) -> tuple[float, float, float]:
    spec = STYLES[style]
    t = 2 * math.pi * (f % 1.0)
    if name in SECTIONS:
        i = SECTIONS.index(name)
        phase = t + spec.phase - i * 0.92
        # Barrido de hombros a dobladillo; cada estilo vive durante todo
        # el ciclo, en vez de volver a reposo cada vuelta.
        pitch = spec.pitch[i] + spec.flex[i] * (
            0.78 * math.sin(phase) + 0.22 * math.sin(2 * t + spec.phase - i * 0.68))
        roll = spec.roll[i] * math.sin(phase - .8)
        yaw = (.45 + i * .45) * math.sin(phase + 1.1)
        if style == "caminar":
            pitch += (0.8 + i * 0.65) * math.sin(2 * phase - .6)
        elif style == "deterioro":
            pitch += (2 + i * 2.2) * beat(phase)
            roll += (0.8 + i * .75) * math.sin(3 * t - i * .95) * beat(phase)
        elif style == "agua":
            yaw *= 2.1
        return pitch, yaw, roll

    m = RIBBON.fullmatch(name)
    if m:
        col, seg = map(int, m.groups())
        side = side_of(name, col)
        hand = math.copysign(1.0, side)
        tail = (seg / 6) ** 1.20
        q = .16 + .84 * tail
        a = t + spec.phase - .57 * seg + .25 * col
        wave = math.sin(a) + .23 * math.sin(2 * a + .4)
        lag = math.sin(t + hand * .62 - .28 * seg)
        amp = spec.ripple * q * (.82 + .18 * abs(side))
        # Seg0 ancora la tela al cuello. Las puntas obedecen al resto
        # del paño; el rotZ abre las alas sin fabricar otro offset XYZ.
        pitch = amp * .44 * wave
        yaw = amp * .45 * math.cos(a) - spec.spread * side * (.08 + .24 * tail)
        roll = amp * (.66 * wave + .34 * hand * lag) - side * spec.spread * q
        if style == "caminar":
            roll += hand * 4.3 * q * math.sin(t - .44 * seg)
        elif style == "correr":
            pitch += 2.8 * q * math.sin(2 * a + .9)
        elif style == "caer":
            pitch += 4.1 * q * math.sin(2 * a - .6)
        elif style == "deterioro":
            roll += 10.0 * q * hand * beat(a) * math.sin(3 * t + .48 * col - .33 * seg)
        if col in (0, 10):       # gajos cortos cosidos junto a la hombrera
            pitch, yaw, roll = pitch*.58, yaw*.55, roll*.57
        return pitch, yaw, roll

    col = int(name.rsplit("_", 1)[1]) if name.rsplit("_", 1)[-1].isdigit() else 0
    side = side_of(name, col)
    a = t + spec.phase + side * .73
    if name.startswith("v17_cowl_tooth_"):
        # Solapa de tela pesada: rebote corto. El resto del cuello ancla.
        return .18 * spec.ripple * math.sin(a - .5), 0.0, .12 * spec.ripple * math.sin(a)
    if name.startswith(('v17_cowl_front_', 'v17_cowl_back_', 'v18_chain_')):
        # El pliegue del cuello y su costura quedan reunidos.
        return 0.0, 0.0, 0.0
    if name.startswith("v18_pad_"):
        return .55 * math.sin(a), 0.0, .37 * side * math.cos(a)
    if name.startswith("v17_vein_"):
        # Grabadas en su jirón. Rotan con él, escala heredada sin cambios.
        return 0.0, 0.0, 0.0
    return .45 * math.sin(a), 0.0, .47 * math.sin(a + .6)


def slope(name: str, style: str, f: float) -> tuple[float, float, float]:
    """Derivada en fase normalizada; se usa sólo para tangentes en BB."""
    h = 1e-5
    return tuple((p - m) / (2 * h) for p, m in
                 zip(sample(name, style, f + h), sample(name, style, f - h)))


def _self_test() -> None:
    tip = "v17_ribbon_4_seg6"
    assert len(STYLES) == 8
    for style in STYLES:
        for name in (*SECTIONS, tip, "v17_ribbon_7_seg0", "v17_cowl_tooth_3", "v18_pad_1"):
            assert sample(name, style, 0) == sample(name, style, 1)
            assert max(abs(a - b) for a, b in zip(slope(name, style, 0), slope(name, style, 1))) < 1e-6
            assert any(abs(a - b) > .1 for a, b in zip(sample(name, style, 0), sample(name, style, .31)))
    assert sample("cape_top", "volar", .5)[0] > sample("cape_top", "correr", .5)[0] + 8
    assert sample("cape_bottom", "caer", .5)[0] > sample("cape_bottom", "volar", .5)[0] + 18
    assert sample(tip, "agachado", .25)[2] < sample(tip, "volar", .25)[2]
    print("8 curvas rotacionales periódicas, con tangentes periódicas y perfiles de bisagra distintos")


if __name__ == "__main__":
    _self_test()
