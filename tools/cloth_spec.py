#!/usr/bin/env python3
"""Especificación compartida de la superficie de tela v1.7.0.

El atlas de armadura sigue siendo de 128x128 y su alfa es prístino. La capa
equipada usa una ilustración continua de 96x48 texels (todos opacos) para sus
caras norte/sur, y columnas/zonas reservadas igual de opacas para creases,
forro, ribetes, yugo y costuras.

v1.6.0 corrige el defecto principal de v1.5.x: antes cada sección tomaba sus
propios bounds geométricos (distintos anchos y alturas) mientras la UV siempre
repartía 16 filas y 96/COLUMNS columnas. La ilustración se estiraba de forma
diferente en cada tercio, partiendo el medallón y las filigranas. Ahora las
tres secciones comparten UN rectángulo global y la misma escala, así que los
paneles reconstruyen el canvas como un mosaico sin costuras.

  * 9 columnas x 3 filas = 27 paneles, con retardo de fase en runtime.
  * hem_uv() da a cada lengüeta su propia porción del dobladillo continuo.

v1.7.0: FOLDS=3 pliegues ANCHOS en lugar de 9 rayas finas. fold_wave() es la
única fuente de verdad: el sombreado 2D del canvas y el relieve 3D en Z de
armor_model_pipeline.py muestrean la MISMA onda, así que cada valle oscuro
coincide con una crease geométrica y cada cresta iluminada con un panel
adelantado. Antes el relieve era una parábola y el sombreado 9 senos, sin
relación entre sí: la capa parecía una tabla rayada.

tools/armor_model_pipeline.py construye la geometría, tools/texture_pipeline.py
pinta el canvas y CapaArmorModel.java anima los huesos v15_cloth_*.
"""

from __future__ import annotations

import math

COLUMNS = 9
FOLDS = 3
SECTIONS = ("cape_top", "cape_mid", "cape_bottom")
CANVAS = {"uv": [0.0, 0.0], "uv_size": [96.0, 48.0]}
SECTION_V = ((0.0, 16.0), (16.0, 32.0), (32.0, 48.0))
STRIP_W = CANVAS["uv_size"][0] / COLUMNS


def fold_wave(u: float) -> float:
    """+1 en la cresta del pliegue, -1 en el valle (donde va la crease)."""
    return math.cos(2.0 * math.pi * FOLDS * u)


def fold_at_column(column: int) -> float:
    """Muestra de la onda en el centro de una columna del mosaico."""
    return fold_wave((column + 0.5) / COLUMNS)


def fold_valleys() -> tuple[int, ...]:
    """Columnas cuyo centro cae en un valle: ahí van las creases 3D."""
    return tuple(col for col in range(COLUMNS)
                 if fold_at_column(col) < -0.5)

UV = {
    # Superficie principal: una sola ilustración de alta resolución reducida a
    # 96x48. Todas sus filas y columnas están opacas en el PNG original.
    "cloth": dict(CANVAS),
    "top_band": {"uv": [0.0, 0.0], "uv_size": [96.0, 2.0]},
    "bottom_band": {"uv": [0.0, 46.0], "uv_size": [96.0, 2.0]},
    # Zonas sin emisivos: creases oscuros / iluminados, forro y ribete.
    "crease_dark": {"uv": [105.0, 0.0], "uv_size": [2.0, 48.0]},
    "crease_light": {"uv": [107.0, 0.0], "uv_size": [2.0, 48.0]},
    "edge": {"uv": [105.0, 0.0], "uv_size": [3.0, 21.0]},
    "lining": {"uv": [120.0, 0.0], "uv_size": [2.0, 48.0]},
    "rim": {"uv": [122.0, 0.0], "uv_size": [2.0, 48.0]},
    # Zonas ya emisivas / de armadura del atlas aprobado.
    "bright": {"uv": [69.0, 109.0], "uv_size": [6.0, 18.0]},
    "yoke": {"uv": [57.0, 76.0], "uv_size": [14.0, 17.0]},
}

# Rectángulos (x0, y0, x1, y1) donde el PNG prístino tiene alfa=255 en TODOS
# sus texels. La CI comprueba que ninguna UV nueva se salga de aquí.
OPAQUE_RECTS = (
    (0.0, 0.0, 96.0, 48.0),
    (105.0, 0.0, 109.0, 48.0),
    (120.0, 0.0, 124.0, 48.0),
    (69.0, 109.0, 75.0, 127.0),
    (57.0, 76.0, 71.0, 93.0),
)


def cloth_uv(section: int, column: int) -> dict:
    """Franja vertical continua para un panel de tela.

    GeoQuad.build invierte U cuando mirror=false, y BakedModelFactory invierte
    X al construir el cubo. Las dos inversiones se compensan: la columna `i`
    de la geometría debe tomar la franja `i` del canvas para que el mosaico
    quede en orden. (Validado con tools/preview_cloth.py --uv-test.)
    """
    v, v_end = SECTION_V[section]
    return {
        "uv": [round(column * STRIP_W, 4), v],
        "uv_size": [round(STRIP_W, 4), v_end - v],
    }


def hem_uv(column: int) -> dict:
    """Cada lengüeta toma su porción del dobladillo, no todo el chevron."""
    return {
        "uv": [round(column * STRIP_W, 4), 46.0],
        "uv_size": [round(STRIP_W, 4), 2.0],
    }


def section_uv(region: str, section: int, width: float | None = None) -> dict:
    """Misma franja de una columna reservada, alineada con la sección."""
    spec = UV[region]
    v, v_end = SECTION_V[section]
    height = v_end - v
    u, base_v = spec["uv"]
    w = spec["uv_size"][0] if width is None else width
    h = min(spec["uv_size"][1], height)
    # Las columnas 105..123 empiezan en v=0; las zonas emisivas/yugo ya
    # tienen su propia v absoluta y se usan completas.
    offset = v if base_v == 0.0 else 0.0
    return {"uv": [u, base_v + offset], "uv_size": [w, h]}


def assert_opaque(spec: dict) -> None:
    u, v = spec["uv"]
    w, h = spec["uv_size"]
    assert w > 0 and h > 0, spec
    assert 0 <= u and 0 <= v and u + w <= 128 and v + h <= 128, spec
    assert any(
        u >= x0 and v >= y0 and u + w <= x1 and v + h <= y1
        for x0, y0, x1, y1 in OPAQUE_RECTS
    ), f"UV {spec} no cae en una zona opaca"
