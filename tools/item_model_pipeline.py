#!/usr/bin/env python3
"""
Genera el geo y la animación de la capa plegada para el item 3D (v1.5.1).

El modelo deja de ser una serie de cinco rectángulos y pasa a ser una prenda
con 7 pliegues en abanico, nervios de ribete, yugo con alas, cuello levantado,
broche con marco y cadena, costuras laterales y dobladillo de puntas. Cada
pliegue muestrea una franja vertical distinta del atlas de 128×128, así que
las siete caras delanteras reconstruyen UNA sola ilustración continua.

También escribe animations/item/cape_folded.animation.json: el balanceo de los
pliegues pasa a estar en la animación (no en Java), y las cuatro animaciones
idle/moving/sprint/air siguen disponibles para el controlador del item.

Uso:  python tools/item_model_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from fold_spec import PANELS, TOP_Y, UV

ROOT = Path(__file__).resolve().parents[1]
OUT_GEO = ROOT / "src/main/resources/assets/capatest/geo/item/cape_folded.geo.json"
OUT_ANIM = ROOT / "src/main/resources/assets/capatest/animations/item/cape_folded.animation.json"


def faces(front: dict, back: dict | None = None) -> dict:
    side = dict(UV["edge"])
    return {
        "north": dict(front),
        "south": dict(back or front),
        "east": dict(side),
        "west": dict(side),
        "up": dict(side),
        "down": dict(side),
    }


def cube(origin, size, front, back=None):
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": faces(front, back),
    }


def bone(name, parent, pivot, rotation, cubes):
    return {
        "name": name,
        "parent": parent,
        "pivot": [round(v, 4) for v in pivot],
        "rotation": [round(v, 4) for v in rotation],
        "cubes": cubes,
    }


def build_geo() -> dict:
    bones = [
        bone("cape", None, [0, 12, 0], [0, 0, 0], [
            cube((-7.2, 1.2, -1.25), (14.4, 12.8, 0.9), UV["lining"]),
        ]),
    ]

    # 1. Siete pliegues en abanico, con altura/profundidad/rotación graduales.
    for p in PANELS:
        i = p["index"]
        bones.append(bone(
            f"fold_{i}", "cape",
            [p["x"] + p["width"] / 2.0, TOP_Y, p["depth"]],
            [p["rx"], p["ry"], p["rz"]],
            [cube(
                (p["x"], TOP_Y - p["height"], p["depth"]),
                (p["width"], p["height"], 0.55),
                p["strip"],
            )],
        ))

    # 2. Nervios de ribete entre pliegues.
    for i in range(6):
        a, b = PANELS[i], PANELS[i + 1]
        x = b["x"] - 0.09
        z = (a["depth"] + b["depth"]) / 2.0 + 0.30
        h = min(a["height"], b["height"]) * 0.94
        bones.append(bone(
            f"ridge_{i}", "cape",
            [x + 0.09, TOP_Y - h / 2.0, z],
            [0, (a["ry"] + b["ry"]) * 0.25, 0],
            [cube((x, TOP_Y - h, z), (0.18, h, 0.14), UV["piping"])],
        ))

    # 3. Yugo, alas y cuello levantado.
    bones.append(bone("yoke", "cape", [0, 14.2, 0], [0, 0, 0], [
        cube((-7.8, 13.5, -1.35), (15.6, 1.8, 3.1), UV["top_band"]),
    ]))
    bones.append(bone("collar_center", "yoke", [0, 14.6, 1.7], [-14, 0, 0], [
        cube((-2.2, 14.7, 1.55), (4.4, 0.9, 0.7), UV["top_band"]),
    ]))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -5.0 if sx < 0 else 2.4
        bones.append(bone(
            f"collar_{side}", "yoke",
            [x + 1.3, 14.6, 1.6],
            [-10, 0, -sx * 12],
            [cube((x, 14.4, 1.45), (2.6, 0.8, 0.6), UV["top_band"])],
        ))
        wx = -7.9 if sx < 0 else 5.9
        bones.append(bone(
            f"wing_{side}", "yoke",
            [wx + 1.0, 13.8, 1.2],
            [6, sx * 10, sx * 18],
            [cube((wx, 13.4, 1.15), (2.0, 1.2, 0.6), UV["top_band"])],
        ))

    # 4. Broche: marco, gema y dos tramos de cadena.
    bones.append(bone("clasp_frame", "yoke", [0, 14.0, 1.8], [0, 0, 0], [
        cube((-1.75, 12.75, 1.65), (3.5, 3.5, 0.30), UV["piping"]),
    ]))
    bones.append(bone("clasp", "yoke", [0, 14.0, 2.0], [0, 0, 0], [
        cube((-1.4, 13.1, 1.95), (2.8, 2.8, 0.65), UV["gem"]),
    ]))
    bones.append(bone("chain_L", "yoke", [-3.0, 14.2, 1.9], [0, 0, -8], [
        cube((-4.1, 14.05, 1.85), (2.2, 0.35, 0.25), UV["piping"]),
    ]))
    bones.append(bone("chain_R", "yoke", [3.0, 14.2, 1.9], [0, 0, 8], [
        cube((1.9, 14.05, 1.85), (2.2, 0.35, 0.25), UV["piping"]),
    ]))

    # 5. Costuras laterales y puntas del dobladillo.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -7.18 if sx < 0 else 6.96
        bones.append(bone(
            f"strap_{side}", "cape",
            [x + 0.11, 8.0, 1.25],
            [0, -sx * 4, 0],
            [cube((x, 1.4, 1.25), (0.22, 12.2, 0.18), UV["piping"])],
        ))
    for p in PANELS:
        i = p["index"]
        hw = 1.6
        x = p["x"] + p["width"] / 2.0 - hw / 2.0
        tilt = -12.0 if i % 2 == 0 else 12.0
        bones.append(bone(
            f"hem_{i}", "cape",
            [x + hw / 2.0, 1.0, 0.7],
            [0, 0, tilt],
            [cube((x, 0.55, 0.62), (hw, 1.0, 0.35), UV["bottom_band"])],
        ))

    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.cape_folded",
                    "texture_width": 128,
                    "texture_height": 128,
                    "visible_bounds_width": 3.5,
                    "visible_bounds_height": 4.0,
                    "visible_bounds_offset": [0, 0.5, 0],
                },
                "bones": bones,
            }
        ],
    }


def rot(frames: dict[float, list[float]]) -> dict:
    return {
        "rotation": {
            f"{t:.2f}": {"vector": [round(v, 3) for v in vec], "easing": "easeInOutSine"}
            for t, vec in frames.items()
        }
    }


def build_animations() -> dict:
    folds = {f"fold_{p['index']}": p for p in PANELS}

    def fold_frames(mid: float, spread: float, phase: float = 0.0):
        out = {}
        for name, p in folds.items():
            i = p["index"]
            out[name] = rot({
                0.0: [0, 0, 0],
                mid / 2.0: [spread * 0.5, 0, (i - 3) * spread * 0.16],
                mid: [0, 0, 0],
            })
        return out

    idle = {
        "cape": rot({0.0: [0, 0, 0], 2.0: [0.8, 0, 0.4], 4.0: [0, 0, 0]}),
        "yoke": rot({0.0: [0, 0, 0], 2.0: [-0.4, 0, -0.2], 4.0: [0, 0, 0]}),
        "collar_center": rot({0.0: [0, 0, 0], 2.0: [1.2, 0, 0], 4.0: [0, 0, 0]}),
        "clasp": rot({0.0: [0, 0, 0], 2.0: [0, 0, 2.0], 4.0: [0, 0, 0]}),
    }
    idle.update(fold_frames(4.0, 0.9))
    for i in range(7):
        idle[f"hem_{i}"] = rot({
            0.0: [0, 0, 0],
            2.0: [0, 0, 1.6 if i % 2 == 0 else -1.6],
            4.0: [0, 0, 0],
        })

    moving = {
        "cape": rot({0.0: [2.5, 0, 0], 0.6: [4.0, 0, 1.0], 1.2: [2.5, 0, 0]}),
        "yoke": rot({0.0: [-0.5, 0, 0], 0.6: [-1.0, 0, 0.4], 1.2: [-0.5, 0, 0]}),
    }
    moving.update(fold_frames(1.2, 1.6))
    sprint = {
        "cape": rot({0.0: [5.0, 0, 0], 0.4: [8.0, 0, 1.6], 0.8: [5.0, 0, 0]}),
        "yoke": rot({0.0: [-1.0, 0, 0], 0.4: [-1.6, 0, 0.6], 0.8: [-1.0, 0, 0]}),
    }
    sprint.update(fold_frames(0.8, 2.4))
    air = {
        "cape": rot({0.0: [8.0, 0, 0], 0.75: [11.0, 0, -1.5], 1.5: [8.0, 0, 0]}),
        "yoke": rot({0.0: [-1.5, 0, 0], 0.75: [-2.2, 0, -0.6], 1.5: [-1.5, 0, 0]}),
    }
    air.update(fold_frames(1.5, 2.0))

    return {
        "format_version": "1.8.0",
        "animations": {
            "animation.idle": {"loop": True, "animation_length": 4.0, "bones": idle},
            "animation.moving": {"loop": True, "animation_length": 1.2, "bones": moving},
            "animation.sprint": {"loop": True, "animation_length": 0.8, "bones": sprint},
            "animation.air": {"loop": True, "animation_length": 1.5, "bones": air},
        },
    }


def main() -> None:
    geo = build_geo()
    anim = build_animations()
    names = {b["name"] for b in geo["minecraft:geometry"][0]["bones"]}
    for anim_name, spec in anim["animations"].items():
        missing = set(spec["bones"]) - names
        assert not missing, (anim_name, missing)
    OUT_GEO.parent.mkdir(parents=True, exist_ok=True)
    OUT_ANIM.parent.mkdir(parents=True, exist_ok=True)
    OUT_GEO.write_text(json.dumps(geo, indent=2, ensure_ascii=False) + "\n")
    OUT_ANIM.write_text(json.dumps(anim, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_GEO.relative_to(ROOT)}: {len(names)} bones")
    print(f"wrote {OUT_ANIM.relative_to(ROOT)}: 4 animations, all bones valid")


if __name__ == "__main__":
    main()
