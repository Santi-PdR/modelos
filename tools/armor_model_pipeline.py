#!/usr/bin/env python3
"""Reconstruye la capa EQUIPADA con VOLUMEN 3D REAL (v1.12.0).

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
    cuello de 3 piezas, placa central, bandas y faldillas).
  * v1.12.0: la tela pasa de láminas de 0.10 a BLOQUES de 0.85, el relieve
    compartido de 0.085 a 0.28, y TODAS las decoraciones se anclan a la
    cara SUR (+Z) en lugar de quedar dentro del panel. Se añaden 2 hombreras
    TRASERAS sólidas (antes sólo las delanteras, invisibles desde la espalda),
    6 placas escalonadas, 6 eslabones 3D, 6 remaches, un medallón con cuerpo
    y un gorget. Total: **193 huesos / 281 cubos**.

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
Total v1.9.0: **171 huesos / 234 cubos**; v1.12.0: **193 / 281**.

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
        # v1.12.0: con bloques de 0.85 los cantos son muy visibles. Usar el
        # tono CLARO de la sarga (no el forro oscuro) evita que las 9 columnas
        # se lean como barrotes desde el perfil; el sombreado por normal ya
        # oscurece estas caras lo suficiente para dar volumen.
        "east": spec("crease_light", section),
        "west": spec("crease_light", section),
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

# v1.12.0 VOLUMEN REAL. Hasta v1.11.0 la tela era una lamina de 0.10 de
# grosor y el relieve de los pliegues solo 0.085: en el juego se veia como un
# poster plano. Ahora cada panel es un BLOQUE de 0.85 y la onda compartida
# FOLDS=3 separa crestas/valles 0.42 en Z (< 0.85, sin huecos). Todas las
# decoraciones se anclan a face_z(): la cara SUR (+Z) que mira el espectador
# cuando la capa esta en la espalda. Antes iban a panel_z+0.03, es decir,
# DENTRO del panel, y por eso no se veian.
PANEL_DEPTH = 0.85
RELIEF = 0.28


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

    `fold_at_column` vale +0.5 en las crestas y -1 en los valles (9 columnas,
    FOLDS=3): la diferencia maxima entre columnas vecinas es 1.5 * RELIEF =
    0.42, MENOR que PANEL_DEPTH (0.85). Asi los bloques se solapan y nunca
    queda una grieta, pero el escalon de profundidad SI se ve de lado y de 3/4.
    Era 0.085 en v1.11.0 (invisible).
    """
    norm = (column - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
    return (2.55 + 0.10 * section + 0.16 * (1.0 - norm * norm)
            + RELIEF * fold_at_column(column))


def face_z(section: int, column: int) -> float:
    """Z de la cara SUR del panel (la que se ve desde la espalda)."""
    return panel_z(section, column) + PANEL_DEPTH


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
            pivot = [x + width / 2.0, (y_lo + y_hi) / 2.0, z + PANEL_DEPTH / 2.0]
            # Sin giro Y por columna: cualquier giro abre huecos entre
            # franjas UV. La inclinación X es común a toda la fila, así el
            # mosaico sigue cerrado y la capa cae hacia atrás.
            rotation = [0.6 + 1.0 * si, 0.0, 0.0]
            uv = cloth_uv(si, col)
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section, pivot, rotation,
                [cube((x, y_lo, z), (width, y_hi - y_lo, PANEL_DEPTH), uv, uv, si)],
            ))

        # 2. Una crease 3D por VALLE de la onda compartida FOLDS=3 (columnas
        #    1, 4, 7). Coincide exactamente con la línea oscura del canvas:
        #    sombreado y relieve cuentan el mismo pliegue, sin código de barras.
        for k, valley in enumerate(fold_valleys()):
            x = x0 + (valley + 0.5) * step - 0.022
            z = face_z(si, valley) + 0.02
            tone = spec("crease_dark" if k % 2 == 0 else "crease_light", si)
            bones.append(bone(
                f"v15_crease_{section}_{k}",
                f"v15_cloth_{section}_{valley}",
                [x + 0.022, (y_lo + y_hi) / 2.0, z],
                [0.0, 0.0, 0.0],
                [cube((x - 0.05, y_lo + 0.05, z), (0.13, y_hi - y_lo - 0.10, 0.20),
                      tone, None, si)],
            ))

        # 3. Ribetes laterales: enmarcan la tela sin neón estridente.
        for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
            x = x0 - 0.02 if sx < 0 else x1 - 0.14
            z = face_z(si, col) + 0.03
            bones.append(bone(
                f"v15_pipe_{section}_{side}",
                f"v15_cloth_{section}_{col}",
                [x + 0.07, (y_lo + y_hi) / 2.0, z],
                [0.0, -sx * 2.0, 0.0],
                [cube((x - 0.06, y_lo + 0.10, z), (0.24, y_hi - y_lo - 0.20, 0.34),
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
        z = face_z(2, col) + 0.02
        tilt = -1.2 if col % 2 == 0 else 1.2
        uv = hem_uv(col)
        bones.append(bone(
            f"v15_hem_{col}", f"v15_cloth_cape_bottom_{col}",
            [center, gy0 - 0.06, z],
            [2.0 + 2.0 * (1.0 - norm * norm), 0.0, tilt],
            [cube((center - bstep * 0.48, gy0 - 0.06 - length, z),
                  (bstep * 0.96, length, 0.58), uv, uv, 2)],
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
        z = face_z(si, column) + 0.12
        return si, column, x, y, z

    star_points = ((18, 18), (78, 18), (26, 35), (70, 35), (48, 30))
    for i, (su, sv) in enumerate(star_points):
        si, col, sx, sy, sz = canvas_point(su, sv)
        section = SECTIONS[si]
        size = 0.34
        bones.append(bone(
            f"v15_star_{i}",
            f"v15_cloth_{section}_{col}",
            [sx, sy, sz], [0.0, 0.0, 45.0],
            [cube((sx - size / 2.0, sy - size / 2.0, sz),
                  (size, size, 0.32),
                  spec("bright"), spec("bright"), si)],
        ))

    # 4c. v1.9.0: 4 fragmentos orbitales alrededor del núcleo de Blight Star.
    #     Son diamantes aún más pequeños que las estrellas, en los puntos
    #     cardinales del medallón. CapaArmorModel los hace girar despacio.
    orbit_points = ((48.0, 12.4), (54.1, 18.5), (48.0, 24.6), (41.9, 18.5))
    for i, (su, sv) in enumerate(orbit_points):
        si, col, sx, sy, sz = canvas_point(su, sv)
        section = SECTIONS[si]
        size = 0.22
        bones.append(bone(
            f"v15_orbit_{i}",
            f"v15_cloth_{section}_{col}",
            [sx, sy, sz + 0.015], [0.0, 0.0, 45.0],
            [cube((sx - size / 2.0, sy - size / 2.0, sz + 0.015),
                  (size, size, 0.26),
                  spec("bright"), spec("bright"), si)],
        ))

    # 4d. v1.9.0: RELIEVE 3D REAL. Un nervio grueso en cada cresta de la onda
    #     (0, 3, 6 por sección) y dos paneles laterales que cuelgan de los
    #     hombros con giro en Y/Z. La tela sigue siendo un mosaico continuo.
    for si, section in enumerate(SECTIONS):
        x0, x1, y_lo, y_hi, step = rows[si]
        for k, crest in enumerate(fold_crests()):
            x = x0 + (crest + 0.5) * step - 0.06
            z = face_z(si, crest) + 0.03
            bones.append(bone(
                f"v15_ridge_{section}_{k}",
                f"v15_cloth_{section}_{crest}",
                [x + 0.06, (y_lo + y_hi) / 2.0, z],
                [0.0, 0.0, 0.0],
                [cube((x - 0.08, y_lo + 0.08, z),
                      (0.20, y_hi - y_lo - 0.16, 0.28),
                      spec("crease_light"), spec("crease_light"), si)],
            ))
    # 4d2. Dos CORTINAS laterales CONTINUAS (una por lado), no seis barras
    #      segmentadas: cuelgan del panel central y caen de hombros a dobladillo.
    for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
        x = gx0 - 0.18 if sx < 0 else gx1 - 0.42
        z = face_z(1, col) + 0.05
        bones.append(bone(
            f"v15_drape_{side}", f"v15_cloth_cape_mid_{col}",
            [x + 0.35, (gy0 + gy1) / 2.0, z],
            [1.5, sx * 8.0, sx * 3.0],
            [
                cube((x, gy0 + 0.10, z),
                     (0.80, gy1 - gy0 - 0.20, 0.58),
                     spec("crease_light"), spec("crease_light"), 1),
                cube((x if sx < 0 else x + 0.66, gy0 + 0.10, z + 0.03),
                     (0.14, gy1 - gy0 - 0.20, 0.62),
                     spec("rim"), spec("rim"), 1),
            ],
        ))

    # 4e. Pesas del dobladillo: 5 diamantes que cuelgan de las lengüetas.
    #     Heredan el vaivén de v15_hem_* y refuerzan la lectura de prenda
    #     colgada, no de rectángulo pegado a la espalda.
    bx0, _, _, _, bstep = rows[2]
    for j, col in enumerate((0, 2, 4, 6, 8)):
        center = bx0 + (col + 0.5) * bstep
        z = face_z(2, col) + 0.18
        bones.append(bone(
            f"v15_weight_{j}", f"v15_hem_{col}",
            [center, gy0 - 1.15, z], [0.0, 0.0, 45.0],
            [cube((center - 0.20, gy0 - 1.36, z),
                  (0.40, 0.40, 0.36),
                  spec("bright"), spec("bright"), 2)],
        ))

    # 4f. Cuello trasero levantado y tirantes de suspensión desde los hombros.
    for i, (cx, rz) in enumerate(((-2.25, -8.0), (0.0, 0.0), (2.25, 8.0))):
        bones.append(bone(
            f"v15_back_collar_{i}", "cape_top",
            [cx, gy1 - 0.05, 3.45], [0.0, 0.0, rz],
            [cube((cx - 1.30, gy1 - 0.85, 2.65),
                  (2.60, 1.65, 1.55),
                  spec("yoke"), spec("yoke"), 0)],
        ))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -4.6 if sx < 0 else 4.35
        bones.append(bone(
            f"v15_suspend_{side}", "chestplate",
            [x + 0.12, 22.0, 1.6], [0.0, 0.0, sx * 18.0],
            [cube((x - 0.06, 20.3, 1.35), (0.38, 3.4, 0.55),
                  spec("rim"), spec("rim"), 0),
             cube((x - 0.11, 20.6, 1.28), (0.48, 0.30, 0.68),
                  spec("bright"), spec("bright"), 0)],
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
                cube((px - 0.55, 22.05, -2.35), (3.30, 1.75, 2.15),
                     spec("yoke"), spec("yoke"), 0),
                cube((px - 0.65, 23.65, -2.45), (3.50, 0.34, 2.35),
                     spec("rim"), spec("rim"), 0),
                cube((px + 0.35, 22.55, -2.58), (0.80, 0.80, 0.32),
                     spec("bright"), spec("bright"), 0),
                cube((px - 0.35, 21.75, -2.30), (2.90, 0.30, 2.00),
                     spec("crease_light"), spec("crease_light"), 0),
            ],
        ))
        sx2 = -2.0 if sx < 0 else 2.0
        bones.append(bone(
            f"v15_front_strap_{side}", "chestplate",
            [sx2, 20.8, -2.45], [0.0, 0.0, -sx * 36.0],
            [cube((sx2 - 0.24, 19.0, -2.62),
                  (0.48, 3.6, 0.55),
                  spec("rim"), spec("rim"), 0)],
        ))
        bones.append(bone(
            f"v15_front_chain_{side}", "chestplate",
            [sx * 0.9, 19.1, -2.55], [0.0, 0.0, sx * 5.0],
            [cube((sx * 0.9 - 0.16, 17.6, -2.72),
                  (0.32, 2.4, 0.46),
                  spec("rim"), spec("rim"), 0)],
        ))
    bones.append(bone(
        "v15_front_clasp", "chestplate",
        [0.0, 21.6, -2.68], [0.0, 0.0, 45.0],
        [cube((-0.55, 21.10, -2.90), (1.10, 1.10, 0.62),
              spec("bright"), spec("bright"), 0),
         cube((-0.70, 21.00, -2.80), (1.40, 1.30, 0.18),
              spec("yoke"), spec("yoke"), 0)],
    ))
    for i, (cx, rz) in enumerate(((-2.1, -14.0), (0.0, 0.0), (2.1, 14.0))):
        bones.append(bone(
            f"v15_front_collar_{i}", "chestplate",
            [cx, 23.5, -1.95], [0.0, 0.0, rz],
            [cube((cx - 1.0, 22.9, -2.30), (2.0, 1.5, 1.20),
                  spec("yoke"), spec("yoke"), 0),
             cube((cx - 1.05, 24.25, -2.40), (2.10, 0.28, 1.35),
                  spec("rim"), spec("rim"), 0)],
        ))

    # 4h. Más arnés delantero: placa central, bandas que unen hombros y
    #     dos faldillas cortas con punta emisiva. Así el frente no queda
    #     como cuatro barras sueltas y se lee como prenda colgada.
    bones.append(bone(
        "v15_front_placket", "chestplate",
        [0.0, 19.4, -2.62], [0.0, 0.0, 0.0],
        [
            cube((-0.50, 17.5, -2.80), (1.00, 3.9, 0.55),
                 spec("yoke"), spec("yoke"), 0),
            cube((-0.28, 20.7, -2.92), (0.56, 0.56, 0.28),
                 spec("bright"), spec("bright"), 0),
        ],
    ))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        bx = -3.4 if sx < 0 else 1.4
        bones.append(bone(
            f"v15_front_band_{side}", "chestplate",
            [bx + 1.0, 21.5, -2.50], [0.0, 0.0, sx * 18.0],
            [cube((bx, 21.20, -2.62), (2.0, 0.42, 0.50),
                  spec("rim"), spec("rim"), 0)],
        ))
        tx = -1.6 if sx < 0 else 1.2
        bones.append(bone(
            f"v15_front_tassel_{side}", "chestplate",
            [tx + 0.2, 16.6, -2.56], [0.0, 0.0, sx * 4.0],
            [
                cube((tx - 0.08, 15.4, -2.72), (0.56, 1.6, 0.46),
                     spec("rim"), spec("rim"), 0),
                cube((tx + 0.06, 15.0, -2.82), (0.32, 0.32, 0.26),
                     spec("bright"), spec("bright"), 0),
            ],
        ))

    # 5. Cuello: dos piezas delgadas con la MISMA tela del canvas, no bloques
    #    de color plano. Sustituyen a las hombreras boxy sin cortar la lectura.
    tx0, tx1, _, _, _ = rows[0]
    for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
        x = tx0 - 0.20 if sx < 0 else tx1 - 1.00
        z = face_z(0, col) + 0.05
        uv = cloth_uv(0, col)
        bones.append(bone(
            f"v15_shoulder_{side}", f"v15_cloth_cape_top_{col}",
            [x + 0.60, gy1 - 1.25, z], [2.0, -sx * 3.0, -sx * 3.0],
            [cube((x + 0.18, gy1 - 1.85, z), (0.90, 1.40, 0.55), uv, uv, 0),
             cube((x - 0.10, gy1 - 0.45, z - 0.05), (1.40, 0.26, 0.82),
                  spec("rim"), spec("rim"), 0)],
        ))

    # 6. Broche: diamante pequeño y girado 45°, no un rectángulo magenta.
    #    El medallón grande ya está pintado en el canvas; esto sólo da relieve.
    bones.append(bone(
        "v15_clasp", "cape_top",
        [0.0, gy1 - 1.15, face_z(0, 4) + 0.35], [0.0, 0.0, 45.0],
        [cube((-0.55, gy1 - 1.70, face_z(0, 4) + 0.10), (1.10, 1.10, 0.60),
              spec("bright"), spec("bright"), 0),
         cube((-0.72, gy1 - 1.88, face_z(0, 4) + 0.02), (1.44, 1.44, 0.20),
              spec("yoke"), spec("yoke"), 0)],
    ))

    # ------------------------------------------------------------------
    # 7. v1.12.0 — VOLUMEN 3D EN LA ESPALDA (lo que el usuario ve en F5).
    #    Hasta aqui las "hombreras" colgaban de chestplate en Z NEGATIVO
    #    (frente del jugador): desde atras solo se veia la lamina de tela.
    #    Ahora hay hombreras TRASERAS solidas que envuelven el hombro,
    #    placas escalonadas, cadenas 3D y un medallon con cuerpo. Todas
    #    cuelgan de `chestplate` (no de los 61 detalles ocultos) y usan
    #    solo UV de zonas 100% opacas del atlas.
    # ------------------------------------------------------------------
    for side, sx in (("L", -1.0), ("R", 1.0)):
        # Placa principal de la hombrera trasera: bloque con 3 ejes reales.
        hx = -7.05 if sx < 0 else 3.45
        bones.append(bone(
            f"v15_rear_pad_{side}", "chestplate",
            [hx + 1.80, 23.0, 3.55], [4.0, sx * 9.0, -sx * 9.0],
            [
                cube((hx, 22.05, 2.55), (3.60, 1.95, 2.05),
                     spec("yoke"), spec("yoke"), 0),             # cuerpo
                cube((hx - 0.18, 23.85, 2.42), (3.96, 0.38, 2.32),
                     spec("rim"), spec("rim"), 0),               # cresta oro
                cube((hx + 0.30, 22.35, 4.52), (0.95, 0.95, 0.42),
                     spec("bright"), spec("bright"), 0),          # gema
            ],
        ))
        # Greca de 3 placas que baja por el borde lateral de la capa: da
        # relieve y "armadura" sin amontonar cajas en los hombros.
        for k in range(3):
            py = 18.60 - k * 4.30
            px = -6.35 if sx < 0 else 5.55
            bones.append(bone(
                f"v15_slab_{side}_{k}", "chestplate",
                [px + 0.40, py + 0.30, 3.55], [0.0, 0.0, -sx * 3.0],
                [cube((px, py, 3.05), (0.80, 0.62, 1.05),
                      spec("yoke"), spec("yoke"), 0),
                 cube((px - 0.06, py + 0.55, 2.98), (0.92, 0.14, 1.18),
                      spec("rim"), spec("rim"), 0)],
            ))
        # Cadena 3D: eslabones alternos desde la hombrera al broche central.
        for k in range(3):
            cx = sx * (5.55 - k * 1.55)
            cy = 21.55 - k * 0.30
            bones.append(bone(
                f"v15_chain3d_{side}_{k}", "chestplate",
                [cx, cy, 4.05], [0.0, 0.0, (30.0 if k % 2 else -30.0)],
                [cube((cx - 0.16, cy - 0.16, 3.80), (0.32, 0.32, 0.50),
                      spec("rim"), spec("rim"), 0)],
            ))
        # Remaches en el borde exterior de la capa.
        for k in range(3):
            ry = 18.4 - k * 4.2
            rx = -6.55 if sx < 0 else 6.25
            bones.append(bone(
                f"v15_stud_{side}_{k}", "chestplate",
                [rx + 0.15, ry + 0.15, 3.65], [0.0, 0.0, 45.0],
                [cube((rx, ry, 3.30), (0.30, 0.30, 0.55),
                      spec("bright"), spec("bright"), 0)],
            ))

    # Medallon central 3D: marco + gema con relieve real sobre el canvas.
    mz = face_z(1, 4) + 0.12
    bones.append(bone(
        "v15_medallion", "chestplate",
        [0.0, 17.0, mz + 0.55], [0.0, 0.0, 45.0],
        [cube((-1.05, 15.95, mz), (2.10, 2.10, 0.32),
              spec("yoke"), spec("yoke"), 0),
         cube((-0.78, 16.22, mz + 0.30), (1.56, 1.56, 0.55),
              spec("bright"), spec("bright"), 0),
         cube((-0.30, 16.70, mz + 0.82), (0.60, 0.60, 0.28),
              spec("bright"), spec("bright"), 0)],
    ))
    # Gorget / collar alto frontal que cierra el conjunto por arriba.
    bones.append(bone(
        "v15_gorget", "chestplate",
        [0.0, 23.6, 3.30], [0.0, 0.0, 0.0],
        [cube((-2.90, 23.15, 2.60), (5.80, 1.10, 1.55),
              spec("yoke"), spec("yoke"), 0),
         cube((-3.05, 24.10, 2.50), (6.10, 0.30, 1.75),
              spec("rim"), spec("rim"), 0),
         cube((-0.45, 23.40, 4.10), (0.90, 0.90, 0.40),
              spec("bright"), spec("bright"), 0)],
    ))

    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 5.2
    desc["visible_bounds_height"] = 5.2
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
    assert sum(1 for n in names if n.startswith("v15_rear_pad_")) == 2
    assert sum(1 for n in names if n.startswith("v15_slab_")) == 6
    assert sum(1 for n in names if n.startswith("v15_chain3d_")) == 6
    assert sum(1 for n in names if n.startswith("v15_stud_")) == 6
    assert "v15_medallion" in names and "v15_gorget" in names
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
