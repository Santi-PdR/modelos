#!/usr/bin/env python3
"""Reconstruye la capa EQUIPADA como una superficie de tela continua (v1.5.0).

Lee tools/originals/capa_deteriorer_evilsaiyan.geo.json (72 huesos / 126 cubos,
copia prístina aprobada) y NO modifica ni uno solo de esos huesos. Añade una
segunda piel hecha de 13 columnas por cada una de las 3 secciones:

  * 39 paneles delgados, ligeramente curvados en Z y girados en Y, que
    reemplazan visualmente a los 15 cubos planos originales;
  * 36 nervios/creases en los límites de columna, con sombra y rim light;
  * 6 ribetes laterales emisivos, 13 puntas de dobladillo y 2 alas de
    hombro; las tres secciones se solapan sin costuras horizontales.

En runtime CapaArmorModel oculta SÓLO los cubos de cape_top/mid/bottom (no sus
hijos), así que los 72 huesos y las animaciones hand-made siguen mandando:
los paneles nuevos son hijos de esas secciones y heredan idle/moving/sprint/air.
Además el modelo Java les aplica una curva de amplitud con retardo de fase,
inspirada en WaveyCapes / Finery / GlowberryClient.

Todas las UV nuevas caen en rectángulos 100% opacos del atlas de 128×128;
alfa base y cobertura emisiva no cambian. Uso:

    python3 tools/armor_model_pipeline.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from cloth_spec import (
    COLUMNS,
    SECTIONS,
    UV,
    assert_opaque,
    cloth_uv,
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


def section_bounds(base: dict, index: int) -> tuple[float, float, float, float]:
    cubes = base["cubes"]
    x0 = min(c["origin"][0] for c in cubes) - 0.32 - 0.08 * index
    x1 = max(c["origin"][0] + c["size"][0] for c in cubes) + 0.32 + 0.08 * index
    y0 = min(c["origin"][1] for c in cubes) - 0.10
    y1 = max(c["origin"][1] + c["size"][1] for c in cubes) + 0.12
    return x0, x1, y0, y1


def panel_z(index: int, column: int) -> float:
    norm = (column - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
    return 2.48 + 0.24 * (1.0 - norm * norm) + 0.035 * math.sin(column * 1.31 + index * 0.7)


def build() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)
    by_name = {b["name"]: b for b in original_bones}

    section_info = []
    for si, section in enumerate(SECTIONS):
        x0, x1, y0, y1 = section_bounds(by_name[section], si)
        step = (x1 - x0) / COLUMNS
        section_info.append((x0, x1, y0, y1, step))

        # 1. Paneles de tela: 13 franjas solapadas, curvadas y con rotación
        #    propia para que la luz lea pliegues en vez de una tabla.
        for col in range(COLUMNS):
            norm = (col - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
            x = x0 + col * step - 0.14
            width = step + 0.28
            z = panel_z(si, col)
            pivot = [x + width / 2.0, (y0 + y1) / 2.0, z]
            rotation = [
                0.25 + 0.25 * si + 0.15 * math.cos(col * 1.7 + si),
                norm * 4.8 + (0.5 if col % 2 else -0.5),
                norm * 0.8 + 0.35 * math.sin(col * 1.3 + si * 0.9),
            ]
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section, pivot, rotation,
                [cube((x, y0, z), (width, y1 - y0, 0.12),
                      cloth_uv(si, col), cloth_uv(si, col), si)],
            ))

        # 2. Creases: filete oscuro + fino rim light en cada límite UV.
        for col in range(COLUMNS - 1):
            x = x0 + (col + 1) * step - 0.035
            z = (panel_z(si, col) + panel_z(si, col + 1)) / 2.0 + 0.11
            dark = spec("crease_dark", si)
            light = spec("crease_light", si)
            bones.append(bone(
                f"v15_crease_{section}_{col}",
                f"v15_cloth_{section}_{col}",
                [x + 0.035, (y0 + y1) / 2.0, z],
                [0.0, (col - 6) * 0.5, 0.0],
                [cube((x, y0 + 0.04, z), (0.07, y1 - y0 - 0.08, 0.05),
                      dark if col % 2 else light, None, si)],
            ))

        # 3. Ribetes laterales: heredan el movimiento del panel del borde.
        for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
            x = x0 - 0.03 if sx < 0 else x1 - 0.15
            z = panel_z(si, col) + 0.12
            bones.append(bone(
                f"v15_pipe_{section}_{side}",
                f"v15_cloth_{section}_{col}",
                [x + 0.09, (y0 + y1) / 2.0, z],
                [0.0, -sx * 5.0, -sx * 1.5],
                [cube((x, y0 + 0.12, z), (0.18, y1 - y0 - 0.24, 0.12),
                      spec("bright"), spec("bright"), si)],
            ))

    # 4. Sin costuras horizontales añadidas: las tres secciones se solapan y
    #    el canvas continuo se encarga de unirlas visualmente.

    # 5. Dobladillo: 13 lengüetas inclinadas, cada una hija de su panel.
    bx0, bx1, by0, _, bstep = section_info[2]
    for col in range(COLUMNS):
        center = bx0 + (col + 0.5) * bstep
        x = center - 0.58
        z = panel_z(2, col) + 0.14
        tilt = -11.0 if col % 2 == 0 else 11.0
        bones.append(bone(
            f"v15_hem_{col}", f"v15_cloth_cape_bottom_{col}",
            [center, by0 - 0.45, z], [0.0, 0.0, tilt],
            [
                cube((x, by0 - 0.98, z), (1.16, 1.05, 0.16),
                     spec("bottom_band"), spec("bottom_band"), 2),
                cube((center - 0.24, by0 - 1.25, z + 0.05), (0.48, 0.42, 0.10),
                     spec("bright"), spec("bright"), 2),
            ],
        ))

    # 6. Alas de hombro: rompen la línea recta del yugo original.
    tx0, tx1, _, _, _ = section_info[0]
    for side, sx, col in (("L", -1.0, 0), ("R", 1.0, COLUMNS - 1)):
        x = tx0 - 0.75 if sx < 0 else tx1 - 1.25
        z = panel_z(0, col) + 0.16
        bones.append(bone(
            f"v15_shoulder_{side}", f"v15_cloth_cape_top_{col}",
            [x + 1.0, 21.5, z], [7.0, -sx * 11.0, -sx * 15.0],
            [cube((x, 19.7, z), (2.0, 3.25, 0.26),
                  spec("yoke"), spec("yoke"), 0)],
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
