"""Invariantes de las revisiones RGB de la capa equipada (desde v1.56.0)."""
from __future__ import annotations

import base64
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

import bbmodel_export as bb
import cape_animation_pipeline as anim
import preview_cloth as preview
from cape_atlas_v1230 import build_clean_atlas

GEO_SHA = "f70f8debf7fafaba75016b46800b9fc817ba5c189553ff35652d9e995e1a75fc"
ANIM_SHA = "6a5543d1b0c9facd3afa72eaecd636e42b10849768dd43936db57f2d9103157a"


@dataclass(frozen=True)
class VerifiedEdit:
    geo: dict
    before: Path
    atlas: Image.Image
    delta: np.ndarray
    protected: np.ndarray


def rgba(data: Path | bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data) if isinstance(data, bytes) else data) as image:
        return np.asarray(image.convert("RGBA"))


def png(image: Image.Image) -> bytes:
    with io.BytesIO() as stream:
        image.save(stream, format="PNG")
        return stream.getvalue()


def same_model(before: dict, after: dict, atlas: Image.Image) -> None:
    # Ni un cambio en cubos, UV, UUID, jerarquía ni keyframes.
    assert {k: v for k, v in before.items() if k not in ("name", "textures")} == {
        k: v for k, v in after.items() if k not in ("name", "textures")}, "cambió el modelo además del atlas"
    assert len(after["textures"]) == len(before["textures"]) == 1
    a, b = before["textures"][0], after["textures"][0]
    assert {k: v for k, v in a.items() if k != "source"} == {k: v for k, v in b.items() if k != "source"}
    data = base64.b64decode(b["source"].split(",", 1)[1])
    assert np.array_equal(rgba(data), np.asarray(atlas)), "el .bbmodel no lleva el atlas repintado"


def validate(baseline: Path, *, candidate: bool) -> VerifiedEdit:
    for line in (baseline / "SHA256SUMS.txt").read_text().splitlines():
        sha, name = line.split("  ", 1)
        assert hashlib.sha256((baseline / name).read_bytes()).hexdigest() == sha, name
    old_atlas = baseline / preview.ARMOR_TEX.relative_to(preview.ASSETS)
    for tex in (baseline / "textures").rglob("*.png"):
        if tex != old_atlas:
            assert tex.read_bytes() == (preview.ASSETS / tex.relative_to(baseline)).read_bytes(), tex.name
    geo_bytes, animation_bytes = preview.ARMOR_GEO.read_bytes(), anim.ANIM.read_bytes()
    assert hashlib.sha256(geo_bytes).hexdigest() == GEO_SHA, "cambió el geo"
    assert hashlib.sha256(animation_bytes).hexdigest() == ANIM_SHA, "cambió el animation.json"
    anim.ribbon_rms(json.loads(animation_bytes))

    atlas, glowmask = build_clean_atlas()
    before, after = rgba(old_atlas), np.asarray(atlas)
    assert before.shape == after.shape == (128, 128, 4)
    assert after[..., 3].min() == 255, "perdió opacidad"
    old_glow = old_atlas.with_stem(old_atlas.stem + "_glowmask")
    assert old_glow.read_bytes() == png(glowmask), "cambió el glowmask generado"
    glow = np.asarray(glowmask)[..., 3] > 0
    assert np.array_equal(before[glow], after[glow]), "cambió el RGB bajo el neón/halo"
    delta = np.abs(after[..., :3].astype(int) - before[..., :3]).max(axis=2)

    geo = preview.load(preview.ARMOR_GEO)
    before_model = json.loads((baseline / f"CAPA_{baseline.name}.bbmodel").read_text())
    if candidate:
        model = bb.build(geo, atlas)
    else:
        assert preview.ARMOR_TEX.read_bytes() == png(atlas), "atlas sin regenerar"
        model = json.loads(bb.DOC.read_text())
        assert model["name"] == f"capa_deteriorer_evilsaiyan_v{bb.VER_TAG}", "nombre interno viejo"
    same_model(before_model, model, atlas)
    return VerifiedEdit(geo, old_atlas, atlas, delta, glow)


def render_pair(edit: VerifiedEdit, *, yaw: float, pitch: float, size: int,
                bg: tuple[int, int, int]) -> tuple[Image.Image, Image.Image]:
    hidden = preview.effective_hidden(edit.geo)
    before = preview.render(edit.geo, edit.before, hidden, yaw=yaw, pitch=pitch, size=size, bg=bg)
    after = preview.render(edit.geo, io.BytesIO(png(edit.atlas)), hidden,
                           yaw=yaw, pitch=pitch, size=size, bg=bg)
    return before, after
