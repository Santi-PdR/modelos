#!/usr/bin/env python3
"""Hornea la coreografía rotacional para GeckoLib.

La base v1.58.0 es la fuente de los canales espaciales BLOQUEADOS y de las
pistas de la armadura oculta. Se reemplazan sólo las rotaciones del rig
visible y de sus anclas. Nunca se lee la propia salida como entrada.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cape_motion as M

ROOT = Path(__file__).resolve().parents[1]
ANIM = (ROOT / "src/main/resources/assets/capatest/animations/item/armor"
        / "capa_deteriorer_evilsaiyan.animation.json")
GEO = (ROOT / "src/main/resources/assets/capatest/geo/item/armor"
       / "capa_deteriorer_evilsaiyan.geo.json")

BASE_ANIM = (ROOT / "docs/respaldos/v1.58.0/animations/item/armor"
             / "capa_deteriorer_evilsaiyan.animation.json")
STYLE_BY_CLIP = {
    "animation.idle": "idle",
    "animation.moving": "caminar",
    "animation.sprint": "correr",
    "animation.air": "volar",
    "animation.fall": "caer",
    "animation.sneak": "agachado",
    "animation.swim": "agua",
    "animation.deterioro": "deterioro",
}
# El runtime consume muestras densas de la curva continua; el proyecto
# editable añade tangentes a esas mismas muestras, no otra animación.
SAMPLES = 24
GENERATED_PREFIXES = ("v17_", "v18_", "v15_cloth_", "v15_hem_")


def animated(name: str) -> bool:
    return name in M.SECTIONS or name.startswith(GENERATED_PREFIXES)


def _time(t: float) -> str:
    return f"{t:.5f}".rstrip("0").rstrip(".")


def build(geo: dict | None = None) -> dict:
    data = json.loads(BASE_ANIM.read_text())
    if geo is None:
        geo = json.loads(GEO.read_text())["minecraft:geometry"][0]
    names = [b["name"] for b in geo["bones"] if animated(b["name"])]
    assert len(names) == 153, len(names)
    assert set(data["animations"]) == set(STYLE_BY_CLIP)
    for clip, style in STYLE_BY_CLIP.items():
        anim = data["animations"][clip]
        length = M.STYLES[style].length
        assert length == float(anim["animation_length"]), (clip, length)
        anim["loop"] = True
        for name in names:
            tracks = anim["bones"].setdefault(name, {})
            tracks["rotation"] = {
                _time(length * j / SAMPLES): {
                    "vector": [round(v, 4) for v in M.sample(name, style, j / SAMPLES)],
                    "easing": "linear",
                }
                for j in range(SAMPLES + 1)
            }
    return data


def ribbon_rms(data: dict) -> dict[str, float]:
    """RMS de rotación en grados sobre los keyframes de los 84 mechones."""
    result = {}
    for clip in STYLE_BY_CLIP:
        angles = [angle for name, tracks in data["animations"][clip]["bones"].items()
                  if name.startswith("v17_ribbon_")
                  for keyframe in tracks["rotation"].values() for angle in keyframe["vector"]]
        result[clip] = math.sqrt(math.fsum(a * a for a in angles) / len(angles))
    assert len(result) == len({round(rms, 4) for rms in result.values()}) == 8, result
    return result


def main() -> None:
    data = build()
    rms = ribbon_rms(data)
    # Compacto: 17 muestras x todos los huesos x 8 clips llenarían varios
    # MB con indent=2. El runtime sólo necesita JSON válido y sin `null`.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    assert "null" not in text, "JsonNull rompe GeckoLib"
    ANIM.write_text(text + "\n")
    for clip in STYLE_BY_CLIP:
        a = data["animations"][clip]
        n = sum(len(ch) for b in a["bones"].values() for ch in b.values())
        print(f"  {clip:20s} {len(a['bones']):3d} huesos, {n:5d} keyframes"
              f" | RMS rotación {rms[clip]:.4f}°")
    print(f"wrote {ANIM.relative_to(ROOT)}: {len(text):,} bytes")


if __name__ == "__main__":
    main()
