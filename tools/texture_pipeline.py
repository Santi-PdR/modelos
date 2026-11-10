#!/usr/bin/env python3
"""
Procedural texture upgrade for the "Capa Deteriorer Evil Saiyan" (v1.2.0).

Why procedural instead of AI-generated art:
    The 128x128 armor texture is a strict UV atlas. Every cube face of
    capa_deteriorer_evilsaiyan.geo.json samples a fixed rectangle of it, so a
    repainted texture would misalign every single piece of the cape. This
    pipeline reads the pristine originals from tools/originals/, derives a UV
    usage mask from the geometry, and enhances ONLY the colour channels of
    already-opaque pixels. Alpha is preserved byte-for-byte, which keeps the
    silhouette and the GeckoLib emissive mask valid.

    GeckoLib's AutoGlowingTexture ignores the glowmask RGB and uses only its
    ALPHA; it also *zeroes* those pixels in the base texture. Therefore:
      * glow brightness is driven by the base texture colour at those pixels,
      * the glowmask must not grow, or it would punch holes in the cape.

Outputs (all committed, so CI needs no Python deps):
    textures/item/armor/capa_deteriorer_evilsaiyan.png            128x128
    textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png  128x128
    textures/item/capa_deteriorer_evilsaiyan.png                  64x64
    textures/item/cape_folded.png                                  64x64  (3D item atlas)
    textures/particle/capa_ember_0..2.png                          16x16  (custom particles)

Usage:  python tools/texture_pipeline.py     (requires Pillow + numpy)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "tools" / "originals"
ASSETS = ROOT / "src" / "main" / "resources" / "assets" / "capatest"
GEO = ASSETS / "geo" / "item" / "armor" / "capa_deteriorer_evilsaiyan.geo.json"
ARMOR_DIR = ASSETS / "textures" / "item" / "armor"
ICON = ASSETS / "textures" / "item" / "capa_deteriorer_evilsaiyan.png"

SIZE = 128
SEED = 20261110


# --------------------------------------------------------------------------
# UV atlas mask: which texels are actually sampled by the 126 geo cubes
# --------------------------------------------------------------------------
def uv_usage_mask(size: int = SIZE) -> np.ndarray:
    geometry = json.loads(GEO.read_text())["minecraft:geometry"][0]
    mask = np.zeros((size, size), dtype=bool)

    for bone in geometry.get("bones", []):
        for cube in bone.get("cubes", []):
            uv = cube.get("uv", {})
            if not isinstance(uv, dict):
                continue
            for spec in uv.values():
                if not isinstance(spec, dict) or "uv" not in spec:
                    continue
                u, v = spec["uv"]
                w, h = spec.get("uv_size", [0.0, 0.0])
                x0, x1 = sorted((float(u), float(u) + float(w)))
                y0, y1 = sorted((float(v), float(v) + float(h)))
                xi0, xi1 = max(0, int(math.floor(x0))), min(size, int(math.ceil(x1)))
                yi0, yi1 = max(0, int(math.floor(y0))), min(size, int(math.ceil(y1)))
                if xi1 > xi0 and yi1 > yi0:
                    mask[yi0:yi1, xi0:xi1] = True

    return mask


def dilate(binary: np.ndarray, radius: int = 1) -> np.ndarray:
    out = np.zeros_like(binary)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            out |= np.roll(np.roll(binary, dy, axis=0), dx, axis=1)
    return out


# --------------------------------------------------------------------------
# 1. Armor texture: cloth grain, cool shadows, crimson/violet energy veins
# --------------------------------------------------------------------------
def build_armor(used: np.ndarray) -> tuple[Image.Image, Image.Image]:
    base = np.asarray(Image.open(ORIGINALS / "armor.png").convert("RGBA"), dtype=np.float32)
    glow = np.asarray(Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"), dtype=np.float32)

    rgb, alpha = base[..., :3], base[..., 3]
    opaque = alpha > 0
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w]

    # Deterministic, slightly blurred noise + a fine woven diagonal grain.
    rng = np.random.default_rng(SEED)
    raw = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    smooth = (
        np.asarray(
            Image.fromarray(np.clip(raw * 40 + 128, 0, 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(0.55)
            ),
            dtype=np.float32,
        )
        - 128.0
    ) / 40.0
    weave = np.sin(xx * np.pi / 2.0) * np.sin(yy * np.pi / 2.0)
    grain = weave * 2.6 + smooth * 5.0

    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    neon_raw = np.clip((luma - 55.0) / 110.0, 0.0, 1.0)  # 0 = cloth, 1 = neon trim
    neon_w = neon_raw * opaque
    cloth_w = np.where(opaque, 1.0 - neon_raw, 0.0)

    out = rgb.copy()

    # Cool the dark cloth towards deep indigo and add cloth grain + top lighting.
    vertical_light = ((1.0 - yy / (h - 1)) - 0.5) * 17.0
    for channel, mul in enumerate((0.96, 0.93, 1.11)):
        out[..., channel] = rgb[..., channel] * mul + cloth_w * (grain + vertical_light)

    # Energy bleed: cape cloth immediately around neon lines picks up a violet halo.
    neon_core = (luma > 118) & opaque
    near = dilate(neon_core) & ~neon_core & opaque & used
    out[..., 0] += near * 15.0
    out[..., 1] += near * 3.0
    out[..., 2] += near * 25.0

    # Brighten and saturate the neon trim itself (crimson core / violet edge).
    boost = neon_w
    out[..., 0] += boost * (rgb[..., 0] * 0.28 + 26.0)
    out[..., 1] += boost * (rgb[..., 1] * 0.10 + 6.0)
    out[..., 2] += boost * (rgb[..., 2] * 0.22 + 34.0)

    # GeckoLib's emissive pass reuses these very pixels, so push them harder.
    emissive = glow[..., 3] > 0
    out[..., 0] = np.where(emissive, out[..., 0] * 1.12 + 26.0, out[..., 0])
    out[..., 1] = np.where(emissive, out[..., 1] * 1.05 + 8.0, out[..., 1])
    out[..., 2] = np.where(emissive, out[..., 2] * 1.12 + 30.0, out[..., 2])

    out = np.clip(out, 0, 255)
    out = np.where(opaque[..., None], out, rgb)  # never paint into transparent texels
    armor = np.dstack((out, alpha)).astype(np.uint8)

    # Glowmask: only alpha matters to GeckoLib, and only existing pixels may
    # stay lit (growing it would erase more base pixels => holes in the cape).
    ga = glow[..., 3]
    new_alpha = np.where(ga > 0, np.clip(ga * 1.10 + 14.0, 0, 255), 0)
    grgb = np.clip(glow[..., :3] * 1.18 + 18.0, 0, 255)
    glowmask = np.dstack((grgb, new_alpha)).astype(np.uint8)

    return Image.fromarray(armor, "RGBA"), Image.fromarray(glowmask, "RGBA")


# --------------------------------------------------------------------------
# 2. Inventory icon: 4x supersampled cape silhouette (16x16 -> 64x64)
# --------------------------------------------------------------------------
def build_icon() -> Image.Image:
    s = 256
    transparent = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    outline = [
        (80, 20), (176, 20), (190, 38), (203, 112), (218, 206),
        (206, 220), (190, 208), (174, 228), (158, 210), (142, 230),
        (126, 210), (110, 228), (94, 208), (78, 220), (66, 206),
        (53, 112), (66, 38),
    ]

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(outline, fill=255)

    # Vertical cloth gradient: dark violet shoulders -> deep crimson hem.
    cloth = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cloth)
    for y in range(s):
        t = y / (s - 1)
        top, bottom = (22.0, 12.0, 42.0), (74.0, 12.0, 40.0)
        col = tuple(int(top[c] * (1 - t) + bottom[c] * t) for c in range(3))
        cd.line([(0, y), (s, y)], fill=col + (255,))
    cloth = Image.composite(cloth, transparent, mask)

    # Fold shading, clipped to the silhouette.
    folds = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    fd = ImageDraw.Draw(folds)
    for i, x in enumerate(range(70, 200, 18)):
        shade = 115 if i % 2 == 0 else 38
        fd.line([(x, 28), (x + (x - 128) * 0.30, 214)], fill=(shade, 16, shade, 62), width=9)
    fd.line([(80, 26), (176, 26)], fill=(150, 70, 210, 90), width=7)
    fd.line([(128, 30), (128, 214)], fill=(220, 120, 220, 45), width=3)
    folds = Image.composite(folds, transparent, mask)
    cloth = Image.alpha_composite(cloth, folds)

    # Shoulder yoke / Evil-Saiyan style pauldrons, drawn over the cloth.
    yoke = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    yd = ImageDraw.Draw(yoke)
    yd.polygon([(48, 12), (92, 12), (98, 40), (66, 52), (50, 34)], fill=(26, 14, 44, 255))
    yd.polygon([(208, 12), (164, 12), (158, 40), (190, 52), (206, 34)], fill=(26, 14, 44, 255))
    yd.line([(48, 12), (92, 12), (98, 40), (66, 52), (50, 34), (48, 12)],
            fill=(168, 92, 255, 210), width=3)
    yd.line([(208, 12), (164, 12), (158, 40), (190, 52), (206, 34), (208, 12)],
            fill=(168, 92, 255, 210), width=3)
    cloth = Image.alpha_composite(cloth, yoke)

    # Neon trim + central emblem, with a soft bloom behind them.
    neon = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neon)
    path = outline + [outline[0]]
    nd.line(path, fill=(255, 62, 168, 255), width=6, joint="curve")
    nd.line([(p[0] + (128 - p[0]) * 0.10, p[1] + 12) for p in outline[2:15]],
            fill=(150, 92, 255, 170), width=3, joint="curve")
    nd.line([(80, 24), (176, 24)], fill=(255, 150, 220, 235), width=5)
    # Scattered energy motes following the cloth folds.
    motes = [(92, 96), (106, 132), (150, 108), (164, 150), (84, 168),
             (176, 182), (112, 186), (144, 170), (128, 146)]
    for mx, my in motes:
        nd.ellipse([(mx - 3, my - 3), (mx + 3, my + 3)], fill=(255, 90, 190, 220))
    # Chest emblem: diamond with a bright core.
    nd.polygon([(128, 58), (143, 80), (128, 102), (113, 80)], outline=(255, 90, 190, 255), width=4)
    nd.ellipse([(122, 74), (134, 86)], fill=(240, 210, 255, 255))

    bloom = neon.filter(ImageFilter.GaussianBlur(7))
    bloom.putalpha(bloom.getchannel("A").point(lambda v: int(v * 0.55)))
    composed = Image.alpha_composite(cloth, bloom)
    composed = Image.alpha_composite(composed, neon)

    # Fine cloth noise, only inside the silhouette.
    rng = np.random.default_rng(SEED + 1)
    noise = rng.normal(0, 7, (s, s)).astype(np.float32)
    arr = np.asarray(composed, dtype=np.float32).copy()
    inside = np.asarray(mask, dtype=bool) & (arr[..., 3] > 0)
    arr[..., :3] += noise[..., None] * inside[..., None]
    composed = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    return composed.resize((64, 64), Image.LANCZOS)


# --------------------------------------------------------------------------
# 3. Atlas for the folded 3D inventory model (opaque cloth, UV-mapped)
# --------------------------------------------------------------------------
def build_folded_texture() -> Image.Image:
    s = 64
    yy, xx = np.mgrid[0:s, 0:s]
    t = (yy / (s - 1))[..., None]
    top = np.array([24.0, 14.0, 46.0])
    bottom = np.array([78.0, 14.0, 46.0])
    rgb = top * (1.0 - t) + bottom * t

    folds = (np.sin(xx * np.pi / 7.0) * 9.0 + np.cos(xx * np.pi / 3.0) * 4.0)[..., None]
    rng = np.random.default_rng(SEED + 2)
    rgb = rgb + folds + rng.normal(0, 3.5, (s, s))[..., None]

    border = (xx < 3) | (xx > s - 4)
    rgb[..., 0] += border * 90.0
    rgb[..., 1] += border * 12.0
    rgb[..., 2] += border * 70.0

    band = (yy >= 4) & (yy < 9)  # yoke
    rgb[..., 0] += band * 70.0
    rgb[..., 1] += band * 20.0
    rgb[..., 2] += band * 110.0

    seam = ((xx % 12) < 1) & (yy > 10)  # vertical energy seams
    rgb[..., 0] += seam * 30.0
    rgb[..., 2] += seam * 45.0

    diamond = np.abs(xx - 32) + np.abs(yy - 22) < 7  # chest emblem
    rgb[..., 0] += diamond * 100.0
    rgb[..., 1] += diamond * 40.0
    rgb[..., 2] += diamond * 120.0

    rgb = np.clip(rgb, 0, 255)
    alpha = np.full((s, s, 1), 255.0)
    return Image.fromarray(np.dstack((rgb, alpha)).astype(np.uint8), "RGBA")


# --------------------------------------------------------------------------
# 4. Three animated ember sprites (transparent, additive-looking)
# --------------------------------------------------------------------------
def build_particle_sprites() -> list[Image.Image]:
    s = 16
    yy, xx = np.mgrid[0:s, 0:s]
    c = (s - 1) / 2.0
    radius = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    sprites = []

    for frame, spread in enumerate((2.0, 3.1, 4.2)):
        glow = np.clip(1.0 - radius / (spread * 2.3), 0.0, 1.0) ** 1.6
        core = np.clip(1.0 - radius / spread, 0.0, 1.0)
        # Small upward wisp on later frames.
        wisp = np.clip(1.0 - (np.abs(xx - c) / (spread * 0.55)), 0.0, 1.0) * \
            np.clip((c - yy) / (spread * 1.8), 0.0, 1.0) * 0.35 * frame
        alpha = np.clip((glow * 0.62 + core * 0.8 + wisp) * 255.0, 0, 255)

        rgb = np.zeros((s, s, 3), dtype=np.float32)
        rgb[..., 0] = 80.0 + 175.0 * core
        rgb[..., 1] = 20.0 + 70.0 * core
        rgb[..., 2] = 110.0 + 145.0 * core
        sprites.append(Image.fromarray(
            np.dstack((np.clip(rgb, 0, 255), alpha)).astype(np.uint8), "RGBA"))

    return sprites


def main() -> None:
    used = uv_usage_mask()
    print(f"UV texels used by geometry: {used.mean() * 100:.1f}%")

    armor, glowmask = build_armor(used)
    armor.save(ARMOR_DIR / "capa_deteriorer_evilsaiyan.png")
    glowmask.save(ARMOR_DIR / "capa_deteriorer_evilsaiyan_glowmask.png")
    print("armor:", armor.size, "glowmask:", glowmask.size)

    icon = build_icon()
    icon.save(ICON)
    print("icon:", icon.size)

    folded = build_folded_texture()
    folded.save(ASSETS / "textures/item/cape_folded.png")
    print("folded atlas:", folded.size)

    particle_dir = ASSETS / "textures/particle"
    particle_dir.mkdir(parents=True, exist_ok=True)
    embers = build_particle_sprites()
    for index, sprite in enumerate(embers):
        sprite.save(particle_dir / f"capa_ember_{index}.png")
    print(f"particle sprites: {len(embers)} x 16x16")

    # Sanity: glowmask must stay 128x128 and must not cover new texels.
    ga = np.asarray(Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"))[..., 3]
    gb = np.asarray(glowmask)[..., 3]
    assert (ga > 0).sum() == (gb > 0).sum(), "glowmask coverage changed - would punch holes"
    print(f"emissive texels unchanged: {(ga > 0).sum()}")


if __name__ == "__main__":
    main()
