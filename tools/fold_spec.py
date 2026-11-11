#!/usr/bin/env python3
"""Especificación compartida del item plegado v1.9.0: un bulto de tela 3D.

El item deja de ser un abanico de 7 láminas casi planas (v1.4-v1.7) y pasa a
ser una capa DOBLADA con volumen: bloque de forro detrás, 7 franjas delanteras
con relieve en Z, yugo, cuello levantado, broche de diamante, 3 rollos de tela
en la base y 5 puntas de dobladillo. Las 7 franjas siguen sampleando porciones
continuas del atlas de 128x128, así que reconstruyen la MISMA ilustración,
pero ahora con grosor, capas y una silueta legible en mano y en el slot.

tools/texture_pipeline.py usa STRIP_OFFSETS/STRIP_WIDTHS para el sombreado por
pliegue y tools/item_model_pipeline.py usa PANELS para el geo y la animación.
v1.9.0 añade dos regiones reservadas para las hombreras del bulto y una
animación propia de item en GUI/mano (`animation.item`).
"""

from __future__ import annotations

# 120 columnas para las 7 franjas; 120..128 quedan reservadas al forro y al
# ribete. Antes las franjas ocupaban 128 y pisaban esas columnas reservadas.
STRIP_WIDTHS = [17, 17, 17, 18, 17, 17, 17]
STRIP_OFFSETS: list[int] = []
_acc = 0
for _w in STRIP_WIDTHS:
    STRIP_OFFSETS.append(_acc)
    _acc += _w
assert sum(STRIP_WIDTHS) == 120
assert STRIP_OFFSETS[-1] + STRIP_WIDTHS[-1] == 120

WIDTH = 9.6
PANEL_WIDTH = WIDTH / 7.0
TOP_Y = 12.2
BOTTOM_Y = 1.6
LEFT_X = -WIDTH / 2.0


def _panel(i: int) -> dict:
    norm = (i - 3) / 3.0
    bulge = 1.0 - norm * norm
    return {
        "index": i,
        "x": LEFT_X + i * PANEL_WIDTH,
        "width": PANEL_WIDTH,
        "height": TOP_Y - BOTTOM_Y + 0.4 * bulge,
        # Relieve en Z: el centro del bulto viene hacia el espectador.
        "depth": 1.05 + 0.35 * bulge,
        "bulge": bulge,
        # Rotación mínima: curva suave, no abanico abierto.
        "rx": 0.0,
        "ry": (i - 3) * 0.6,
        "rz": 0.0,
        "strip": {"uv": [STRIP_OFFSETS[i], 0], "uv_size": [STRIP_WIDTHS[i], 128]},
    }


PANELS = [_panel(i) for i in range(7)]

# Regiones reservadas en el atlas folded. `edge` ya no pisa el yoke; `roll`
# pinta los tres pliegues horizontales de la base.
UV = {
    "lining": {"uv": [120, 0], "uv_size": [4, 128]},
    "piping": {"uv": [124, 0], "uv_size": [4, 128]},
    "edge": {"uv": [96, 64], "uv_size": [10, 8]},
    "top_band": {"uv": [0, 0], "uv_size": [120, 10]},
    "bottom_band": {"uv": [0, 118], "uv_size": [120, 10]},
    "gem": {"uv": [54, 30], "uv_size": [20, 22]},
    "roll": {"uv": [96, 48], "uv_size": [24, 16]},
    # v1.9.0: hombreras del bulto plegado. Zonas libres entre `edge` y el
    # borde derecho, lejos del canvas y del broche.
    "pauldron": {"uv": [96, 72], "uv_size": [24, 16]},
    "pauldron_rim": {"uv": [96, 88], "uv_size": [24, 8]},
}
