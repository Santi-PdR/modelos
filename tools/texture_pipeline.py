#!/usr/bin/env python3
"""
Procedural texture suite for the "Capa Deteriorer Evil Saiyan" (v1.3.0).

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

    The folded 3D item model uses its own 128x128 artwork atlas (generated from
    the same cape design as the icon), and the ember particles use three soft,
    anti-aliased 16x16 sprites.

Outputs (all committed, so CI needs no Python deps):
    textures/item/armor/capa_deteriorer_evilsaiyan.png            128x128
    textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png  128x128
    textures/item/capa_deteriorer_evilsaiyan.png                  64x64
    textures/item/cape_folded.png                                  128x128 (3D item atlas)
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


def _blurred_noise(rng: np.random.Generator, shape: tuple[int, int], radius: float) -> np.ndarray:
    raw = rng.normal(0.0, 1.0, shape).astype(np.float32)
    img = Image.fromarray(np.clip(raw * 40 + 128, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius)
    )
    return (np.asarray(img, dtype=np.float32) - 128.0) / 40.0


# --------------------------------------------------------------------------
# 1. Armor texture: woven cloth, fold lighting, violet bloom, hot neon core
# --------------------------------------------------------------------------
def build_armor(used: np.ndarray) -> tuple[Image.Image, Image.Image]:
    base = np.asarray(Image.open(ORIGINALS / "armor.png").convert("RGBA"), dtype=np.float32)
    glow = np.asarray(Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"), dtype=np.float32)

    rgb, alpha = base[..., :3], base[..., 3]
    opaque = alpha > 0
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w]

    rng = np.random.default_rng(SEED)
    fine = _blurred_noise(rng, (h, w), 0.55)
    medium = _blurred_noise(rng, (h, w), 2.4)

    # Multi-scale fabric: plain weave + diagonal twill + broad cloth folds.
    weave = np.sin(xx * np.pi / 2.0) * np.sin(yy * np.pi / 2.0)
    twill = np.sin((xx + yy) * np.pi / 3.0)
    folds = np.sin(xx * np.pi / 8.0 + np.sin(yy * np.pi / 30.0) * 0.6) * np.cos(yy * np.pi / 24.0)
    grain = weave * 3.2 + twill * 1.6 + fine * 6.0 + medium * 8.0

    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    neon_raw = np.clip((luma - 52.0) / 112.0, 0.0, 1.0)
    neon_w = neon_raw * opaque
    cloth_w = np.where(opaque, 1.0 - neon_raw, 0.0)

    out = rgb.copy()
    vertical_light = (1.0 - yy / (h - 1) - 0.5) * 22.0
    warm = np.clip((yy / (h - 1) - 0.45) / 0.55, 0.0, 1.0)[..., None]

    # Cooler indigo at the shoulders, plum/crimson shadows toward the hem.
    for channel, mul in enumerate((0.92, 0.90, 1.16)):
        out[..., channel] = rgb[..., channel] * mul + cloth_w * (
            grain + vertical_light + folds * 9.0
        )
    out[..., 0] += cloth_w * warm[..., 0] * 17.0
    out[..., 1] += cloth_w * warm[..., 0] * 2.0
    out[..., 2] += cloth_w * warm[..., 0] * 11.0

    # Soft violet bloom bleeding from the neon veins into the surrounding cloth.
    neon_core = (luma > 108) & opaque
    bloom = np.asarray(
        Image.fromarray((neon_core * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(2.3)
        ),
        dtype=np.float32,
    ) / 255.0
    halo = bloom * cloth_w
    out[..., 0] += halo * 36.0
    out[..., 1] += halo * 9.0
    out[..., 2] += halo * 48.0

    # Rim light along UV-island borders => the 126 cube faces read as real folds.
    island_edge = used & dilate(~used, 2) & opaque
    out[..., 0] += island_edge * 17.0
    out[..., 1] += island_edge * 6.0
    out[..., 2] += island_edge * 23.0

    # Crimson core / violet edge on the trim itself.
    boost = neon_w
    out[..., 0] += boost * (rgb[..., 0] * 0.34 + 32.0)
    out[..., 1] += boost * (rgb[..., 1] * 0.12 + 7.0)
    out[..., 2] += boost * (rgb[..., 2] * 0.26 + 40.0)
    hot = (luma > 176) & opaque
    out[..., 0] += hot * 42.0
    out[..., 1] += hot * 36.0
    out[..., 2] += hot * 50.0

    # GeckoLib's emissive pass reuses these very pixels, so push them harder.
    emissive = glow[..., 3] > 0
    out[..., 0] = np.where(emissive, out[..., 0] * 1.16 + 34.0, out[..., 0])
    out[..., 1] = np.where(emissive, out[..., 1] * 1.08 + 11.0, out[..., 1])
    out[..., 2] = np.where(emissive, out[..., 2] * 1.16 + 38.0, out[..., 2])

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
# 2. Cape artwork: shared by the 64x64 icon and the 128x128 3D item atlas
# --------------------------------------------------------------------------
def build_cape_artwork(s: int = 256) -> Image.Image:
    """High-resolution cape illustration with transparent background."""
    k = s / 256.0
    p = lambda x, y: (int(round(x * k)), int(round(y * k)))
    transparent = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    outline = [
        (80, 20), (176, 20), (190, 38), (203, 112), (218, 206),
        (206, 220), (190, 208), (174, 228), (158, 210), (142, 230),
        (126, 210), (110, 228), (94, 208), (78, 220), (66, 206),
        (53, 112), (66, 38),
    ]
    pts = [p(x, y) for x, y in outline]

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)

    # Vertical cloth gradient: indigo shoulders -> deep crimson hem.
    cloth = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cloth)
    for y in range(s):
        t = y / (s - 1)
        top, bottom = (20.0, 12.0, 40.0), (72.0, 10.0, 38.0)
        col = tuple(int(top[c] * (1 - t) + bottom[c] * t) for c in range(3))
        cd.line([(0, y), (s, y)], fill=col + (255,))
    cloth = Image.composite(cloth, transparent, mask)

    # Fold shading, clipped to the silhouette.
    folds = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    fd = ImageDraw.Draw(folds)
    for i, x in enumerate(range(70, 200, 16)):
        shade = 104 if i % 2 == 0 else 26
        fd.line([p(x, 26), p(x + (x - 128) * 0.32, 216)],
                fill=(shade, 14, shade, 58), width=max(1, int(9 * k)))
    fd.line([p(80, 26), p(176, 26)], fill=(150, 70, 210, 92), width=max(1, int(7 * k)))
    fd.line([p(128, 30), p(128, 214)], fill=(220, 120, 220, 40), width=max(1, int(3 * k)))
    folds = Image.composite(folds, transparent, mask)
    cloth = Image.alpha_composite(cloth, folds)

    # Shoulder yoke / Evil-Saiyan pauldrons.
    yoke = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    yd = ImageDraw.Draw(yoke)
    yd.polygon([p(*q) for q in [(48, 12), (92, 12), (98, 40), (66, 52), (50, 34)]],
               fill=(24, 13, 42, 255))
    yd.polygon([p(*q) for q in [(208, 12), (164, 12), (158, 40), (190, 52), (206, 34)]],
               fill=(24, 13, 42, 255))
    for poly in (
        [(48, 12), (92, 12), (98, 40), (66, 52), (50, 34), (48, 12)],
        [(208, 12), (164, 12), (158, 40), (190, 52), (206, 34), (208, 12)],
    ):
        yd.line([p(*q) for q in poly], fill=(168, 92, 255, 215), width=max(1, int(3 * k)))
    cloth = Image.alpha_composite(cloth, yoke)

    # Neon trim, branching veins, motes and central emblem.
    neon = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neon)
    nd.line(pts + [pts[0]], fill=(255, 66, 172, 255), width=max(1, int(6 * k)), joint="curve")
    nd.line([p(x + (128 - x) * 0.10, y + 12) for x, y in outline[2:15]],
            fill=(150, 96, 255, 175), width=max(1, int(3 * k)), joint="curve")
    nd.line([p(80, 24), p(176, 24)], fill=(255, 152, 222, 235), width=max(1, int(5 * k)))

    veins = [
        [(128, 96), (112, 128), (96, 168), (84, 204)],
        [(128, 96), (146, 130), (162, 170), (176, 206)],
        [(128, 100), (126, 142), (120, 186)],
        [(100, 120), (88, 152), (92, 190)],
        [(156, 120), (170, 154), (166, 192)],
    ]
    for v in veins:
        nd.line([p(*q) for q in v], fill=(240, 58, 140, 205),
                width=max(1, int(3 * k)), joint="curve")
    motes = [(92, 96), (106, 132), (150, 108), (164, 150), (84, 168),
             (176, 182), (112, 186), (144, 170), (128, 146), (118, 200), (140, 198)]
    for mx, my in motes:
        r = max(1, int(3 * k))
        nd.ellipse([p(mx - 3, my - 3), p(mx + 3, my + 3)], fill=(255, 96, 190, 225))
    nd.polygon([p(*q) for q in [(128, 56), (146, 82), (128, 108), (110, 82)]],
               outline=(255, 96, 190, 255), width=max(1, int(4 * k)))
    nd.ellipse([p(121, 75), p(135, 89)], fill=(242, 214, 255, 255))
    nd.ellipse([p(125, 79), p(131, 85)], fill=(255, 255, 255, 255))

    bloom = neon.filter(ImageFilter.GaussianBlur(max(2, int(7 * k))))
    bloom.putalpha(bloom.getchannel("A").point(lambda v: int(v * 0.58)))
    composed = Image.alpha_composite(cloth, bloom)
    composed = Image.alpha_composite(composed, neon)

    # Fine woven noise, only inside the silhouette.
    rng = np.random.default_rng(SEED + 1)
    noise = rng.normal(0, 7, (s, s)).astype(np.float32)
    arr = np.asarray(composed, dtype=np.float32).copy()
    inside = np.asarray(mask, dtype=bool) & (arr[..., 3] > 0)
    arr[..., :3] += noise[..., None] * inside[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def build_icon() -> Image.Image:
    """64x64 inventory icon (transparent background)."""
    return build_cape_artwork(512).resize((64, 64), Image.LANCZOS)


# --------------------------------------------------------------------------
# 3. Atlas for the folded 3D inventory model (opaque, 128x128, 5 UV strips)
# --------------------------------------------------------------------------
def build_folded_texture() -> Image.Image:
    s = 512
    yy, xx = np.mgrid[0:s, 0:s]
    t = (yy / (s - 1))[..., None]
    top = np.array([16.0, 10.0, 32.0])
    bottom = np.array([52.0, 10.0, 34.0])
    rgb = top * (1.0 - t) + bottom * t

    weave = (np.sin(xx * np.pi / 2.0) * np.sin(yy * np.pi / 2.0) * 3.0)[..., None]
    folds = (np.sin(xx * np.pi / 46.0) * 9.0 + np.cos(yy * np.pi / 80.0) * 5.0)[..., None]
    rng = np.random.default_rng(SEED + 2)
    rgb = rgb + weave + folds + rng.normal(0, 4.0, (s, s))[..., None]
    alpha = np.full((s, s, 1), 255.0)
    bg = Image.fromarray(np.dstack((np.clip(rgb, 0, 255), alpha)).astype(np.uint8), "RGBA")

    # Stretch the cape artwork horizontally so the five 3D folds sample a
    # continuous, detailed cape front rather than a narrow centred icon.
    art = build_cape_artwork(256).resize((620, 512), Image.LANCZOS)
    art = art.crop(((620 - 512) // 2, 0, (620 - 512) // 2 + 512, 512))
    out = Image.alpha_composite(bg, art)

    # Woven gold/violet yoke band and hem, plus a subtle side seam.
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, s - 1, int(9 * s / 128)], fill=(58, 26, 78, 255))
    d.line([(0, int(11 * s / 128)), (s, int(11 * s / 128))],
           fill=(196, 118, 246, 255), width=max(2, int(2 * s / 128)))
    d.rectangle([0, s - int(9 * s / 128), s - 1, s - 1], fill=(26, 8, 30, 255))
    for side in (int(1.5 * s / 128), s - int(1.5 * s / 128)):
        d.line([(side, 0), (side, s)], fill=(120, 40, 160, 255), width=max(1, int(s / 128)))

    return out.resize((SIZE, SIZE), Image.LANCZOS)


# --------------------------------------------------------------------------
# 4. Three soft ember sprites (anti-aliased, low intensity)
# --------------------------------------------------------------------------
def build_particle_sprites() -> list[Image.Image]:
    """Tres estados de brasa: núcleo cálido, destello frío y halo apagándose.

    Se generan a 64px y se reducen con Lanczos para que el sprite de 16px
    tenga antialiasing real. La intensidad es deliberadamente baja: el aura
    debe acompañar la capa, no llenar el cielo de motas.
    """
    s = 64
    out_s = 16
    yy, xx = np.mgrid[0:s, 0:s]
    c = (s - 1) / 2.0
    r2 = (xx - c) ** 2 + (yy - c) ** 2
    sprites = []

    # spread, tinte RGB, potencia del núcleo, brillo de la cruz
    frames = [
        (6.2, (1.00, 0.36, 0.78), 0.90, 0.05),
        (8.0, (0.88, 0.52, 1.00), 0.72, 0.34),
        (10.4, (0.58, 0.42, 0.96), 0.34, 0.08),
    ]

    for frame, (spread, tint, core_power, cross_power) in enumerate(frames):
        halo = np.exp(-r2 / (2.0 * (spread * 1.5) ** 2)) * 0.34
        core = np.exp(-r2 / (2.0 * (spread * 0.42) ** 2)) * core_power
        ring = (
            np.exp(-((np.sqrt(r2) - spread * 1.15) ** 2)
                   / (2.0 * (spread * 0.22) ** 2)) * 0.16
            if frame == 2 else 0.0
        )
        flare = (
            np.exp(-((xx - c) ** 2) / (2.0 * (spread * 0.14) ** 2))
            * np.exp(-((yy - c) ** 2) / (2.0 * (spread * 1.05) ** 2))
            + np.exp(-((yy - c) ** 2) / (2.0 * (spread * 0.14) ** 2))
            * np.exp(-((xx - c) ** 2) / (2.0 * (spread * 1.05) ** 2))
        ) * cross_power
        a = np.clip((halo + core + ring + flare) * 0.62, 0.0, 1.0)

        rgb = np.zeros((s, s, 3), dtype=np.float32)
        for channel, base in enumerate((72.0, 26.0, 92.0)):
            rgb[..., channel] = base + (255.0 * tint[channel] - base) * np.clip(
                core + flare * 0.5, 0.0, 1.0
            )
        img = Image.fromarray(
            np.dstack((np.clip(rgb, 0, 255), a * 255.0)).astype(np.uint8), "RGBA"
        )
        sprites.append(img.resize((out_s, out_s), Image.LANCZOS))

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
    print(f"particle sprites: {len(embers)} x {embers[0].size[0]}x{embers[0].size[1]}")

    # Sanity: glowmask must stay 128x128 and must not cover new texels.
    ga = np.asarray(Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"))[..., 3]
    gb = np.asarray(glowmask)[..., 3]
    assert (ga > 0).sum() == (gb > 0).sum(), "glowmask coverage changed - would punch holes"
    print(f"emissive texels unchanged: {(ga > 0).sum()}")
    assert np.array_equal(
        np.asarray(Image.open(ORIGINALS / "armor.png").convert("RGBA"))[..., 3],
        np.asarray(armor)[..., 3],
    ), "base alpha changed"


if __name__ == "__main__":
    main()
