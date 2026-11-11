#!/usr/bin/env python3
"""
Genera el geo y la animación de la capa plegada para el item 3D (v1.12.0).

v1.8.0: el item deja de ser un abanico plano de siete láminas y pasa a ser un
BULTO de capa doblada con grosor real. Hay un bloque de forro detrás, siete
franjas delanteras con relieve en Z (no rotación en abanico), un yugo con
cuello levantado, un broche de diamante, dos cadenas, dos tiras laterales,
tres rollos de tela en la base y cinco puntas de dobladillo. Las siete caras
delanteras siguen reconstruyendo UNA sola ilustración continua del atlas.

v1.9.0: añade dos HOMBRERAS con relieve propio y una animación de item
dedicada (`animation.item`) con balanceo, bob, giro del broche, escala y
apertura de pliegues. El controlador Java la usa cuando no hay entidad
(inventario, hotbar, mano), mientras que idle/moving/sprint/air siguen
disponibles para el resto de contextos.

Uso:  python tools/item_model_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from fold_spec import BOTTOM_Y, PANELS, TOP_Y, UV, WIDTH

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
    """Un hueso raíz NO debe llevar `"parent": null`.

    GeckoLib 4.8.x deserializa `parent` con
    `GsonHelper.getAsString(obj, "parent", null)`. Si la clave está presente
    con valor `null`, Gson ve un `JsonNull` e intenta `getAsString()`, que
    lanza `UnsupportedOperationException`; GeckoLib lo envuelve en
    `GeckoLibException: <geo>: Error loading model file` durante el reload de
    recursos. El formato Bedrock correcto es omitir la clave por completo:
    `GeometryTree.fromModel` ya trata `parent == null` como hueso raíz.
    """
    data = {"name": name}
    if parent is not None:
        data["parent"] = parent
    data.update({
        "pivot": [round(v, 4) for v in pivot],
        "rotation": [round(v, 4) for v in rotation],
        "cubes": cubes,
    })
    return data


def build_geo() -> dict:
    bones = [
        # Forro: da grosor real al bulto y se ve en los lados / al girarlo.
        bone("cape", None, [0, 8.0, 0], [0, 0, 0], [
            cube((-WIDTH / 2.0, BOTTOM_Y - 0.4, -1.1),
                 (WIDTH, TOP_Y - BOTTOM_Y + 0.8, 2.2), UV["lining"]),
        ]),
    ]

    # 1. Siete franjas delanteras: misma ilustración, relieve en Z y curva
    #    suave. Ya NO se abren en abanico: el item se lee como paño doblado.
    for p in PANELS:
        i = p["index"]
        bones.append(bone(
            f"fold_{i}", "cape",
            [p["x"] + p["width"] / 2.0, TOP_Y, p["depth"]],
            [p["rx"], p["ry"], p["rz"]],
            [cube((p["x"], BOTTOM_Y, p["depth"]),
                  (p["width"], p["height"], 0.5), p["strip"])],
        ))

    # 2. Nervios de ribete entre franjas, ligeramente por delante de la tela.
    for i in range(6):
        a, b = PANELS[i], PANELS[i + 1]
        x = b["x"] - 0.07
        z = (a["depth"] + b["depth"]) / 2.0 + 0.55
        h = min(a["height"], b["height"]) * 0.98
        bones.append(bone(
            f"ridge_{i}", "cape",
            [x + 0.07, BOTTOM_Y + h / 2.0, z],
            [0, (a["ry"] + b["ry"]) * 0.18, 0],
            [cube((x, BOTTOM_Y + 0.1, z), (0.14, h, 0.12), UV["piping"])],
        ))

    # 3. Yugo, cuello levantado y alas de hombro.
    bones.append(bone("yoke", "cape", [0, TOP_Y, 0], [0, 0, 0], [
        cube((-WIDTH / 2.0 - 0.4, TOP_Y, -1.25),
             (WIDTH + 0.8, 1.6, 3.0), UV["top_band"]),
    ]))
    bones.append(bone(
        "collar_center", "yoke", [0, TOP_Y + 1.2, 1.8], [-12, 0, 0],
        [cube((-1.6, TOP_Y + 1.0, 1.55), (3.2, 0.8, 0.6), UV["top_band"])],
    ))
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -3.6 if sx < 0 else 1.2
        bones.append(bone(
            f"collar_{side}", "yoke",
            [x + 1.2, TOP_Y + 1.2, 1.6], [-10, 0, -sx * 10],
            [cube((x, TOP_Y + 0.9, 1.45), (2.4, 0.8, 0.6), UV["top_band"])],
        ))
        wx = -WIDTH / 2.0 - 0.5 if sx < 0 else WIDTH / 2.0 - 1.5
        bones.append(bone(
            f"wing_{side}", "yoke",
            [wx + 1.0, TOP_Y + 0.6, 1.2], [6, sx * 10, sx * 16],
            [cube((wx, TOP_Y + 0.2, 1.15), (2.0, 1.2, 0.6), UV["top_band"])],
        ))

    # 3b. v1.9.0: hombreras del bulto. Dos capas (paño + ribete) con giro
    #     propio; dan la silueta de capa colgada incluso en el slot.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        px = -WIDTH / 2.0 - 1.0 if sx < 0 else WIDTH / 2.0 - 1.0
        bones.append(bone(
            f"pauldron_{side}", "yoke",
            [px + 1.0, TOP_Y + 0.8, 1.35], [6.0, sx * 10.0, sx * 14.0],
            [
                cube((px, TOP_Y + 0.1, 1.20), (2.0, 1.35, 0.55),
                     UV["pauldron"]),
                cube((px + 0.12, TOP_Y + 1.30, 1.12), (1.76, 0.22, 0.18),
                     UV["pauldron_rim"]),
            ],
        ))

    # 4. Broche: marco y gema en DIAMANTE (rotación del hueso, no del cubo),
    #    con dos tramos de cadena. Es el punto focal del item en la mano.
    bones.append(bone(
        "clasp_frame", "yoke", [0, TOP_Y + 0.7, 2.0], [0, 0, 45],
        [cube((-1.5, TOP_Y - 0.8, 1.9), (3.0, 3.0, 0.25), UV["piping"])],
    ))
    bones.append(bone(
        "clasp", "yoke", [0, TOP_Y + 0.7, 2.15], [0, 0, 45],
        [cube((-1.15, TOP_Y - 0.45, 2.05), (2.3, 2.3, 0.35), UV["gem"])],
    ))
    bones.append(bone(
        "chain_L", "yoke", [-2.7, TOP_Y + 1.0, 2.0], [0, 0, -8],
        [cube((-3.9, TOP_Y + 0.85, 1.95), (2.2, 0.30, 0.25), UV["piping"])],
    ))
    bones.append(bone(
        "chain_R", "yoke", [2.7, TOP_Y + 1.0, 2.0], [0, 0, 8],
        [cube((1.7, TOP_Y + 0.85, 1.95), (2.2, 0.30, 0.25), UV["piping"])],
    ))

    # 5. Tiras laterales: enmarcan el bulto sin tapar la ilustración.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        x = -WIDTH / 2.0 + 0.05 if sx < 0 else WIDTH / 2.0 - 0.27
        bones.append(bone(
            f"strap_{side}", "cape",
            [x + 0.11, 8.0, 1.75], [0, -sx * 3, 0],
            [cube((x, BOTTOM_Y + 0.2, 1.70),
                  (0.22, TOP_Y - BOTTOM_Y - 0.4, 0.18), UV["piping"])],
        ))

    # 6. Tres ROLLOS de tela en la base: dan la lectura de "capa doblada".
    for j in range(3):
        y = BOTTOM_Y - 1.15 + j * 0.62
        z = 1.55 + 0.12 * j
        bones.append(bone(
            f"roll_{j}", "cape", [0, y + 0.28, z], [0, 0, 0],
            [cube((-WIDTH / 2.0 + 0.2, y, z),
                  (WIDTH - 0.4, 0.55, 0.5), UV["roll"])],
        ))

    # 7. Cinco puntas de dobladillo con inclinación alterna.
    span = (WIDTH - 1.2) / 5.0
    for i in range(5):
        x = -WIDTH / 2.0 + 0.6 + i * span
        hw = span * 0.82
        bones.append(bone(
            f"hem_{i}", "cape",
            [x + hw / 2.0, BOTTOM_Y - 1.55, 1.9],
            [0, 0, -8 if i % 2 == 0 else 8],
            [cube((x, BOTTOM_Y - 1.95, 1.85),
                  (hw, 0.70, 0.30), UV["bottom_band"])],
        ))

    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.cape_folded",
                    "texture_width": 128,
                    "texture_height": 128,
                    "visible_bounds_width": 3.2,
                    "visible_bounds_height": 3.6,
                    "visible_bounds_offset": [0, 0.5, 0],
                },
                "bones": bones,
            }
        ],
    }


def channel(name: str, frames: dict[float, list[float]]) -> dict:
    return {
        name: {
            f"{t:.2f}": {"vector": [round(v, 3) for v in vec], "easing": "easeInOutSine"}
            for t, vec in frames.items()
        }
    }


def rot(frames: dict[float, list[float]]) -> dict:
    return channel("rotation", frames)


def pos(frames: dict[float, list[float]]) -> dict:
    return channel("position", frames)


def scale(frames: dict[float, list[float]]) -> dict:
    return channel("scale", frames)


def build_animations() -> dict:
    folds = {f"fold_{p['index']}": p for p in PANELS}

    def fold_frames(mid: float, spread: float):
        out = {}
        for name, p in folds.items():
            i = p["index"]
            out[name] = rot({
                0.0: [0, 0, 0],
                mid / 2.0: [spread * 0.5, 0, (i - 3) * spread * 0.14],
                mid: [0, 0, 0],
            })
        return out

    def hem_frames(mid: float, spread: float):
        return {
            f"hem_{i}": rot({
                0.0: [0, 0, 0],
                mid / 2.0: [0, 0, spread if i % 2 == 0 else -spread],
                mid: [0, 0, 0],
            })
            for i in range(5)
        }

    def roll_frames(mid: float, spread: float):
        return {
            f"roll_{j}": rot({
                0.0: [0, 0, 0],
                mid / 2.0: [spread * (0.4 + 0.3 * j), 0, 0],
                mid: [0, 0, 0],
            })
            for j in range(3)
        }

    def pauldron_frames(mid: float, spread: float):
        return {
            side: rot({
                0.0: [0, 0, 0],
                mid / 2.0: [spread * 0.4, 0, (1 if side.endswith("L") else -1) * spread],
                mid: [0, 0, 0],
            })
            for side in ("pauldron_L", "pauldron_R")
        }

    idle = {
        "cape": rot({0.0: [0, 0, 0], 2.0: [0.7, 0, 0.3], 4.0: [0, 0, 0]}),
        "yoke": rot({0.0: [0, 0, 0], 2.0: [-0.3, 0, -0.2], 4.0: [0, 0, 0]}),
        "collar_center": rot({0.0: [0, 0, 0], 2.0: [1.0, 0, 0], 4.0: [0, 0, 0]}),
        "clasp": rot({0.0: [0, 0, 0], 2.0: [0, 0, 2.0], 4.0: [0, 0, 0]}),
    }
    idle.update(fold_frames(4.0, 0.8))
    idle.update(hem_frames(4.0, 1.4))
    idle.update(roll_frames(4.0, 0.6))
    idle.update(pauldron_frames(4.0, 0.6))

    moving = {
        "cape": rot({0.0: [2.0, 0, 0], 0.6: [3.2, 0, 0.8], 1.2: [2.0, 0, 0]}),
        "yoke": rot({0.0: [-0.4, 0, 0], 0.6: [-0.8, 0, 0.3], 1.2: [-0.4, 0, 0]}),
    }
    moving.update(fold_frames(1.2, 1.4))
    moving.update(hem_frames(1.2, 2.2))
    moving.update(roll_frames(1.2, 1.0))
    moving.update(pauldron_frames(1.2, 1.2))

    sprint = {
        "cape": rot({0.0: [4.0, 0, 0], 0.4: [6.4, 0, 1.3], 0.8: [4.0, 0, 0]}),
        "yoke": rot({0.0: [-0.8, 0, 0], 0.4: [-1.3, 0, 0.5], 0.8: [-0.8, 0, 0]}),
    }
    sprint.update(fold_frames(0.8, 2.0))
    sprint.update(hem_frames(0.8, 3.0))
    sprint.update(roll_frames(0.8, 1.5))
    sprint.update(pauldron_frames(0.8, 1.8))

    air = {
        "cape": rot({0.0: [6.5, 0, 0], 0.75: [9.0, 0, -1.2], 1.5: [6.5, 0, 0]}),
        "yoke": rot({0.0: [-1.2, 0, 0], 0.75: [-1.8, 0, -0.5], 1.5: [-1.2, 0, 0]}),
    }
    air.update(fold_frames(1.5, 1.8))
    air.update(hem_frames(1.5, 2.6))
    air.update(roll_frames(1.5, 1.3))
    air.update(pauldron_frames(1.5, 1.5))

    # v1.9.0: animación PROPIA del item en GUI/hotbar/mano. Es más visible
    # que el idle de armadura: bob, balanceo, apertura de pliegues, giro del
    # broche, pulso de escala y vaivén de hombreras. Sigue siendo suave.
    cape_item = rot({
        0.0: [0.0, 0.0, 0.0],
        0.8: [2.4, 1.2, -1.6],
        1.6: [0.0, 0.0, 0.0],
        2.4: [-1.8, -1.0, 1.4],
        3.2: [0.0, 0.0, 0.0],
    })
    cape_item.update(pos({
        0.0: [0.0, 0.0, 0.0],
        0.8: [0.0, 0.10, 0.0],
        1.6: [0.0, 0.0, 0.0],
        2.4: [0.0, -0.05, 0.0],
        3.2: [0.0, 0.0, 0.0],
    }))
    clasp_item = rot({
        0.0: [0, 0, 0],
        1.6: [0, 0, 14.0],
        3.2: [0, 0, 0],
    })
    clasp_item.update(scale({
        0.0: [1.0, 1.0, 1.0],
        0.8: [1.08, 1.08, 1.08],
        1.6: [1.0, 1.0, 1.0],
        2.4: [1.05, 1.05, 1.05],
        3.2: [1.0, 1.0, 1.0],
    }))
    item = {
        "cape": cape_item,
        "yoke": rot({
            0.0: [0, 0, 0], 0.8: [-1.2, 0.6, 0.4], 1.6: [0, 0, 0],
            2.4: [0.9, -0.5, -0.3], 3.2: [0, 0, 0],
        }),
        "collar_center": rot({
            0.0: [0, 0, 0], 1.6: [3.0, 0, 0], 3.2: [0, 0, 0],
        }),
        "clasp": clasp_item,
        "clasp_frame": rot({
            0.0: [0, 0, 0], 1.6: [0, 0, -5.0], 3.2: [0, 0, 0],
        }),
    }
    item.update(fold_frames(3.2, 2.4))
    item.update(hem_frames(3.2, 4.0))
    item.update(roll_frames(3.2, 1.4))
    item.update(pauldron_frames(3.2, 2.2))
    for side in ("chain_L", "chain_R"):
        sign = -1.0 if side.endswith("L") else 1.0
        item[side] = rot({
            0.0: [0, 0, 0],
            1.6: [0, 0, sign * 5.0],
            3.2: [0, 0, 0],
        })

    return {
        "format_version": "1.8.0",
        "animations": {
            "animation.idle": {"loop": True, "animation_length": 4.0, "bones": idle},
            "animation.moving": {"loop": True, "animation_length": 1.2, "bones": moving},
            "animation.sprint": {"loop": True, "animation_length": 0.8, "bones": sprint},
            "animation.air": {"loop": True, "animation_length": 1.5, "bones": air},
            "animation.item": {"loop": True, "animation_length": 3.2, "bones": item},
        },
    }


def main() -> None:
    geo = build_geo()
    anim = build_animations()
    bones = geo["minecraft:geometry"][0]["bones"]
    names = {b["name"] for b in bones}

    # Regresión del crash v1.6.0: ningún valor null en el geo y todos los
    # padres declarados deben existir. Gson no tolera JsonNull en `parent`.
    def find_null(value, path="geo"):
        if value is None:
            yield path
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from find_null(item, f"{path}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                yield from find_null(item, f"{path}/{index}")

    nulls = list(find_null(geo))
    assert not nulls, f"JsonNull en el geo (GeckoLib no lo tolera): {nulls[:5]}"
    dangling = sorted({b["parent"] for b in bones if "parent" in b} - names)
    assert not dangling, f"huesos con padre inexistente: {dangling}"
    assert "parent" not in bones[0], "el hueso raíz no debe declarar parent"
    assert len(names) == 36, f"geo plegado inesperado: {len(names)} huesos"
    assert {"pauldron_L", "pauldron_R"} <= names
    assert "animation.item" in anim["animations"]

    for bone in bones:
        for c in bone.get("cubes", []):
            for face in c["uv"].values():
                u, v = face["uv"]
                w, h = face["uv_size"]
                assert w > 0 and h > 0, face
                assert 0 <= u and 0 <= v and u + w <= 128 and v + h <= 128, face

    for anim_name, spec in anim["animations"].items():
        missing = set(spec["bones"]) - names
        assert not missing, (anim_name, missing)
    OUT_GEO.parent.mkdir(parents=True, exist_ok=True)
    OUT_ANIM.parent.mkdir(parents=True, exist_ok=True)
    OUT_GEO.write_text(json.dumps(geo, indent=2, ensure_ascii=False) + "\n")
    OUT_ANIM.write_text(json.dumps(anim, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_GEO.relative_to(ROOT)}: {len(names)} bones")
    print(f"wrote {OUT_ANIM.relative_to(ROOT)}: 5 animations, all bones valid")


if __name__ == "__main__":
    main()
