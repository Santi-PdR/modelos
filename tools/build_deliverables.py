#!/usr/bin/env python3
"""Reconstruye TODOS los entregables de docs/ y preview/ desde el repo.

Este script es el ÚNICO punto de entrada para regenerar los entregables:

  1. geo + atlas + icono      (tools/armor_model_pipeline.py, texture_pipeline.py)
  2. clips + .bbmodel          (tools/cape_animation_pipeline.py, bbmodel_export.py)
  3. recursos del visor        (preview/assets/)
  4. previews software          (tools/preview_cloth.py)
  5. GIF + hoja de estados      (tools/present_v1600.py)
  6. comparativas              (render software + medidas)
  7. visor autocontenido       (tools/build_standalone_preview.py)

Antes estos pasos vivían en scripts sueltos de /tmp, fuera del repo: los
entregables de docs/ NO eran reproducibles. Ahora todo está versionado.

Uso:
    PYTHONPATH=tools:tools/_deps python3 tools/build_deliverables.py [--skip-gen]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from cape_icon import first_frame

import cape_fit
import cape_aura
import cape_nocturne
import cape_reference
import cape_stride
import cape_sway
import cape_wings

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/main/resources/assets/capatest"
PREVIEW = ROOT / "preview"
A = PREVIEW / "assets"
D = ROOT / "docs"

ENV = dict(os.environ, PYTHONPATH="tools:tools/_deps")


def run(*cmd: str) -> str:
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True)
    if p.returncode:
        print(p.stdout[-3000:])
        print(p.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    lines = p.stdout.strip().splitlines()
    print("  ", lines[-1] if lines else cmd[0])
    return p.stdout


def mod_version() -> str:
    for line in (ROOT / "gradle.properties").read_text().splitlines():
        if line.startswith("mod_version="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("falta mod_version en gradle.properties")


def step_geo_y_textura(ver: str) -> None:
    print(f"1) geo + atlas + icono (v{ver})")
    run(sys.executable, "tools/armor_model_pipeline.py")
    run(sys.executable, "tools/texture_pipeline.py")


def step_animaciones(ver: str) -> None:
    print(f"2) clips + .bbmodel (v{ver})")
    run(sys.executable, "tools/cape_animation_pipeline.py")
    run(sys.executable, "tools/bbmodel_export.py")
    doc = D / f"CAPA_v{ver}.bbmodel"
    assert (A / "capa_deteriorer_evilsaiyan.bbmodel").read_bytes() == doc.read_bytes(), \
        "el .bbmodel de preview/ no coincide con el de docs/"


def step_recursos_visor() -> None:
    print("3) recursos del visor")
    A.mkdir(parents=True, exist_ok=True)
    (A / "particles").mkdir(exist_ok=True)
    copy = {
        "geo/item/armor/capa_deteriorer_evilsaiyan.geo.json": "armor.geo.json",
        "animations/item/armor/capa_deteriorer_evilsaiyan.animation.json": "armor.animation.json",
        "textures/item/armor/capa_deteriorer_evilsaiyan.png": "armor.png",
        "textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png": "armor_glowmask.png",
        "textures/item/armor/capa_deteriorer_evilsaiyan_halo.png": "armor_halo.png",
        "textures/item/cape_folded.png": "folded.png",
        "textures/item/cape_folded_glowmask.png": "folded_glowmask.png",
    }
    copy.update({f"textures/particle/capa_spark_{i}.png": f"capa_spark_{i}.png" for i in range(3)})
    for src, dst in copy.items():
        shutil.copy(RES / src, A / dst)
    first_frame().save(A / "icon.png", optimize=True)
    (A / 'aura.json').write_text(json.dumps(cape_aura.profile(), separators=(',', ':')) + '\n')
    (A / 'nocturne.json').write_text(json.dumps(cape_nocturne.profile(), separators=(',', ':')) + '\n')
    (A / 'fit.json').write_text(json.dumps(cape_fit.viewer_profile(placed=True), separators=(',', ':')) + '\n')
    (A / 'stride.json').write_text(json.dumps(cape_stride.profile(), separators=(',', ':')) + '\n')
    (A / 'sway.json').write_text(json.dumps(cape_sway.profile(), separators=(',', ':')) + '\n')
    (A / 'wings.json').write_text(json.dumps(cape_wings.profile(), separators=(',', ':')) + '\n')
    (A / 'reference-frame.json').write_text(json.dumps(cape_reference.viewer_camera()) + '\n')
    with Image.open(cape_reference.SOURCE) as source:
        source.convert('RGB').crop(cape_reference.CROP).save(A / 'reference-crop.png', optimize=True)
    atlas = Image.open(A / "armor.png").convert("RGBA")
    atlas.crop((0, 0, 96, 48)).resize((576, 288), Image.NEAREST).save(A / "canvas.png")
    atlas.resize((384, 384), Image.NEAREST).save(A / "atlas.png")
    Image.open(A / "armor_glowmask.png").convert("RGBA").resize(
        (384, 384), Image.NEAREST).save(A / "glowmask.png")


def step_previews(out: Path) -> None:
    print("4) previews software")
    run(sys.executable, "tools/preview_cloth.py", "--out", str(out), "--uv-test")
    mapa = {
        "full.png": "capa_v1170_preview.png",
        "icon.png": "capa_v1170_icon.png",
        "side_relief.png": "capa_v1170_side_relief.png",
        "front_rig.png": "capa_v1170_front_rig.png",
        "folded_glowmask.png": "capa_v1170_item_glowmask.png",
        "particles.png": "capa_v1170_particles.png",
        "uv_test_front.png": "capa_v1170_uv_test.png",
    }
    for src, dst in mapa.items():
        shutil.copy(out / src, D / dst)


def step_gifs_y_estados(ver: str) -> None:
    print("5) comparativas")
    art_ver = cape_reference.registered_version(ver)
    if ver.startswith('1.67.'):
        # Keep the historical registered exterior plates. New in-game
        # motion comparisons are published separately from those renders.
        run(sys.executable, "tools/present_v1670.py", "--out", str(D))
    else:
        run(sys.executable, "tools/present_v1600.py", "--out", str(D), "--gif")
    shutil.copy(D / f"capa_v{art_ver.replace('.', '')}_antes_despues.png", A / "antes_despues.png")
    shutil.copy(D / f"capa_v{art_ver.replace('.', '')}_registro.png", A / "registro.png")
    if art_ver in ('1.64.0', '1.65.0', '1.66.0'):
        shutil.copy(D / 'capa_v1640_ajuste.png', A / 'ajuste.png')
    if art_ver in ('1.65.0', '1.66.0'):
        shutil.copy(D / 'capa_v1650_cuello.png', A / 'cuello.png')
    shutil.copy(D / "capa_v1170_estados.png", A / "estados.png")
    shutil.copy(D / "capa_v1170_animaciones.gif", A / "animacion.gif")


def step_comparativas(ver: str) -> None:
    print("6) comparativas")
    # La comparación registrada y su máscara ya salen de present_v1600.
    shutil.copy(D / "capa_v1170_comparativa.png", A / "comparativa_final.png")
    from present_v1640 import icon_panel
    icon_panel(D / 'capa_v1170_icon_compare.png')
    shutil.copy(D / 'capa_v1170_icon_compare.png', D / 'capa_v1170_icon_remaster.png')


def step_visor() -> None:
    print("7) visor autocontenido")
    run(sys.executable, "tools/build_standalone_preview.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-gen", action="store_true",
                    help="no regenera geo/atlas/icono ( sólo entregables de docs/)")
    ap.add_argument("--out", type=Path, default=A / "renders",
                    help="carpeta temporal de los renders software")
    args = ap.parse_args()

    ver = mod_version()
    if not args.skip_gen:
        step_geo_y_textura(ver)
    step_animaciones(ver)
    step_recursos_visor()
    args.out.mkdir(parents=True, exist_ok=True)
    step_previews(args.out)
    step_gifs_y_estados(ver)
    step_comparativas(ver)
    step_visor()
    print(f"ENTREGABLES v{ver} OK")


if __name__ == "__main__":
    main()
