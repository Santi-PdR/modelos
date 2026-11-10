#!/usr/bin/env python3
"""
Añade relieve a la capa EQUIPADA sin tocar la geometría original.

Lee tools/originals/capa_deteriorer_evilsaiyan.geo.json (72 huesos / 126 cubos,
copia prístina del modelo aprobado) y le añade:

  * 15 pliegues en relieve: un nervio estrecho por cada panel de cape_top,
    cape_mid y cape_bottom, ligeramente adelantado y girado en Y. Su UV es un
    filete vertical del MISMO panel, así que no inventa texeles transparentes.
  * 2 alas de hombro que rompen la línea recta del yugo.
  * 2 costuras laterales luminosas (región emisiva ya existente).
  * 7 puntas de dobladillo con el mismo filete rosa del sigilo.

Las animaciones idle/moving/sprint/air NO se modifican: los huesos nuevos son
hijos de cape_top/mid/bottom y heredan su movimiento. El atlas y el glowmask
tampoco se tocan; todas las UV nuevas caen en zonas ya opacas.

Uso:  python tools/armor_model_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

EDGE = {"uv": [105.0, 0.0], "uv_size": [3.0, 21.217]}
BRIGHT = {"uv": [69.0, 109.0], "uv_size": [6.0, 18.0]}
YOKE = {"uv": [57.0, 76.0], "uv_size": [14.0, 17.0]}


def faces(north: dict, south: dict) -> dict:
    return {
        "north": dict(north),
        "south": dict(south),
        "east": dict(EDGE),
        "west": dict(EDGE),
        "up": dict(EDGE),
        "down": dict(EDGE),
    }


def cube(origin, size, north, south):
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": faces(north, south),
    }


def center_slice(spec: dict, width: float = 1.4) -> dict:
    u, v = spec["uv"]
    w, h = spec["uv_size"]
    return {"uv": [round(u + w / 2.0 - width / 2.0, 4), v], "uv_size": [width, h]}


def build() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)
    by_name = {b["name"]: b for b in original_bones}

    # 1. Nervios de tela: uno por panel, en las tres secciones de la capa.
    for section in ("cape_top", "cape_mid", "cape_bottom"):
        base = by_name[section]
        for i, src in enumerate(base["cubes"]):
            o, s = src["origin"], src["size"]
            ridge_w = 0.30
            x = o[0] + s[0] / 2.0 - ridge_w / 2.0
            z = o[2] + s[2] + 0.055
            south = center_slice(src["uv"]["south"])
            north = center_slice(src["uv"]["north"])
            bones.append({
                "name": f"v14_drape_{section}_{i}",
                "parent": section,
                "pivot": [round(x + ridge_w / 2.0, 4), round(o[1] + s[1] / 2.0, 4), round(z, 4)],
                "rotation": [0.0, round((i - 2) * 2.6, 3), round((i - 2) * 0.7, 3)],
                "cubes": [cube((x, o[1], z), (ridge_w, s[1], 0.16), north, south)],
            })

    # 2. Alas de hombro: prolongan el yugo hacia fuera con un giro suave.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -5.45 if sx < 0 else 3.45
        bones.append({
            "name": f"v14_wing_{side}",
            "parent": "cape_top",
            "pivot": [x + 1.1, 21.0, 2.7],
            "rotation": [8.0, -sx * 12.0, -sx * 18.0],
            "cubes": [cube((x, 19.6, 2.62), (2.2, 3.1, 0.42), YOKE, YOKE)],
        })

    # 3. Costuras laterales: filete emisivo, siguiendo la curva de la capa.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -6.55 if sx < 0 else 6.35
        bones.append({
            "name": f"v14_seam_{side}",
            "parent": "cape_mid",
            "pivot": [x + 0.09, 12.5, 2.55],
            "rotation": [0.0, -sx * 6.0, 0.0],
            "cubes": [cube((x, 5.35, 2.55), (0.18, 12.0, 0.14), BRIGHT, BRIGHT)],
        })

    # 4. Puntas del dobladillo: zigzag discreto bajo cape_bottom.
    for i in range(7):
        x = -5.85 + i * 1.95
        tilt = -14.0 if i % 2 == 0 else 14.0
        bones.append({
            "name": f"v14_hem_{i}",
            "parent": "cape_bottom",
            "pivot": [round(x + 0.38, 4), 4.55, 2.2],
            "rotation": [0.0, 0.0, tilt],
            "cubes": [cube((x, 4.0, 2.12), (0.76, 1.1, 0.18), BRIGHT, BRIGHT)],
        })

    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 4
    desc["visible_bounds_height"] = 4.5
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    # Garantía: los 72 huesos aprobados siguen byte-idénticos en JSON.
    assert geo["bones"][:72] == original_bones
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, "
          f"{sum(len(b.get('cubes', [])) for b in geo['bones'])} cubes")


if __name__ == "__main__":
    main()
