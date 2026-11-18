#!/usr/bin/env python3
"""Reconstruye TODOS los entregables de docs/ y preview/ desde el repo.

Este script es el ÚNICO punto de entrada para regenerar los entregables:

  1. geo + atlas + icono      (tools/armor_model_pipeline.py, texture_pipeline.py)
  2. clips + .bbmodel          (tools/cape_animation_pipeline.py, bbmodel_export.py)
  3. recursos del visor        (preview/assets/)
  4. previews software          (tools/preview_cloth.py)
  5. GIF + hoja de estados      (tools/present_v1590.py)
  6. comparativas              (render software + medidas)
  7. visor autocontenido       (tools/build_standalone_preview.py)

Antes estos pasos vivían en scripts sueltos de /tmp, fuera del repo: los
entregables de docs/ NO eran reproducibles. Ahora todo está versionado.

Uso:
    PYTHONPATH=tools:tools/_deps python3 tools/build_deliverables.py [--skip-gen]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

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
        "textures/particle/capa_spark_1.png": "capa_spark_1.png",
        "textures/item/armor/capa_deteriorer_evilsaiyan.png": "armor.png",
        "textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png": "armor_glowmask.png",
        "textures/item/capa_deteriorer_evilsaiyan.png": "icon.png",
        "textures/item/cape_folded.png": "folded.png",
        "textures/item/cape_folded_glowmask.png": "folded_glowmask.png",
    }
    for src, dst in copy.items():
        shutil.copy(RES / src, A / dst)
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
    print("5) comparación a escala, GIF y 8 poses")
    run(sys.executable, "tools/present_v1590.py", "--out", str(D), "--gif")
    shutil.copy(D / f"capa_v{ver.replace('.', '')}_antes_despues.png", A / "antes_despues.png")
    shutil.copy(D / "capa_v1170_estados.png", A / "estados.png")
    shutil.copy(D / "capa_v1170_animaciones.gif", A / "animacion.gif")


def step_comparativas(ver: str) -> None:
    print("6) comparativas")
    sys.path.insert(0, str(ROOT / "tools"))
    import numpy as np  # noqa: E402
    import preview_cloth as P  # noqa: E402

    armor = P.load(P.ARMOR_GEO)
    hidden = P.effective_hidden(armor)
    front = P.render(armor, P.ARMOR_TEX, hidden, yaw=0, pitch=8, size=705)

    ref = Image.open(ROOT / "referencias/REFERENCIA_CAPA.png").convert("RGB").crop(
        (385, 55, 695, 525)).resize((465, 705), Image.LANCZOS)
    cmp_img = Image.new("RGB", (1230, 800), (14, 12, 20))
    cd = ImageDraw.Draw(cmp_img)
    cmp_img.paste(ref, (8, 40))
    cmp_img.paste(front, (490, 40))
    cd.text((10, 16), "TU REFERENCIA (Blockbench)", fill=(240, 232, 245))
    cd.text((494, 16), f"v{ver} - dobladillo partido, solapas oblicuas y acero estratificado",
            fill=(240, 232, 245))
    cd.text((10, 754), "Izquierda: TU captura (el maniqui blanco es solo escala). "
                       "Derecha: la capa SOLA, como se abre en Blockbench",
            fill=(150, 140, 165))
    cd.text((10, 774), f"v{ver}: 12 gajos con forro | cadena en arco | 8 poses rotacionales",
            fill=(150, 140, 165))
    cmp_img.save(D / "capa_v1170_comparativa.png")
    cmp_img.save(A / "comparativa_final.png")

    sil = Image.new("RGB", (940, 330), (14, 12, 20))
    sil.paste(ref.resize((465, 330), Image.LANCZOS), (6, 0))
    sil.paste(front.crop((0, 120, 705, 705)).resize((465, 330), Image.LANCZOS), (475, 0))
    ImageDraw.Draw(sil).text((10, 308), "silueta medida del PNG", fill=(235, 228, 245))
    ImageDraw.Draw(sil).text((479, 308), f"silueta del modelo v{ver}", fill=(235, 228, 245))
    sil.save(D / "capa_v1170_silhouette_compare.png")

    aprobado = Image.open(ROOT / "referencias/ICONO_APROBADO_BACKUP.png").convert(
        "RGBA").resize((256, 256), Image.NEAREST)
    activo = Image.open(RES / "textures/item/capa_deteriorer_evilsaiyan.png").convert(
        "RGBA").resize((256, 256), Image.NEAREST)
    thumb = Image.open(ROOT / "referencias/REFERENCIA_CAPA_thumb.png").convert(
        "RGBA").resize((256, 256), Image.NEAREST)
    ic = Image.new("RGB", (798, 296), (14, 12, 20))
    ic.paste(thumb, (6, 34))
    ic.paste(aprobado, (270, 34))
    ic.paste(activo, (534, 34))
    d = ImageDraw.Draw(ic)
    d.text((10, 12), "referencia 200x200", fill=(235, 228, 245))
    d.text((274, 12), "icono APROBADO (backup intocable)", fill=(235, 228, 245))
    # v1.28.0: el icono activo es el PREFERIDO de la v1.25.0 (el que eligio
    # el usuario): no lleva acero ni el rediseño de la v1.27.0.
    d.text((538, 12), f"icono v{ver} (PREFERIDO v1.25.0, byte a byte)",
           fill=(235, 228, 245))
    ic.save(D / "capa_v1170_icon_compare.png")
    ic.save(D / "capa_v1170_icon_remaster.png")
    _ = np  # numpy ya importado: el render usa numpy por debajo


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
