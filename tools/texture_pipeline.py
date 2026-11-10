#!/usr/bin/env python3
"""
Procedural texture suite for the "Capa Deteriorer Evil Saiyan" (v1.6.0).

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

    v1.6.0 paints ONE 96x48 cloth illustration into a fully opaque corner of
    the atlas and maps it onto a single 9x3 rectangle (27 panels) that spans
    the whole cape, so no section is stretched or cut. There are no painted
    seam lines: the folds are shading and gentle Z relief. Reserved columns
    supply dark creases, violet rim lights, lining and piping. The pristine
    neon-line glowmask is kept, with a soft bloom. Alpha and emissive texel
    count are still unchanged.

    The icon and the folded 3D item model sample THAT SAME canvas, so the
    medallion, filigree and hem match the equipped cape. The folded atlas is
    split into seven continuous UV strips with baked per-fold shading,
    stitching and reserved piping columns. Ember particles use three soft,
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
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from cloth_spec import COLUMNS, OPAQUE_RECTS, UV as CLOTH_UV
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
def build_armor_cloth_canvas(glow_alpha: np.ndarray) -> np.ndarray:
    """Pinta un material de tela legible a 96x48 texels, no un mosaico.

    Se dibuja a 8x con líneas de al menos ~1 texel de grosor y se reduce con
    Lanczos. A la resolución real de Minecraft eso importa más que el detalle
    sub-texel: pliegues anchos, ribetes gruesos, medallón grande y dobladillo
    en chevron. El glowmask prístino se conserva pero apenas tiñe el material.
    """
    cw = int(CLOTH_UV["cloth"]["uv_size"][0])  # 96
    ch = int(CLOTH_UV["cloth"]["uv_size"][1])  # 48
    scale = 8
    w, h = cw * scale, ch * scale
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / float(w - 1)
    v = yy / float(h - 1)
    rng = np.random.default_rng(SEED + 11)

    # v1.6.0: material algo más claro. En el juego la capa va en la espalda,
    # con menos luz que en un preview; un púrpura demasiado negro pierde el
    # medallón y la filigrana. Sigue siendo la misma gama Evil-Saiyan.
    top = np.array([29.0, 14.0, 54.0], dtype=np.float32)
    bottom = np.array([82.0, 13.0, 48.0], dtype=np.float32)
    base = top * (1.0 - v[..., None]) + bottom * v[..., None]

    fold_phase = u * COLUMNS + 0.04 * np.sin(v * np.pi * 1.5)
    fold_light = np.power(np.clip(0.5 + 0.5 * np.sin(2.0 * np.pi * fold_phase), 0.0, 1.0), 1.2)
    crease = np.exp(-((np.mod(fold_phase, 1.0) - 0.5) ** 2) / (2.0 * 0.08 ** 2))
    radial = np.exp(-(((u - 0.5) / 0.30) ** 2 + ((v - 0.30) / 0.42) ** 2) * 1.4)
    vignette = np.exp(-((u - 0.02) / 0.06) ** 2) + np.exp(-((u - 0.98) / 0.06) ** 2)
    weave = (np.sin(xx * np.pi / 3.0) * np.sin(yy * np.pi / 3.0) * 1.3
             + np.sin((xx + yy) * np.pi / 5.0) * 0.7)
    twill = np.sin((xx * 0.55 - yy * 0.32) * np.pi / 7.0) * 1.6
    grain = rng.normal(0.0, 1.4, (h, w)).astype(np.float32)
    # Luz cenital suave: la tela se aclara en los hombros y se asienta en el
    # dobladillo. Es un degradado continuo, no una raya por sección.
    drape = np.power(1.0 - v, 1.4)[..., None] * np.array([10.0, 3.0, 14.0])
    rgb = base + drape
    rgb += (fold_light[..., None] - 0.5) * np.array([10.0, 4.0, 14.0])
    rgb -= crease[..., None] * np.array([9.0, 3.0, 11.0])
    rgb += radial[..., None] * np.array([44.0, 11.0, 54.0])
    rgb -= vignette[..., None] * np.array([18.0, 6.0, 18.0])
    rgb += (weave + twill + grain)[..., None] * np.array([0.7, 0.5, 0.9])

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    p = lambda x, y: (int(round(x * scale)), int(round(y * scale)))
    line = lambda pts, fill, width: d.line([p(*q) for q in pts], fill=fill,
                                          width=max(1, int(width * scale)), joint="curve")

    # Yugo y ribetes: líneas de ~1 texel, no filamentos que desaparecen al
    # reducir la ilustración al atlas real.
    d.polygon([p(*q) for q in [(1, 1), (95, 1), (91, 6), (5, 6)]],
              fill=(26, 13, 48, 255))
    line([(1, 5.6), (95, 5.6)], (180, 106, 220, 235), 1.0)
    line([(4, 2), (18, 6)], (232, 176, 112, 190), 0.6)
    line([(92, 2), (78, 6)], (232, 176, 112, 190), 0.6)

    # v1.6.0: SIN líneas horizontales ni de columna. Cualquier raya dibujada
    # aquí se convierte en una costura visible entre paneles del mosaico; los
    # pliegues ya los aportan fold_light/crease y el relieve 3D suave en Z.
    # SECTION_V sigue siendo la división UV, no una costura pintada.

    for x, inward in ((1.5, 0.06), (94.5, -0.06)):
        line([(x, 6), (x + (48 - x) * inward, 44)], (246, 84, 184, 240), 1.2)
        line([(x + 1.8, 6), (x + 1.8 + (48 - x) * inward, 44)],
             (132, 66, 196, 190), 0.7)
        for j in range(16):
            y = 7.0 + j * 2.3
            d.ellipse([p(x - 0.35, y - 0.35), p(x + 0.35, y + 0.35)],
                      fill=(255, 198, 232, 190))

    # Medallón central y filigrana simétrica que atraviesa las 3 secciones.
    cx, cy = 48.0, 14.0
    for r, col, width in ((12.5, (176, 96, 220, 190), 1.0),
                          (9.0, (248, 104, 196, 225), 0.9)):
        d.ellipse([p(cx - r, cy - r), p(cx + r, cy + r)],
                  outline=col, width=max(1, int(width * scale)))
    diamond = [(cx, 4.5), (cx + 12.5, cy), (cx, 23.5), (cx - 12.5, cy)]
    d.polygon([p(*q) for q in diamond], fill=(40, 12, 56, 235))
    line(diamond + [diamond[0]], (255, 118, 208, 250), 1.3)
    inner = [(cx, 9), (cx + 6, cy), (cx, 19), (cx - 6, cy)]
    line(inner + [inner[0]], (238, 200, 255, 230), 0.8)
    d.ellipse([p(cx - 2.1, cy - 2.3), p(cx + 2.1, cy + 2.3)],
              fill=(255, 248, 255, 255))

    line([(48, 23.5), (48, 43.5)], (238, 92, 192, 220), 1.0)
    for path in (
        [(48, 23.5), (34, 32), (22, 43.5)],
        [(48, 23.5), (62, 32), (74, 43.5)],
        [(22, 27), (31, 34), (38, 43.5)],
        [(74, 27), (65, 34), (58, 43.5)],
    ):
        line(path, (172, 72, 202, 185), 0.8)
    for mx, my in ((18, 18), (78, 18), (26, 35), (70, 35),
                   (38, 40), (58, 40), (48, 30)):
        d.ellipse([p(mx - 0.8, my - 0.8), p(mx + 0.8, my + 0.8)],
                  fill=(255, 146, 216, 210))

    # Dobladillo con chevrones grandes y pespuntes.
    d.rectangle([p(1, 44), p(95, 47.9)], fill=(26, 8, 36, 255))
    # Un chevron por columna de tela: el festón del canvas coincide con las
    # lengüetas v15_hem_* y no se repite dentro de cada una.
    chevron = [(1.0 + i * 94.0 / COLUMNS, 44.2 + (2.2 if i % 2 else 0.0))
               for i in range(COLUMNS + 1)]
    line(chevron, (196, 88, 168, 205), 1.0)
    for i in range(COLUMNS):
        x = 2.0 + i * 92.0 / COLUMNS
        line([(x, 47.7), (x + 1.6, 43.8)], (126, 52, 164, 120), 0.4)

    img = Image.alpha_composite(img, overlay)

    # Cobertura emisiva intacta, pero sin dejar que las venas antiguas
    # conviertan la tela en ruido. El brillo lo aportan ribetes y medallón.
    em = Image.fromarray(
        np.clip(glow_alpha[0:ch, 0:cw], 0, 255).astype(np.uint8)
    ).resize((w, h), Image.LANCZOS)
    halo = em.filter(ImageFilter.GaussianBlur(2.0 * scale))
    arr = np.asarray(img, dtype=np.float32).copy()
    halo_arr = np.asarray(halo, dtype=np.float32) / 255.0
    arr[..., :3] += halo_arr[..., None] * np.array([12.0, 3.0, 16.0])
    em_arr = np.asarray(em, dtype=np.float32) / 255.0
    hot = np.array([150.0, 60.0, 150.0])
    arr[..., :3] = (arr[..., :3] * (1.0 - em_arr[..., None] * 0.12)
                    + hot * em_arr[..., None] * 0.12)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    return np.asarray(img.resize((cw, ch), Image.LANCZOS).convert("RGB"),
                      dtype=np.float32)


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
    canvas = build_armor_cloth_canvas(glow[..., 3])
    out[0:48, 0:96, :] = canvas
    out = paint_reserved_cloth_strips(out, glow[..., 3])
    # Los texels emisivos del canvas quedan deliberadamente discretos: el glowmask
    # conserva su cobertura, pero el material y el medallón mandan en la capa.

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
def add_cape_brocade(cloth: Image.Image, mask: Image.Image, outline: list,
                     s: int) -> Image.Image:
    """Bordado, pespuntes y material de alta resolución para el atlas folded."""
    k = s / 256.0
    p = lambda x, y: (int(round(x * k)), int(round(y * k)))
    transparent = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    details = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    dd = ImageDraw.Draw(details)

    # Twill diagonal y finas luces de pliegue, siempre dentro de la silueta.
    for x in range(-s, 2 * s, max(4, int(12 * k))):
        dd.line([p(x, 0), p(x + s, s)], fill=(186, 112, 220, 18), width=max(1, int(1 * k)))
    for x in range(70, 200, 16):
        dd.line([p(x + 3, 28), p(x + 3 + (x - 128) * 0.32, 214)],
                fill=(224, 152, 244, 30), width=max(1, int(2 * k)))

    # Doble ribete: exterior dorado apagado, interior violeta/rosa.
    pts = [p(x, y) for x, y in outline]
    inner = [(128 + (x - 128) * 0.94, 120 + (y - 120) * 0.94) for x, y in outline]
    dd.line([p(*q) for q in outline + [outline[0]]],
            fill=(236, 174, 116, 105), width=max(1, int(1.1 * k)), joint="curve")
    dd.line([p(*q) for q in inner + [inner[0]]],
            fill=(255, 112, 202, 150), width=max(1, int(1.4 * k)), joint="curve")

    # Pespuntes reales a lo largo de todo el contorno.
    r = max(1, int(0.85 * k))
    for a, b in zip(pts, pts[1:] + pts[:1]):
        dist = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        steps = max(1, int(dist / max(2.0, 7.0 * k)))
        for j in range(steps + 1):
            t = j / float(steps)
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            dd.ellipse([int(x - r), int(y - r), int(x + r), int(y + r)],
                       fill=(255, 218, 246, 105))

    # Halo y medallón con anillos concéntricos, sin inventar glowmask.
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([p(94, 44), p(162, 112)], fill=(255, 72, 174, 95))
    glow = glow.filter(ImageFilter.GaussianBlur(max(2, int(9 * k))))
    details = Image.alpha_composite(details, glow)
    dd = ImageDraw.Draw(details)
    for rr, col, width in ((31, (196, 118, 232, 150), 1.2),
                           (23, (255, 106, 196, 205), 1.4),
                           (12, (246, 222, 255, 210), 1.1)):
        dd.ellipse([p(128 - rr, 82 - rr), p(128 + rr, 82 + rr)],
                   outline=col, width=max(1, int(width * k)))
    dd.polygon([p(*q) for q in [(128, 56), (146, 82), (128, 108), (110, 82)]],
               outline=(255, 148, 218, 235), width=max(1, int(2 * k)))
    for mx, my in ((76, 92), (180, 92), (86, 160), (170, 160),
                   (104, 192), (152, 192), (128, 142)):
        dd.ellipse([p(mx - 2, my - 2), p(mx + 2, my + 2)],
                   fill=(255, 142, 210, 150))

    # Chevron inferior para que el dobladillo tenga peso y textura.
    dd.line([p(*q) for q in [(70, 206), (86, 218), (102, 206), (118, 220),
                             (134, 206), (150, 220), (166, 206), (182, 218)]],
            fill=(214, 108, 226, 115), width=max(1, int(1.3 * k)), joint="curve")

    details = Image.composite(details, transparent, mask)
    return Image.alpha_composite(cloth, details)


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
    cloth = add_cape_brocade(cloth, mask, outline, s)

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


def cloth_canvas_rgba(s: int) -> Image.Image:
    """El mismo canvas 96x48 que usa la capa equipada, ampliado a `s` px.

    v1.6.0: el icono, el item 3D plegado y la capa equipada deben contar el
    MISMO diseño. Antes el folded/icon usaban una ilustración aparte con dos
    medallones y venas neón que no existían en la tela equipada.
    """
    glow = np.asarray(
        Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"),
        dtype=np.float32,
    )
    canvas = np.clip(build_armor_cloth_canvas(glow[..., 3]), 0, 255).astype(np.uint8)
    return Image.fromarray(canvas, "RGB").convert("RGBA").resize(
        (s, s), Image.LANCZOS
    )


def build_icon() -> Image.Image:
    """Icono 64x64: silueta clásica, pero con el bordado de la tela v1.6.0."""
    s = 512
    silhouette = build_cape_artwork(s)
    mask = silhouette.getchannel("A")
    transparent = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out = Image.composite(cloth_canvas_rgba(s), transparent, mask)
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(9)), mask)
    rim = Image.new("RGBA", (s, s), (236, 116, 214, 255))
    rim.putalpha(edge.point(lambda a: min(255, int(a * 0.85))))
    return Image.alpha_composite(out, rim).resize((64, 64), Image.LANCZOS)


# --------------------------------------------------------------------------
# 3. Atlas for the folded 3D inventory model (opaque, 128x128, 7 UV strips)
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

    # v1.6.0: las siete caras plegadas muestrean el MISMO canvas continuo que
    # la capa equipada. Una pizca del grano del fondo conserva la textura de
    # tejido sin tapar el medallón ni la filigrana.
    art = np.asarray(cloth_canvas_rgba(s), dtype=np.float32)
    mix = art * 0.88 + np.asarray(bg, dtype=np.float32) * 0.12
    out = Image.fromarray(np.clip(mix, 0, 255).astype(np.uint8), "RGBA")

    # Baked lighting per fold: cada franja tiene centro iluminado, bordes en
    # sombra y una leve caída de luz hacia el dobladillo. Así las 7 caras
    # parecen tela doblada y no una imagen plana partida en columnas.
    arr = np.asarray(out, dtype=np.float32).copy()
    body0, body1 = int(10 * s / 128), int(118 * s / 128)
    vertical = np.linspace(1.04, 0.88, body1 - body0, dtype=np.float32)[:, None, None]
    for panel, offset, width in zip(PANELS, STRIP_OFFSETS, STRIP_WIDTHS):
        x0, x1 = int(offset * s / 128), int((offset + width) * s / 128)
        local = np.linspace(0.0, 1.0, x1 - x0, dtype=np.float32)[None, :, None]
        ridge = np.power(np.clip(np.sin(local * np.pi), 0.0, 1.0), 0.65)
        shade = (0.66 + 0.24 * panel["bulge"] + 0.22 * ridge) * vertical
        arr[body0:body1, x0:x1, :3] *= shade

    # Creases exactly at the seven UV boundaries, with a thin rim highlight.
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(out)
    for boundary in STRIP_OFFSETS[1:]:
        x = int(boundary * s / 128)
        d.line([(x, body0), (x, body1)], fill=(14, 5, 22, 255), width=2)
        d.line([(x + 2, body0), (x + 2, body1)], fill=(126, 52, 178, 255), width=1)

    # Woven violet yoke band and hem.
    d.rectangle([0, 0, s - 1, int(9 * s / 128)], fill=(58, 26, 78, 255))
    d.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
           fill=(196, 118, 246, 255), width=max(2, int(2 * s / 128)))
    d.rectangle([0, s - int(9 * s / 128), s - 1, s - 1], fill=(26, 8, 30, 255))
    d.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
           fill=(154, 62, 198, 255), width=max(1, int(s / 128)))

    # Reserved columns: dark lining (120..123) and neon piping (124..127).
    arr = np.asarray(out, dtype=np.float32).copy()
    lining0 = int(UV["lining"]["uv"][0] * s / 128)
    piping0 = int(UV["piping"]["uv"][0] * s / 128)
    arr[:, lining0:piping0, :3] = np.array([20.0, 8.0, 30.0])
    glow = np.array([188.0, 78.0, 226.0]) * (0.72 + 0.28 * t[:, piping0:s, :])
    arr[:, piping0:s, :3] = np.clip(glow, 0, 255)
    arr[:, lining0:s, 3] = 255.0
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

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
