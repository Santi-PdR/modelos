#!/usr/bin/env python3
"""Prueba de la mejora visual v1.56.0 frente a la entrega v1.55.0.

--candidate usa los generadores en memoria, antes de tocar los entregables.
Sin esa opción se verifican el atlas, geo y .bbmodel que se van a publicar.
--comparison exporta las dos versiones con la misma cámara y escala.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import armor_model_pipeline as geo_pipeline
import bbmodel_export as bb
import cape_animation_pipeline as anim
import preview_cloth as preview
from cape_atlas_v1230 import build_clean_atlas

ROOT = preview.ROOT
BACKUP = ROOT / "docs/respaldos/v1.55.0b"
BASE_ATLAS = BACKUP / "textures/item/armor/capa_deteriorer_evilsaiyan.png"
BASE_ANIMATION_SHA = "6a5543d1b0c9facd3afa72eaecd636e42b10849768dd43936db57f2d9103157a"


def pixels(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGBA"))


def png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def check_atlas(atlas: Image.Image, glow: bytes) -> tuple[int, int, int]:
    with Image.open(BASE_ATLAS) as im:
        base = pixels(im)
    current = pixels(atlas)
    assert current.shape == base.shape == (128, 128, 4)
    assert int(current[..., 3].min()) == 255, "se perdió opacidad en el atlas 3D"
    assert glow == BASE_ATLAS.with_stem(BASE_ATLAS.stem + "_glowmask").read_bytes()
    with Image.open(io.BytesIO(glow)) as im:
        emissive = pixels(im)[..., 3] > 0
    assert np.array_equal(current[emissive], base[emissive]), "cambió el RGB de neón/halo"
    delta = np.abs(current[..., :3].astype(int) - base[..., :3]).max(axis=2)
    cloth = delta[:96, :96]
    # Comparar ambas capas del paño 3D, no un parche sin UV ni el item.
    # El neón queda fuera del denominador: está prohibido modificarlo.
    for rows in (slice(0, 48), slice(48, 96)):
        face = cloth[rows][~emissive[rows, :96]]
        assert (face > 0).mean() > 0.90, "el cambio no cubre suficiente paño"
        assert (face >= 32).mean() > 0.55, "el cambio de color es demasiado sutil"
    total, cloth_changed, high = (int(np.count_nonzero(delta)),
                                  int(np.count_nonzero(cloth)), int((cloth >= 32).sum()))
    print(f"Atlas 3D: {total}/16384 texels RGB distintos; paño {cloth_changed}/9216, "
          f"{high} con Δ ≥ 32/255. Alfa mínimo 255; {emissive.sum()} texels de energía intactos.")
    return total, cloth_changed, high


def check_model(before: dict, after: dict, atlas: Image.Image) -> None:
    for key in ("elements", "groups"):
        assert {e["name"]: e["uuid"] for e in before[key]} == {
            e["name"]: e["uuid"] for e in after[key]}, f"UUID modificado ({key})"
    assert after["outliner"] == before["outliner"], "la jerarquía cambió"
    assert after["animations"] == before["animations"], "cambiaron los 8 clips de Blockbench"
    raw = base64.b64decode(after["textures"][0]["source"].split(",", 1)[1])
    with Image.open(io.BytesIO(raw)) as im:
        assert np.array_equal(pixels(im), pixels(atlas)), "atlas viejo embebido en .bbmodel"

    old, new = ({e["name"]: e for e in model["elements"]} for model in (before, after))
    for name, min_gain in (("v17_cowl_back_2_0", 1.25), ("v17_cowl_tooth_3_0", 2.25)):
        a, b = old[name], new[name]
        h0, h1 = (e["to"][1] - e["from"][1] for e in (a, b))
        assert h1 - h0 >= min_gain, (name, h0, h1)
        assert a["from"] != b["from"] and b["visibility"], name
        print(f"{name}: {h0:.2f} → {h1:.2f} u; "
              f"{a['from']}..{a['to']} → {b['from']}..{b['to']}")


def sample(channel, t: float, default) -> np.ndarray:
    if channel is None or isinstance(channel, list):
        return np.array(default if channel is None else channel, dtype=float)
    keys = sorted((float(k), v) for k, v in channel.items())

    def value(key):
        return np.array(key if isinstance(key, list) else key["vector"], dtype=float)

    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            f = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            ease = b.get("easing", "linear") if isinstance(b, dict) else "linear"
            if ease == "easeInOutSine":
                f = (1 - math.cos(math.pi * f)) / 2
            elif ease == "easeOutSine":
                f = math.sin(f * math.pi / 2)
            elif ease == "easeInSine":
                f = 1 - math.cos(f * math.pi / 2)
            else:
                assert ease == "linear", ease
            return value(a) * (1 - f) + value(b) * f
    return value(keys[-1][1])


def check_clearance(geometry: dict, clips: dict) -> None:
    """Holgura estática y muestreo de clips, en el espacio .geo de GeckoLib.

    No es un test del cliente: se mide contra torso/ropa (Z=2.25) y cabeza
    neutra (Y≥24, Z≤4). Incluye el inflate y la jerarquía de los cubos.
    """
    hidden = preview.effective_hidden(geometry)
    bones = {b["name"]: b for b in geometry["bones"]}
    boxes = []
    for name, bone in bones.items():
        if name in hidden:
            continue
        for cube in bone.get("cubes", ()):
            x, y, z = cube["origin"]
            w, h, d = cube["size"]
            inflate = cube["inflate"]
            verts = (np.array([-x - w, y, z]) - inflate
                     + preview.CORNERS * (np.array([w, h, d]) + 2 * inflate))
            boxes.append((name, np.c_[verts, np.ones(8)].T))
    identity = np.eye(4)
    near = (math.inf, "", 0.0, "")
    for clip, tracks, times in [("reposo", {}, [0.0])] + [
        (name, data["bones"], np.linspace(0, float(data["animation_length"]), 33))
        for name, data in clips.items()
    ]:
        for t in times:
            cache = {}

            def matrix(name):
                if name not in cache:
                    bone = bones[name]
                    ch = tracks.get(name, {})
                    p = np.array(bone["pivot"]) * [-1, 1, 1]
                    r = (np.array(bone.get("rotation", [0, 0, 0]))
                         + sample(ch.get("rotation"), t, [0] * 3))
                    s = sample(ch.get("scale"), t, [1] * 3)
                    pos = sample(ch.get("position"), t, [0] * 3) * [-1, 1, 1]
                    parent = matrix(bone["parent"]) if "parent" in bone else identity
                    cache[name] = parent @ preview.T(p + pos) @ preview.rotmat(r) @ np.diag(
                        [*s, 1.0]) @ preview.T(-p)
                return cache[name]

            for name, verts in boxes:
                x, y, z, _ = matrix(name) @ verts
                near = min(near, (float(z.min()), clip, float(t), name))
                # Separación conservadora por ejes, sin ajustar la pose
                # de cabeza para ocultar una intersección.
                assert y.max() < 24 or z.min() > 4 or x.min() > 4 or x.max() < -4, (
                    "intersección potencial con cabeza", clip, t, name, y.max(), z.min())
    assert near[0] > 2.25, ("capa dentro del torso/ropa", near)
    print(f"+Z: cara más próxima al torso {near[0]:.3f} u (>2.25), "
          "reposo + 33 muestras por clip, inflate incluido.")


def comparison(path: Path, before_geo: dict, after_geo: dict, after_atlas: Path,
               stats: tuple[int, int, int]) -> None:
    size, pitch = 536, 8
    pairs = ((before_geo, BASE_ATLAS), (after_geo, after_atlas))
    all_points = np.concatenate([
        face[0] @ preview.R("x", pitch)[:3, :3].T
        for geo, _ in pairs for face in preview.collect(geo, preview.effective_hidden(geo))])
    lo, hi = all_points.min(axis=0), all_points.max(axis=0)
    frame = (*(lo[:2] + hi[:2]) / 2, (size - 42) / max(hi[:2] - lo[:2]))
    plate = Image.new("RGB", (1152, 912), (19, 15, 26))
    d = ImageDraw.Draw(plate)
    text, muted, accent = (250, 235, 238), (184, 166, 188), (245, 177, 151)

    def label(x, y, message, scale, color=text):
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", scale)
        except OSError:
            font = ImageFont.load_default(size=scale)
            message = unicodedata.normalize("NFKD", message).encode("ascii", "ignore").decode()
        d.text((x, y), message, font=font, fill=color)

    label(28, 24, "MANTLE OF THE BLIGHT STAR", 30)
    label(28, 65, "Modelo equipado  /  Misma cámara y escala  /  Render software", 19, muted)
    for i, (geo, atlas) in enumerate(pairs):
        x = 28 + 560 * i
        d.rounded_rectangle((x - 1, 110, x + size + 1, 872), radius=12,
                            fill=(27, 21, 34), outline=(68, 48, 64), width=1)
        label(x + 17, 124, ("v1.55.0    ANTES", "v1.56.0    PAÑO Y CUELLO NUEVOS")[i],
              22, (muted, accent)[i])
        render = preview.render(geo, atlas, preview.effective_hidden(geo), pitch=pitch,
                                size=size, bg=(32, 25, 39), frame=frame)
        plate.paste(render, (x, 159))
        with Image.open(atlas) as im:
            cloth = im.convert("RGB").crop((0, 0, 96, 96)).resize((144, 144), Image.Resampling.NEAREST)
        plate.paste(cloth, (x + 17, 712))
        label(x + 179, 718, "Atlas 3D · paño y forro", 19)
        changed = f"{stats[1]:,}".replace(",", ".")
        lines = (("Cuello dorsal: 3,90 u", "Faldón central: 3,20 u", "Referencia publicada"),
                 ("Cuello dorsal: 5,20 u", "Faldón central: 5,50 u",
                  f"{changed} texels del paño repintados"))[i]
        for j, line in enumerate(lines):
            label(x + 179, 753 + 27 * j, line, 17, muted)
    label(28, 880, "RGB solo  ·  Alfa 255  ·  Icono y glowmasks byte-idénticos  ·  8 clips intactos", 17, muted)
    plate.save(path, optimize=True)


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--candidate", action="store_true")
    cli.add_argument("--comparison", type=Path)
    args = cli.parse_args()
    if args.candidate and args.comparison:
        cli.error("generar la comparativa después de verificar los archivos exportados")
    for line in (BACKUP / "SHA256SUMS.txt").read_text().splitlines():
        sha, name = line.split("  ", 1)
        assert hashlib.sha256((BACKUP / name).read_bytes()).hexdigest() == sha, name

    old_model = json.loads((BACKUP / "CAPA_v1.55.0.bbmodel").read_text())
    made_geo = geo_pipeline.build()["minecraft:geometry"][0]
    made_atlas, made_glow = build_clean_atlas()
    if args.candidate:
        model = bb.build(made_geo, made_atlas)
        stats = check_atlas(made_atlas, png_bytes(made_glow))
    else:
        assert preview.load(preview.ARMOR_GEO) == made_geo, "geo sin regenerar"
        model = json.loads(bb.DOC.read_text())
        assert model == bb.build(made_geo, made_atlas), ".bbmodel sin regenerar"
        assert preview.ARMOR_TEX.read_bytes() == png_bytes(made_atlas), "atlas sin regenerar"
        glow_path = preview.ARMOR_TEX.with_stem(preview.ARMOR_TEX.stem + "_glowmask")
        stats = check_atlas(made_atlas, glow_path.read_bytes())
        for tex in (BACKUP / "textures").rglob("*.png"):
            if tex != BASE_ATLAS:
                assert tex.read_bytes() == (preview.ASSETS / tex.relative_to(BACKUP)).read_bytes(), tex.name

    check_model(old_model, model, made_atlas)
    runtime = anim.ANIM.read_bytes()
    assert hashlib.sha256(runtime).hexdigest() == BASE_ANIMATION_SHA, "cambió el animation.json"
    clips = json.loads(runtime)
    check_clearance(made_geo, clips["animations"])
    assert len(anim.ribbon_rms(clips)) == 8
    if args.comparison:
        before_geo = preview.load(BACKUP / "capa_deteriorer_evilsaiyan.geo.json")
        comparison(args.comparison, before_geo, made_geo, preview.ARMOR_TEX, stats)
    print("OK: cambio 3D probado frente a v1.55.0; UUIDs, clips y energía preservados.")


if __name__ == "__main__":
    main()
