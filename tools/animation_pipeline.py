#!/usr/bin/env python3
"""
Adds two derived animation states to the cape without touching the two
hand-authored ones the user already liked.

    animation.idle    -> untouched (53 bones, 3.6 s)
    animation.moving  -> untouched (38 bones, 1.0 s)
    animation.sprint  -> derived from moving: faster cycle, wider flare
    animation.air     -> derived from moving: slower "billowing" cycle with the
                         cape bones swept further back for jumps / falls

The original file is json.dumps(..., indent=2) formatted, so rewriting it with
the same settings keeps idle/moving byte-identical and produces a small diff.
The script is idempotent: sprint/air are always re-derived from `moving`, so
re-running it never compounds the transformation.

Usage:  python tools/animation_pipeline.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANIM = (
    ROOT
    / "src/main/resources/assets/capatest/animations/item/armor"
    / "capa_deteriorer_evilsaiyan.animation.json"
)

# Bones that carry the cloth: their X rotation is exaggerated in the air state.
CLOTH_BONE_PREFIXES = ("cape_", "colgajo_", "espina_", "ala_", "tela_")


def derive(src: dict, *, time_scale: float, rot: float, pos: float, cloth_x: float = 1.0) -> dict:
    anim = copy.deepcopy(src)
    anim["animation_length"] = round(float(src.get("animation_length", 1.0)) * time_scale, 4)

    for bone, channels in anim["bones"].items():
        is_cloth = bone.startswith(CLOTH_BONE_PREFIXES)
        for channel, frames in channels.items():
            rebuilt = {}
            for time_key, keyframe in frames.items():
                new_time = f"{float(time_key) * time_scale:.4g}"
                vector = [float(v) for v in keyframe["vector"]]

                if channel == "scale":
                    # Never multiply scale channels: [1,1,1] must stay [1,1,1].
                    vector = [1.0 + (v - 1.0) * pos for v in vector]
                elif channel == "position":
                    vector = [v * pos for v in vector]
                else:  # rotation (degrees)
                    vector = [v * rot for v in vector]
                    if is_cloth and cloth_x != 1.0:
                        vector[0] *= cloth_x

                rebuilt[new_time] = {
                    "vector": [round(v, 4) for v in vector],
                    "easing": keyframe["easing"],
                }
            channels[channel] = rebuilt

    return anim


def main() -> None:
    original_text = ANIM.read_text()
    data = json.loads(original_text)
    animations = data["animations"]

    assert "animation.idle" in animations and "animation.moving" in animations
    base = animations["animation.moving"]

    sprint = derive(base, time_scale=0.72, rot=1.18, pos=1.12)
    air = derive(base, time_scale=1.35, rot=0.90, pos=0.85, cloth_x=1.55)

    # Stable, readable order.
    rebuilt = {}
    for name, anim in animations.items():
        rebuilt[name] = anim
        if name == "animation.moving":
            rebuilt["animation.sprint"] = sprint
            rebuilt["animation.air"] = air
    data["animations"] = rebuilt

    output = json.dumps(data, indent=2, ensure_ascii=False)

    # Guarantee the two hand-made animations were not altered.
    fresh = json.loads(output)["animations"]
    for name in ("animation.idle", "animation.moving"):
        assert fresh[name] == animations[name], f"{name} changed!"

    ANIM.write_text(output)
    print("animations:", list(fresh))
    for name in ("animation.idle", "animation.moving", "animation.sprint", "animation.air"):
        a = fresh[name]
        print(f"  {name:20s} length={a['animation_length']:<6} bones={len(a['bones'])} loop={a['loop']}")


if __name__ == "__main__":
    main()
