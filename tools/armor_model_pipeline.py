#!/usr/bin/env python3
"""Reconstruye la capa EQUIPADA como una superficie de tela continua (v1.9.0).

Lee tools/originals/capa_deteriorer_evilsaiyan.geo.json (72 huesos / 126 cubos,
copia prístina aprobada) y NO modifica ni uno solo de esos huesos. Añade una
segunda piel hecha de 9 columnas por cada una de las 3 secciones:

  * 27 paneles delgados con curvatura suave en Z, que reconstruyen el canvas
    de 96x48 como un mosaico sin costuras;
  * 9 pliegues maestros (3 por sección) en los VALLES de la onda compartida
    FOLDS=3, 6 ribetes laterales, 9 lengüetas de dobladillo con festón real,
    2 alas de cuello, 1 broche emisivo, 5 estrellas 3D y 4 fragmentos
    orbitales de Blight Star alrededor del medallón;
  * v1.9.0: 9 nervios 3D en las crestas, 2 cortinas laterales continuas,
    5 pesas de dobladillo, cuello trasero, 2 tirantes de suspensión y un
    arnés delantero completo (2 hombreras, 2 tiras, 2 cadenas, broche y
    cuello de 3 piezas, placa central, bandas y faldillas). Total:
    171 huesos / 234 cubos.

v1.7.0: el relieve 3D y el sombreado del canvas muestrean la MISMA onda
(cloth_spec.fold_wave). Antes el relieve era una parábola y el canvas tenía
9 senos independientes: la capa parecía una tabla rayada. Ahora hay 3
pliegues anchos; cada valle oscuro coincide con una crease geométrica y cada
cresta iluminada con un panel adelantado.

v1.8.0: añade 5 pequeñas estrellas 3D (`v15_star_*`) en las coordenadas de la
constelación del canvas. Usan la zona emisiva `bright` ya existente, así que
el `CapaGlowLayer` las hace latir sin ampliar la cobertura del glowmask.

v1.9.0: añade 4 fragmentos orbitales (`v15_orbit_*`) alrededor del núcleo de
Blight Star, relieve grueso en las crestas, drapeados laterales, pesas que
cuelgan, cuello trasero, tirantes y un arnés FRONTAL con hombreras. La tela
sigue lisa/continua: el 3D vive en capas delgadas encima del mosaico.
Total: **171 huesos / 234 cubos**.

Diferencia clave frente a v1.5.x: las tres secciones comparten UN rectángulo
global de tela. Antes cada sección usaba sus propios bounds (distintos anchos
y alturas) con la misma UV de 16 filas, así que la ilustración se estiraba de
forma diferente en cada tercio: el medallón se partía y las filigranas no
continuaban. Ahora la escala es idéntica y el mosaico encaja.

En runtime CapaArmorModel oculta los cubos de cape_top/mid/bottom y el detalle
boxy original, pero deja vivos todos sus hijos: los 72 huesos y las animaciones
hand-made siguen mandando. El modelo Java aplica además una onda con retardo
de fase, inspirada en WaveyCapes / Finery / GlowberryClient.

Todas las UV nuevas caen en rectángulos 100% opacos del atlas de 128x128;
alfa base y cobertura emisiva no cambian. Uso:

    python3 tools/armor_model_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from cloth_spec import (
    COLUMNS,
    FOLDS,
    SECTION_V,
    SECTIONS,
    STRIP_W,
    UV,
    assert_opaque,
    cloth_uv,
    fold_at_column,
    fold_crests,
    fold_valleys,
    hem_uv,
    section_uv,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"


def spec(region: str, section: int | None = None, width: float | None = None) -> dict:
    result = dict(section_uv(region, section, width)) if section is not None else dict(UV[region])
    assert_opaque(result)
    return result


def faces(north: dict, south: dict | None = None, section: int = 0) -> dict:
    out = {
        "north": dict(north),
        "south": dict(south or north),
        "east": spec("edge", section),
        "west": spec("edge", section),
        "up": spec("top_band"),
        "down": spec("bottom_band"),
    }
    for face in out.values():
        assert_opaque(face)
    return out


def cube(origin, size, north, south=None, section: int = 0):
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": faces(north, south, section),
    }


def bone(name: str, parent: str, pivot, rotation, cubes):
    return {
        "name": name,
        "parent": parent,
        "pivot": [round(v, 4) for v in pivot],
        "rotation": [round(v, 4) for v in rotation],
        "cubes": cubes,
    }


def global_bounds(by_name: dict) -> tuple[float, float, float, float]:
    """Un ÚNICO rectángulo para las 3 secciones (adiós a la distorsión UV)."""
    cubes = [c for section in SECTIONS for c in by_name[section]["cubes"]]
    x0 = min(c["origin"][0] for c in cubes)
    x1 = max(c["origin"][0] + c["size"][0] for c in cubes)
    y0 = min(c["origin"][1] for c in cubes)
    y1 = max(c["origin"][1] + c["size"][1] for c in cubes)
    return x0, x1, y0, y1


# Vuelo de campana MUY sutil. Un 6% se probó y producía escalones visibles en
# los ribetes laterales (cada fila quedaba a distinto x); al 1% la silueta
# deja de ser un rectángulo perfecto sin romper la línea continua del borde.
# Es sólo geometría: las UV siguen siendo las mismas franjas globales.
FLARE = (0.99, 1.00, 1.01)


def row_bounds(gx0, gx1, gy0, gy1, section: int):
    """Fila `section` (0=arriba): x0, x1, y0, y1, paso de columna."""
    f = FLARE[section]
    x0, x1 = gx0 * f, gx1 * f
    row_h = (gy1 - gy0) / len(SECTIONS)
    y_lo = gy0 + (len(SECTIONS) - 1 - section) * row_h
    y_hi = y_lo + row_h
    if section < len(SECTIONS) - 1:
        y_lo -= 0.05          # cubre la junta con la fila inferior
    if section > 0:
        y_hi += 0.05          # cubre la junta con la fila superior
    return x0, x1, y_lo, y_hi, (x1 - x0) / COLUMNS


def panel_z(section: int, column: int) -> float:
    """Relieve en Z muestreando la MISMA onda que el sombreado del canvas.

    `fold_at_column` vale +1 en las crestas y -1 en los valles. La amplitud
    (0.055) es menor que el grosor del panel (0.10) para que dos columnas
    vecinas nunca dejen un hueco visto de lado; el pliegue se lee por la
    diferencia de profundidad y por la crease 3D, no por una grieta.
    """
    norm = (column - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
    # v1.9.0: relieve más notorio sin abrir huecos. La amplitud sigue siendo
    # menor que el grosor útil del conjunto (panel 0.10 + nervios y drapeados).
    return (2.58 + 0.11 * section + 0.18 * (1.0 - norm * norm)
            + 0.085 * fold_at_column(column))


def build() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)
    by_name = {b["name"]: b for b in original_bones}

    gx0, gx1, gy0, gy1 = global_bounds(by_name)
    rows = [row_bounds(gx0, gx1, gy0, gy1, si) for si in range(len(SECTIONS))]

    for si, section in enumerate(SECTIONS):
        x0, x1, y_lo, y_hi, step = rows[si]

        # 1. Paneles de tela: mosaico 9x3 con curvatura en Z y giro mínimo.
        #    Casi planos en reposo para que las UV encajen; la onda la aplica
        #    CapaArmorModel en runtime (en radianes).
        for col in range(COLUMNS):
            x = x0 + col * step - 0.045
            width = step + 0.09
            z = panel_z(si, col)
            pivot = [x + width / 2.0, (y_lo + y_hi) / 2.0, z]
            # Sin giro Y por columna: cualquier giro abre huecos entre
            # franjas UV. La inclinación X es común a toda la fila, así el
            # mosaico sigue cerrado y la capa cae hacia atrás.
            rotation = [0.6 + 1.0 * si, 0.0, 0.0]
            uv = cloth_uv(si, col)
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section, pivot, rotation,
                [cube((x, y_lo, z), (width, y_hi - y_lo, 0.10), uv, uv, si)],
            ))

        # 2. Una crease 3D por VALLE de la onda compartida FOLDS=3 (columnas
        #    1, 4, 7). Coincide exactamente con la línea oscura del canvas:
        #    sombreado y relieve cuentan el mismo pliegue, sin código de barras.
        for k, valley in enumerate(fold_valleys()):
            x = x0 + (valley + 0.5) * step - 0.022
            z = panel_z(si, valley) + 0.03
            tone = spec("crease_dark" if k % 2 == 0 else "crease_light", si)
            bones.append(bone(
                f"v15_crease_{section}_{k}",
                f"v15_cloth_{section}_{valley}",
                [x + 0.022, (y_lo + y_hi) / 2.0, z],
                [0.0, 0.0, 0.0],
                [cube((x, y_lo + 0.05, z), (0.044, y_hi - y_lo - 0.10, 0.035),
                      tone, None, si)],
            ))

        # 3. Ribetes laterales: enmarcan la tela sin neón estridente.
        for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
            x = x0 - 0.02 if sx < 0 else x1 - 0.14
            z = panel_z(si, col) + 0.07
            bones.append(bone(
                f"v15_pipe_{section}_{side}",
                f"v15_cloth_{section}_{col}",
                [x + 0.07, (y_lo + y_hi) / 2.0, z],
                [0.0, -sx * 2.0, 0.0],
                [cube((x, y_lo + 0.10, z), (0.14, y_hi - y_lo - 0.20, 0.09),
                      spec("rim"), spec("rim"), si)],
            ))

    # 4. Dobladillo con FESTÓN REAL: las lengüetas centrales cuelgan más y se
    #    inclinan hacia atrás. Cada una samplea SÓLO su porción del chevron,
    #    así el festón pintado no se repite 9 veces.
    bx0, _, _, _, bstep = rows[2]
    for col in range(COLUMNS):
        center = bx0 + (col + 0.5) * bstep
        norm = (col - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
        length = 0.52 + 0.34 * (1.0 - norm * norm)
        z = panel_z(2, col) + 0.05
        tilt = -1.2 if col % 2 == 0 else 1.2
        uv = hem_uv(col)
        bones.append(bone(
            f"v15_hem_{col}", f"v15_cloth_cape_bottom_{col}",
            [center, gy0 - 0.06, z],
            [2.0 + 2.0 * (1.0 - norm * norm), 0.0, tilt],
            [cube((center - bstep * 0.48, gy0 - 0.06 - length, z),
                  (bstep * 0.96, length, 0.11), uv, uv, 2)],
        ))

    # 4b. Estrellas 3D de la constelación: 5 gemas diminutas que coinciden
    #     con los puntos brillantes del canvas. Usan la zona emisiva `bright`
    #     ya existente, así que CapaGlowLayer las hace latir SIN ampliar la
    #     cobertura del glowmask prístino (no se abren huecos en la tela).
    def canvas_point(u: float, v: float):
        si = next(i for i, (a, b) in enumerate(SECTION_V) if a <= v < b)
        column = min(COLUMNS - 1, max(0, int(u / STRIP_W)))
        x = gx0 + (u / 96.0) * (gx1 - gx0)
        y = gy1 - (v / 48.0) * (gy1 - gy0)
        z = panel_z(si, column) + 0.09
        return si, column, x, y, z

    star_points = ((18, 18), (78, 18), (26, 35), (70, 35), (48, 30))
    for i, (su, sv) in enumerate(star_points):
        si, col, sx, sy, sz = canvas_point(su, sv)
        section = SECTIONS[si]
        size = 0.20
        bones.append(bone(
            f"v15_star_{i}",
            f"v15_cloth_{section}_{col}",
            [sx, sy, sz], [0.0, 0.0, 45.0],
            [cube((sx - size / 2.0, sy - size / 2.0, sz),
                  (size, size, 0.045),
                  spec("bright"), spec("bright"), si)],
        ))

    # 4c. v1.9.0: 4 fragmentos orbitales alrededor del núcleo de Blight Star.
    #     Son diamantes aún más pequeños que las estrellas, en los puntos
    #     cardinales del medallón. CapaArmorModel los hace girar despacio.
    orbit_points = ((48.0, 12.4), (54.1, 18.5), (48.0, 24.6), (41.9, 18.5))
    for i, (su, sv) in enumerate(orbit_points):
        si, col, sx, sy, sz = canvas_point(su, sv)
        section = SECTIONS[si]
        size = 0.13
        bones.append(bone(
            f"v15_orbit_{i}",
            f"v15_cloth_{section}_{col}",
            [sx, sy, sz + 0.015], [0.0, 0.0, 45.0],
            [cube((sx - size / 2.0, sy - size / 2.0, sz + 0.015),
                  (size, size, 0.035),
                  spec("bright"), spec("bright"), si)],
        ))

    # 4d. v1.9.0: RELIEVE 3D REAL. Un nervio grueso en cada cresta de la onda
    #     (0, 3, 6 por sección) y dos paneles laterales que cuelgan de los
    #     hombros con giro en Y/Z. La tela sigue siendo un mosaico continuo.
    for si, section in enumerate(SECTIONS):
        x0, x1, y_lo, y_hi, step = rows[si]
        for k, crest in enumerate(fold_crests()):
            x = x0 + (crest + 0.5) * step - 0.06
            z = panel_z(si, crest) + 0.13
            bones.append(bone(
                f"v15_ridge_{section}_{k}",
                f"v15_cloth_{section}_{crest}",
                [x + 0.06, (y_lo + y_hi) / 2.0, z],
                [0.0, 0.0, 0.0],
                [cube((x, y_lo + 0.08, z),
                      (0.12, y_hi - y_lo - 0.16, 0.16),
                      spec("crease_light"), spec("crease_light"), si)],
            ))
    # 4d2. Dos CORTINAS laterales CONTINUAS (una por lado), no seis barras
    #      segmentadas: cuelgan del panel central y caen de hombros a dobladillo.
    for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
        x = gx0 - 0.18 if sx < 0 else gx1 - 0.42
        z = panel_z(1, col) + 0.16
        bones.append(bone(
            f"v15_drape_{side}", f"v15_cloth_cape_mid_{col}",
            [x + 0.35, (gy0 + gy1) / 2.0, z],
            [1.5, sx * 8.0, sx * 3.0],
            [
                cube((x, gy0 + 0.10, z),
                     (0.70, gy1 - gy0 - 0.20, 0.20),
                     spec("crease_light"), spec("crease_light"), 1),
                cube((x if sx < 0 else x + 0.60, gy0 + 0.10, z + 0.02),
                     (0.10, gy1 - gy0 - 0.20, 0.22),
                     spec("rim"), spec("rim"), 1),
            ],
        ))

    # 4e. Pesas del dobladillo: 5 diamantes que cuelgan de las lengüetas.
    #     Heredan el vaivén de v15_hem_* y refuerzan la lectura de prenda
    #     colgada, no de rectángulo pegado a la espalda.
    bx0, _, _, _, bstep = rows[2]
    for j, col in enumerate((0, 2, 4, 6, 8)):
        center = bx0 + (col + 0.5) * bstep
        z = panel_z(2, col) + 0.14
        bones.append(bone(
            f"v15_weight_{j}", f"v15_hem_{col}",
            [center, gy0 - 1.15, z], [0.0, 0.0, 45.0],
            [cube((center - 0.11, gy0 - 1.28, z),
                  (0.22, 0.22, 0.10),
                  spec("bright"), spec("bright"), 2)],
        ))

    # 4f. Cuello trasero levantado y tirantes de suspensión desde los hombros.
    for i, (cx, rz) in enumerate(((-2.4, -12.0), (0.0, 0.0), (2.4, 12.0))):
        bones.append(bone(
            f"v15_back_collar_{i}", "cape_top",
            [cx, gy1 + 0.35, 2.95], [0.0, 0.0, rz],
            [cube((cx - 1.0, gy1 - 0.25, 2.75),
                  (2.0, 1.1, 0.45),
                  spec("yoke"), spec("yoke"), 0)],
        ))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -4.6 if sx < 0 else 4.35
        bones.append(bone(
            f"v15_suspend_{side}", "chestplate",
            [x + 0.12, 22.0, 1.6], [0.0, 0.0, sx * 18.0],
            [cube((x, 20.3, 1.45), (0.24, 3.4, 0.24),
                  spec("rim"), spec("rim"), 0)],
        ))

    # 4g. v1.9.0: FRENTE del jugador. Hombreras con relieve, arnés diagonal,
    #     broche, cadenas y cuello delantero. Todo cuelga de `chestplate`
    #     (no de los huesos boxy ocultos), así que se ve en F5 y con Curios.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        px = -5.35 if sx < 0 else 3.35
        bones.append(bone(
            f"v15_pauldron_{side}", "chestplate",
            [px + 1.0, 22.9, -1.0],
            [4.0, sx * 12.0, sx * 8.0],
            [
                cube((px, 22.2, -1.65), (2.0, 1.4, 0.42),
                     spec("yoke"), spec("yoke"), 0),
                cube((px + 0.15, 23.35, -1.72), (1.7, 0.22, 0.18),
                     spec("rim"), spec("rim"), 0),
                cube((px + 0.78, 22.65, -1.82), (0.44, 0.44, 0.14),
                     spec("bright"), spec("bright"), 0),
            ],
        ))
        sx2 = -2.0 if sx < 0 else 2.0
        bones.append(bone(
            f"v15_front_strap_{side}", "chestplate",
            [sx2, 20.8, -2.45], [0.0, 0.0, -sx * 36.0],
            [cube((sx2 - 0.14, 19.0, -2.52),
                  (0.28, 3.6, 0.16),
                  spec("rim"), spec("rim"), 0)],
        ))
        bones.append(bone(
            f"v15_front_chain_{side}", "chestplate",
            [sx * 0.9, 19.1, -2.55], [0.0, 0.0, sx * 5.0],
            [cube((sx * 0.9 - 0.09, 17.6, -2.62),
                  (0.18, 2.4, 0.14),
                  spec("rim"), spec("rim"), 0)],
        ))
    bones.append(bone(
        "v15_front_clasp", "chestplate",
        [0.0, 21.6, -2.68], [0.0, 0.0, 45.0],
        [cube((-0.36, 21.24, -2.75), (0.72, 0.72, 0.16),
              spec("bright"), spec("bright"), 0)],
    ))
    for i, (cx, rz) in enumerate(((-2.1, -14.0), (0.0, 0.0), (2.1, 14.0))):
        bones.append(bone(
            f"v15_front_collar_{i}", "chestplate",
            [cx, 23.5, -1.95], [0.0, 0.0, rz],
            [cube((cx - 0.9, 23.0, -2.15), (1.8, 1.0, 0.42),
                  spec("yoke"), spec("yoke"), 0)],
        ))

    # 4h. Más arnés delantero: placa central, bandas que unen hombros y
    #     dos faldillas cortas con punta emisiva. Así el frente no queda
    #     como cuatro barras sueltas y se lee como prenda colgada.
    bones.append(bone(
        "v15_front_placket", "chestplate",
        [0.0, 19.4, -2.62], [0.0, 0.0, 0.0],
        [
            cube((-0.34, 17.5, -2.68), (0.68, 3.9, 0.14),
                 spec("yoke"), spec("yoke"), 0),
            cube((-0.20, 20.7, -2.76), (0.40, 0.40, 0.12),
                 spec("bright"), spec("bright"), 0),
        ],
    ))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        bx = -3.4 if sx < 0 else 1.4
        bones.append(bone(
            f"v15_front_band_{side}", "chestplate",
            [bx + 1.0, 21.5, -2.50], [0.0, 0.0, sx * 18.0],
            [cube((bx, 21.28, -2.56), (2.0, 0.30, 0.14),
                  spec("rim"), spec("rim"), 0)],
        ))
        tx = -1.6 if sx < 0 else 1.2
        bones.append(bone(
            f"v15_front_tassel_{side}", "chestplate",
            [tx + 0.2, 16.6, -2.56], [0.0, 0.0, sx * 4.0],
            [
                cube((tx, 15.4, -2.62), (0.40, 1.6, 0.14),
                     spec("rim"), spec("rim"), 0),
                cube((tx + 0.10, 15.1, -2.70), (0.20, 0.20, 0.10),
                     spec("bright"), spec("bright"), 0),
            ],
        ))

    # 5. Cuello: dos piezas delgadas con la MISMA tela del canvas, no bloques
    #    de color plano. Sustituyen a las hombreras boxy sin cortar la lectura.
    tx0, tx1, _, _, _ = rows[0]
    for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
        x = tx0 - 0.20 if sx < 0 else tx1 - 1.00
        z = panel_z(0, col) + 0.03
        uv = cloth_uv(0, col)
        bones.append(bone(
            f"v15_shoulder_{side}", f"v15_cloth_cape_top_{col}",
            [x + 0.60, gy1 - 1.25, z], [4.0, -sx * 5.0, -sx * 7.0],
            [cube((x, gy1 - 2.35, z), (1.2, 2.0, 0.10), uv, uv, 0)],
        ))

    # 6. Broche: diamante pequeño y girado 45°, no un rectángulo magenta.
    #    El medallón grande ya está pintado en el canvas; esto sólo da relieve.
    bones.append(bone(
        "v15_clasp", "cape_top",
        [0.0, gy1 - 1.15, 2.96], [0.0, 0.0, 45.0],
        [cube((-0.33, gy1 - 1.48, 2.90), (0.66, 0.66, 0.10),
              spec("bright"), spec("bright"), 0)],
    ))

    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 4.5
    desc["visible_bounds_height"] = 4.8
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    # Garantía: los 72 huesos aprobados siguen byte-idénticos en JSON.
    assert geo["bones"][:72] == original_bones
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    assert sum(1 for n in names if n.startswith("v15_cloth_")) == COLUMNS * len(SECTIONS)
    assert sum(1 for n in names if n.startswith("v15_orbit_")) == 4
    assert sum(1 for n in names if n.startswith("v15_ridge_")) == 9
    assert sum(1 for n in names if n.startswith("v15_drape_")) == 2
    assert sum(1 for n in names if n.startswith("v15_weight_")) == 5
    assert sum(1 for n in names if n.startswith("v15_back_collar_")) == 3
    assert sum(1 for n in names if n.startswith("v15_suspend_")) == 2
    assert sum(1 for n in names if n.startswith("v15_pauldron_")) == 2
    assert sum(1 for n in names if n.startswith("v15_front_")) == 13
    parents = set(names)
    for b in bones:
        assert b.get("parent") is None or b["parent"] in parents, b["name"]
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")


if __name__ == "__main__":
    main()
