#!/usr/bin/env python3
"""Verifica el repintado RGB de v1.57.0 frente al respaldo de v1.56.0.

--candidate prueba la salida del pintor y del exportador sin escribir assets.
--comparison escribe un render antes/después con el mismo modelo y cámara.
"""
from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from texture_regression import VerifiedEdit, render_pair, validate

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/respaldos/v1.56.0"
BG = (29, 25, 35)


def check_atlas(edit: VerifiedEdit) -> None:
    cloth = edit.delta[:96, :96]
    for rows in (slice(0, 48), slice(48, 96)):
        available = cloth[rows][~edit.protected[rows, :96]]
        assert (available >= 24).mean() > 0.40, "la capa de tela apenas cambia"
    print(f"Atlas 3D: {(edit.delta > 0).sum()} texels RGB distintos; paño y forro: "
          f"{(cloth > 0).sum()}/9216, {(cloth >= 32).sum()} con Δ ≥ 32/255. "
          f"Alfa 255 y {edit.protected.sum()} texels de energía intactos.")


def comparison(path: Path, renders: tuple[Image.Image, Image.Image]) -> None:
    image = Image.new("RGB", (1232, 668), (21, 17, 26))
    draw = ImageDraw.Draw(image)
    text, muted, accent = (249, 235, 241), (190, 173, 193), (245, 150, 198)

    def label(x, y, words, size, fill=text):
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            font = ImageFont.load_default(size=size)
            words = unicodedata.normalize("NFKD", words).encode("ascii", "ignore").decode()
        draw.text((x, y), words, font=font, fill=fill)

    label(26, 23, "MANTLE OF THE BLIGHT STAR", 28)
    label(26, 63, "Paño 3D repintado a partir de las capturas de Blockbench", 18, muted)
    draw.rounded_rectangle((24, 112, 251, 611), radius=12,
                           fill=(31, 24, 36), outline=(66, 46, 62))
    label(37, 127, "TUS REFERENCIAS", 17)
    for i, name in enumerate(("REFERENCIA_CAPA_thumb.png", "REFERENCIA_CAPA_acabado.png")):
        with Image.open(ROOT / "referencias" / name) as ref:
            image.paste(ref.convert("RGB"), (37, 159 + 209 * i))
    label(37, 577, "Granate / violeta / neón", 15, muted)
    for i, render in enumerate(renders):
        x = 270 + 470 * i
        draw.rounded_rectangle((x, 112, x + 456, 611), radius=12,
                               fill=BG, outline=(66, 46, 62))
        label(x + 16, 125, ("v1.56.0  /  ANTES", "v1.57.0  /  TEXTURA NUEVA")[i],
              19, (muted, accent)[i])
        image.paste(render, (x, 155))
    label(26, 632, "Mismas UV, cámara y geometría  ·  Alfa 255  ·  Sin cambios de brillo ni movimiento", 17, muted)
    image.save(path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--comparison", type=Path)
    args = parser.parse_args()
    edit = validate(BASELINE, candidate=args.candidate)
    check_atlas(edit)
    renders = render_pair(edit, yaw=-28, pitch=8, size=456, bg=BG)
    before, after = (np.asarray(image).astype(int) for image in renders)
    visible = (before != BG).any(axis=2) | (after != BG).any(axis=2)
    changed = (np.abs(after - before).max(axis=2)[visible] >= 20).mean()
    assert changed > 0.24, "no hay un cambio claro sobre el modelo 3D"
    print(f"Render equipado 3/4: {changed:.1%} de los píxeles visibles con Δ ≥ 20/255.")
    if args.comparison:
        comparison(args.comparison, renders)
    print("OK: paño 3D nuevo, icono, glowmasks, geometría y 8 clips intactos.")


if __name__ == "__main__":
    main()
