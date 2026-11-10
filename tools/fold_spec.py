#!/usr/bin/env python3
"""Especificación compartida del modelo plegado v1.4.0.

Define cómo se reparte el atlas de 128×128 entre siete pliegues y la pose de
cada uno. tools/texture_pipeline.py usa STRIP_OFFSETS para dibujar los nervios
y tools/item_model_pipeline.py usa PANELS para construir el geo y la animación.
"""

from __future__ import annotations

STRIP_WIDTHS = [18, 18, 18, 19, 18, 18, 19]
STRIP_OFFSETS: list[int] = []
_acc = 0
for _w in STRIP_WIDTHS:
    STRIP_OFFSETS.append(_acc)
    _acc += _w
assert sum(STRIP_WIDTHS) == 128
assert STRIP_OFFSETS[-1] + STRIP_WIDTHS[-1] == 128

WIDTH = 14.4
PANEL_WIDTH = WIDTH / 7.0
TOP_Y = 14.2
LEFT_X = -WIDTH / 2.0


def _panel(i: int) -> dict:
    norm = (i - 3) / 3.0
    bulge = 1.0 - norm * norm
    return {
        "index": i,
        "x": LEFT_X + i * PANEL_WIDTH,
        "width": PANEL_WIDTH,
        "height": 9.6 + 3.2 * bulge,
        "depth": 0.15 + 1.0 * bulge,
        "bulge": bulge,
        "rx": 1.2 * (1.0 - bulge) + 0.2,
        "ry": (i - 3) * 2.4,
        "rz": (i - 3) * 0.9,
        "strip": {"uv": [STRIP_OFFSETS[i], 0], "uv_size": [STRIP_WIDTHS[i], 128]},
    }


PANELS = [_panel(i) for i in range(7)]

# Regiones reservadas en el atlas folded.
UV = {
    "lining": {"uv": [120, 0], "uv_size": [4, 128]},
    "piping": {"uv": [124, 0], "uv_size": [4, 128]},
    "edge": {"uv": [0, 0], "uv_size": [10, 8]},
    "top_band": {"uv": [0, 0], "uv_size": [120, 10]},
    "bottom_band": {"uv": [0, 118], "uv_size": [120, 10]},
    "gem": {"uv": [54, 30], "uv_size": [20, 22]},
}
