"""Lectura de las pistas físicas de GeckoLib (tiempo en segundos).

Las rotaciones nuevas son un bake lineal; los arcos easing de los cuatro
clips antiguos son necesarios para el comparativo exacto de v1.58.0.
"""
from __future__ import annotations

import math
from bisect import bisect_right

DEFAULTS = {"rotation": (0., 0., 0.), "position": (0., 0., 0.), "scale": (1., 1., 1.)}


def prepare(track):
    if isinstance(track, list):
        return (0.,), (tuple(track),), ("linear",)
    keys = sorted((float(t), p) for t, p in track.items())
    return (tuple(t for t, p in keys),
            tuple(tuple(p if isinstance(p, list) else p["vector"]) for t, p in keys),
            tuple("linear" if isinstance(p, list) else p.get("easing", "linear") for t, p in keys))


def prepare_clip(clip, names=None):
    return {name: {ch: prepare(track) for ch, track in channels.items() if ch in DEFAULTS}
            for name, channels in clip["bones"].items() if names is None or name in names}


def sample(track, t):
    times, values, ease = track
    index = bisect_right(times, t)
    if index == 0:
        return values[0]
    if index == len(times):
        return values[-1]
    x = (t - times[index - 1]) / (times[index] - times[index - 1])
    if ease[index] == "easeInOutSine":
        x = (1 - math.cos(math.pi * x)) / 2
    elif ease[index] == "easeOutSine":
        x = math.sin(x * math.pi / 2)
    elif ease[index] == "easeInSine":
        x = 1 - math.cos(x * math.pi / 2)
    elif ease[index] != "linear":
        raise ValueError(f"easing de GeckoLib no soportado: {ease[index]}")
    return tuple(a + x * (b - a) for a, b in zip(values[index - 1], values[index]))
