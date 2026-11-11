#!/usr/bin/env python3
"""
Procedural texture suite for the Mantle of the Blight Star (v1.12.0).

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
    its own (v1.11.0), then REDRAWN for v1.12.0 because the user rejected it:
    the 16x16 ICON_PIXEL_MAP now has jutting gold pauldrons with cyan gems,
    a trapezoidal mantle with THREE wide pleats, a 5-pixel diamond clasp,
    gold embroidery, cold veins, the Blight Star and a hanging three-point
    hem. Flat palette, hard outline, Image.NEAREST, no gradients/AA/bloom.

    v1.12.0 also gives the EQUIPPED cape real 3D volume (see
    armor_model_pipeline.py): 0.85-thick cloth blocks instead of 0.10 sheets,
    solid rear pauldrons, a raised collar, stepped plates, 3D chains and a
    medallion with depth. The reserved cloth strips are lightened so the
    newly visible side faces read as thick twill, not black bars.

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
    """Canvas 96x48 v1.14.0: DETERIORO + EVIL SAIYAN ROSÉ.

    Base de carmesí muy oscuro que cae a violeta-negro, parches de morado
    desvaído y gris ceniza (desgaste), trama de sarga, pliegues anchos y
    agujeros rasgados. Encima, una red de GRIETAS DE ENERGÍA con núcleo
    rosa encendido, halo magenta y borde violeta-negro: recorren toda la
    capa de los hombros al dobladillo, se ramifican y se vuelven más densas
    abajo, donde la prenda se desintegra.

    Devuelve (RGB 96x48, tinta rosa, tinta fría). Las tintas alimentan el
    bloom del color base y el glowmask del item plegado. El alfa base NO se
    toca y la cobertura emisiva del atlas (1636 texels) se REDISTRIBUYE a
    las grietas en build_armor(), sin crecer: así no se abren huecos.
    """
    cw, ch = 96, 48
    scale = 4
    w, h = cw * scale, ch * scale
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / float(w - 1)
    v = yy / float(h - 1)
    rng = np.random.default_rng(SEED + 11)

    n_fine = _blurred_noise(rng, (h, w), 0.7)
    n_med = _blurred_noise(rng, (h, w), 2.6)
    n_big = _blurred_noise(rng, (h, w), 8.0)

    # Carmesí oscuro arriba -> violeta-negro abajo.
    top = np.array([47.0, 11.0, 26.0], dtype=np.float32)
    bot = np.array([11.0, 6.0, 20.0], dtype=np.float32)
    rgb = top * (1.0 - v[..., None]) + bot * v[..., None]

    # Morado desvaído en parches grandes y gris ceniza de desgaste.
    rgb += np.clip(n_big, 0.0, 1.4)[..., None] * np.array([14.0, 3.0, 26.0])
    ash = np.clip(0.5 + 0.5 * n_med, 0.0, 1.0)[..., None]
    rgb += ash * (0.22 + 0.42 * v)[..., None] * np.array([24.0, 23.0, 27.0])

    # Tres pliegues anchos (misma onda que el relieve 3D) con sombreado.
    fold = np.cos(2.0 * np.pi * FOLDS * u + 0.10 * np.sin(v * np.pi * 1.7))
    rgb += (0.5 + 0.5 * fold)[..., None] * np.array([12.0, 2.0, 16.0])
    rgb -= (0.5 - 0.5 * fold)[..., None] * np.array([13.0, 5.0, 14.0])

    # Trama, sarga diagonal y grano de hilo viejo.
    weave = np.sin(xx * np.pi / 2.0) * np.sin(yy * np.pi / 2.0) * 2.3
    twill = np.sin((xx + yy) * np.pi / 3.3) * 1.7
    rgb += (weave + twill + n_fine * 5.0)[..., None] * np.array([0.9, 0.8, 1.1])

    # Viñeta: los bordes de la tela se comen la luz.
    vig = (np.exp(-((u - 0.015) / 0.055) ** 2)
           + np.exp(-((u - 0.985) / 0.055) ** 2))[..., None]
    rgb -= vig * np.array([16.0, 5.0, 18.0])

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # Agujeros y desgarros oscuros, más frecuentes hacia el dobladillo.
    holes = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(holes)
    for _ in range(46):
        hx = float(rng.uniform(2.0, 94.0))
        hy = float(rng.uniform(6.0, 47.0))
        rad = float(rng.uniform(0.5, 2.1)) * (0.5 + 0.9 * hy / 48.0)
        hd.ellipse([int((hx - rad) * scale), int((hy - rad) * scale),
                    int((hx + rad) * scale), int((hy + rad) * scale)],
                   fill=(7, 4, 13, 235))
    img = Image.alpha_composite(img, holes)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    glow_ink = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow_ink)
    cool_ink = Image.new("L", (w, h), 0)
    cd = ImageDraw.Draw(cool_ink)
    p = lambda x, y: (int(round(x * scale)), int(round(y * scale)))

    ROSE = (255, 122, 200, 255)
    ROSE_CORE = (255, 196, 232, 255)
    MAGENTA = (206, 20, 132, 240)
    MAGENTA_DARK = (104, 8, 66, 205)

    # Bordes iluminados: un filete rosa de 1 px recorre ambos lados.
    for ex in (0.7, 95.3):
        d.line([p(ex, 0), p(ex, 47.9)], fill=(214, 40, 138, 170),
               width=max(1, int(0.30 * scale)))
        gd.line([p(ex, 0), p(ex, 47.9)], fill=120,
                width=max(1, int(0.35 * scale)))

    # 11 grietas principales con ramificaciones y nodos. Cada una serpentea
    # desde el hombro hasta el dobladillo; el jitter crece hacia abajo para
    # leer como energía inestable que desprende la tela.
    for ci in range(6):
        x = (4.0, 19.0, 31.0, 52.0, 70.0, 87.0)[ci] + float(rng.uniform(-2.0, 2.0))
        pts = []
        for j in range(24):
            yv = -1.0 + j * 2.15
            x += float(rng.uniform(-0.55, 0.55)) + 0.42 * math.sin(j * 0.55 + ci)
            x += 0.24 * (j / 24.0) * math.sin(ci * 2.1)
            x = max(1.0, min(95.0, x))
            pts.append(p(x, yv))
        # La grieta se DIBUJA A TROZOS: tramos que se encienden y se
        # apagan. Una línea continua parecía un código de barras; los
        # huecos la convierten en energía inestable sobre tela podrida.
        spans = ((0, 6), (7, 12), (13, 18), (19, 24))
        for si, (a, b) in enumerate(spans):
            seg = pts[a:b]
            if len(seg) < 2:
                continue
            power = 1.0 if (ci + si) % 3 else 0.55
            halo = MAGENTA_DARK if power > 0.8 else (72, 6, 48, 170)
            d.line(seg, fill=halo, width=max(2, int(1.25 * scale * power)), joint="curve")
            d.line(seg, fill=MAGENTA, width=max(1, int(0.60 * scale * power)), joint="curve")
            d.line(seg, fill=ROSE, width=max(1, int(0.30 * scale)), joint="curve")
            gd.line(seg, fill=int(225 * power), width=max(1, int(0.45 * scale)), joint="curve")
            cd.line(seg, fill=70, width=max(1, int(0.30 * scale)), joint="curve")
        # Ramas cortas que se abren en la mitad inferior.
        for j in range(3):
            k = 5 + j * 6
            if k + 2 >= len(pts):
                break
            a = pts[k]
            bx = pts[k + 1][0] + int(float(rng.uniform(2.5, 8.5)) * scale) * (1 if ci % 2 else -1)
            by = pts[k + 1][1] + int(0.9 * scale)
            d.line([a, (bx, by)], fill=MAGENTA, width=max(1, int(0.75 * scale)))
            d.line([a, (bx, by)], fill=ROSE, width=max(1, int(0.30 * scale)))
            gd.line([a, (bx, by)], fill=150, width=max(1, int(0.35 * scale)))
        # Nodos de energía (chispas) a lo largo de la grieta.
        for j in range(3, 24, 7):
            qx, qy = pts[j]
            r = max(1, int(0.75 * scale))
            d.ellipse([qx - r, qy - r, qx + r, qy + r], fill=ROSE_CORE)
            gd.ellipse([qx - r, qy - r, qx + r, qy + r], fill=255)

    # Vettable diagonales secundarias: rompen la verticalidad y recuerdan
    # los jirones de la referencia de Blockbench.
    for di in range(7):
        x0 = 2.0 + di * 13.5 + float(rng.uniform(-3.0, 3.0))
        y0 = 6.0 + float(rng.uniform(0.0, 30.0))
        dx = float(rng.uniform(4.0, 11.0)) * (1.0 if di % 2 else -1.0)
        dy = float(rng.uniform(5.0, 12.0))
        seg = [p(x0, y0), p(x0 + dx * 0.5, y0 + dy * 0.5), p(x0 + dx, y0 + dy)]
        d.line(seg, fill=MAGENTA, width=max(1, int(0.50 * scale)), joint="curve")
        d.line(seg, fill=ROSE, width=max(1, int(0.25 * scale)), joint="curve")
        gd.line(seg, fill=165, width=max(1, int(0.35 * scale)), joint="curve")

    # Ceniza / chispas sueltas: puntos de 1 px sin halo, deterministas.
    for _ in range(64):
        sx = float(rng.uniform(0.0, 96.0))
        sy = float(rng.uniform(0.0, 48.0))
        q = p(sx, sy)
        if q[0] >= w or q[1] >= h:
            continue
        hot = rng.random() < (0.25 + 0.45 * sy / 48.0)
        d.point(q, fill=ROSE if hot else (96, 88, 100, 190))
        if hot:
            gd.point(q, fill=190)

    img = Image.alpha_composite(img, overlay)

    # Bloom rosa alrededor del núcleo: contraste alto sin tocar el alfa.
    ink = np.asarray(glow_ink, dtype=np.float32) / 255.0
    blur = np.asarray(
        Image.fromarray((ink * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1.7 * scale)), dtype=np.float32
    ) / 255.0
    arr = np.asarray(img, dtype=np.float32).copy()
    arr[..., :3] += blur[..., None] * np.array([27.0, 4.0, 20.0])
    arr[..., :3] += ink[..., None] * np.array([15.0, 4.0, 12.0])

    cool = np.asarray(cool_ink, dtype=np.float32) / 255.0
    cool_blur = np.asarray(
        Image.fromarray((cool * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(1.4 * scale)), dtype=np.float32
    ) / 255.0
    arr[..., :3] += cool_blur[..., None] * np.array([6.0, 14.0, 26.0])

    # Reducción 4x -> 96x48 (BOX conserva la media, no añade AA al icono).
    small = np.asarray(
        Image.fromarray(np.clip(arr[..., :3], 0, 255).astype(np.uint8), "RGB")
        .resize((cw, ch), Image.BOX), dtype=np.float32
    )
    ink_small = np.asarray(glow_ink.resize((cw, ch), Image.BOX), dtype=np.float32) / 255.0
    cool_small = np.asarray(cool_ink.resize((cw, ch), Image.BOX), dtype=np.float32) / 255.0
    return small, ink_small, cool_small


def paint_reserved_cloth_strips(out: np.ndarray, glow_alpha: np.ndarray) -> np.ndarray:
    """Columnas reservadas v1.14.0: ceniza, forro y rampa de energía Rosé.

    El atlas sigue teniendo EXACTAMENTE el mismo alfa. Lo que cambia es el
    RGB de esas franjas ya opacas: los cantos de los jirones pasan a gris
    ceniza / violeta, el ribete a una vena magenta y el parche emisivo a una
    rampa rosa -> magenta -> violeta-negro de la que samplean los 56
    microvóxeles. Cada partícula toma un sub-rectángulo de 2x2 distinto.
    """
    y = np.arange(128, dtype=np.float32).reshape(128, 1, 1) / 127.0

    # Gris ceniza y violeta apagado para los cantos con grosor real.
    out[:, 105:107, :3] = np.array([56.0, 51.0, 60.0]) + y * np.array([10.0, 5.0, 16.0])
    out[:, 107:109, :3] = np.array([82.0, 32.0, 88.0]) + y * np.array([16.0, 4.0, 22.0])
    out[:, 120:122, :3] = np.array([34.0, 14.0, 44.0]) + y * np.array([14.0, 3.0, 18.0])

    # Vena de energía vertical: rosa encendido arriba, magenta en el centro,
    # violeta-negro abajo. Bézier cuadrática, NO un degradado suave en el
    # icono (que sigue siendo pixel art plano).
    t = y
    hot = np.array([255.0, 122.0, 200.0], dtype=np.float32)
    mag = np.array([206.0, 20.0, 132.0], dtype=np.float32)
    dark = np.array([17.0, 8.0, 28.0], dtype=np.float32)
    ramp = (hot * (1.0 - t) ** 2 + 2.0 * mag * t * (1.0 - t) + dark * t ** 2)
    out[:, 122:124, :3] = ramp

    # Parche de los microvóxeles (6x18). Gradiente 2D: el eje X va de rosa a
    # magenta y el eje Y se apaga a violeta-negro. Así 56 cubos de 1-2 px
    # pueden tomar colores distintos con UV distintas.
    ey = np.linspace(0.0, 1.0, 18, dtype=np.float32).reshape(18, 1, 1)
    ex = np.linspace(0.0, 1.0, 6, dtype=np.float32).reshape(1, 6, 1)
    energy = (hot * (1.0 - ey) * (1.0 - ex)
              + mag * (1.0 - ey) * ex
              + dark * ey)
    energy[ey[..., 0, 0] > 0.78, ...] = np.array([26.0, 10.0, 38.0])
    out[109:127, 69:75, :3] = energy

    # Yugo / cuello: carmesí oscuro con dos vetas magenta finas.
    yoke = out[76:93, 57:71, :3]
    yoke[...] = np.array([46.0, 12.0, 34.0]) + y[:17] * np.array([14.0, 3.0, 20.0])
    yoke[:, 2:3, :] = np.array([214.0, 28.0, 140.0])
    yoke[:, 11:12, :] = np.array([160.0, 18.0, 108.0])
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
def _fit_emissive_mask(priority: np.ndarray, opaque: np.ndarray, target: int,
                       allowed: np.ndarray | None = None) -> np.ndarray:
    """Elige EXACTAMENTE `target` texels opacos, priorizando energía y grietas.

    GeckoLib borra del color base los pixeles marcados en el glowmask. Si la
    cobertura creciera aparecerían agujeros en la capa; si decreciera, las
    grietas no brillarían. Por eso se mantiene el conteo prístino (1636) y
    sólo se trasladan a las nuevas grietas de energía.
    """
    mask = np.zeros((SIZE, SIZE), dtype=bool)
    count = 0
    for level in (2, 1):
        ys, xs = np.nonzero((priority == level) & opaque & ~mask)
        order = np.lexsort((xs, ys))
        for i in order:
            if count >= target:
                break
            mask[ys[i], xs[i]] = True
            count += 1
        if count >= target:
            break
    if count < target:
        for radius in (1, 2, 3, 5):
            pool = dilate(mask, radius) & opaque & ~mask & (allowed if allowed is not None else True)
            ys, xs = np.nonzero(pool)
            for i in np.lexsort((xs, ys)):
                if count >= target:
                    break
                mask[ys[i], xs[i]] = True
                count += 1
            if count >= target:
                break
    assert count == target, (count, target)
    return mask


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

    # v1.14.0: el realce emisivo se aplica DESPUÉS de pintar las grietas
    # (más abajo), usando la máscara redistribuida, no la prístina.

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

    # v1.14.0: las GRIETAS se vuelven emisivas. Se trasladan los 1636
    # texels del glowmask prístino (mismo conteo, cero agujeros nuevos) a
    # los núcleos de energía, a la rampa de los microvóxeles y a las venas.
    ga = glow[..., 3]
    target = int((ga > 0).sum())
    crack_blur = np.asarray(
        Image.fromarray((np.clip(canvas_glow * 2.2, 0, 1) * 255).astype(np.uint8))
        .filter(ImageFilter.GaussianBlur(1.1)), dtype=np.float32
    ) / 255.0
    crack = crack_blur > 0.045
    priority = np.zeros((SIZE, SIZE), dtype=np.int8)
    priority[109:127, 69:75] = 2          # rampa de microvóxeles
    priority[0:48, 122:124] = 2          # vena de los bordes
    priority[0:48, 0:96] = np.where(crack, 1, 0)
    allowed = np.zeros((SIZE, SIZE), dtype=bool)
    allowed[0:48, 0:96] = True
    allowed[109:127, 69:75] = True
    allowed[0:48, 122:124] = True
    emissive = _fit_emissive_mask(priority, opaque, target, allowed)

    out[..., 0] = np.where(emissive, out[..., 0] * 1.12 + 38.0, out[..., 0])
    out[..., 1] = np.where(emissive, out[..., 1] * 1.06 + 10.0, out[..., 1])
    out[..., 2] = np.where(emissive, out[..., 2] * 1.12 + 40.0, out[..., 2])

    out = np.clip(out, 0, 255)
    out = np.where(opaque[..., None], out, rgb)  # never paint into transparent texels
    armor = np.dstack((out, alpha)).astype(np.uint8)

    # GeckoLib sólo lee el ALFA del glowmask; el RGB se deja coherente con
    # el rosa encendido para que también se vea bien en editores externos.
    grgb = np.broadcast_to(
        np.array([255.0, 110.0, 190.0], dtype=np.float32), (SIZE, SIZE, 3)
    ).copy()
    grgb[~emissive] = np.array([14.0, 6.0, 22.0])
    new_alpha = np.where(emissive, 255.0, 0.0)
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
# v1.12.0 ICON: pixel art 2D/RPG de 16x16 REDISENADO (hombreras + broche).
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

# v1.14.0: el usuario APROBO el icono "Blight Star" de v1.13.0 y pidio
# actualizarlo segun la capa nueva (Deterioro / Evil Saiyan Rose). Se
# conserva EXACTAMENTE su silueta y su logica de 5 tonos cercanos; cambian
# la paleta (carmesi oscuro + morado desvaido + gris ceniza, acentos rosa y
# magenta), las grietas de energia, el dobladillo mas deshilachado y 4
# microvoxeles flotantes. Sigue siendo 16x16 plano, NEAREST, sin AA,
# degradados ni bloom. ICON_ALTERNATIVE guarda la forma aprobada para que el
# visor permita comparar antes/despues.
ICON_ALTERNATIVE = (
    "..KKGG....GGKK..",
    "...HGHHHKKHGH...",
    "....HHHHHHKKK...",
    "...HMLMGKKLLLK..",
    "...HELGWGMLEDK..",
    "...GDLLGMMLLGK..",
    "...HDLLMHLLLLK..",
    "...HMLLMHLLMLHK.",
    "...HMLMCKLMDLDK.",
    "..HEMLECEHMDLDHK",
    ".HDMLDMEKKMDEDDK",
    ".HDMDDMDKHMLMDDK",
    "KHMDDMLDKDMDDDDK",
    "KHDDMDDHKLDDDDK.",
    ".KKGHDHGKDHKGK..",
    "...KK.KKK.KK....",
)

# Icono ACTIVO v1.14.0.
ICON_PIXEL_MAP = (
    "..KKGG....GGKK..",
    "...HGHHHKKHGH...",
    ".P..HHHHHHKKK...",
    "...HMLMGKKLLLK..",
    "...HELGWGMLEDK..",
    "...GDLLGMMLLGK..",
    "...HELLMHLLELK..",
    "...HCLLMHLLMLHK.",
    "...HMLMCKLMPLDP.",
    "..HEELECEHMDLDHK",
    ".HDMLDMEKKMGEDDK",
    "PHDMDDMDKHMLMDDK",
    "KHMDPMLDKDMEDDDK",
    "KHDDMDDHKLDDDDKP",
    ".KK.HD.GKDH.GK..",
    "..K.KK..K.K.K...",
)

ICON_CANDIDATES = {"aprobado_v1130": ICON_ALTERNATIVE, "rose_v1140": ICON_PIXEL_MAP}



# Paleta plana (9 tonos opacos + transparente): mismos violetas que v1.10.0,
# más los acentos fríos de Blight Star y el oro de cuello/hombreras/dobladillo.
ICON_PALETTE = {
    ".": (0, 0, 0, 0),
    "K": (12, 5, 18, 255),       # contorno violeta-negro
    "H": (42, 11, 28, 255),     # carmesi muy oscuro
    "D": (66, 24, 70, 255),     # morado desvaido
    "M": (88, 30, 84, 255),     # tono medio
    "L": (112, 52, 108, 255),   # luz del pliegue
    "G": (232, 104, 172, 255),  # rosa encendido (broche / hombreras)
    "W": (255, 222, 238, 255),  # nucleo del broche
    "C": (214, 34, 138, 255),   # magenta Evil Saiyan
    "E": (96, 22, 72, 255),     # veta de energia apagada
    "P": (140, 20, 96, 255),    # microvoxel / chispa de ceniza
}




def build_icon_artwork(size: int = 64) -> Image.Image:
    """Icono 64x64 de PIXEL ART DURO (16x16 -> 4x, Image.NEAREST).

    v1.13.0 recupero la LOGICA VISUAL de la referencia 1: silueta organica,
    5 tonos muy cercanos, contorno duro y acentos minimos. El usuario lo
    APROBO. v1.14.0 conserva esa forma y solo la adapta a la capa nueva:
    carmesi oscuro / morado desvaido / gris ceniza, grietas rosa y magenta,
    dobladillo de 5 puntas y 4 microvoxeles. Sin oro ni cian.

    Todo el detalle vive en ICON_PIXEL_MAP: no hay overlays, degradados,
    antialiasing ni bloom. Solo un rim light discreto de UN pixel, aplicado
    como suma por pixel (no cambia la silueta ni el alfa).
    """
    rows = ICON_PIXEL_MAP
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), "icono base 16x16"
    grid = [list(r) for r in rows]

    px = np.zeros((16, 16, 4), dtype=np.uint8)
    for y in range(16):
        for x in range(16):
            px[y, x] = ICON_PALETTE[grid[y][x]]

    # Rim light de UN pixel en el borde superior/izquierdo del violeta.
    # Se excluyen oro, cian, blanco y contorno para no blanquear el broche.
    opaque = px[..., 3] > 0
    for y in range(16):
        for x in range(16):
            if not opaque[y, x] or grid[y][x] in (".", "K", "G", "W", "C", "E", "P"):
                continue
            if x == 0 or y == 0 or not opaque[y, x - 1] or not opaque[y - 1, x]:
                px[y, x, :3] = np.clip(
                    px[y, x, :3].astype(np.int16) + np.array([24, 8, 22], dtype=np.int16),
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
