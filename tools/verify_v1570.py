#!/usr/bin/env python3
"""Verifica el repintado RGB de v1.57.0 frente al respaldo de v1.56.0.

--candidate prueba la salida del pintor y del exportador sin escribir assets.
--comparison escribe un render antes/después con el mismo modelo y cámara.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import bbmodel_export as bb
import cape_animation_pipeline as anim
import preview_cloth as preview
from cape_atlas_v1230 import build_clean_atlas

ROOT = preview.ROOT
BASELINE = ROOT / "docs/respaldos/v1.56.0"
OLD_ATLAS = BASELINE / preview.ARMOR_TEX.relative_to(preview.ASSETS)
GEO_SHA = "f70f8debf7fafaba75016b46800b9fc817ba5c189553ff35652d9e995e1a75fc"
ANIM_SHA = "6a5543d1b0c9facd3afa72eaecd636e42b10849768dd43936db57f2d9103157a"
BG = (29, 25, 35)


def rgba(data: Path | bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data) if isinstance(data, bytes) else data) as image:
        return np.asarray(image.convert("RGBA"))


def png(image: Image.Image) -> bytes:
    with io.BytesIO() as stream:
        image.save(stream, format="PNG")
        return stream.getvalue()


def check_atlas(atlas: Image.Image, glowmask: Image.Image) -> None:
    before, after = rgba(OLD_ATLAS), np.asarray(atlas)
    assert before.shape == after.shape == (128, 128, 4)
    assert after[..., 3].min() == 255, "perdió opacidad"
    old_glow = OLD_ATLAS.with_stem(OLD_ATLAS.stem + "_glowmask")
    assert old_glow.read_bytes() == png(glowmask), "cambió el glowmask generado"
    glow = np.asarray(glowmask)[..., 3] > 0
    assert np.array_equal(before[glow], after[glow]), "cambió el RGB bajo el neón/halo"
    diff = np.abs(after[..., :3].astype(int) - before[..., :3]).max(axis=2)
    cloth = diff[:96, :96]
    for rows in (slice(0, 48), slice(48, 96)):
        available = cloth[rows][~glow[rows, :96]]
        assert (available >= 24).mean() > 0.40, "la capa de tela apenas cambia"
    print(f"Atlas 3D: {(diff > 0).sum()} texels RGB distintos; paño y forro: "
          f"{(cloth > 0).sum()}/9216, {(cloth >= 32).sum()} con Δ ≥ 32/255. "
          f"Alfa 255 y {glow.sum()} texels de energía intactos.")


def same_model(before: dict, after: dict, atlas: Image.Image) -> None:
    # El nombre de versión y la imagen embebida son las únicas diferencias.
    assert {k: v for k, v in before.items() if k not in ("name", "textures")} == {
        k: v for k, v in after.items() if k not in ("name", "textures")}, "cambió el modelo además del atlas"
    assert len(after["textures"]) == len(before["textures"]) == 1
    a, b = before["textures"][0], after["textures"][0]
    assert {k: v for k, v in a.items() if k != "source"} == {k: v for k, v in b.items() if k != "source"}
    data = base64.b64decode(b["source"].split(",", 1)[1])
    assert np.array_equal(rgba(data), np.asarray(atlas)), "el .bbmodel no lleva el atlas repintado"


def render_pair(geo: dict, atlas: Image.Image) -> tuple[Image.Image, Image.Image]:
    hidden = preview.effective_hidden(geo)
    # Mismos UV, geo y cámara: la diferencia del render viene sólo del color.
    sources = (OLD_ATLAS, io.BytesIO(png(atlas)))
    before, after = [preview.render(geo, src, hidden, yaw=-28, pitch=8, size=456, bg=BG)
                     for src in sources]
    old, new = np.asarray(before).astype(int), np.asarray(after).astype(int)
    visible = (old != BG).any(axis=2) | (new != BG).any(axis=2)
    changed = (np.abs(new - old).max(axis=2)[visible] >= 20).mean()
    assert changed > 0.24, "no hay un cambio claro sobre el modelo 3D"
    print(f"Render equipado 3/4: {changed:.1%} de los píxeles visibles con Δ ≥ 20/255.")
    return before, after


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
    for line in (BASELINE / "SHA256SUMS.txt").read_text().splitlines():
        sha, name = line.split("  ", 1)
        assert hashlib.sha256((BASELINE / name).read_bytes()).hexdigest() == sha, name
    for tex in (BASELINE / "textures").rglob("*.png"):
        if tex != OLD_ATLAS:
            assert tex.read_bytes() == (preview.ASSETS / tex.relative_to(BASELINE)).read_bytes(), tex.name
    assert hashlib.sha256(preview.ARMOR_GEO.read_bytes()).hexdigest() == GEO_SHA, "cambió el geo"
    assert hashlib.sha256(anim.ANIM.read_bytes()).hexdigest() == ANIM_SHA, "cambió el animation.json"
    anim.ribbon_rms(json.loads(anim.ANIM.read_text()))

    before = json.loads((BASELINE / "CAPA_v1.56.0.bbmodel").read_text())
    geo = preview.load(preview.ARMOR_GEO)
    atlas, glow = build_clean_atlas()
    check_atlas(atlas, glow)
    if args.candidate:
        after = bb.build(geo, atlas)
    else:
        assert preview.ARMOR_TEX.read_bytes() == png(atlas), "atlas sin regenerar"
        after = json.loads(bb.DOC.read_text())
        assert after["name"] == f"capa_deteriorer_evilsaiyan_v{bb.VER_TAG}", "nombre interno viejo"
    same_model(before, after, atlas)
    renders = render_pair(geo, atlas)
    if args.comparison:
        comparison(args.comparison, renders)
    print("OK: paño 3D nuevo, icono, glowmasks, geometría y 8 clips intactos.")


if __name__ == "__main__":
    main()
