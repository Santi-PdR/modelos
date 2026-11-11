#!/usr/bin/env python3
"""
Procedural texture suite for the Mantle of the Blight Star (v1.11.0).

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
    motifs. v1.9.0 redraws it from the two 16x16 reference capes: broad
    shoulders, high collar, warm clasp, central fold, scalloped hem and a
    gold/cyan rim, translated to the violet Blight Star palette. The folded 3D
    item uses a fitted (not distorted) canvas band, a readable diamond gem and
    a separate `cape_folded_glowmask.png` rendered with a pulsing eyes layer
    by CapaItemGlowLayer.

    v1.11.0 gives the pixel-art icon its OWN silhouette. v1.10.0 copied the
    two reference capes (which are the SAME 16x16 shape recoloured): a single
    centred hood-peak, a square body and a centre split that opens into two
    flaring legs. The user liked the pixel-art STYLE but asked for a shape of
    its own. ICON_PIXEL_MAP is now a distinct, symmetric mantle: two standing
    collar peaks with an open V, jutting gold pauldrons, a pinched waist, a
    flared skirt, THREE bright vertical pleats, a diamond throat clasp, the
    cyan Blight Star and a three-point crown hem (echoing FOLDS=3). Same
    approved technique: flat palette, hard outline, Image.NEAREST, no AA.

    v1.10.0 replaces the smooth illustrated 64x64 icon with TRUE 16x16 pixel
    art (ICON_PIXEL_MAP/ICON_PALETTE, upscaled 4x with Image.NEAREST), matching
    the two 2D-RPG reference capes the user supplied: flat palette, hard
    outline, no antialiasing, gradient or bloom. It also reworks the cloth
    canvas: woven twill, filled faceted medallion with a gold setting,
    stitch()-based embroidery instead of neon magenta lines, and a much lower
    bloom. Alpha and the 1636 emissive texels stay untouched.

    v1.9.0 keeps the whole smooth v1.8.0 cloth and adds a "blighted star"
    identity: eight cool rays, a broken cyan orbit around the medallion, cold
    spore-like specks and a second particle sprite set. A separate `cool_ink`
    channel drives a cyan bloom in the base colour and a cyan contribution to
    the FOLDED item's glowmask. The armor glowmask coverage and base alpha
    remain pristine. Ember and blight-mote particles each use three soft,
    anti-aliased 16x16 sprites.

Outputs (all committed, so CI needs no Python deps):
    textures/item/armor/capa_deteriorer_evilsaiyan.png            128x128
    textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png  128x128
    textures/item/capa_deteriorer_evilsaiyan.png                  64x64
    textures/item/cape_folded.png                                  128x128 (3D item atlas)
    textures/item/cape_folded_glowmask.png                         128x128 (efecto del item)
    textures/particle/capa_ember_0..2.png                          16x16  (brasas cálidas)
    textures/particle/capa_blight_mote_0..2.png                    16x16  (motas frías v1.9.0)

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
SEED = 20261111


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
def build_armor_cloth_canvas(glow_alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Canvas 96x48 v1.10.0: paño tejido y bordado, SIN aspecto de neón.

    v1.9.0 dibujaba un gran diamante magenta de líneas finas sobre un fondo
    casi negro: la crítica fue que parecía "feísima". v1.10.0 baja la
    saturación, sube la presencia de la sarga (trama, diagonal, grano),
    rellena el medallón con facetas oscuras, cambia las líneas por puntadas
    de hilo dorado y deja el cian sólo en el núcleo de Blight Star.

    Devuelve (RGB 96x48, tinta violeta, tinta cian). Las tintas realzan el
    color base y construyen el glowmask del item, pero NO amplían la
    cobertura emisiva del atlas de armadura: el glowmask prístino (1636
    texels) y el alfa base siguen intactos. La onda 2D/3D compartida no cambia.
    """
    cw = int(CLOTH_UV["cloth"]["uv_size"][0])  # 96
    ch = int(CLOTH_UV["cloth"]["uv_size"][1])  # 48
    scale = 8
    w, h = cw * scale, ch * scale
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / float(w - 1)
    v = yy / float(h - 1)
    rng = np.random.default_rng(SEED + 11)

    top = np.array([38.0, 22.0, 64.0], dtype=np.float32)
    bottom = np.array([94.0, 28.0, 64.0], dtype=np.float32)
    base = top * (1.0 - v[..., None]) + bottom * v[..., None]
    fold_phase = u * FOLDS + 0.02 * np.sin(v * np.pi * 1.5)
    wave = np.cos(2.0 * np.pi * fold_phase)
    fold_light = np.power(np.clip(0.5 + 0.5 * wave, 0.0, 1.0), 1.15)
    crease = np.exp(-((np.mod(fold_phase, 1.0) - 0.5) ** 2) / (2.0 * 0.11 ** 2))
    radial = np.exp(-(((u - 0.5) / 0.34) ** 2 + ((v - 0.38) / 0.46) ** 2) * 1.4)
    vignette = np.exp(-((u - 0.02) / 0.06) ** 2) + np.exp(-((u - 0.98) / 0.06) ** 2)
    weave = (np.sin(xx * np.pi / 3.0) * np.sin(yy * np.pi / 3.0) * 2.1
             + np.sin((xx + yy) * np.pi / 5.0) * 1.1)
    twill = np.sin((xx * 0.55 - yy * 0.32) * np.pi / 7.0) * 2.4
    warp = np.sin(xx * np.pi / 11.0) * np.sin(yy * np.pi / 29.0) * 1.8
    grain = rng.normal(0.0, 1.1, (h, w)).astype(np.float32)
    drape = np.power(1.0 - v, 1.4)[..., None] * np.array([12.0, 4.0, 16.0])
    rgb = base + drape
    rgb += (fold_light[..., None] - 0.5) * np.array([15.0, 6.0, 19.0])
    rgb -= crease[..., None] * np.array([11.0, 4.0, 13.0])
    rgb += radial[..., None] * np.array([30.0, 9.0, 40.0])
    rgb -= vignette[..., None] * np.array([22.0, 8.0, 22.0])
    rgb += (weave + twill + warp + grain)[..., None] * np.array([1.0, 0.7, 1.2])

    # Campo de estrellas tenue y determinista (puntos de hilo, no ruido).
    for _ in range(64):
        sx = float(rng.uniform(2.0, 94.0))
        sy = float(rng.uniform(8.5, 41.5))
        if abs(sx - 48.0) < 13.0 and sy < 31.0:
            continue
        sr = float(rng.uniform(0.18, 0.38))
        warm = rng.random() < 0.62
        rgb[int(sy * scale), int(sx * scale)] += (
            np.array([20.0, 14.0, 8.0]) if warm else np.array([5.0, 12.0, 16.0])
        )

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    glow_ink = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow_ink)
    cool_ink = Image.new("L", (w, h), 0)
    cd = ImageDraw.Draw(cool_ink)
    p = lambda x, y: (int(round(x * scale)), int(round(y * scale)))

    GOLD = (232, 192, 126, 240)
    GOLD_DIM = (190, 150, 100, 200)
    THREAD = (206, 146, 186, 185)
    VIOLET = (146, 88, 172, 185)
    CYAN = (128, 214, 238, 225)
    DARK = (22, 10, 34, 255)

    def line(pts, fill, width, glow=0):
        coords = [p(*q) for q in pts]
        wpx = max(1, int(width * scale))
        d.line(coords, fill=fill, width=wpx, joint="curve")
        if glow:
            gd.line(coords, fill=glow, width=max(1, int(wpx * 0.8)))

    def stitch(pts, fill, step=1.25, length=0.82, width=0.40, glow=0):
        """Puntada corta: bordado en vez de línea neón continua."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            dist = math.hypot(x1 - x0, y1 - y0)
            if dist < 1e-6:
                continue
            n = max(1, int(dist / step))
            for k in range(n):
                t0 = k * step / dist
                t1 = min(1.0, t0 + length / dist)
                a = (x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0)
                b = (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)
                line([a, b], fill, width, glow)

    def ellipse(box, fill, width=0, glow=0):
        coords = [p(box[0], box[1]), p(box[2], box[3])]
        if width:
            d.ellipse(coords, outline=fill, width=max(1, int(width * scale)))
        else:
            d.ellipse(coords, fill=fill)
        if glow:
            gd.ellipse(coords, fill=glow)

    def cool_line(pts, width, glow=170):
        coords = [p(*q) for q in pts]
        cd.line(coords, fill=glow, width=max(1, int(width * scale)), joint="curve")

    def cool_ellipse(box, glow=170):
        coords = [p(box[0], box[1]), p(box[2], box[3])]
        cd.ellipse(coords, fill=glow)

    # 1. Yugo de tela tejida, con pespuntes dorados en vez de una raya rosa.
    d.polygon([p(*q) for q in [(1, 1), (95, 1), (91, 7), (5, 7)]],
              fill=(30, 16, 50, 255))
    stitch([(1, 6.8), (95, 6.8)], GOLD, step=1.3, length=0.9, width=0.48, glow=95)
    stitch([(4, 2), (18, 6)], GOLD_DIM, width=0.28)
    stitch([(92, 2), (78, 6)], GOLD_DIM, width=0.28)
    for j in range(38):
        x = 2.0 + j * 92.0 / 37.0
        ellipse((x - 0.24, 6.45, x + 0.24, 6.95), (216, 178, 122, 175))

    # 2. Doble ribete: oro apagado por fuera, violeta por dentro, con puntadas.
    border = [(1.6, 7.6), (94.4, 7.6), (94.4, 42.0), (1.6, 42.0)]
    stitch(border + [border[0]], GOLD, step=1.35, length=1.0, width=0.50, glow=90)
    inner_border = [(3.1, 9.1), (92.9, 9.1), (92.9, 40.5), (3.1, 40.5)]
    stitch(inner_border + [inner_border[0]], THREAD, step=1.25, length=0.85, width=0.40, glow=70)

    # 3. Medallón RELLENO: facetas de paño oscuro, engarce dorado y estrella
    #    cian. Ya no es un diamante de contorno magenta sobre fondo negro.
    cx, cy = 48.0, 18.5
    diamond = [(cx, 7.0), (cx + 11.0, cy), (cx, 30.0), (cx - 11.0, cy)]
    d.polygon([p(*q) for q in diamond], fill=(26, 12, 42, 255))
    inner_facet = [(cx, 10.0), (cx + 7.6, cy), (cx, 27.0), (cx - 7.6, cy)]
    d.polygon([p(*q) for q in inner_facet], fill=(42, 18, 58, 255))
    # bisel: mitad iluminada, mitad en sombra
    d.polygon([p(*q) for q in [(cx, 10.0), (cx + 7.6, cy), (cx, 27.0)]],
              fill=(58, 26, 76, 235))
    stitch(diamond + [diamond[0]], GOLD, step=1.25, length=0.9, width=0.58, glow=140)
    stitch(inner_facet + [inner_facet[0]], GOLD_DIM, step=1.2, length=0.7, width=0.42, glow=85)
    for r, col, glow in ((10.4, VIOLET, 55), (7.6, (110, 70, 140, 140), 35)):
        ellipse((cx - r, cy - r, cx + r, cy + r), col, 0.4, glow)
    for gx, gy in diamond:
        ellipse((gx - 0.8, gy - 0.8, gx + 0.8, gy + 0.8),
                (226, 190, 126, 235), glow=150)

    # 3b. Núcleo de Blight Star: 8 rayos cian cortos y órbita discontinua
    #     dorada (antes 12 arcos cian que parecían una rueda).
    for j in range(8):
        a = 2.0 * math.pi * j / 8.0
        ray = [(cx + 1.1 * math.cos(a), cy + 1.1 * math.sin(a)),
               (cx + 3.2 * math.cos(a), cy + 3.2 * math.sin(a))]
        line(ray, CYAN, 0.40, 120)
        cool_line(ray, 0.30, 205)
    ellipse((cx - 1.5, cy - 1.7, cx + 1.5, cy + 1.7), (36, 24, 54, 255))
    ellipse((cx - 0.62, cy - 0.62, cx + 0.62, cy + 0.62),
            (226, 250, 255, 255), glow=255)
    cool_ellipse((cx - 0.85, cy - 0.85, cx + 0.85, cy + 0.85), 255)
    for j in range(10):
        a0 = 2.0 * math.pi * j / 10.0 + 0.06
        a1 = a0 + 0.24
        arc = [(cx + 12.2 * math.cos(a), cy + 12.2 * math.sin(a))
               for a in np.linspace(a0, a1, 5)]
        stitch(arc, GOLD_DIM, step=1.2, length=0.5, width=0.26, glow=35)

    # 4. Constelación bordada: hilo, no líneas luminosas. Las 5 estrellas 3D
    #    siguen usando la misma zona emisiva `bright` del atlas.
    stars = [(18, 18), (78, 18), (26, 35), (70, 35), (48, 30)]
    stitch([(48, 29.0), (48, 41.5)], THREAD, step=1.2, length=0.85, width=0.46, glow=85)
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
        stitch(path, THREAD, step=1.35, length=0.85, width=0.40, glow=65)
    for mx, my in stars:
        ellipse((mx - 0.85, my - 0.85, mx + 0.85, my + 0.85),
                (236, 198, 132, 235), glow=200)
        stitch([(mx - 1.6, my), (mx + 1.6, my)], GOLD_DIM, width=0.22, glow=35)
        stitch([(mx, my - 1.6), (mx, my + 1.6)], GOLD_DIM, width=0.22, glow=35)

    # 5. Sigilos laterales pequeños, bordados en oro apagado.
    for sx, sy in ((8, 12), (88, 12), (8, 26), (88, 26), (8, 38), (88, 38)):
        sig = [(sx, sy - 1.5), (sx + 1.5, sy), (sx, sy + 1.5), (sx - 1.5, sy)]
        stitch(sig + [sig[0]], GOLD_DIM, step=1.1, length=0.5, width=0.24, glow=30)
        ellipse((sx - 0.3, sy - 0.3, sx + 0.3, sy + 0.3),
                (220, 186, 126, 200), glow=110)

    # 4b. Bordado vertical en los valles de los 3 pliegues: da detalle de
    #     cerca SIN crear las rayas neón de v1.5.x ni tapar el medallón.
    for k in range(1, FOLDS):
        fx = 96.0 * k / FOLDS
        stitch([(fx, 9.5), (fx, 41.0)], GOLD_DIM,
               step=2.1, length=0.9, width=0.26, glow=30)

    # 5b. Esporas frías discretas, como la segunda referencia pero apagadas.
    for _ in range(26):
        sx = float(rng.uniform(3.0, 93.0))
        sy = float(rng.uniform(8.0, 41.0))
        if abs(sx - 48.0) < 12.0 and sy < 31.0:
            continue
        rad = float(rng.uniform(0.16, 0.30))
        ellipse((sx - rad, sy - rad, sx + rad, sy + rad),
                (120, 200, 220, 90))
        cool_ellipse((sx - rad * 1.2, sy - rad * 1.2,
                      sx + rad * 1.2, sy + rad * 1.2), 60)

    # 6. Desgaste: rozaduras muy discretas, sin motas rosas por todo el paño.
    for _ in range(95):
        wx = float(rng.uniform(1.0, 95.0))
        wy = float(rng.uniform(7.5, 41.5))
        edge = max(0.0, 1.0 - min(wx, 96.0 - wx) / 12.0)
        low = max(0.0, (wy - 27.0) / 14.0)
        if rng.random() > min(1.0, 0.08 + 0.32 * low + 0.22 * edge):
            continue
        rad = float(rng.uniform(0.35, 0.62))
        col = ((196, 160, 128, 34) if rng.random() < 0.5
               else (14, 5, 22, 48))
        ellipse((wx - rad, wy - rad, wx + rad, wy + rad), col)

    # 7. Dobladillo: chevron de hilo + pespuntes, sin franja rosa.
    d.rectangle([p(1, 42), p(95, 47.9)], fill=(28, 12, 38, 255))
    chevron = [(1.0 + i * 94.0 / COLUMNS, 42.8 + (1.8 if i % 2 else 0.0))
               for i in range(COLUMNS + 1)]
    stitch(chevron, GOLD, step=1.2, length=0.85, width=0.48, glow=95)
    stitch([(1, 42.2), (95, 42.2)], GOLD_DIM, step=1.5, length=0.7, width=0.28)
    for i in range(COLUMNS):
        x = 2.0 + i * 92.0 / COLUMNS
        stitch([(x, 47.7), (x + 1.6, 42.6)], VIOLET, step=1.1, length=0.5, width=0.22)

    img = Image.alpha_composite(img, overlay)

    # Tinta de bordado: bloom MUCHO más bajo que en v1.9.0. Sólo color base.
    ink = np.asarray(glow_ink, dtype=np.float32) / 255.0
    blur = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(2.0 * scale)
        ), dtype=np.float32
    ) / 255.0
    arr = np.asarray(img, dtype=np.float32).copy()
    arr[..., :3] += blur[..., None] * np.array([7.0, 4.0, 6.0])
    arr[..., :3] += ink[..., None] * np.array([13.0, 8.0, 11.0])

    cool = np.asarray(cool_ink, dtype=np.float32) / 255.0
    cool_blur = np.asarray(
        Image.fromarray((cool * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1.8 * scale)
        ), dtype=np.float32
    ) / 255.0
    arr[..., :3] += cool_blur[..., None] * np.array([1.0, 6.0, 9.0])
    arr[..., :3] += cool[..., None] * np.array([2.0, 18.0, 24.0])

    # Cobertura emisiva original intacta; sólo tiñe el material.
    em = Image.fromarray(
        np.clip(glow_alpha[0:ch, 0:cw], 0, 255).astype(np.uint8)
    ).resize((w, h), Image.LANCZOS)
    halo = em.filter(ImageFilter.GaussianBlur(2.0 * scale))
    halo_arr = np.asarray(halo, dtype=np.float32) / 255.0
    arr[..., :3] += halo_arr[..., None] * np.array([8.0, 3.0, 10.0])
    em_arr = np.asarray(em, dtype=np.float32) / 255.0
    hot = np.array([120.0, 70.0, 130.0])
    arr[..., :3] = (arr[..., :3] * (1.0 - em_arr[..., None] * 0.10)
                    + hot * em_arr[..., None] * 0.10)
    final = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    rgb_small = np.asarray(final.resize((cw, ch), Image.LANCZOS).convert("RGB"),
                           dtype=np.float32)
    glow_small = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8)).resize(
            (cw, ch), Image.LANCZOS
        ), dtype=np.float32
    ) / 255.0
    cool_small = np.asarray(
        Image.fromarray((cool * 255).astype(np.uint8)).resize(
            (cw, ch), Image.LANCZOS
        ), dtype=np.float32
    ) / 255.0
    return rgb_small, glow_small, cool_small


def paint_reserved_cloth_strips(out: np.ndarray, glow_alpha: np.ndarray) -> np.ndarray:
    """Creases, forro, ribete y zona emisiva en rectángulos ya opacos."""
    y = np.arange(128, dtype=np.float32).reshape(128, 1, 1) / 127.0
    # v1.5.1: contraste de crease reducido. En v1.5.0 las 36 creases leían
    # como un código de barras; ahora acompañan al sombreado del canvas.
    out[:, 105:107, :3] = np.array([34.0, 14.0, 48.0]) + y * np.array([6.0, 2.0, 8.0])
    out[:, 107:109, :3] = np.array([60.0, 28.0, 86.0]) + y * np.array([8.0, 3.0, 12.0])
    out[:, 120:122, :3] = np.array([18.0, 8.0, 30.0]) + y * np.array([10.0, 2.0, 10.0])
    # v1.10.0: ribete menos neón, más hilo dorado/violeta apagado.
    out[:, 122:124, :3] = np.array([92.0, 48.0, 126.0]) + y * np.array([30.0, 12.0, 36.0])

    em = glow_alpha[109:127, 69:75] > 0
    bright = out[109:127, 69:75, :3]
    bright[...] = np.array([46.0, 10.0, 44.0])
    bright[em] = np.array([226.0, 142.0, 198.0])

    yoke = out[76:93, 57:71, :3]
    yoke[...] = yoke * 0.72 + np.array([24.0, 14.0, 34.0])
    yoke[glow_alpha[76:93, 57:71] > 0] = np.array([206.0, 158.0, 128.0])
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
    canvas, canvas_glow, canvas_cool = build_armor_cloth_canvas(glow[..., 3])
    out[0:48, 0:96, :] = canvas
    # La tinta nueva del bordado ya venía realzada; un bloom suave extra hace
    # que constelación y medallón se lean incluso de noche, SIN tocar el alpha
    # del glowmask prístino (no se abren huecos en la tela).
    soft = Image.fromarray(
        (np.clip(canvas_glow, 0, 1) * 255).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(1.2))
    soft_arr = np.asarray(soft, dtype=np.float32) / 255.0
    out[0:48, 0:96, :3] += soft_arr[..., None] * np.array([8.0, 2.0, 12.0])
    # v1.9.0: el segundo bloom, cian, se mantiene por debajo del violeta.
    cool_soft = Image.fromarray(
        (np.clip(canvas_cool, 0, 1) * 255).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(0.8))
    cool_arr = np.asarray(cool_soft, dtype=np.float32) / 255.0
    out[0:48, 0:96, :3] += cool_arr[..., None] * np.array([1.0, 5.0, 8.0])
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
    el mismo degradado de la tela. v1.9.0 devuelve además el glowmask del item
    con DOS tintas: violeta para el bordado y cian para Blight Star.
    """
    glow = np.asarray(
        Image.open(ORIGINALS / "armor_glowmask.png").convert("RGBA"),
        dtype=np.float32,
    )
    rgb, ink_small, cool_small = build_armor_cloth_canvas(glow[..., 3])
    canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    ink = Image.fromarray((np.clip(ink_small, 0, 1) * 255).astype(np.uint8), "L")
    cool = Image.fromarray((np.clip(cool_small, 0, 1) * 255).astype(np.uint8), "L")
    cw, ch = canvas.size
    scale = min(w / float(cw), h / float(ch))
    fw, fh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    fitted = canvas.resize((fw, fh), Image.LANCZOS)
    fitted_ink = ink.resize((fw, fh), Image.LANCZOS)
    fitted_cool = cool.resize((fw, fh), Image.LANCZOS)
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
    ink_rgba = Image.new("RGBA", (fw, fh), (226, 176, 120, 0))
    ink_rgba.putalpha(fitted_ink)
    cool_rgba = Image.new("RGBA", (fw, fh), (130, 238, 255, 0))
    cool_rgba.putalpha(fitted_cool)
    glow_out.alpha_composite(ink_rgba, (px, py))
    glow_out.alpha_composite(cool_rgba, (px, py))
    return out, glow_out


# --------------------------------------------------------------------------
# v1.11.0 ICON: pixel art 2D/RPG de 16x16 con SILUETA PROPIA.
#
# Las dos referencias (image-13/14) son EL MISMO icono 16x16 recoloreado: un
# único pico de capucha centrado, cuerpo cuadrado y una hendidura central
# inferior que abre dos piernas acampanadas. v1.10.0 las COPIÓ (recoloreadas);
# el usuario aprobó el estilo pixel art pero pidió «que tenga su propia forma».
#
# Forma propia, deliberadamente distinta y simétrica:
#   * cuello alto de DOS picos con escote en V abierto y ribete dorado;
#   * hombreras que SOBRESALEN por encima del cuello (y=3);
#   * cintura ceñida (y=5..8) y faldón acampanado (y=9..12);
#   * tres pliegues VERTICALES luminosos (M/L/D, H sólo en los valles);
#   * dobladillo de TRES puntas (tridente, eco de FOLDS=3), NO la hendidura
#     central de las referencias;
#   * broche diamante en la garganta y estrella cian de Blight Star en el pecho.
# Técnica intacta: paleta plana, contorno duro, CERO AA/degradado/bloom,
# ampliado 4x con Image.NEAREST.
# --------------------------------------------------------------------------

ICON_PIXEL_MAP = (
    "....GG....GG....",
    "...GDHK..KHDG...",
    "...GDHGKKGHDG...",
    ".GGMDHMLLMHDMGG.",
    ".GLMDHMLLMHDMLG.",
    "..KMDHMLLMHDMK..",
    "..KMDHMLLMHDMK..",
    "..KMDHMLLMHDMK..",
    "..KMDHMLLMHDMK..",
    ".KLMDHMLLMHDMLK.",
    "KMLMDHMLLMHDMLMK",
    "KMLMDHMLLMHDMLMK",
    "KMLMKKMLLMKKMLMK",
    "KMLK..KLLK..KLMK",
    "KMLK..KLLK..KLMK",
    ".GG....GG....GG.",
)

# Paleta plana (9 tonos opacos + transparente): mismos violetas que v1.10.0,
# más los acentos fríos de Blight Star y el oro de cuello/hombreras/dobladillo.
ICON_PALETTE = {
    ".": (0, 0, 0, 0),
    "K": (15, 8, 22, 255),       # contorno duro
    "H": (43, 14, 54, 255),      # sombra profunda del pliegue
    "D": (72, 22, 78, 255),      # sarga base
    "M": (97, 31, 96, 255),      # tono medio
    "L": (126, 47, 116, 255),    # hombros iluminados
    "G": (232, 194, 118, 255),   # broche cálido
    "W": (226, 250, 255, 255),   # núcleo de la estrella
    "C": (110, 216, 240, 255),   # cian de Blight Star
    "E": (58, 150, 184, 255),    # veta fría apagada
}


def build_icon_artwork(size: int = 64) -> Image.Image:
    """Icono 64x64 con píxeles de 4x4, NO una ilustración con antialiasing.

    Se dibuja a 16x16 con la SILUETA PROPIA de v1.11.0 (dos picos de cuello,
    hombreras, cintura, tres pliegues y dobladillo de tres puntas), se añaden
    el broche de 5 píxeles en la garganta, una estrella cian de 4 puntas y
    vetas frías, y se amplía con `Image.NEAREST`. Bloques de color definidos:
    el estilo de icono 2D de RPG aprobado, con forma ya no copiada.
    """
    rows = ICON_PIXEL_MAP
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), "icono base 16x16"
    grid = [list(r) for r in rows]

    def put(x, y, ch):
        if 0 <= x < 16 and 0 <= y < 16 and grid[y][x] != ".":
            grid[y][x] = ch

    # Broche: diamante de 5 px en la GARGANTA, cerrando el escote en V de los
    # dos picos del cuello. Núcleo claro para que se lea en el slot.
    put(7, 2, "G")
    put(6, 3, "G")
    put(7, 3, "W")
    put(8, 3, "G")
    put(7, 4, "G")

    # Estrella de Blight Star sobre el pliegue CENTRAL: 4 puntas + núcleo.
    put(7, 8, "W")
    put(6, 8, "C")
    put(8, 8, "C")
    put(7, 7, "C")
    put(7, 9, "C")

    # Vetas cian sueltas, equivalentes a las vetas verdes de la referencia 2.
    for x, y in ((3, 6), (12, 6), (2, 10), (13, 10),
                 (5, 11), (10, 11)):
        put(x, y, "E")

    px = np.zeros((16, 16, 4), dtype=np.uint8)
    for y in range(16):
        for x in range(16):
            px[y, x] = ICON_PALETTE[grid[y][x]]

    # Rim light de UN píxel en el borde superior/izquierdo. Es una suma
    # discreta por píxel: sigue siendo pixel art, sin blur ni degradado.
    opaque = px[..., 3] > 0
    for y in range(16):
        for x in range(16):
            if not opaque[y, x] or grid[y][x] in (".", "K", "G", "W", "C"):
                continue
            if x == 0 or y == 0 or not opaque[y, x - 1] or not opaque[y - 1, x]:
                px[y, x, :3] = np.clip(
                    px[y, x, :3].astype(np.int16) + np.array([26, 10, 24], dtype=np.int16),
                    0, 255,
                ).astype(np.uint8)

    small = Image.fromarray(px, "RGBA")
    return small.resize((size, size), Image.NEAREST)


def build_icon() -> Image.Image:
    return build_icon_artwork(64)


def build_folded_texture() -> tuple[Image.Image, Image.Image]:
    """Atlas 128x128 del bulto plegado + glowmask para CapaItemGlowLayer.

    El canvas va en una banda central con su proporción real (no estirado),
    las siete franjas siguen reconstruyendo la ilustración y el sombreado por
    pliegue les da volumen. `gem`, `roll`, yugo, dobladillo y columnas
    reservadas se pintan aparte. El glowmask marca SOLO la tinta brillante,
    el broche, los nervios y los ribetes. v1.9.0 dibuja además la estrella
    cian de Blight Star dentro de la gema del broche.
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
           fill=(188, 146, 98, 255), width=max(2, int(2 * s / 128)))
    gd.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
            fill=(206, 166, 112, 170), width=max(2, int(2 * s / 128)))
    d.rectangle([0, s - int(9 * s / 128), s - 1, s - 1], fill=(26, 8, 30, 255))
    d.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
           fill=(110, 56, 142, 255), width=max(1, int(s / 128)))
    gd.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
            fill=(160, 92, 186, 150), width=max(1, int(s / 128)))

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

    # v1.9.0: regiones de las hombreras del item plegado. Paño oscuro con
    # ribete cálido/cian y una gema central, en sus propias UV reservadas.
    px0, py0 = int(96 * s / 128), int(72 * s / 128)
    px1, py1 = int(120 * s / 128), int(88 * s / 128)
    d.rectangle([px0, py0, px1, py1], fill=(32, 12, 48, 255))
    d.line([(px0, py0 + 2), (px1, py0 + 2)], fill=(222, 178, 112, 230),
           width=max(1, int(0.9 * s / 128)))
    d.line([(px0, py1 - 2), (px1, py1 - 2)], fill=(135, 225, 245, 210),
           width=max(1, int(0.9 * s / 128)))
    gd.line([(px0, py0 + 2), (px1, py0 + 2)], fill=(230, 190, 120, 170),
            width=max(1, int(0.9 * s / 128)))
    gd.line([(px0, py1 - 2), (px1, py1 - 2)], fill=(135, 225, 245, 170),
            width=max(1, int(0.9 * s / 128)))
    for j in range(3):
        mx = px0 + int((j + 0.5) * (px1 - px0) / 3.0)
        my = py0 + int((py1 - py0) * 0.52)
        rad = max(1, int(1.2 * s / 128))
        d.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                  fill=(226, 186, 126, 220))
        gd.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                   fill=(226, 176, 116, 190))
    pr0, pr1 = int(96 * s / 128), int(88 * s / 128)
    pr2, pr3 = int(120 * s / 128), int(96 * s / 128)
    d.rectangle([pr0, pr1, pr2, pr3], fill=(28, 10, 40, 255))
    d.line([(pr0, pr1 + 1), (pr2, pr1 + 1)], fill=(150, 235, 255, 220),
           width=max(1, int(0.8 * s / 128)))
    gd.line([(pr0, pr1 + 1), (pr2, pr1 + 1)], fill=(150, 235, 255, 170),
            width=max(1, int(0.8 * s / 128)))

    # Gema del broche: diamante con núcleo blanco, muy legible en la mano.
    gx0, gy0 = int(54 * s / 128), int(30 * s / 128)
    gx1, gy1 = int(74 * s / 128), int(52 * s / 128)
    cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    half = min(gx1 - gx0, gy1 - gy0) // 2 - 4
    d.rectangle([gx0, gy0, gx1, gy1], fill=(24, 10, 40, 255))
    diamond = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
    d.polygon(diamond, fill=(42, 18, 58, 255))
    d.line(diamond + [diamond[0]], fill=(226, 182, 116, 255),
           width=max(2, int(1.2 * s / 128)))
    inner = [(cx, cy - half // 2), (cx + half // 2, cy),
             (cx, cy + half // 2), (cx - half // 2, cy)]
    d.line(inner + [inner[0]], fill=(206, 170, 128, 255),
           width=max(1, int(0.8 * s / 128)))
    core = max(2, int(3 * s / 128))
    d.ellipse([cx - core, cy - core, cx + core, cy + core],
              fill=(255, 255, 255, 255))
    gd.polygon(diamond, fill=(226, 170, 110, 190))
    gd.line(diamond + [diamond[0]], fill=(240, 200, 140, 255),
            width=max(2, int(1.2 * s / 128)))
    gd.ellipse([cx - core, cy - core, cx + core, cy + core],
               fill=(255, 255, 255, 255))

    # v1.9.0: ocho rayos cian salen del núcleo del broche. Van también al
    # glowmask del item, así que CapaItemGlowLayer los hace latir en frío.
    ray_w = max(1, int(0.7 * s / 128))
    for j in range(8):
        a = 2.0 * math.pi * j / 8.0
        r0, r1 = core * 1.5, half * 0.72
        ray = [(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
               (cx + r1 * math.cos(a), cy + r1 * math.sin(a))]
        d.line(ray, fill=(150, 240, 255, 235), width=ray_w)
        gd.line(ray, fill=(150, 240, 255, 235), width=ray_w)
    d.ellipse([cx - core // 2, cy - core // 2,
               cx + core // 2, cy + core // 2],
              fill=(210, 255, 255, 255))
    gd.ellipse([cx - core // 2, cy - core // 2,
                cx + core // 2, cy + core // 2],
               fill=(210, 255, 255, 255))

    # Tres motas frías en la región reservada de los rollos de tela.
    for j in range(3):
        mx = rx0 + int((j + 0.5) * (rx1 - rx0) / 3.0)
        my = ry0 + int((ry1 - ry0) * (0.30 + 0.20 * j))
        rad = max(1, int(1.2 * s / 128))
        d.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                  fill=(130, 225, 245, 200))
        gd.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                   fill=(130, 225, 245, 190))

    # Columnas reservadas: forro oscuro y ribete violeta/neón.
    arr = np.asarray(out, dtype=np.float32).copy()
    t = (np.arange(s, dtype=np.float32).reshape(s, 1, 1) / (s - 1))
    lining0, piping0 = int(120 * s / 128), int(124 * s / 128)
    arr[:, lining0:piping0, :3] = np.array([20.0, 8.0, 30.0])
    glow_col = np.array([112.0, 62.0, 146.0]) * (0.72 + 0.28 * t)
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


def build_blight_sprites() -> list[Image.Image]:
    """Tres sprites fríos de 16x16 para la mota orbital de Blight Star.

    A diferencia de la brasa, el tercer frame es un anillo hueco: la mota
    parece apagarse como una estrella lejana en vez de convertirse en humo.
    Se generan a 64px y se reducen con Lanczos para conservar antialiasing.
    """
    s = 64
    out_s = 16
    yy, xx = np.mgrid[0:s, 0:s]
    c = (s - 1) / 2.0
    r2 = (xx - c) ** 2 + (yy - c) ** 2
    sprites = []

    # spread, núcleo, anillo, cruz
    frames = [
        (5.0, 0.86, 0.16, 0.10),
        (7.2, 0.58, 0.34, 0.22),
        (9.4, 0.30, 0.44, 0.12),
    ]

    for spread, core_power, ring_power, cross_power in frames:
        core = np.exp(-r2 / (2.0 * (spread * 0.35) ** 2)) * core_power
        ring = (np.exp(-((np.sqrt(r2) - spread) ** 2)
                       / (2.0 * (spread * 0.18) ** 2)) * ring_power)
        cross = (
            np.exp(-((xx - c) ** 2) / (2.0 * (spread * 0.12) ** 2))
            + np.exp(-((yy - c) ** 2) / (2.0 * (spread * 0.12) ** 2))
        ) * cross_power * np.exp(-r2 / (2.0 * (spread * 1.30) ** 2))
        a = np.clip((core + ring + cross) * 0.64, 0.0, 1.0)

        rgb = np.zeros((s, s, 3), dtype=np.float32)
        tint = (0.42, 0.90, 1.00)
        for channel, base in enumerate((16.0, 34.0, 58.0)):
            intensity = np.clip(core + ring * 0.60 + cross * 0.50, 0.0, 1.0)
            rgb[..., channel] = base + (255.0 * tint[channel] - base) * intensity
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
    print(f"ember sprites: {len(embers)} x {embers[0].size[0]}x{embers[0].size[1]}")

    motes = build_blight_sprites()
    for index, sprite in enumerate(motes):
        assert sprite.size == (16, 16), sprite.size
        sprite.save(particle_dir / f"capa_blight_mote_{index}.png")
    print(f"blight mote sprites: {len(motes)} x {motes[0].size[0]}x{motes[0].size[1]}")
    blight_particle = json.loads((ASSETS / "particles/capa_blight_mote.json").read_text())
    assert len(blight_particle["textures"]) == 3

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
