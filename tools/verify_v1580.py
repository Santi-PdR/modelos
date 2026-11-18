#!/usr/bin/env python3
"""Compara el cuello y los jirones v1.58.0 con la entrega v1.57.0.

--candidate usa el atlas y el .bbmodel en memoria, antes de regenerar.
--comparison muestra las dos capturas de revisión y el antes/después.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cloth_spec import COWL_TILES
from texture_regression import VerifiedEdit, render_pair, validate

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/respaldos/v1.57.0"
BG = (27, 23, 32)
SIZE = 448


def check_atlas(edit: VerifiedEdit) -> None:
    cloth = np.zeros_like(edit.protected)
    cloth[:96, :96] = True
    cowl = np.zeros_like(cloth)
    for x0, y0, x1, y1 in COWL_TILES.values():
        cowl[y0:y1, x0:x1] = True
    outside = (edit.delta != 0) & ~(cloth | cowl)
    # La muesca del forro v1.57.0 sobresalía un texel de su franja.
    # Al pintar cada franja por separado, esa coordenada vuelve al fondo.
    assert edit.atlas.getpixel((46, 96)) == (26, 10, 36, 255)
    outside[96, 46] = False
    assert not outside.any(), "se repintaron piezas ajenas al paño"
    editable = ~edit.protected
    for label, delta in (("paño", edit.delta[:48, :96][editable[:48, :96]]),
                         ("forro", edit.delta[48:96, :96][editable[48:96, :96]]),
                         ("cuello", edit.delta[cowl & editable])):
        assert (delta >= 20).mean() > 0.35, f"el cambio de {label} es demasiado leve"
    print(f"Atlas: {(edit.delta > 0).sum()} texels RGB nuevos, "
          f"{(edit.delta[cloth] > 0).sum()} de paño y forro, "
          f"{(edit.delta[cowl] > 0).sum()} del cuello. "
          f"Alfa 255; {edit.protected.sum()} de energía intactos.")


def check_view(edit: VerifiedEdit, yaw: float) -> tuple[tuple[Image.Image, Image.Image], float]:
    images = render_pair(edit, yaw=yaw, pitch=6, size=SIZE, bg=BG)
    before, after = (np.asarray(im, dtype=int) for im in images)
    visible = (before != BG).any(axis=2) | (after != BG).any(axis=2)
    delta = np.abs(after - before).max(axis=2)
    changed = (delta[visible] >= 20).mean()
    lo, hi = np.where(visible)[0][[0, -1]]
    upper = slice(lo, lo + round(0.27 * (hi - lo)))
    lower = slice(lo + round(0.54 * (hi - lo)), hi + 1)
    top_delta = (delta[upper][visible[upper]] >= 20).mean()
    assert changed > 0.28 and top_delta > 0.27, ("cambio poco visible en 3D", yaw, changed, top_delta)

    def cool_cloth(image):
        # Indicador de tejido violeta mate en los jirones. No cuenta los
        # píxeles claros ni el rosa fuerte del núcleo de energía.
        r, _, b = image[lower][visible[lower]].T
        return ((r >= 34) & (r <= 130) & (b - r >= 14)).mean()

    old_cool, new_cool = map(cool_cloth, (before, after))
    assert new_cool - old_cool > 0.18, ("no gana presencia el violeta", yaw, old_cool, new_cool)
    print(f"Vista {yaw:+.0f}°: {changed:.1%} de píxeles visibles con Δ ≥ 20/255; "
          f"violeta mate en jirones {old_cool:.1%} → {new_cool:.1%}.")
    return images, changed


def comparison(path: Path, images: tuple[Image.Image, Image.Image], changed: float) -> None:
    plate = Image.new("RGB", (1212, 838), (20, 17, 25))
    draw = ImageDraw.Draw(plate)
    text, muted, accent = (248, 236, 241), (193, 174, 194), (238, 166, 217)

    def label(x, y, words, size, ink=text, *, bold=False):
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
        except OSError:
            font = ImageFont.load_default(size=size)
        draw.text((x, y), words, font=font, fill=ink)

    label(26, 26, "MANTLE OF THE BLIGHT STAR", 29, bold=True)
    label(27, 67, "Revisión de la capa equipada · Cuello y jirones", 19, muted)
    draw.rounded_rectangle((24, 118, 242, 774), radius=12,
                           fill=(31, 24, 36), outline=(66, 48, 65))
    label(38, 135, "TUS CAPTURAS", 16, muted, bold=True)
    label(38, 161, "v1.57.0 en Blockbench", 15)
    for i, (filename, caption) in enumerate((
            ("REVISION_v1.57.0_equipada.png", "Con maniquí"),
            ("REVISION_v1.57.0_sola.png", "Sólo la capa"))):
        top = 196 + i * 222
        with Image.open(ROOT / "referencias" / filename) as ref:
            picture = ref.convert("RGB")
            picture.thumbnail((192, 184), Image.Resampling.LANCZOS)
            plate.paste(picture, (38 + (192 - picture.width) // 2, top))
        label(38, top + 186, caption, 15, muted)
    label(38, 670, f"{changed:.0%}", 29, accent, bold=True)
    label(38, 709, "Δ ≥ 20/255 en el render", 14, muted)

    # El acercamiento recorta la misma región de las dos vistas.
    mask = (np.asarray(images[0]) != BG).any(axis=2)
    yy, xx = np.where(mask)
    crop = (int(xx.min()) - 5, int(yy.min()), int(xx.max()) + 6,
            int(yy.min()) + round((yy.max() - yy.min()) * 0.26))
    for i, image in enumerate(images):
        x = 257 + i * 472
        draw.rounded_rectangle((x, 118, x + 459, 774), radius=12,
                               fill=BG, outline=(66, 48, 65))
        label(x + 16, 135, ("v1.57.0  /  ANTES", "v1.58.0  /  NUEVOS PLIEGUES")[i],
              18, muted if i == 0 else accent, bold=True)
        plate.paste(image, (x + 6, 161))
        draw.line((x + 16, 610, x + 442, 610), fill=(68, 50, 65), width=1)
        label(x + 16, 620, "Detalle del cuello", 15, muted)
        detail = image.crop(crop)
        scale = min(424 / detail.width, 122 / detail.height)
        detail = detail.resize((round(detail.width * scale), round(detail.height * scale)),
                               Image.Resampling.NEAREST)
        plate.paste(detail, (x + (460 - detail.width) // 2, 645))
    label(26, 798, "Render software · Misma cámara, malla y UV · Glow e icono intactos · 8 animaciones", 16, muted)
    plate.save(path, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--comparison", type=Path)
    args = parser.parse_args()
    edit = validate(BASELINE, candidate=args.candidate)
    check_atlas(edit)
    front, changed = check_view(edit, yaw=0)
    check_view(edit, yaw=-29)
    if args.comparison:
        comparison(args.comparison, front, changed)
    print("OK: cuello y jirones repintados; modelo, UV, 8 clips, icono y energía intactos.")


if __name__ == "__main__":
    main()
