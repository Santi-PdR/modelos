#!/usr/bin/env python3
"""
Genera el geo de la capa plegada para el item 3D (cape_folded.geo.json).

A diferencia de la v1.2.0 (una unica placa de 2 cubos), aqui la capa se
construye con un dorso + cinco pliegues a distinta profundidad/altura +
yoke + broche. Cada pliegue muestrea una franja vertical distinta del atlas
de 128x128, de modo que las cinco caras delanteras forman UNA sola imagen de
capa continua en vez de repetir un cuadrado morado.

Uso:  python tools/item_model_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/cape_folded.geo.json"

# Cinco pliegues: x, altura, profundidad (z) y rotacion inicial.
PANELS = [
    {"x": -7.0, "h": 10.4, "z": 0.30, "rx": 1.2, "rz": -2.2},
    {"x": -4.2, "h": 12.0, "z": 0.72, "rx": 0.4, "rz": -0.8},
    {"x": -1.4, "h": 11.2, "z": 0.95, "rx": 0.0, "rz": 0.0},
    {"x": 1.4, "h": 12.4, "z": 0.72, "rx": 0.4, "rz": 0.8},
    {"x": 4.2, "h": 10.0, "z": 0.30, "rx": 1.2, "rz": 2.2},
]

EDGE_UV = {"uv": [0, 0], "uv_size": [10, 8]}       # franja oscura del yoke
ALL_ART = {"uv": [0, 0], "uv_size": [125, 128]}    # capa completa (dorso)


def faces(front: dict) -> dict:
    """north/south = arte de la capa; el resto = franja oscura."""
    return {
        "north": dict(front),
        "south": dict(front),
        "east": dict(EDGE_UV),
        "west": dict(EDGE_UV),
        "up": dict(EDGE_UV),
        "down": dict(EDGE_UV),
    }


def cube(origin, size, front):
    return {"origin": list(origin), "size": list(size), "uv": faces(front)}


def build() -> dict:
    bones = [
        {
            "name": "cape",
            "pivot": [0, 12, 0],
            "cubes": [cube(
                (-7.0, 1.2, -1.1),
                (14.0, 12.8, 0.9),
                ALL_ART,
            )],
        }
    ]

    for i, p in enumerate(PANELS):
        strip = {"uv": [25 * i, 0], "uv_size": [25, 128]}
        bones.append({
            "name": f"fold_{i}",
            "parent": "cape",
            "pivot": [p["x"] + 1.35, 12, 0],
            "rotation": [p["rx"], 0, p["rz"]],
            "cubes": [cube(
                (p["x"], 14.0 - p["h"], p["z"]),
                (2.7, p["h"], 0.55),
                strip,
            )],
        })

    bones.append({
        "name": "yoke",
        "parent": "cape",
        "pivot": [0, 14, 0],
        "cubes": [cube(
            (-7.6, 13.3, -1.3),
            (15.2, 2.2, 3.0),
            {"uv": [0, 0], "uv_size": [125, 10]},
        )],
    })

    bones.append({
        "name": "clasp",
        "parent": "yoke",
        "pivot": [0, 14, 0],
        "cubes": [cube(
            (-1.5, 13.1, 1.65),
            (3.0, 3.0, 0.7),
            {"uv": [54, 30], "uv_size": [20, 22]},
        )],
    })

    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.cape_folded",
                    "texture_width": 128,
                    "texture_height": 128,
                    "visible_bounds_width": 3,
                    "visible_bounds_height": 3.5,
                    "visible_bounds_offset": [0, 0.6, 0],
                },
                "bones": bones,
            }
        ],
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['minecraft:geometry'][0]['bones'])} bones")


if __name__ == "__main__":
    main()
