#!/usr/bin/env python3
"""Genera las pistas de los huesos `v17_*`/`v18_*` en el animation.json de GeckoLib.

REGRESIÓN CORREGIDA (rev. B): el `animation.json` aprobado tenía 4 clips con
53/38 huesos... pero TODOS eran huesos de la armadura vieja que Java oculta
con `setHidden(true)`. Ningún `v17_ribbon_*`, `v17_cowl_*` ni `v17_vein_*`
tenía un solo keyframe: en el juego la capa nueva sólo se movía por el
parche cosmético de `CapaArmorModel`, y si el fail-safe se activaba quedaba
completamente rígida.

Ahora los OCHO clips (uno por estado del portador) llevan la MISMA curva
`cape_motion.sample()` que el `.bbmodel`, el visor y (en espíritu)
`CapaArmorModel`. Se conservan las pistas originales byte por byte en
contenido: este script sólo AÑADE pistas nuevas y es idempotente (las
regenera desde cero cada vez).

Uso:  PYTHONPATH=tools python3 tools/cape_animation_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

import cape_motion as M

ROOT = Path(__file__).resolve().parents[1]
ANIM = (ROOT / "src/main/resources/assets/capatest/animations/item/armor"
        / "capa_deteriorer_evilsaiyan.animation.json")
GEO = (ROOT / "src/main/resources/assets/capatest/geo/item/armor"
       / "capa_deteriorer_evilsaiyan.geo.json")

# Un clip por estado del portador.
# v1.22.0: el controlador Java elige entre OCHO estados reales. Antes
# `animation.air` era un CLON de correr: saltar, caer y volar con elytra
# se movían exactamente igual que esprintar en llano.
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
# v1.21.0: 9 muestras con easeInOutSine PARABA la tela en cada keyframe
# (la velocidad se anulaba 9 veces por ciclo). 17 muestras + interpolación
# lineal siguen la curva analítica C1 sin pausas robóticas.
SAMPLES = 16                    # 17 keyframes por hueso y clip
GENERATED_PREFIXES = ("v17_", "v18_", "v15_cloth_", "v15_hem_")


def _vec(values) -> dict:
    return {"vector": [round(float(v), 4) for v in values],
            "easing": "linear"}


def _time(length: float, f: float) -> str:
    return f"{round(length * f, 4):g}"


def build() -> dict:
    data = json.loads(ANIM.read_text())
    geo = json.loads(GEO.read_text())["minecraft:geometry"][0]
    names = [b["name"] for b in geo["bones"]
             if b["name"].startswith(GENERATED_PREFIXES)
             and not b["name"].startswith(("v17_mote_", "v17_ash_",
                                          "v16_mote_", "v16_ash_"))]
    assert len(names) == 150, len(names)

    # v1.30.0: POSE DE REPOSO PARA LAS TRANSICIONES.
    #
    # Cada clip (salvo idle) lleva `posbias`/`bias` constantes aplicados
    # a TODOS sus keyframes, incluido f=0 y f=1. Así `animation.air`
    # (volar) empezaba y terminaba en (-0.57, 0.35, 0.90) mientras
    # `animation.idle` lo hacía en (-0.09, -0.28, -0.31): al entrar o
    # salir del clip al saltar, la capa daba un salto brusco de ~1.2u
    # en Z + rotación instantánea = el "teletransporte" que reportó el
    # usuario.
    #
    # Fix: TODOS los clips (salvo idle) arrancan y terminan en la pose
    # de reposo de idle. El movimiento propio del estado se desarrolla
    # en el interior del clip; las transiciones entran/salen sin
    # discontinuidad. Es la técnica estándar de animaciones loopables.
    idle_rest = {}
    for name in names:
        p = M.sample(name, "idle", 0.0)
        idle_rest[name] = p

    for clip, style in STYLE_BY_CLIP.items():
        if clip not in data["animations"]:
            # v1.22.0: los 4 estados nuevos no existían en el JSON
            # aprobado. Se crean con su duración canónica; el pipeline
            # rellena las pistas y es idempotente.
            data["animations"][clip] = {
                "animation_length": M.STYLES[style]["length"],
                "bones": {},
            }
        anim = data["animations"][clip]
        length = float(anim["animation_length"])
        # Idempotencia: descartar lo generado en una ejecución anterior.
        for old in [b for b in anim["bones"] if b.startswith(GENERATED_PREFIXES)]:
            del anim["bones"][old]
        for name in names:
            rotation, position, scale = {}, {}, {}
            for j in range(SAMPLES + 1):
                f = j / SAMPLES
                t = _time(length, f)
                pose = M.sample(name, style, f)
                rotation[t] = _vec(pose["rot"])
                # v1.21.0: las puntas se DESPLAZAN, no sólo giran en el
                # sitio. Antes GeckoLib perdía el canal `position` que sí
                # tenía el .bbmodel y la capa se veía distinta en el juego.
                if pose["has_pos"]:
                    position[t] = _vec(pose["pos"])
                if pose["has_scale"]:
                    scale[t] = _vec(pose["scale"])
            if clip != "animation.idle":
                # Forzar los keyframes de borde (f=0, f=1) a la pose de
                # reposo de idle para que ninguna transición pegue un
                # salto. El movimiento propio vive en el interior.
                t0, t1 = _time(length, 0.0), _time(length, 1.0)
                rp = idle_rest[name]
                rotation[t0] = _vec(rp["rot"])
                rotation[t1] = _vec(rp["rot"])
                if position:
                    position[t0] = _vec(rp["pos"])
                    position[t1] = _vec(rp["pos"])
                if scale:
                    scale[t0] = _vec(rp["scale"])
                    scale[t1] = _vec(rp["scale"])
            tracks = {"rotation": rotation}
            if position:
                tracks["position"] = position
            if scale:
                tracks["scale"] = scale
            anim["bones"][name] = tracks
    return data


def main() -> None:
    data = build()
    # Compacto: 17 muestras x todos los huesos x 8 clips llenarían varios
    # MB con indent=2. El runtime sólo necesita JSON válido y sin `null`.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    assert "null" not in text, "JsonNull rompe GeckoLib"
    ANIM.write_text(text + "\n")
    for clip in STYLE_BY_CLIP:
        a = data["animations"][clip]
        n = sum(len(ch) for b in a["bones"].values() for ch in b.values())
        print(f"  {clip:20s} {len(a['bones']):3d} huesos, {n:5d} keyframes")
    print(f"wrote {ANIM.relative_to(ROOT)}: {len(text):,} bytes")


if __name__ == "__main__":
    main()
