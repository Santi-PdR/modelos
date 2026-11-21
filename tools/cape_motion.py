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
    "idle":       Style(3.60, (.35, .66, -.70), (.27, .76, 1.73), (.09, .39, 1.02), .70, 2.30, .25, 1.12),
    "caminar":    Style(1.00, (7, 4.8, -2.7), (.57, 1.42, 2.85), (.36, .84, 1.78), 2.4, 4.0, -.24, 1.08),
    "correr":     Style(0.72, (26, 12, -7.4), (.44, 1.06, 2.42), (.20, .53, 1.06), -6.0, 4.4, -.37, .78),
    "volar":      Style(1.35, (44, 11, -4.7), (1.42, 2.72, 4.0), (.63, 1.76, 3.5), 10.8, 7.60, 1.46, .83),
    "caer":       Style(0.90, (17, 17, 19), (1.5, 3.1, 5.1), (.79, 1.95, 3.8), 5.1, 7.0, 1.65, 1.08),
    "agachado":   Style(2.60, (7.8, -1.8, -7.6), (.38, .74, 1.10), (.09, .28, .74), -8.3, 1.48, .28, 1.18),
    "agua":       Style(3.20, (11.5, 7, -11.8), (1.55, 3.1, 4.7), (.58, 3.28, 7.9), 3.6, 5.4, 2.2, 1.35),
    "deterioro":  Style(3.00, (5.8, 2.15, 8.3), (1.7, 2.68, 4.35), (.69, 2.23, 3.55), 4.3, 6.8, 1.10, 1.12),
}
SECTIONS = ("cape_top", "cape_mid", "cape_bottom")
GAITS = ("caminar", "correr")
QUIET = ("idle", "agachado")
RIBBON = re.compile(r"v17_ribbon_(\d+)_seg(\d+)")


LAST_JOINT = 4


def beat(angle: float) -> float:
    """Dos impulsos por vuelta: el primero más fuerte, el segundo un eco."""
    return .56 * ((1.0 + math.cos(angle)) / 2) ** 3 + .44 * ((1.0 - math.cos(angle)) / 2) ** 3


def gait_hinge(spec: Style, i: int, t: float, sprint: bool) -> tuple[float, float, float]:
    # Vanilla's stride is one full left/right pair. Load twice per cycle,
    # with the return travelling down the cloth instead of pumping its seat.
    a = t + spec.phase - spec.lag * .54 * i
    recoil = .82 * math.sin(2 * a) + .18 * math.sin(a - .35)
    yaw = (.12 + i * .22 if sprint else .24 + i * .32) * math.sin(a + .85)
    roll = spec.roll[i] * math.sin(a - .55)
    return spec.pitch[i] + spec.flex[i] * recoil, yaw, roll


def gait_ribbon(spec: Style, side: float, q: float, seg: int, t: float, sprint: bool) -> tuple[float, float, float]:
    a = t + spec.phase - spec.lag * (.40 + .24 * seg + .036 * seg**2)
    amp = spec.ripple * q * (.76 + .24 * abs(side))
    recoil = math.sin(2 * a - .16)
    # Walking transfers weight from edge to edge. In a sprint the drape
    # stays swept back and the hem mostly follows the two smaller rebounds.
    cross = math.sin(a - .42)
    pitch = amp * (.32 * recoil + .10 * math.sin(a + .35 * side))
    pitch += (0.78 if sprint else 2.8) * side * q * cross
    yaw = .14 * amp * math.cos(a + .35 * side) - .22 * spec.spread * side * q
    roll = amp * (.32 * math.sin(a - .65) + .18 * side * recoil) - .71 * side * spec.spread * q
    roll += (0.5 if sprint else 1.7) * q * side * cross
    return pitch, yaw, roll


def quiet_hinge(spec: Style, i: int, t: float, crouched: bool) -> tuple[float, float, float]:
    # Little motion at the seam. A delayed fold carries the breath out to
    # the hem; in a crouch the last hinge folds down under the middle panel.
    a = t + spec.phase - spec.lag * i
    wave = .94 * math.sin(a) + .06 * math.sin(2 * a + .4)
    yaw = ((.11, .24, .57) if crouched else (.17, .42, .94))[i] * math.sin(a + .86)
    return spec.pitch[i] + spec.flex[i] * wave, yaw, spec.roll[i] * math.sin(a - .70)


def quiet_ribbon(spec: Style, side: float, q: float, seg: int, t: float, crouched: bool) -> tuple[float, float, float]:
    # The two sides do not breathe in unison. Asymmetric phase, not an
    # offset at the attachment, lets the edge travel across the folds.
    a = t + spec.phase - spec.lag * (.40 * seg + .04 * seg**2) + .62 * side
    amp = spec.ripple * q * (.80 + .20 * abs(side))
    pitch = .48 * amp * math.sin(a) + q * (-.35 if crouched else .22 * side)
    yaw = .22 * amp * math.cos(a + .22) - .22 * spec.spread * side * q
    roll = amp * (.55 * math.sin(a - .72) + .12 * side * math.cos(a)) - .71 * spec.spread * side * q
    return pitch, yaw, roll


def sample(name: str, style: str, f: float) -> tuple[float, float, float]:
    spec = STYLES[style]
    t = 2 * math.pi * (f % 1.0)
    if name in SECTIONS:
        i = SECTIONS.index(name)
        if style in GAITS:
            return gait_hinge(spec, i, t, style == "correr")
        if style in QUIET:
            return quiet_hinge(spec, i, t, style == "agachado")
        phase = t + spec.phase - spec.lag * i
        # La onda se propaga desde la costura sin volver a reposo al cerrar
        # el ciclo. La sección superior es la más contenida.
        pitch = spec.pitch[i] + spec.flex[i] * (
            .86 * math.sin(phase) + .14 * math.sin(2 * phase + .45))
        roll = spec.roll[i] * math.sin(phase - .7)
        yaw = (.36 + i * .39) * math.sin(phase + 1.1)
        if style == "volar":
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
        # The sewn root has no extra local swing. At the last articulated
        # segment three solids share one rotation; no flapping loose tip.
        tail = seg / LAST_JOINT
        q = tail**1.45
        if style in GAITS:
            pitch, yaw, roll = gait_ribbon(spec, side, q, seg, t, style == "correr")
        elif style in QUIET:
            pitch, yaw, roll = quiet_ribbon(spec, side, q, seg, t, style == "agachado")
        else:
            a = t + spec.phase - spec.lag * (.36 * seg + .038 * seg**2)
            wave = math.sin(a + .35 * side) + .14 * math.sin(2 * a + .42)
            amp = spec.ripple * q * (.76 + .24 * abs(side))
            pitch = .42 * amp * wave
            yaw = .24 * amp * math.cos(a + .35*side) - .22 * spec.spread * side * q
            roll = amp * (.60 * math.sin(a - .62) + .27 * side * wave) - .71 * side * spec.spread * q
            if style == "caer":
                pitch += 2.36 * q * (.5 + .5 * math.cos(a - .22))**3
            elif style == "agua":
                yaw += 1.32 * q * math.cos(a - .55)
            elif style == "deterioro":
                pitch += 3.15 * q * beat(a)
                roll += 3.35 * q * math.copysign(1., side) * beat(a) * math.sin(2*a + .32*side)
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

    phases = [j/120 for j in range(120)]
    def pitches(name, style):
        return [sample(name, style, f)[0] for f in phases]

    # Two rebounds, increasing amplitude and a later crest at each hinge.
    # Alternation across the walking hem is distinct from that rebound.
    side_to_side = []
    for style in GAITS:
        sections = [pitches(n, style) for n in SECTIONS]
        arcs = [max(a) - min(a) for a in sections]
        assert .6 < arcs[0] < 1.25 and arcs[0] * 1.5 < arcs[1] < arcs[2] < 6
        for a in sections:
            strength = [math.hypot(sum(v * math.sin(n * 2*math.pi*f) for v, f in zip(a, phases)),
                                   sum(v * math.cos(n * 2*math.pi*f) for v, f in zip(a, phases))) for n in (1,2)]
            assert strength[1] > 4 * strength[0], (style, strength)
        crests = [max(range(60), key=a.__getitem__) for a in sections]
        assert crests[0] < crests[1] < crests[2], (style, crests)
        edge = [x-y for x, y in zip(*(pitches(f'v17_ribbon_{c}_seg4',style) for c in (2,9)))]
        side_to_side.append(max(edge) - min(edge))
    assert side_to_side[0] > 3 * side_to_side[1]
    for style in QUIET:
        sections = [pitches(n, style) for n in SECTIONS]
        arcs = [max(a) - min(a) for a in sections]
        assert .35 < arcs[0] < .85 and arcs[0] < arcs[1] < arcs[2] < 3.6, (style, arcs)
        crests = [max(range(len(a)), key=a.__getitem__) for a in sections]
        assert crests[0] < crests[1] < crests[2], (style, crests)
    assert max(pitches(SECTIONS[-1], 'agachado')) < -6.
    print("8 curvas periódicas; doble apoyo, balance de marcha y reposo con retardo hacia el dobladillo")


if __name__ == "__main__":
    _self_test()
