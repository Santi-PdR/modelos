#!/usr/bin/env python3
"""Genera RelicAnimations.java a partir de tools/relic_manifest.json.

El manifiesto es la fuente de verdad de los nombres/duraciones/tipos de las 20
animaciones. Este script evita copiar nombres a mano y permite que el CI
verifique que el Java generado sigue coincidiendo con el manifiesto:

    python3 tools/gen_relic_constants.py --check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "relic_manifest.json"
OUT = ROOT / "src/main/java/com/santipdr/holocore/common/RelicAnimations.java"

HEADER = """// ARCHIVO GENERADO - NO EDITAR A MANO.
// Fuente: tools/relic_manifest.json
// Regenerar: python3 tools/gen_relic_constants.py
// Verificar: python3 tools/gen_relic_constants.py --check
package com.santipdr.holocore.common;

import java.util.List;
import software.bernie.geckolib.core.animation.RawAnimation;

/**
 * Nombres, duraciones y {@link RawAnimation} de la reliquia, generados desde
 * {@code export/relic_manifest.json} (v19). Un nombre mal escrito aqui provoca
 * que GeckoLib no encuentre la animacion y el hueso se quede en reposo, asi que
 * la lista se valida en el CI contra el propio JSON de animaciones.
 */
public final class RelicAnimations {

    private RelicAnimations() {
    }
"""

FOOTER = """}
"""


def const_name(anim_id: str) -> str:
    # animation.relic.idle_charged -> IDLE_CHARGED
    tail = anim_id.split(".", 2)[2]
    return tail.upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    anims = manifest["animations"]
    trans_min, trans_max = manifest["recommended_transition_ticks"]

    lines = [HEADER]
    for anim in anims:
        name = const_name(anim["name"])
        lines.append(f'    /** {anim["name"]} - {anim["length_s"]} s - {anim["kind"]}'
                     f'{" (loop)" if anim["loop"] else ""}. */')
        lines.append(f'    public static final String {name} = "{anim["name"]}";')
        lines.append(f'    public static final double {name}_SECONDS = {anim["length_s"]};')
        builder = "thenLoop" if anim["loop"] else "thenPlay"
        lines.append(f'    public static final RawAnimation {name}_RAW = '
                     f'RawAnimation.begin().{builder}({name});')
        lines.append("")

    names = ", ".join(f'{const_name(a["name"])}_RAW' for a in anims)
    lines.append("    /** Las 20 animaciones, en el orden del manifiesto. */")
    lines.append(f"    public static final List<RawAnimation> ALL = List.of({names});")
    lines.append("")
    lines.append("    /** Nombres exactos (los que usan los .json), mismos indices que {@link #ALL}. */")
    lines.append("    public static final List<String> ALL_NAMES = List.of("
                 + ", ".join(const_name(a["name"]) for a in anims) + ");")
    lines.append("")
    lines.append(f"    /** Transicion recomendada por el manifiesto: [{trans_min}, {trans_max}] ticks. */")
    lines.append("    public static final int TRANSITION_TICKS = 6;")
    lines.append(FOOTER)

    generated = "\n".join(lines)

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != generated:
            print(f"ERROR: {OUT} no coincide con el manifiesto. "
                  "Ejecuta python3 tools/gen_relic_constants.py", file=sys.stderr)
            return 1
        print("RelicAnimations.java coincide con el manifiesto.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generated, encoding="utf-8")
    print(f"Escrito {OUT} ({len(anims)} animaciones).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
