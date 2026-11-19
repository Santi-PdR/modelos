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
    phase: float
    lag: float                       # propagación de la onda hacia el borde


STYLES = {
    "idle":       Style(3.60, (.35, .65, -.55), (.44, .87, 1.48), (.12, .48, .89), .38, 1.56, .25, 1.04),
    "caminar":    Style(1.00, (7, 4.8, -2.7), (1.22, 2.7, 4.3), (.51, 1.35, 2.6), 2.4, 4.2, .42, 1.13),
    "correr":     Style(0.72, (26, 12, -7.4), (1.3, 2.75, 4.6), (.39, .97, 1.95), -6.0, 5.6, .82, .80),
    "volar":      Style(1.35, (44, 11, -4.7), (1.42, 2.72, 4.0), (.63, 1.76, 3.5), 10.8, 7.60, 1.46, .83),
    "caer":       Style(0.90, (17, 17, 19), (1.5, 3.1, 5.1), (.79, 1.95, 3.8), 5.1, 7.0, 1.65, 1.08),
    "agachado":   Style(2.60, (7.5, -3.25, -4.75), (.66, 1.09, 1.5), (.13, .45, .91), -9.5, 1.85, .28, 1.0),
    "agua":       Style(3.20, (11.5, 7, -11.8), (1.55, 3.1, 4.7), (.58, 3.28, 7.9), 3.6, 5.4, 2.2, 1.35),
    "deterioro":  Style(3.00, (5.8, 2.15, 8.3), (1.7, 2.68, 4.35), (.69, 2.23, 3.55), 4.3, 6.8, 1.10, 1.12),
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
        phase = t + spec.phase - spec.lag * i
        # La onda se propaga desde la costura sin volver a reposo al cerrar
        # el ciclo. La sección superior es la más contenida.
        pitch = spec.pitch[i] + spec.flex[i] * (
            .86 * math.sin(phase) + .14 * math.sin(2 * phase + .45))
        roll = spec.roll[i] * math.sin(phase - .7)
        yaw = (.36 + i * .39) * math.sin(phase + 1.1)
        if style == "caminar":
            # Dos pasos por vuelta; la oscilación lateral cambia de pie.
            pitch += (.65 + i*.67) * math.cos(2*phase - .6)
            yaw += (.25 + i*.31) * math.sin(phase - .66)
        elif style == "volar":
            # Planeo más sostenido, con balanceo, no aleteo desde el cuello.
            yaw += (.18 + i*.48) * math.cos(phase - .48)
        elif style == "caer":
            # La subida de la orilla tiene un impulso y una recuperación.
            pulse = (.5 + .5*math.cos(phase - .25))**3
            pitch += (1.9 + i*2.0) * pulse
        elif style == "deterioro":
            pitch += (1.8 + i * 2.20) * beat(phase)
            roll += (.75 + i * .71) * math.sin(3 * t - i * .95) * beat(phase)
        elif style == "agua":
            yaw *= 2.2
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
        a = t + spec.phase - spec.lag * (.36 * seg + .038 * seg**2)
        wave = math.sin(a + .35 * side) + .14 * math.sin(2 * a + .42)
        amp = spec.ripple * q * (.76 + .24 * abs(side))
        pitch = .42 * amp * wave
        yaw = .24 * amp * math.cos(a + .35*side) - .22 * spec.spread * side * q
        roll = amp * (.60 * math.sin(a - .62) + .27 * side * wave) - .71 * side * spec.spread * q
        if style == "caminar":
            pitch += 1.55 * side * q * math.sin(a - .45)
            roll += hand * 1.75 * q * math.sin(a - .63)
        elif style == "correr":
            pitch += 1.32 * q * math.sin(2 * a + .82 + .55*side)
        elif style == "caer":
            pitch += 2.36 * q * (.5 + .5 * math.cos(a - .22))**3
        elif style == "agua":
            yaw += 1.32 * q * math.cos(a - .55)
        elif style == "deterioro":
            pitch += 3.15 * q * beat(a)
            roll += 3.35 * q * hand * beat(a) * math.sin(2*a + .32*side)
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
