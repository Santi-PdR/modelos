#!/usr/bin/env python3
"""Eight periodic poses for a rigid yoke and a delayed cloth hem.

Render and editor sample the same curves. Only the cloth flexes; hardware,
collar and the fastening pads have no breathing/scale or free translation.
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
    "idle":       Style(3.60, (0.4, 0.5, -0.7), (.6, 1.0, 1.7), (.14, .62, .96), 0.45, 1.8, .25),
    "caminar":    Style(1.00, (8, 5, -2), (1.8, 3.4, 4.5), (.74, 1.8, 3.2), 2.2, 4.0, .4),
    "correr":     Style(0.72, (27, 12, -7), (2.1, 3.2, 5.3), (.64, 1.8, 3.8), -5.5, 6.4, .8),
    "volar":      Style(1.35, (45, 11, -5), (2.7, 4.2, 5.0), (.74, 1.5, 2.8), 11.5, 8.4, 1.5),
    "caer":       Style(0.90, (18, 19, 22), (2.5, 4.7, 6.3), (.85, 2.4, 4.2), 5.0, 7.8, 2.0),
    "agachado":   Style(2.60, (9, -4, -6), (.8, 1.2, 1.8), (.18, .53, 1.1), -10.5, 2.1, .3),
    "agua":       Style(3.20, (12, 7, -12), (1.7, 3.6, 5.1), (.65, 3.6, 8.1), 3.6, 5.2, 2.3),
    "deterioro":  Style(3.00, (6, 2, 9), (1.8, 2.8, 4.7), (.72, 2.4, 3.6), 4.2, 7.0, 1.1),
}
SECTIONS = ("cape_top", "cape_mid", "cape_bottom")
RIBBON = re.compile(r"v17_ribbon_(\d+)_seg(\d+)")


LAST_JOINT = 4


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
        if not 1 <= seg <= LAST_JOINT:
            return 0., 0., 0.
        side = (col - 5.5) / 5.5
        hand = math.copysign(1.0, side)
        # The sewn root has no extra local swing. At the last articulated
        # segment three solids share one rotation; no flapping loose tip.
        tail = seg / LAST_JOINT
        q = tail**1.45
        a = t + spec.phase - .62 * seg + .32 * side
        wave = math.sin(a) + .13 * math.sin(2 * a + .4)
        ensemble = math.sin(t + spec.phase - .62 * seg - .68)
        amp = spec.ripple * q * (.76 + .24 * abs(side))
        pitch = .44 * amp * wave
        yaw = .26 * amp * math.cos(a) - .22 * spec.spread * side * q
        roll = amp * (.64 * ensemble + .25 * side * wave) - .72 * side * spec.spread * q
        if style == "caminar":
            roll += hand * 2.4 * q * math.sin(t - .54 * seg)
        elif style == "correr":
            pitch += 1.50 * q * math.sin(2 * a + .9)
        elif style == "caer":
            pitch += 2.30 * q * math.sin(2 * a - .6)
        elif style == "deterioro":
            pitch += 3.6 * q * beat(a)
            roll += 3.6 * q * hand * beat(a) * math.sin(2 * t + .32 * side - .42 * seg)
        if col in (0, 10):
            pitch, yaw, roll = pitch*.63, yaw*.56, roll*.60
        return pitch, yaw, roll

    # The yoke is stitched, not a collection of independently pumping
    # plates. Keep those tracks at their neutral values for raw clip swaps.
    return 0.0, 0.0, 0.0


def slope(name: str, style: str, f: float) -> tuple[float, float, float]:
    """Derivada en fase normalizada; se usa sólo para tangentes en BB."""
    h = 1e-5
    return tuple((p - m) / (2 * h) for p, m in
                 zip(sample(name, style, f + h), sample(name, style, f - h)))


def _self_test() -> None:
    tip = "v17_ribbon_4_seg4"
    assert len(STYLES) == 8
    for style in STYLES:
        for name in (*SECTIONS, tip, "v17_ribbon_7_seg2"):
            assert sample(name, style, 0) == sample(name, style, 1)
            assert max(abs(a - b) for a, b in zip(slope(name, style, 0), slope(name, style, 1))) < 1e-6
            assert any(abs(a - b) > .1 for a, b in zip(sample(name, style, 0), sample(name, style, .31)))
        for n in ("v17_ribbon_7_seg0", "v17_cowl_tooth_3", "v18_pad_1", "v18_chain_0"):
            assert sample(n, style, .37) == (0., 0., 0.)
    assert sample("cape_top", "volar", .5)[0] > sample("cape_top", "correr", .5)[0] + 8
    assert sample("cape_bottom", "caer", .5)[0] > sample("cape_bottom", "volar", .5)[0] + 18
    assert sample(tip, "agachado", .25)[2] < sample(tip, "volar", .25)[2]
    print("8 curvas rotacionales periódicas, con tangentes periódicas y perfiles de bisagra distintos")


if __name__ == "__main__":
    _self_test()
