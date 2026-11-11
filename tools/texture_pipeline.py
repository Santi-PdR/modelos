#!/usr/bin/env python3
"""
Procedural texture suite for the Dying Star Mantle (v1.8.0).

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

    v1.8.0 keeps the continuous 96x48 canvas and the 9x3 mosaic, but REDESIGNS
    it: a complete medallion below the yoke (it used to be cropped at the top),
    a clear double border, constellations, starfield, side sigils, a taller
    chevron hem and embroidered filigree. The new bright ink is baked into the
    base texture with bloom, while the pristine glowmask coverage stays
    byte-for-byte unchanged (1636 texels) so no holes can appear. Five tiny
    3D stars on the equipped cape reuse the original emissive UV patch.

    The 64x64 icon is NO LONGER a 96x48 canvas stretched to a square: it is a
    dedicated, correctly proportioned folded-cloak illustration with the same
    motifs. The folded 3D item uses a fitted (not distorted) canvas band, a
    readable diamond gem and a separate `cape_folded_glowmask.png` rendered
    with a pulsing eyes layer by CapaItemGlowLayer. Ember particles use three
    soft, anti-aliased 16x16 sprites.

Outputs (all committed, so CI needs no Python deps):
    textures/item/armor/capa_deteriorer_evilsaiyan.png            128x128
    textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png  128x128
    textures/item/capa_deteriorer_evilsaiyan.png                  64x64
    textures/item/cape_folded.png                                  128x128 (3D item atlas)
    textures/item/cape_folded_glowmask.png                         128x128 (efecto del item)
    textures/particle/capa_ember_0..2.png                          16x16  (custom particles)

Usage:  python tools/texture_pipeline.py     (requires Pillow + numpy)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from cloth_spec import COLUMNS, FOLDS, OPAQUE_RECTS, UV as CLOTH_UV
from fold_spec import PANELS, STRIP_OFFSETS, STRIP_WIDTHS, UV

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
# 1a. v1.5.1: one continuous high-resolution cloth illustration (96x48 UV)
# --------------------------------------------------------------------------
def build_armor_cloth_canvas(glow_alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Canvas 96x48 v1.8.0: medallón COMPLETO, bordes y constelación.

    Devuelve (RGB 96x48, tinta brillante 96x48). La tinta se usa para realzar
    el color base y para el glowmask del item, pero NO amplía la cobertura
    emisiva del atlas de armadura: el glowmask prístino sigue intacto.
    """
    cw = int(CLOTH_UV["cloth"]["uv_size"][0])  # 96
    ch = int(CLOTH_UV["cloth"]["uv_size"][1])  # 48
    scale = 8
    w, h = cw * scale, ch * scale
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / float(w - 1)
    v = yy / float(h - 1)
    rng = np.random.default_rng(SEED + 11)

    top = np.array([29.0, 14.0, 54.0], dtype=np.float32)
    bottom = np.array([82.0, 13.0, 48.0], dtype=np.float32)
    base = top * (1.0 - v[..., None]) + bottom * v[..., None]
    fold_phase = u * FOLDS + 0.02 * np.sin(v * np.pi * 1.5)
    wave = np.cos(2.0 * np.pi * fold_phase)
    fold_light = np.power(np.clip(0.5 + 0.5 * wave, 0.0, 1.0), 1.15)
    crease = np.exp(-((np.mod(fold_phase, 1.0) - 0.5) ** 2) / (2.0 * 0.11 ** 2))
    radial = np.exp(-(((u - 0.5) / 0.34) ** 2 + ((v - 0.38) / 0.46) ** 2) * 1.4)
    vignette = np.exp(-((u - 0.02) / 0.06) ** 2) + np.exp(-((u - 0.98) / 0.06) ** 2)
    weave = (np.sin(xx * np.pi / 3.0) * np.sin(yy * np.pi / 3.0) * 1.3
             + np.sin((xx + yy) * np.pi / 5.0) * 0.7)
    twill = np.sin((xx * 0.55 - yy * 0.32) * np.pi / 7.0) * 1.6
    grain = rng.normal(0.0, 1.4, (h, w)).astype(np.float32)
    drape = np.power(1.0 - v, 1.4)[..., None] * np.array([10.0, 3.0, 14.0])
    rgb = base + drape
    rgb += (fold_light[..., None] - 0.5) * np.array([10.0, 4.0, 14.0])
    rgb -= crease[..., None] * np.array([9.0, 3.0, 11.0])
    rgb += radial[..., None] * np.array([44.0, 11.0, 54.0])
    rgb -= vignette[..., None] * np.array([18.0, 6.0, 18.0])
    rgb += (weave + twill + grain)[..., None] * np.array([0.7, 0.5, 0.9])

    # Campo de estrellas tenue, determinista y sin ruido de un solo texel.
    for _ in range(46):
        sx = float(rng.uniform(2.0, 94.0))
        sy = float(rng.uniform(8.5, 41.5))
        if abs(sx - 48.0) < 13.0 and sy < 31.0:
            continue
        sr = float(rng.uniform(0.22, 0.45))
        rgb[int(sy * scale), int(sx * scale)] += np.array([18.0, 6.0, 22.0])

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    glow_ink = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow_ink)
    p = lambda x, y: (int(round(x * scale)), int(round(y * scale)))

    def line(pts, fill, width, glow=0):
        coords = [p(*q) for q in pts]
        wpx = max(1, int(width * scale))
        d.line(coords, fill=fill, width=wpx, joint="curve")
        if glow:
            gd.line(coords, fill=glow, width=max(1, int(wpx * 0.8)))

    def ellipse(box, fill, width=0, glow=0):
        coords = [p(box[0], box[1]), p(box[2], box[3])]
        if width:
            d.ellipse(coords, outline=fill, width=max(1, int(width * scale)))
        else:
            d.ellipse(coords, fill=fill)
        if glow:
            gd.ellipse(coords, fill=glow)

    # 1. Yugo: banda superior que YA NO tapa el medallón.
    d.polygon([p(*q) for q in [(1, 1), (95, 1), (91, 7), (5, 7)]],
              fill=(26, 13, 48, 255))
    line([(1, 6.8), (95, 6.8)], (190, 140, 210, 190), 0.8, 100)
    line([(4, 2), (18, 6)], (232, 176, 112, 190), 0.6)
    line([(92, 2), (78, 6)], (232, 176, 112, 190), 0.6)
    for j in range(38):
        x = 2.0 + j * 92.0 / 37.0
        ellipse((x - 0.30, 6.45, x + 0.30, 7.05), (255, 214, 246, 150))

    # 2. Doble ribete perimetral: la tela deja de parecer "recortada".
    border = [(1.6, 7.6), (94.4, 7.6), (94.4, 42.0), (1.6, 42.0)]
    line(border + [border[0]], (180, 130, 100, 170), 0.7, 90)
    inner_border = [(3.1, 9.1), (92.9, 9.1), (92.9, 40.5), (3.1, 40.5)]
    line(inner_border + [inner_border[0]], (220, 96, 180, 180), 0.8, 120)

    # 3. Medallón COMPLETO, centrado a v=18.5 (antes a v=14 y lo cortaba
    #    el yugo). Tres anillos, diamante, engarces y núcleo blanco.
    cx, cy = 48.0, 18.5
    for r, col, width, glow in ((10.8, (176, 96, 220, 190), 1.0, 140),
                                (8.0, (248, 104, 196, 225), 0.9, 190),
                                (4.6, (255, 196, 240, 205), 0.7, 160)):
        d.ellipse([p(cx - r, cy - r), p(cx + r, cy + r)],
                  outline=col, width=max(1, int(width * scale)))
        gd.ellipse([p(cx - r, cy - r), p(cx + r, cy + r)],
                   outline=glow, width=max(1, int(width * scale * 0.7)))
    diamond = [(cx, 8.0), (cx + 10.5, cy), (cx, 29.0), (cx - 10.5, cy)]
    d.polygon([p(*q) for q in diamond], fill=(40, 12, 56, 235))
    line(diamond + [diamond[0]], (255, 118, 208, 250), 1.3, 210)
    inner = [(cx, 12.5), (cx + 5.5, cy), (cx, 24.5), (cx - 5.5, cy)]
    line(inner + [inner[0]], (238, 200, 255, 230), 0.8, 150)
    ellipse((cx - 2.0, cy - 2.2, cx + 2.0, cy + 2.2),
            (255, 248, 255, 255), glow=255)
    for gx, gy in diamond:
        ellipse((gx - 0.85, gy - 0.85, gx + 0.85, gy + 0.85),
                (255, 236, 252, 235), glow=200)

    # 4. Constelación y filigrana: líneas delgadas que brillan, no costuras.
    stars = [(18, 18), (78, 18), (26, 35), (70, 35), (48, 30)]
    line([(48, 29.0), (48, 41.5)], (238, 92, 192, 220), 1.0, 175)
    for path in (
        [(48, 29.0), (34, 33), (22, 41.0)],
        [(48, 29.0), (62, 33), (74, 41.0)],
        [(22, 27), (31, 34), (38, 41.0)],
        [(74, 27), (65, 34), (58, 41.0)],
        [(18, 18), (30, 22), (48, 29.0)],
        [(78, 18), (66, 22), (48, 29.0)],
        [(26, 35), (38, 33), (48, 29.0)],
        [(70, 35), (58, 33), (48, 29.0)],
    ):
        line(path, (172, 72, 202, 185), 0.8, 120)
    for mx, my in stars:
        ellipse((mx - 0.9, my - 0.9, mx + 0.9, my + 0.9),
                (255, 146, 216, 220), glow=220)
        line([(mx - 1.6, my), (mx + 1.6, my)], (255, 198, 240, 150), 0.35, 110)
        line([(mx, my - 1.6), (mx, my + 1.6)], (255, 198, 240, 150), 0.35, 110)

    # 5. Sigilos laterales: dan detalle sin dibujar líneas de columna.
    for sx, sy in ((8, 12), (88, 12), (8, 26), (88, 26), (8, 38), (88, 38)):
        sig = [(sx, sy - 1.6), (sx + 1.6, sy), (sx, sy + 1.6), (sx - 1.6, sy)]
        line(sig + [sig[0]], (176, 96, 220, 170), 0.5, 90)
        ellipse((sx - 0.35, sy - 0.35, sx + 0.35, sy + 0.35),
                (255, 210, 244, 190), glow=140)

    # 6. Desgaste "deteriorer": rozaduras discretas en bordes y tercio inferior.
    for _ in range(110):
        wx = float(rng.uniform(1.0, 95.0))
        wy = float(rng.uniform(7.5, 41.5))
        edge = max(0.0, 1.0 - min(wx, 96.0 - wx) / 12.0)
        low = max(0.0, (wy - 27.0) / 14.0)
        if rng.random() > min(1.0, 0.10 + 0.40 * low + 0.26 * edge):
            continue
        rad = float(rng.uniform(0.40, 0.70))
        col = ((228, 170, 216, 46) if rng.random() < 0.45
               else (16, 5, 24, 56))
        ellipse((wx - rad, wy - rad, wx + rad, wy + rad), col)

    # 7. Dobladillo más alto (v=42..48) con chevron y pespuntes.
    d.rectangle([p(1, 42), p(95, 47.9)], fill=(26, 8, 36, 255))
    chevron = [(1.0 + i * 94.0 / COLUMNS, 42.8 + (1.8 if i % 2 else 0.0))
               for i in range(COLUMNS + 1)]
    line(chevron, (180, 80, 160, 180), 0.9, 110)
    line([(1, 42.2), (95, 42.2)], (190, 140, 210, 180), 0.7, 90)
    for i in range(COLUMNS):
        x = 2.0 + i * 92.0 / COLUMNS
        line([(x, 47.7), (x + 1.6, 42.6)], (126, 52, 164, 120), 0.4)

    img = Image.alpha_composite(img, overlay)

    # Tinta brillante: bloom + realce en el color base. No toca el glowmask.
    ink = np.asarray(glow_ink, dtype=np.float32) / 255.0
    blur = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(2.0 * scale)
        ), dtype=np.float32
    ) / 255.0
    arr = np.asarray(img, dtype=np.float32).copy()
    arr[..., :3] += blur[..., None] * np.array([14.0, 3.0, 18.0])
    arr[..., :3] += ink[..., None] * np.array([28.0, 10.0, 34.0])

    # Cobertura emisiva original intacta; sólo tiñe el material.
    em = Image.fromarray(
        np.clip(glow_alpha[0:ch, 0:cw], 0, 255).astype(np.uint8)
    ).resize((w, h), Image.LANCZOS)
    halo = em.filter(ImageFilter.GaussianBlur(2.0 * scale))
    halo_arr = np.asarray(halo, dtype=np.float32) / 255.0
    arr[..., :3] += halo_arr[..., None] * np.array([12.0, 3.0, 16.0])
    em_arr = np.asarray(em, dtype=np.float32) / 255.0
    hot = np.array([150.0, 60.0, 150.0])
    arr[..., :3] = (arr[..., :3] * (1.0 - em_arr[..., None] * 0.12)
                    + hot * em_arr[..., None] * 0.12)
    final = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    rgb_small = np.asarray(final.resize((cw, ch), Image.LANCZOS).convert("RGB"),
                           dtype=np.float32)
    glow_small = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8)).resize(
            (cw, ch), Image.LANCZOS
        ), dtype=np.float32
    ) / 255.0
    return rgb_small, glow_small


def paint_reserved_cloth_strips(out: np.ndarray, glow_alpha: np.ndarray) -> np.ndarray:
    """Creases, forro, ribete y zona emisiva en rectángulos ya opacos."""
    y = np.arange(128, dtype=np.float32).reshape(128, 1, 1) / 127.0
    # v1.5.1: contraste de crease reducido. En v1.5.0 las 36 creases leían
    # como un código de barras; ahora acompañan al sombreado del canvas.
    out[:, 105:107, :3] = np.array([34.0, 14.0, 48.0]) + y * np.array([6.0, 2.0, 8.0])
    out[:, 107:109, :3] = np.array([66.0, 30.0, 94.0]) + y * np.array([10.0, 3.0, 14.0])
    out[:, 120:122, :3] = np.array([18.0, 8.0, 30.0]) + y * np.array([10.0, 2.0, 10.0])
    out[:, 122:124, :3] = np.array([120.0, 52.0, 172.0]) + y * np.array([48.0, 16.0, 58.0])

    em = glow_alpha[109:127, 69:75] > 0
    bright = out[109:127, 69:75, :3]
    bright[...] = np.array([46.0, 10.0, 44.0])
    bright[em] = np.array([255.0, 94.0, 196.0])

    yoke = out[76:93, 57:71, :3]
    yoke[...] = yoke * 0.72 + np.array([24.0, 14.0, 34.0])
    yoke[glow_alpha[76:93, 57:71] > 0] = np.array([238.0, 116.0, 220.0])
    return out


def assert_cloth_uvs() -> None:
    """Ninguna UV v1.5.1 puede samplear un texel transparente."""
    geometry = json.loads(GEO.read_text())["minecraft:geometry"][0]
    checked = 0
    for bone in geometry.get("bones", []):
        if not bone["name"].startswith("v15_"):
            continue
        for cube_spec in bone.get("cubes", []):
            for face in cube_spec["uv"].values():
                u, v = face["uv"]
                width, height = face["uv_size"]
                assert width > 0 and height > 0, face
                assert 0 <= u and 0 <= v and u + width <= 128 and v + height <= 128, face
                assert any(
                    u >= x0 and v >= y0 and u + width <= x1 and v + height <= y1
                    for x0, y0, x1, y1 in OPAQUE_RECTS
                ), f"UV nueva fuera de zona opaca: {face}"
                checked += 1
    assert checked > 250, checked
    print(f"v1.5.1 cloth UV faces checked: {checked}")


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

    # v1.5.1: sustituimos el mosaico de tres paneles cuadrados por UNA sola
    # ilustración de tela. Se pinta después de los realces previos para que el
    # atlas nuevo no herede las costuras del UV antiguo.
    canvas, canvas_glow = build_armor_cloth_canvas(glow[..., 3])
    out[0:48, 0:96, :] = canvas
    # La tinta nueva del bordado ya venía realzada; un bloom suave extra hace
    # que constelación y medallón se lean incluso de noche, SIN tocar el alpha
    # del glowmask prístino (no se abren huecos en la tela).
    soft = Image.fromarray(
        (np.clip(canvas_glow, 0, 1) * 255).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(1.2))
    soft_arr = np.asarray(soft, dtype=np.float32) / 255.0
    out[0:48, 0:96, :3] += soft_arr[..., None] * np.array([8.0, 2.0, 12.0])
    out = paint_reserved_cloth_strips(out, glow[..., 3])

    out = np.clip(out, 0, 255)
    out = np.where(opaque[..., None], out, rgb)  # never paint into transparent texels
    armor = np.dstack((out, alpha)).astype(np.uint8)

    # Glowmask: only alpha matters to GeckoLib, and only existing pixels may
    # stay lit (growing it would erase more base pixels => holes in the cape).
    ga = glow[..., 3]
    new_alpha = np.where(ga > 0, np.clip(ga * 1.10 + 14.0, 0, 255), 0)
    grgb = np.clip(glow[..., :3] * 1.18 + 18.0, 0, 255)
    # El color del glowmask no importa para GeckoLib, pero lo dejamos coherente
    # con el núcleo rosa del canvas; la cobertura (ga > 0) NO cambia.
    grgb[0:48, 0:96] = np.where(
        (ga[0:48, 0:96] > 0)[..., None],
        np.array([150.0, 60.0, 150.0]),
        grgb[0:48, 0:96],
    )
    glowmask = np.dstack((grgb, new_alpha)).astype(np.uint8)

    return Image.fromarray(armor, "RGBA"), Image.fromarray(glowmask, "RGBA")


# --------------------------------------------------------------------------
# 2. Cape artwork: shared by the 64x64 icon and the 128x128 3D item atlas
# --------------------------------------------------------------------------
def cloth_canvas_fitted(w: int, h: int) -> tuple[Image.Image, Image.Image]:
    """Canvas 96x48 encajado SIN distorsión en un rectángulo `w x h`.

    v1.8.0: el icono y el atlas plegado ya no estiran el canvas 2:1 a un
    cuadrado. Se conserva la proporción, se centra y el resto se rellena con
    el mismo degradado de la tela. Devuelve también la tinta brillante para
    construir el glowmask del item.
    """
    glow = np.asarray(
        Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"),
        dtype=np.float32,
    )
    rgb, ink_small = build_armor_cloth_canvas(glow[..., 3])
    canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    ink = Image.fromarray((np.clip(ink_small, 0, 1) * 255).astype(np.uint8), "L")
    cw, ch = canvas.size
    scale = min(w / float(cw), h / float(ch))
    fw, fh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    fitted = canvas.resize((fw, fh), Image.LANCZOS)
    fitted_ink = ink.resize((fw, fh), Image.LANCZOS)
    px, py = (w - fw) // 2, (h - fh) // 2

    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    top = np.array([18.0, 10.0, 36.0], dtype=np.float32)
    bottom = np.array([58.0, 12.0, 40.0], dtype=np.float32)
    bg = np.repeat(top * (1.0 - yy) + bottom * yy, w, axis=1)
    out = Image.fromarray(
        np.dstack((bg, np.full((h, w, 1), 255.0, dtype=np.float32))).astype(np.uint8),
        "RGBA",
    )
    out.alpha_composite(fitted, (px, py))

    glow_out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ink_rgba = Image.new("RGBA", (fw, fh), (255, 120, 210, 0))
    ink_rgba.putalpha(fitted_ink)
    glow_out.alpha_composite(ink_rgba, (px, py))
    return out, glow_out


def build_icon_artwork(s: int = 512) -> Image.Image:
    """Icono 64x64 v1.8.0: capa doblada con proporción CORRECTA.

    Antes se estiraba el canvas 96x48 a 512x512: el medallón se deformaba y
    la silueta parecía recortada. Aquí se dibuja una prenda alta desde cero
    con los mismos motivos (medallón, filigrana, constelación, chevron,
    doble ribete) y un halo suave, sin distorsión.
    """
    k = s / 512.0
    p = lambda x, y: (int(round(x * k)), int(round(y * k)))
    outline = [
        (128, 40), (384, 40), (414, 74), (438, 190), (452, 402),
        (424, 436), (392, 416), (360, 446), (328, 416), (296, 450),
        (264, 416), (232, 450), (200, 416), (168, 446), (136, 416),
        (104, 436), (76, 402), (90, 190), (114, 74),
    ]
    pts = [p(*q) for q in outline]
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    transparent = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # Halo exterior: el item "respira" incluso en un slot oscuro.
    halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(halo).polygon(pts, fill=(214, 70, 184, 150))
    halo = halo.filter(ImageFilter.GaussianBlur(max(2, int(16 * k))))

    yy = np.linspace(0.0, 1.0, s, dtype=np.float32)[:, None, None]
    xx = np.linspace(0.0, 1.0, s, dtype=np.float32)[None, :, None]
    top = np.array([24.0, 12.0, 46.0], dtype=np.float32)
    bottom = np.array([78.0, 14.0, 46.0], dtype=np.float32)
    grad = np.repeat(top * (1.0 - yy) + bottom * yy, s, axis=1)
    wave = np.cos(2.0 * np.pi * FOLDS * xx)
    grad *= (1.0 + 0.10 * wave)
    weave = (np.sin(np.arange(s, dtype=np.float32)[None, :] * np.pi / 3.0)
             * np.sin(np.arange(s, dtype=np.float32)[:, None] * np.pi / 3.0))
    grad += weave[..., None] * np.array([0.7, 0.4, 0.9])
    cx, cy = 0.5 * s, 0.30 * s
    radial = np.exp(-(((np.arange(s, dtype=np.float32)[None, :] - cx) / (0.30 * s)) ** 2
                      + ((np.arange(s, dtype=np.float32)[:, None] - cy) / (0.36 * s)) ** 2) * 1.3)
    grad += radial[..., None] * np.array([34.0, 8.0, 42.0])
    cloth = Image.fromarray(
        np.dstack((np.clip(grad, 0, 255), np.full((s, s, 1), 255.0, dtype=np.float32))).astype(np.uint8),
        "RGBA",
    )
    cloth = Image.composite(cloth, transparent, mask)

    overlay = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Yugo y doble ribete.
    d.polygon([p(*q) for q in [(128, 40), (384, 40), (400, 78), (112, 78)]],
              fill=(28, 14, 50, 255))
    d.line([p(112, 78), p(400, 78)], fill=(214, 158, 232, 235),
           width=max(1, int(2.0 * k)))
    inner = [(256 + (x - 256) * 0.94, 256 + (y - 256) * 0.94) for x, y in outline]
    d.line([p(*q) for q in outline + [outline[0]]], fill=(214, 158, 116, 220),
           width=max(1, int(1.8 * k)), joint="curve")
    d.line([p(*q) for q in inner + [inner[0]]], fill=(255, 112, 202, 225),
           width=max(1, int(2.2 * k)), joint="curve")
    # Pespuntes.
    for a, b in zip(pts, pts[1:] + pts[:1]):
        dist = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        steps = max(1, int(dist / max(2.0, 12.0 * k)))
        for j in range(steps + 1):
            t = j / float(steps)
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            r = max(1, int(1.4 * k))
            d.ellipse([int(x - r), int(y - r), int(x + r), int(y + r)],
                      fill=(255, 218, 246, 150))

    # Medallón completo, tres anillos, diamante y núcleo.
    mx, my = 256, 150
    for r, col, width in ((54, (176, 96, 220, 190), 2.4),
                          (40, (255, 106, 196, 225), 2.6),
                          (23, (246, 222, 255, 210), 2.0)):
        d.ellipse([p(mx - r, my - r), p(mx + r, my + r)],
                  outline=col, width=max(1, int(width * k)))
    diamond = [(mx, 96), (mx + 53, my), (mx, 204), (mx - 53, my)]
    d.polygon([p(*q) for q in diamond], fill=(40, 12, 56, 235))
    d.line([p(*q) for q in diamond + [diamond[0]]], fill=(255, 118, 208, 250),
           width=max(1, int(2.6 * k)))
    d.ellipse([p(mx - 10, my - 11), p(mx + 10, my + 11)],
              fill=(255, 248, 255, 255))
    for gx, gy in diamond:
        d.ellipse([p(gx - 4, gy - 4), p(gx + 4, gy + 4)],
                  fill=(255, 236, 252, 235))

    # Filigrana y constelación.
    for path in (
        [(256, 204), (256, 396)],
        [(256, 204), (170, 280), (112, 388)],
        [(256, 204), (342, 280), (400, 388)],
        [(150, 250), (200, 320), (256, 396)],
        [(362, 250), (312, 320), (256, 396)],
        [(150, 250), (256, 204), (362, 250)],
        [(112, 340), (200, 300), (256, 204)],
        [(400, 340), (312, 300), (256, 204)],
    ):
        d.line([p(*q) for q in path], fill=(190, 86, 208, 190),
               width=max(1, int(1.8 * k)), joint="curve")
    stars = [(150, 250), (362, 250), (200, 320), (312, 320), (256, 270)]
    for sx, sy in stars:
        r = max(1, int(4 * k))
        d.ellipse([p(sx - r, sy - r), p(sx + r, sy + r)],
                  fill=(255, 146, 216, 225))
        d.line([p(sx - 8, sy), p(sx + 8, sy)], fill=(255, 198, 240, 170),
               width=max(1, int(1.2 * k)))
        d.line([p(sx, sy - 8), p(sx, sy + 8)], fill=(255, 198, 240, 170),
               width=max(1, int(1.2 * k)))
    rng = np.random.default_rng(SEED + 7)
    for _ in range(70):
        sx, sy = float(rng.uniform(100, 412)), float(rng.uniform(90, 400))
        if (sx - mx) ** 2 + (sy - my) ** 2 < 70 ** 2:
            continue
        r = max(1, int(1.2 * k))
        d.ellipse([p(sx - r, sy - r), p(sx + r, sy + r)],
                  fill=(226, 156, 238, 110))

    # Chevron inferior.
    chevron = [(76, 402), (112, 418), (152, 402), (192, 422), (232, 402),
               (272, 424), (312, 402), (352, 422), (392, 402), (428, 418),
               (452, 402)]
    d.line([p(*q) for q in chevron], fill=(214, 108, 226, 210),
           width=max(1, int(2.0 * k)), joint="curve")

    overlay = Image.composite(overlay, transparent, mask)
    out = Image.alpha_composite(halo, cloth)
    out = Image.alpha_composite(out, overlay)
    # Borde oscuro de 1 px para que la silueta no se pierda sobre el slot.
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask)
    rim = Image.new("RGBA", (s, s), (236, 116, 214, 255))
    rim.putalpha(edge.point(lambda a: min(255, int(a * 0.8))))
    return Image.alpha_composite(out, rim)


def build_icon() -> Image.Image:
    return build_icon_artwork(512).resize((64, 64), Image.LANCZOS)


def build_folded_texture() -> tuple[Image.Image, Image.Image]:
    """Atlas 128x128 del bulto plegado + glowmask para CapaItemGlowLayer.

    El canvas va en una banda central con su proporción real (no estirado),
    las siete franjas siguen reconstruyendo la ilustración y el sombreado por
    pliegue les da volumen. `gem`, `roll`, yugo, dobladillo y columnas
    reservadas se pintan aparte. El glowmask marca SOLO la tinta brillante,
    el broche, los nervios y los ribetes.
    """
    s = 512
    body0, body1 = int(10 * s / 128), int(118 * s / 128)
    art, ink = cloth_canvas_fitted(int(120 * s / 128), s)
    bg = Image.new("RGBA", (s, s), (20, 9, 34, 255))
    out = bg.copy()
    out.alpha_composite(art, (0, 0))
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow.alpha_composite(ink, (0, 0))

    arr = np.asarray(out, dtype=np.float32).copy()
    for panel, offset, width in zip(PANELS, STRIP_OFFSETS, STRIP_WIDTHS):
        x0, x1 = int(offset * s / 128), int((offset + width) * s / 128)
        if x1 <= x0:
            continue
        local = np.linspace(0.0, 1.0, x1 - x0, dtype=np.float32)[None, :, None]
        ridge = np.power(np.clip(np.sin(local * np.pi), 0.0, 1.0), 0.65)
        vertical = np.linspace(1.05, 0.88, body1 - body0, dtype=np.float32)[:, None, None]
        shade = (0.72 + 0.18 * panel["bulge"] + 0.20 * ridge) * vertical
        arr[body0:body1, x0:x1, :3] *= shade
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(out)
    gd = ImageDraw.Draw(glow)

    # Nervios entre franjas: sombra + realce, y realce en el glowmask.
    # Nervios: sombra fina y realce apagado. En v1.8.0 inicial parecían una
    # reja; ahora acompañan al relieve sin robarle el protagonismo al paño.
    for boundary in STRIP_OFFSETS[1:]:
        x = int(boundary * s / 128)
        d.line([(x, body0), (x, body1)], fill=(14, 5, 22, 220), width=2)
        d.line([(x + 2, body0), (x + 2, body1)], fill=(84, 38, 128, 210), width=1)
        gd.line([(x + 2, body0), (x + 2, body1)], fill=(150, 70, 200, 130), width=1)

    # Tres pliegues HORIZONTALES suaves que cruzan las 7 franjas: refuerzan
    # la lectura de "capa doblada" sin partir la ilustración en costuras.
    for frac in (0.24, 0.52, 0.80):
        fy = body0 + int((body1 - body0) * frac)
        d.line([(0, fy), (int(120 * s / 128), fy)],
               fill=(34, 14, 52, 150), width=max(2, int(2 * s / 128)))
        d.line([(0, fy + 2), (int(120 * s / 128), fy + 2)],
               fill=(118, 54, 164, 95), width=1)

    # Yugo y dobladillo tejidos, más sobrios.
    d.rectangle([0, 0, s - 1, int(9 * s / 128)], fill=(46, 22, 66, 255))
    d.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
           fill=(156, 96, 206, 255), width=max(2, int(2 * s / 128)))
    gd.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
            fill=(180, 110, 220, 170), width=max(2, int(2 * s / 128)))
    d.rectangle([0, s - int(9 * s / 128), s - 1, s - 1], fill=(26, 8, 30, 255))
    d.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
           fill=(128, 54, 172, 255), width=max(1, int(s / 128)))
    gd.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
            fill=(180, 80, 210, 150), width=max(1, int(s / 128)))

    # Tres rollos de tela en la región reservada `roll`.
    rx0, ry0 = int(96 * s / 128), int(48 * s / 128)
    rx1, ry1 = int(120 * s / 128), int(64 * s / 128)
    d.rectangle([rx0, ry0, rx1, ry1], fill=(30, 12, 46, 255))
    for j in range(3):
        ly = ry0 + int((j + 0.5) * (ry1 - ry0) / 3.0)
        d.line([(rx0, ly), (rx1, ly)], fill=(150, 72, 198, 220),
               width=max(1, int(0.8 * s / 128)))
        gd.line([(rx0, ly), (rx1, ly)], fill=(190, 90, 230, 150),
                width=max(1, int(0.8 * s / 128)))

    # Caras laterales (`edge`): neutro, para que no brillen.
    ex0, ey0 = int(96 * s / 128), int(64 * s / 128)
    ex1, ey1 = int(106 * s / 128), int(72 * s / 128)
    d.rectangle([ex0, ey0, ex1, ey1], fill=(22, 10, 34, 255))

    # Gema del broche: diamante con núcleo blanco, muy legible en la mano.
    gx0, gy0 = int(54 * s / 128), int(30 * s / 128)
    gx1, gy1 = int(74 * s / 128), int(52 * s / 128)
    cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    half = min(gx1 - gx0, gy1 - gy0) // 2 - 4
    d.rectangle([gx0, gy0, gx1, gy1], fill=(24, 10, 40, 255))
    diamond = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
    d.polygon(diamond, fill=(60, 18, 72, 255))
    d.line(diamond + [diamond[0]], fill=(255, 120, 210, 255),
           width=max(2, int(1.2 * s / 128)))
    inner = [(cx, cy - half // 2), (cx + half // 2, cy),
             (cx, cy + half // 2), (cx - half // 2, cy)]
    d.line(inner + [inner[0]], fill=(255, 210, 250, 255),
           width=max(1, int(0.8 * s / 128)))
    core = max(2, int(3 * s / 128))
    d.ellipse([cx - core, cy - core, cx + core, cy + core],
              fill=(255, 255, 255, 255))
    gd.polygon(diamond, fill=(255, 90, 200, 210))
    gd.line(diamond + [diamond[0]], fill=(255, 180, 240, 255),
            width=max(2, int(1.2 * s / 128)))
    gd.ellipse([cx - core, cy - core, cx + core, cy + core],
               fill=(255, 255, 255, 255))

    # Columnas reservadas: forro oscuro y ribete violeta/neón.
    arr = np.asarray(out, dtype=np.float32).copy()
    t = (np.arange(s, dtype=np.float32).reshape(s, 1, 1) / (s - 1))
    lining0, piping0 = int(120 * s / 128), int(124 * s / 128)
    arr[:, lining0:piping0, :3] = np.array([20.0, 8.0, 30.0])
    glow_col = np.array([142.0, 62.0, 186.0]) * (0.72 + 0.28 * t)
    arr[:, piping0:s, :3] = np.clip(glow_col, 0, 255)
    arr[:, lining0:s, 3] = 255.0
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    atlas = out.resize((SIZE, SIZE), Image.LANCZOS)
    glowmask = glow.resize((SIZE, SIZE), Image.LANCZOS)
    return atlas, glowmask


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
    assert_cloth_uvs()
    used = uv_usage_mask()
    print(f"UV texels used by geometry: {used.mean() * 100:.1f}%")

    armor, glowmask = build_armor(used)
    armor.save(ARMOR_DIR / "capa_deteriorer_evilsaiyan.png")
    glowmask.save(ARMOR_DIR / "capa_deteriorer_evilsaiyan_glowmask.png")
    print("armor:", armor.size, "glowmask:", glowmask.size)

    icon = build_icon()
    icon.save(ICON)
    print("icon:", icon.size)

    folded, folded_glow = build_folded_texture()
    folded.save(ASSETS / "textures/item/cape_folded.png")
    folded_glow.save(ASSETS / "textures/item/cape_folded_glowmask.png")
    print("folded atlas:", folded.size, "glowmask:", folded_glow.size)

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

    # El glowmask del item es NUEVO y no modifica el atlas de armadura.
    fg = np.asarray(folded_glow)[..., 3]
    assert folded_glow.size == (SIZE, SIZE), folded_glow.size
    assert 0 < (fg > 0).sum() < SIZE * SIZE, "glowmask del item vacío o total"
    print(f"folded glowmask texels: {(fg > 0).sum()}")


if __name__ == "__main__":
    main()
