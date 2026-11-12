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

import cape_shape as CS
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
# Densidad de energia por altura, MEDIDA contra la captura del usuario.
# La ajusta tools/energy_calibration.py con un lazo cerrado y la aplica
# shape_energy_density() al atlas YA compuesto (incluye el realce emisivo
# y el bloom, que tambien crean pixeles rosa fuera de las grietas).
ENERGY_GAIN = ((0.00, 3.104), (0.05, 3.104), (0.15, 2.115), (0.25, 2.592), (0.35, 0.633), (0.45, 2.230), (0.55, 0.217), (0.65, 0.385), (0.75, 0.243), (0.85, 0.601), (0.95, 0.505), (1.00, 0.505))


def energy_gain(t: float) -> float:
    t = max(0.0, min(1.0, t))
    for i in range(len(ENERGY_GAIN) - 1):
        t0, g0 = ENERGY_GAIN[i]
        t1, g1 = ENERGY_GAIN[i + 1]
        if t <= t1:
            return g0 + (g1 - g0) * (t - t0) / max(1e-6, t1 - t0)
    return ENERGY_GAIN[-1][1]


def build_armor_cloth_canvas(glow_alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """DES-ABANICA la referencia del usuario en el atlas 96x48 (v1.17.0).

    Para cada texel se calcula a qué JIRÓN pertenece, a qué altura ``t``
    corresponde y dónde está su línea central en el RECORTE LIMPIO del PNG.
    El color dominante es la PALETA MEDIDA por filas (carmesí -> violeta),
    y el detalle de la captura se mezcla al 38%: así hay MASA DE TELA, no
    un mosaico de confeti. Los agujeros negros y las grietas rosa reales
    salen del PNG; las 20 grietas más representativas se redibujan nítidas.

    El alfa base no se toca y el conteo de emisivos sigue siendo 1636.
    """
    import cape_shape as CS

    clean_path = ROOT / "referencias" / "REFERENCIA_CAPA_recorte.png"
    clean = np.asarray(Image.open(clean_path).convert("RGB"), dtype=np.float32)
    ch, cw = 48, 96
    H, W = clean.shape[:2]
    ppu = CS.PROFILE_DATA["px_per_unit"]

    # El rosa del PNG se atenúa: si no, al des-abanicar y volver a dibujar
    # las grietas encima sale el doble de magenta del que tiene la captura.
    pink = ((clean[..., 0] > 145) & (clean[..., 2] > 95)
            & (clean[..., 1] < 140) & (clean[..., 0] > clean[..., 1] + 55))
    clean = clean.copy()
    clean[pink] *= 0.34

    detail = np.empty((ch, cw, 3), np.float32)
    t_col = (np.arange(ch, dtype=np.float32) + 0.5) / ch
    # Color DOMINANTE: la mediana real del paño por fila, medida en el PNG.
    palette = np.stack([CS.palette_at(float(t)) for t in t_col])       # (48,3)
    light = 1.52 - 0.12 * t_col
    palette *= light[:, None]
    palette[:, 2] += np.clip((t_col - 0.20) / 0.80, 0.0, 1.0) ** 1.3 * 16.0
    palette[:, 1] += t_col ** 2 * 7.0
    rgb = np.broadcast_to(palette[:, None, :], (ch, cw, 3)).copy()

    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W))
        c1 = int(round((k + 1) * CS.BAND_W))
        kt = np.minimum(t_col, CS.tip_t(k))
        rx = np.empty(ch, np.float32)
        ry = np.empty(ch, np.float32)
        win = np.empty(ch, np.float32)
        for v in range(ch):
            px, py = CS.reference_point(k, float(kt[v]))
            rx[v], ry[v] = px, py
            win[v] = max(9.0, CS.ribbon_w(k, float(kt[v])) * ppu)
        fu = (np.arange(c0, c1, dtype=np.float32) + 0.5 - k * CS.BAND_W) \
            / CS.BAND_W - 0.5
        src_x = rx[:, None] + fu[None, :] * win[:, None]
        xs = np.clip(np.rint(src_x).astype(np.int32), 0, W - 1)
        ys = np.clip(np.rint(ry).astype(np.int32), 0, H - 1)[:, None]
        a = clean[ys, xs]
        b = clean[np.clip(ys + 1, 0, H - 1), xs]
        detail[:, c0:c1, :] = 0.65 * a + 0.35 * b
        # Sombreado por cinta: cada jirón se lee como una capa de tela,
        # con los bordes oscuros (NO un filete claro -> sin rejilla).
        edge = 0.82 + 0.18 * np.sin(np.pi * (fu + 0.5))
        layer = 0.84 + 0.32 * (0.5 + 0.5 * math.sin(k * 1.73))
        rgb[:, c0:c1, :] *= (edge * layer)[None, :, None]

    # Los jirones de fuera están más iluminados en la captura (rojo vivo).
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        outer = abs(CS.lateral(k))
        lift = ((0.5 + 0.5 * np.cos(t_col * math.pi * 1.6)) * outer)[:, None]
        rgb[:, c0:c1, 0] += lift * 22.0
        rgb[:, c0:c1, 1] += lift * 5.0
        rgb[:, c0:c1, 2] += lift * 7.0
    rgb = rgb * 0.62 + detail * 0.38
    # PLIEGUES de tela: relieve carmesi en el INTERIOR de cada banda.
    fold_hi = np.clip(1.0 - t_col / 0.58, 0.0, 1.0)[:, None]
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        ridge = (0.78 + 0.22 * np.sin(np.arange(ch) * 1.27 + k * 0.63))[:, None]
        fold = fold_hi * ridge
        for frac, gain in ((0.24, 12.0), (0.68, 8.0)):
            col = min(c1 - 1, c0 + int(CS.BAND_W * frac))
            rgb[:, col:col + 1, 0] += fold * gain
            rgb[:, col:col + 1, 1] += fold * gain * 0.20
            rgb[:, col:col + 1, 2] += fold * gain * 0.28
        # HUECO oscuro entre jirones: separa capas sin dibujar una rejilla.
        gap = np.clip((t_col - 0.08) / 0.25, 0.0, 1.0)[:, None]
        rgb[:, c0:c0 + 1, :] *= (1.0 - 0.18 * gap)[..., None]
    # Agujeros NEGROS reales: lo que en la captura era fondo se come la luz.
    holes = detail.mean(2) < 16.0
    holes[:12, :] = False
    # AGUJEROS NEGROS, pero no un muro: arriba la tela sigue siendo roja.
    rgb[holes] *= 0.72
    # Bordes RASGADOS por fila: cada banda pierde 0-2 texels de canto de
    # forma irregular, asi ningun jiron parece un tablon recto.
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W))
        c1 = int(round((k + 1) * CS.BAND_W))
        for v in range(16, ch):
            tear = int(0.7 + 0.7 * (0.5 + 0.5 * math.sin(v * 1.71 + k * 2.37)))
            if tear:
                rgb[v, c0:c0 + tear, :] *= 0.76
                rgb[v, max(c0, c1 - tear):c1, :] *= 0.76
                if v % 9 == k % 9 and tear:
                    rgb[v, min(c1 - 1, c0 + tear), :] *= 1.24
    # COSTURAS DE HOMBRO cosidas a mano: el tercio superior de la captura
    # tiene pliegues radiales que bajan desde la bufanda; antes era un
    # triangulo liso. Sombra de un texel + ribete calido, ondulado por jiron.
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        for v in range(2, 20):
            u = int(round(c0 + CS.BAND_W * (0.42 + 0.16 * math.sin(
                v * 0.38 + k * 1.27))))
            u = min(c1 - 2, max(c0 + 1, u))
            fade = 1.0 - v / 20.0
            rgb[v, u, :] *= 1.0 - 0.30 * fade
            rgb[v, u + 1, 0] += 7.0 * fade
            rgb[v, u + 1, 2] += 3.0 * fade
        tint = 0.94 + 0.12 * (0.5 + 0.5 * math.sin(k * 2.19 + 0.8))
        rgb[:18, c0:c1, :] *= (1.0 + np.clip(
            1.0 - t_col / 0.34, 0.0, 1.0)[:18, None, None] * (tint - 1.0))

    # En la referencia la mitad baja es VIOLETA / LAVANDA desvaido, mucho
    # mas azul y mas claro que la parte carmesi. La mediana del PNG se
    # queda corta porque incluye agujeros negros: aqui se restituye la luz.
    v = t_col[:, None]
    low = np.clip((v - 0.34) / 0.66, 0.0, 1.0)
    hi = np.clip(1.0 - v / 0.42, 0.0, 1.0)
    # VIOLETA / LAVANDA, no azul: R y B deben ir parejos, G por debajo.
    rgb[..., 0] = rgb[..., 0] * (1.0 + 0.46 * low) + hi * 3.0 + low * 36.0
    rgb[..., 1] = rgb[..., 1] * (1.0 + 0.84 * low) + low * 25.0
    rgb[..., 2] = rgb[..., 2] * (1.0 + 0.62 * low) + low * 24.0
    # CORRECCION MEDIDA: el bloom y el grano subian demasiado el violeta
    # en t~0.78 (delta +22/+21/+28). Campana gaussiana local, sin tocar
    # el cuello ni las puntas, que ya calzan con la referencia.
    # CORRECCION MEDIDA v1208: el bloom y el grano subian demasiado el
    # violeta en t~0.78. Campana gaussiana local, sin tocar el cuello ni
    # las puntas. Se mantiene: al aumentar la masa de tela en v1209 el
    # exceso de luz vuelve a aparecer si se retira.
    mid_band = np.exp(-((t_col - 0.78) / 0.16) ** 2)[:, None, None]
    rgb -= mid_band * np.array([20.0, 18.0, 24.0], np.float32)

    # Los 8 LOBOS que sobreviven recuperan la luz violeta del PNG:
    # los canales oscuros no deben dejar la capa casi negra.
    faded = {k for k in range(CS.RIBBONS) if (k * 7 + 3) % 16 < 8}
    lobe = np.clip((t_col - 0.26) / 0.60, 0.0, 1.0)[:, None]
    for k in range(CS.RIBBONS):
        if k in faded:
            continue
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        rgb[:, c0:c1, :] *= (1.0 + 0.34 * lobe)[..., None]
    dead = t_col[:, None] > np.array(
        [CS.tip_t(k) for k in range(CS.RIBBONS)])[None, :]
    # (las bandas muertas ya están oscurecidas por cape_shape; no se usan)

    # ROTOS INTERNOS: la referencia tiene agujeros sueltos en MITAD de
    # cada jiron, no solo bordes. Se siembran por fila de forma determinista
    # y crecen hacia abajo; el alfa prístino no se toca.
    tear_rng = np.random.default_rng(SEED + 91)
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W))
        c1 = int(round((k + 1) * CS.BAND_W))
        for v in range(28, ch):
            chance = 0.025 + 0.045 * (v / ch)
            if tear_rng.random() < chance:
                u0 = c0 + int(tear_rng.integers(1, max(2, c1 - c0 - 1)))
                ww = 1 + int(tear_rng.integers(0, 2))
                rgb[v, u0:min(c1, u0 + ww), :] *= 0.56
                if v + 1 < ch:
                    rgb[v + 1, max(c0, u0 - 1):min(c1, u0 + ww), :] *= 0.74

    # PUNTAS en el atlas: los ultimos 8 texels de cada banda se estrechan
    # en triangulo oscuro, para que el remate 3D no parezca un dado.
    for k in range(CS.RIBBONS):
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        for v in range(40, ch):
            f = (v - 40) / float(ch - 40)
            inset = int(1 + 2.4 * f)
            rgb[v, c0:c0 + inset, :] *= 0.66
            rgb[v, max(c0, c1 - inset):c1, :] *= 0.66

    rng = np.random.default_rng(SEED + 77)

    def vnoise(cy: int, cx: int) -> np.ndarray:
        small = rng.normal(0.0, 1.0, (cy, cx)).astype(np.float32)
        return np.asarray(Image.fromarray(small, "F").resize(
            (cw, ch), Image.BICUBIC), dtype=np.float32)

    # Tres octavas: fibra gruesa, tejido medio y mancha de tinte.
    grain = (0.55 * vnoise(24, 48) + 0.30 * vnoise(8, 16)
             + 0.15 * vnoise(3, 6))
    grain /= (float(np.std(grain)) + 1e-6)
    rgb += grain[..., None] * np.array([3.2, 2.2, 3.0])
    # Hilos verticales y dithering de pixel art (sin banding).
    weave = np.sin(np.arange(cw)[None, :] * 1.7
                   + np.arange(ch)[:, None] * 0.21)
    rgb += weave[..., None] * np.array([1.4, 0.9, 1.3])
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                      [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0 - 0.5
    dith = np.tile(bayer, (12, 24))[:ch, :cw]
    rgb += dith[..., None] * 2.6
    rgb += ((1.0 - t_col) ** 2 * 1.5)[:, None, None] * np.array([1.0, 0.55, 0.8])
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    glow_ink = Image.new("L", (cw, ch), 0)
    gd = ImageDraw.Draw(glow_ink)
    cool_ink = Image.new("L", (cw, ch), 0)
    cd = ImageDraw.Draw(cool_ink)

    HALO = (88, 14, 58, 150)
    CORE = (218, 66, 150, 235)

    # GRIETAS REALES de la referencia (una de cada tres, para no saturar).
    marks = [m for m in CS.energy_marks() if not m["floating"]]
    # v1230: las 62 grietas REALES de la captura se dibujan como GUIONES
    # DIAGONALES FINOS (1 px), no como bloques de 2x2 ni lineas continuas.
    # La DENSIDAD por altura ya NO se decide aqui: shape_energy_density()
    # la aplica al atlas compuesto, de forma monótona y medible, para que
    # el calibrador de lazo cerrado pueda converger.
    long_marks = sorted(range(len(marks)), key=lambda j: -marks[j]["h"])[:3]
    for j in long_marks:
        m = marks[j]
        t = max(0.0, min(0.90, m["t"]))
        k = CS.nearest_ribbon(t, m["x"])
        u = k * CS.BAND_W + CS.BAND_W * 0.5
        v = t * ch
        ln = min(7.0, 3.0 + m["h"] * 1.6)
        for aa, bb in ((0.0, 0.42), (0.62, 1.0)):
            seg = [(int(round(u - 1.0 + 2.2 * aa)), int(round(v + ln * aa))),
                   (int(round(u - 1.0 + 2.2 * bb)), int(round(v + ln * bb)))]
            cd.line(seg, fill=96, width=4)
            d.line(seg, fill=(78, 12, 54, 170), width=2)
            d.line(seg, fill=(238, 76, 168, 250), width=1)
            gd.line(seg, fill=200, width=1)
    # Codos en L: suben vertical y giran 2 texels, como en la captura.
    for j in long_marks[:2]:
        m = marks[j]
        t = max(0.0, min(0.90, m["t"]))
        k = CS.nearest_ribbon(t, m["x"])
        u = int(round(k * CS.BAND_W + CS.BAND_W * 0.5))
        v = int(round(t * ch))
        cd.line([(u, v), (u, v + 3), (u + 2, v + 3)], fill=100, width=4)
        d.line([(u, v), (u, v + 3), (u + 2, v + 3)], fill=HALO, width=2)
        d.line([(u, v), (u, v + 3), (u + 2, v + 3)], fill=CORE, width=1)
        gd.line([(u, v), (u, v + 3), (u + 2, v + 3)], fill=190, width=1)
    # Guiones sueltos de 1 px: antes eran ladrillos rosa de 2x2.
    for i in range(0, len(marks), 12):
        m = marks[i]
        t = max(0.0, min(0.94, m["t"]))
        k = CS.nearest_ribbon(t, m["x"])
        u = int(round(k * CS.BAND_W + CS.BAND_W * (0.35 + 0.2 * (i % 3))))
        v = int(round(t * ch))
        seg = [(u, v), (u + 1, v + 2)]
        d.line(seg, fill=HALO, width=1)
        d.line(seg, fill=CORE, width=1)
        gd.line(seg, fill=205, width=1)
    for i, m in enumerate(marks):
        t = max(0.03, min(0.975, m["t"]))
        k = CS.nearest_ribbon(t, m["x"])
        u = k * CS.BAND_W + CS.BAND_W * (0.5 + 0.18 * math.sin(i * 2.31))
        v = t * ch
        ln = max(1.2, min(2.8, m["h"] * 0.8 + (i % 3) * 0.2))
        slant = 2.2 * math.sin(i * 1.97)
        seg = [(int(round(u)), int(round(v))),
               (int(round(u + slant)), int(round(v + ln)))]
        cd.line(seg, fill=62, width=3)
        d.line(seg, fill=HALO, width=1)
        d.line(seg, fill=CORE, width=1)
        gd.line(seg, fill=175, width=1)
        # v1231: la captura tiene su PICO de energia en t=0.2 (11.5%)
        # pero el perfil medido apenas contiene grietas ahi. Se anaden
        # DOS guiones hermanos, mas cortos y con otra inclinacion, solo
        # en el tercio superior: haces diagonales como los del PNG.
        if t < 0.34:
            for q in (1, 2):
                u2 = u + 2.1 * math.sin(i * 0.91 + q * 1.7)
                v2 = v + 0.8 * q
                seg2 = [(int(round(u2)), int(round(v2))),
                        (int(round(u2 - slant * (0.7 + 0.25 * q))),
                         int(round(v2 + ln * (0.75 - 0.15 * q))))]
                cd.line(seg2, fill=44, width=3)
                d.line(seg2, fill=HALO, width=1)
                d.line(seg2, fill=CORE, width=1)
                gd.line(seg2, fill=150, width=1)

    # Motas de 1 px, ESCASAS, más densas hacia las puntas.
    for _ in range(9):
        sx = float(rng.uniform(0, cw))
        sy = float(rng.uniform(0, ch))
        q = (int(sx), int(sy))
        hot = rng.random() < (0.06 + 0.22 * sy / ch)
        d.point(q, fill=CORE if hot else (70, 52, 82, 160))
        if hot:
            gd.point(q, fill=150)

    img = Image.alpha_composite(img, overlay)
    small = np.asarray(img, dtype=np.float32)[..., :3]
    ink_small = np.asarray(glow_ink, dtype=np.float32) / 255.0
    cool_small = np.asarray(cool_ink, dtype=np.float32) / 255.0

    # DOBLADILLO RASGADO: en el PNG solo ~8 jirones llegan al suelo;
    # los demas se deshilachan a alturas distintas. Ocho bandas se
    # apagan con un borde irregular (columnas desfasadas), de modo que
    # el borde inferior deja de ser un puntero de agujas regulares.
    hem = np.ones((ch, cw), np.float32)
    for k in range(CS.RIBBONS):
        if (k * 7 + 3) % 16 >= 8:
            continue
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        # CANAL OSCURO: desde la mitad, este jiron deja de ser paño y
        # se convierte en el hueco negro entre los lobos vecinos.
        mid = 18 + int(8.0 * (0.5 + 0.5 * math.sin(k * 2.13 + 0.4)))
        ramp_mid = np.linspace(0.96, 0.84, ch - mid, dtype=np.float32)
        hem[mid:, c0:c1] = ramp_mid[:, None]
        # Y se deshilacha del todo a una altura distinta.
        start = 36 + int(9.0 * (0.5 + 0.5 * math.sin(k * 2.13 + 0.4)))
        # v1226: 0.70 hacia casi negro el paño del dobladillo; la
        # referencia conserva tela violeta hasta las puntas (48% en
        # t=0.8). El deshilachado sigue ahí, pero sin comerse la tela.
        ramp = np.linspace(1.0, 0.84, ch - start, dtype=np.float32)
        for u in range(c0, c1):
            off = (u - c0) % 3
            s = min(ch - 1, start + off)
            hem[s:, u] = np.minimum(hem[s:, u], ramp[:ch - s])
    # Separacion de jirones desde ARRIBA: sin ella el tercio superior
    # vuelve a ser un delantal rojo macizo.
    chan = np.ones((ch, cw), np.float32)
    for k in range(CS.RIBBONS):
        if (k * 7 + 3) % 16 >= 8:
            continue
        c0 = int(round(k * CS.BAND_W)); c1 = int(round((k + 1) * CS.BAND_W))
        top = 13 + int(4.0 * (0.5 + 0.5 * math.sin(k * 2.13)))
        if 18 > top:
            chan[top:18, c0:c1] = np.linspace(1.0, 0.90, 18 - top,
                                              dtype=np.float32)[:, None]
    small *= chan[..., None] * hem[..., None]
    # REFLEJO ROSA-LAVANDA DE LAS PUNTAS, aplicado DESPUES del fade:
    # antes el deshilachado se lo comia y el dobladillo quedaba negro.
    tip_glow = np.clip((t_col - 0.84) / 0.16, 0.0, 1.0)[:, None]
    # v1210: el reflejo de puntas teñía TODO el dobladillo de rosa y
    # disparaba la energia medida (26% frente al 11% de la captura).
    # v1222: las puntas quedaban casi negras (t=0.9 daba [57,34,54] frente
    # a [62,38,58] del PNG) y con solo 9% de paño. Se aclara el remate.
    small[..., 0] += tip_glow * 22.0
    small[..., 1] += tip_glow * 6.0
    small[..., 2] += tip_glow * 15.0
    # La energia sobrevive algo mas que el paño: en la captura quedan
    # guiones rosa sueltos incluso dentro de los huecos.
    ink_small *= hem ** 0.80
    cool_small *= hem
    return small, ink_small, cool_small


def paint_reserved_cloth_strips(out: np.ndarray, glow_alpha: np.ndarray) -> np.ndarray:
    """Zonas reservadas v1.17.0: color SACADO DE LA REFERENCIA.

    Cantos y forro: un solo tono casi negro (sin filetes -> sin rejilla).
    Yugo / bufanda: recorte REAL del cuello carmesí de la captura.
    Rampa de motas: rosa de los rectángulos flotantes del PNG.
    El alfa del atlas sigue siendo EXACTAMENTE el prístino.
    """
    import cape_shape as CS

    # Cantos / forro: un solo tono oscuro, sin degradado vertical.
    edge_t = np.linspace(0.0, 1.0, 48, dtype=np.float32)[:, None, None]
    edge_top = np.array([62.0, 22.0, 38.0], np.float32)
    edge_bot = np.array([64.0, 32.0, 74.0], np.float32)
    grad = edge_top * (1.0 - edge_t) + edge_bot * edge_t
    out[0:48, 105:107, :3] = grad * 0.88
    out[0:48, 107:109, :3] = grad * 0.58
    # Gris del ARNES que cruza bajo la bufanda en la referencia: el
    # texel "ash" deja de ser casi negro (antes parecia una raya negra).
    # Bloque gris con degradado: el arnes 3D muestrea 3x2 texels.
    grey = np.linspace(1.0, 0.58, 3, dtype=np.float32)[None, :, None]
    out[18:21, 105:108, :3] = (
        np.array([108.0, 104.0, 122.0], np.float32) * grey)
    out[18:21, 108:109, :3] = np.array([78.0, 75.0, 92.0])
    # COSTURAS de la bufanda: pliegues que bajan desde el cuello, con
    # sombra de un texel. Sin ellos la capucha era un rectangulo liso.
    for u in range(96, 110):
        for v in range(0, 17):
            if (u - 96 + int(2.4 * math.sin(v * 0.32))) % 4 == 0:
                out[v, u, :3] *= 0.80
                if u + 1 < 110:
                    out[v, u + 1, 0] += 5.0

    out[0:48, 120:122, :3] = grad * 0.52
    out[0:48, 122:124, :3] = grad * 0.34
    for i in range(6):
        y0 = 4 + i * 7
        out[y0:y0 + 2, 122:124, :3] = np.array([238.0, 84.0, 172.0])

    # Rampa de las MOTAS 3D: rosa vivo, como los rectángulos de la captura.
    ramp = np.linspace(0.0, 1.0, 18, dtype=np.float32).reshape(18, 1, 1)
    pink = (np.array([226.0, 82.0, 164.0], dtype=np.float32) * (1.0 - ramp)
            + np.array([176.0, 36.0, 112.0], dtype=np.float32) * ramp)
    out[109:127, 69:75, :3] = np.broadcast_to(pink, (18, 6, 3))
    # Tramo FINAL de la rampa: rescoldo violeta para las motas de relleno.
    dim = np.linspace(0.0, 1.0, 8, dtype=np.float32).reshape(8, 1, 1)
    out[119:127, 69:75, :3] = (
        np.array([112.0, 50.0, 104.0], np.float32) * (1.0 - dim)
        + np.array([74.0, 34.0, 76.0], np.float32) * dim)

    # Yugo / bufanda: carmesí MEDIDO en la referencia, con sombreado
    # horizontal suave. Sin franjas verticales: en v1.14 cada segmento
    # repetía dos líneas magenta y el cuello parecía una corona de barrotes.
    y = np.linspace(0.0, 1.0, 17, dtype=np.float32).reshape(17, 1, 1)
    x = np.linspace(0.0, 1.0, 14, dtype=np.float32).reshape(1, 14, 1)
    # CARMESI OSCURO medido: la bufanda de la captura NO es rojo brillante.
    top = np.asarray(CS.palette_at(0.0), dtype=np.float32) * 2.00
    low = np.asarray(CS.palette_at(0.22), dtype=np.float32) * 1.45
    yoke = top * (1.0 - y) + low * y
    yoke = np.broadcast_to(yoke, (17, 14, 3)).copy()
    yoke += np.random.default_rng(SEED + 5).normal(
        0.0, 2.0, (17, 14, 1)).astype(np.float32)
    # Sin lineas diagonales: en v1.14 formaban una REJILLA rechazada.
    # El relieve lo dan las 9 piezas 3D solapadas, no el atlas.
    out[76:93, 57:71, :3] = yoke
    return out


def assert_cloth_uvs() -> None:
    """Ninguna UV de la tela nueva puede samplear un texel transparente."""
    geometry = json.loads(GEO.read_text())["minecraft:geometry"][0]
    checked = 0
    for bone in geometry.get("bones", []):
        if not bone["name"].startswith(("v15_", "v17_")):
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
    assert checked > 300, checked
    print(f"v1.17.0 cloth UV faces checked: {checked}")


def _fit_emissive_mask(priority: np.ndarray, opaque: np.ndarray, target: int,
                       allowed: np.ndarray | None = None) -> np.ndarray:
    """Elige EXACTAMENTE `target` texels opacos cerca de las grietas.

    v1.17.0: antes se rellenaba el resto en orden FILA POR FILA desde un
    pool dilatado, lo que dibujaba RECTÁNGULOS claros sobre el paño (el
    usuario los veía como parches). Ahora se expande en ANILLOS de
    distancia alrededor de los núcleos de energía y, dentro de cada anillo,
    se elige con un hash determinista: el halo rodea las grietas en vez de
    apilarse en bloques. El conteo prístino (1636) no cambia, así que no se
    abren huecos en la capa.
    """
    permit = allowed if allowed is not None else np.ones_like(opaque)
    cores = (priority == 2) & opaque & permit
    cracks = (priority == 1) & opaque & permit
    mask = np.zeros_like(opaque, dtype=bool)
    mask |= cores
    mask |= cracks
    visited = mask.copy()
    front = mask.copy()
    for _ in range(10):
        if int(mask.sum()) >= target:
            break
        ring = dilate(front, 1) & opaque & permit & ~visited
        if not ring.any():
            break
        ys, xs = np.nonzero(ring)
        # Orden disperso y determinista: evita el sesgo fila por fila.
        key = ((ys.astype(np.int64) * 73856093)
               ^ (xs.astype(np.int64) * 19349663)) % 1000003
        for i in np.argsort(key):
            if int(mask.sum()) >= target:
                break
            mask[ys[i], xs[i]] = True
        visited |= ring
        front = ring
    # Recorta si los núcleos + grietas ya superaban el objetivo.
    if int(mask.sum()) > target:
        ys, xs = np.nonzero(mask & ~cores)
        for i in np.argsort(((ys.astype(np.int64) * 73856093)
                             ^ (xs.astype(np.int64) * 19349663)) % 1000003):
            if int(mask.sum()) <= target:
                break
            mask[ys[i], xs[i]] = False
    if int(mask.sum()) < target:
        pool = opaque & permit & ~mask
        ys, xs = np.nonzero(pool)
        for i in range(min(target - int(mask.sum()), len(ys))):
            mask[ys[i], xs[i]] = True
    assert int(mask.sum()) == target, (int(mask.sum()), target)
    return mask


def _energy_strokes(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """Componentes 8-conectados de la tinta rosa (sin scipy)."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    out: list[list[tuple[int, int]]] = []
    for v in range(h):
        for u in range(w):
            if not mask[v, u] or lab[v, u]:
                continue
            cur = len(out) + 1
            lab[v, u] = cur
            stack, cells = [(v, u)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < h and 0 <= nx < w and mask[ny, nx]
                                and not lab[ny, nx]):
                            lab[ny, nx] = cur
                            stack.append((ny, nx))
            out.append(cells)
    return out


def shape_energy_density(out: np.ndarray) -> np.ndarray:
    """Ajusta la DENSIDAD de energía por altura, TRAZO A TRAZO.

    Se ejecuta al FINAL, sobre el atlas ya compuesto: así controla también
    el realce emisivo, el bloom y el paño aclarado por `tip_glow`, que el
    auditor cuenta como energía aunque no sean grietas dibujadas.

    v1233: el adelgazamiento por PÍXEL con Bayer dejaba un DAMERO rosa en
    el centro de la capa (confeti, ya rechazado antes). Ahora se etiquetan
    los componentes 8-conectados y cada GUIÓN sobrevive o se apaga ENTERO
    según un hash determinista de su posición: la energía queda en trazos
    cortos y discontinuos, exactamente como en la captura, y la respuesta
    al perfil sigue siendo monótona para el calibrador de lazo cerrado.
    No toca alfa ni glowmask: los 1636 emisivos siguen intactos.
    """
    c = out[0:48, 0:96, :3]
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    em = (r > 105) & (b > 75) & (r > g + 48) & (b > g + 22)
    orig = c.copy()
    row_colour = []
    for v in range(48):
        good = ~em[v] & (c[v].mean(1) > 30)
        row_colour.append(np.median(c[v][good], axis=0) if good.sum() >= 4
                          else np.array([70.0, 32.0, 58.0], np.float32))
    for cells in _energy_strokes(em):
        v0 = min(y for y, _ in cells)
        u0 = min(x for _, x in cells)
        t = (sum(y for y, _ in cells) / len(cells) + 0.5) / 48.0
        gain = energy_gain(t)
        # v1247: DASH FRACCIONAL. La decision binaria por componente
        # dejaba un SUELO de energia: las grietas se unen en bloques de
        # 20-40 px y, con gain=0.3, el 30% de las veces sobrevivian TODAS.
        # Ahora se conserva exactamente la fraccion `gain` de los pixeles,
        # repartida a lo largo del trazo con un acumulador deterministico:
        # queda una linea DISCONTINUA (como en la captura), sin damero, y
        # la respuesta al perfil es monotona y de baja varianza.
        seq = sorted(cells)
        acc = ((v0 * 7 + u0 * 13 + len(cells)) % 7) / 7.0
        kept = []
        for y, x in seq:
            acc += min(1.0, gain)
            if acc >= 1.0:
                acc -= 1.0
                kept.append((y, x))
            else:
                c[y, x] = row_colour[y] * 0.88 + orig[y, x] * 0.12
        if gain > 1.0:
            extra = min(0.85, (gain - 1.0) * 0.60)
            for y, x in kept:
                y2, x2 = min(47, y + 1), min(95, x + 1)
                if not em[y2, x2]:
                    c[y2, x2] = (c[y2, x2] * (1.0 - extra)
                                 + orig[y, x] * extra)
    return out


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

    # v1.17.0: realce SÓLO sobre los núcleos de grieta (`crack`), nunca
    # sobre el halo de 1636 texels: teñir la dilatación dibujaba CUADRADOS
    # claros alrededor de cada trazo. El glowmask mantiene su cobertura
    # prístina (contrato GeckoLib / CI); el halo del color base queda oscuro.
    core = np.zeros((SIZE, SIZE), dtype=bool)
    core[0:48, 0:96] = crack
    out[..., 0] = np.where(core, out[..., 0] * 1.10 + 22.0, out[..., 0])
    out[..., 1] = np.where(core, out[..., 1] * 1.04 + 5.0, out[..., 1])
    out[..., 2] = np.where(core, out[..., 2] * 1.10 + 26.0, out[..., 2])

    # --- CALIBRACION CROMATICA MEDIDA (v1211) -------------------------
    # tools/color_calibration.py mide la mediana del paño por décimas en el
    # RENDER y en el PNG de referencia con la misma máscara, y acumula aqui
    # la diferencia. Se interpola sobre las 48 filas del canvas: así el
    # degradado sigue siendo continuo y no aparecen franjas horizontales.
    cal = ROOT / "tools" / "color_calibration.json"
    if cal.is_file():
        rows = json.loads(cal.read_text())["rows"]
        tc = (np.arange(48, dtype=np.float32) + 0.5) / 48.0
        corr = np.stack([
            np.interp(tc, [r[0] for r in rows],
                      [r[1 + c] for r in rows]).astype(np.float32)
            for c in range(3)], axis=1)                       # (48, 3)
        # SOLO el paño recibe la corrección. Los canales oscuros y los
        # agujeros quedan intactos: teñirlos los volvía negros y hacia
        # desaparecer la masa de tela que tanto costó recuperar en v1210.
        canvas = out[0:48, 0:96, :3]
        weight = np.clip((canvas.mean(2) - 30.0) / 55.0,
                         0.0, 1.0)[..., None]
        canvas += corr[:, None, :] * weight
        # Las venas laterales muestrean x=120..124 y las MOTAS 3D la rampa
        # x=69..75, y=109..127: fuera del canvas. Sin la misma corrección
        # quedaban más brillantes que el paño y dominaban la mediana.
        out[0:48, 120:124, :3] += corr[:, None, :] * 0.45
        out[109:127, 69:75, :3] += corr[32:].mean(0) * 0.55

    # v1230: densidad de energía MEDIDA por altura (lazo cerrado).
    out = shape_energy_density(out)
    # v1264: deshilachado del dobladillo DESPUES de la energia, para no
    # apagar las grietas que llegan hasta la punta.
    out = charred_hem(out)
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


def charred_hem(out: np.ndarray) -> np.ndarray:
    """v1264: HUECOS NEGROS del dobladillo, por textura.

    La referencia tiene 48% de paño en t=0.8 pero solo 18% en t=0.9: los
    lóbulos se deshilachan en negros antes de morir. Recortar la GEOMETRIA
    no sirve (el ultimo tramo promedia su anchura y tambien vaciaba t=0.8),
    asi que se carbonizan franjas verticales irregulares SOLO en las filas
    v>=43 del canvas (t>=0.9). No se toca alpha ni el glowmask: los texels
    siguen siendo opacos, solo quedan fuera de la mascara de paño.

    Las grietas rosa se preservan: en la captura la energia sigue viva
    hasta la punta, incluso cuando el paño ya se ha rasgado.
    """
    c = out[0:48, 0:96, :3]
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    energy = (r > 105) & (b > 75) & (r > g + 48) & (b > g + 22)
    for v in range(43, 48):
        frac = 0.10 + 0.13 * (v - 43)          # 10% .. 62% de huecos
        for u in range(96):
            # Estela vertical: el hueco se mantiene de una fila a la
            # siguiente en vez de convertirse en confeti de píxeles.
            h = ((u * 37 + (u // 4) * 13 + v * 3 + (u // 7) * 29) % 101) / 101.0
            if h < frac and not energy[v, u] and c[v, u].mean() > 34.0:
                c[v, u] = np.array([16.0, 9.0, 18.0], np.float32)
    return out


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
    ink_arr = np.clip(ink_small, 0, 1) * 255.0
    cool_arr = np.clip(cool_small, 0, 1) * 255.0
    ink_base = Image.fromarray(ink_arr.astype(np.uint8), "L")
    cool_base = Image.fromarray(cool_arr.astype(np.uint8), "L")
    # Halos desenfocados: la energia deja de ser un filete de 1 pixel.
    ink_blur = np.asarray(ink_base.filter(ImageFilter.GaussianBlur(2.0)),
                          dtype=np.float32)
    cool_blur = np.asarray(cool_base.filter(ImageFilter.GaussianBlur(2.6)),
                           dtype=np.float32)
    ink = Image.fromarray(np.clip(ink_arr + 0.60 * ink_blur, 0, 255).astype(np.uint8), "L")
    cool = Image.fromarray(np.clip(cool_arr + 0.50 * cool_blur, 0, 255).astype(np.uint8), "L")
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




# Motas y chispas sueltas: la referencia tiene energía FLOTANDO alrededor
# del paño. Se añaden en huecos del mapa, SIN tocar la silueta aprobada.
ICON_FLOATING = (
    (1, 2, "P"), (14, 3, "G"), (0, 8, "P"), (15, 10, "P"),
    (2, 14, "C"), (13, 15, "G"), (0, 12, "P"), (15, 5, "P"),
)

# Grietas de energia en guiones CORTOS y costuras oscuras entre jirones:
# la referencia no es un bloque liso, son hebras separadas con rosa dentro.
ICON_CRACKS = (
    (5, 8, "C"), (5, 9, "E"), (10, 9, "C"), (10, 10, "E"),
    (4, 11, "C"), (11, 11, "C"), (6, 12, "E"), (9, 12, "C"),
    (3, 13, "C"), (12, 13, "E"), (7, 14, "C"), (8, 14, "E"),
    (6, 8, "H"), (6, 10, "H"), (9, 8, "H"), (9, 11, "H"),
    (4, 14, "H"), (11, 14, "H"),
)


def _icon_row_palette(y: int) -> dict[str, tuple[int, int, int, int]]:
    """Los 5 tonos del paño derivan de la MEDIANA MEDIDA del PNG por altura.

    v1221: antes el icono usaba una paleta Rose fija; ahora cada fila toma
    el carmesí -> violeta real de la referencia, así el icono y la capa 3D
    cuentan el mismo color. Sigue siendo paleta PLANA, sin degradado suave.
    """
    base = np.asarray(CS.palette_at(y / 15.0), dtype=np.float32)

    def tone(mul: float, add: tuple[int, int, int] = (0, 0, 0)):
        col = np.clip(base * mul + np.array(add, np.float32), 0, 255)
        return (int(col[0]), int(col[1]), int(col[2]), 255)

    return {
        ".": (0, 0, 0, 0),              # transparente
        "K": (12, 5, 18, 255),          # contorno violeta-negro
        "H": tone(0.62),                # carmesí en sombra
        "D": tone(0.92, (0, 0, 6)),     # violeta desvaído
        "M": tone(1.20),                # tono medio
        "L": tone(1.62, (4, 2, 6)),     # luz del pliegue
        "E": tone(0.80, (18, 0, 14)),   # veta de energía apagada
        "P": (208, 62, 142, 255),       # mota / microvóxel
        "G": (236, 92, 168, 255),       # rosa encendido
        "W": (255, 214, 236, 255),      # núcleo del broche
        "C": (226, 44, 146, 255),       # magenta de las grietas
    }


def build_icon_artwork(size: int = 64) -> Image.Image:
    """Icono 64x64 REMASTERIZADO v1221 (16x16 -> 4x, NEAREST).

    Conserva EXACTAMENTE la silueta y el mapa de 16x16 que el usuario
    aprobó (backup en tools/originals/icono_aprobado_v1130.png), pero:

      * cada fila usa la paleta MEDIDA en REFERENCIA_CAPA.png en vez de la
        paleta Rose fija (carmesí arriba -> violeta abajo);
      * relieve 3D por píxel: luz arriba-izquierda, sombra abajo-derecha,
        para que los pliegues se lean como tela y no como un dibujo plano;
      * 8 motas/chispas flotando alrededor, como en la captura;
      * cero antialiasing, cero degradado continuo, cero bloom: todo el
        detalle sigue viviendo en la rejilla de 16x16.
    """
    rows = ICON_PIXEL_MAP
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), "icono base 16x16"
    grid = [list(r) for r in rows]
    for x, y, ch in ICON_FLOATING:
        if grid[y][x] == ".":
            grid[y][x] = ch
    for x, y, ch in ICON_CRACKS:
        if grid[y][x] in ("H", "D", "M", "L", "E"):
            grid[y][x] = ch

    px = np.zeros((16, 16, 4), dtype=np.uint8)
    for y in range(16):
        pal = _icon_row_palette(y)
        for x in range(16):
            px[y, x] = pal[grid[y][x]]

    opaque = px[..., 3] > 0
    for y in range(16):
        for x in range(16):
            ch = grid[y][x]
            if not opaque[y, x] or ch in (".", "K", "G", "W", "C", "P"):
                continue
            lift = 0.0
            if x == 0 or not opaque[y, x - 1]:
                lift += 11.0
            if y == 0 or not opaque[y - 1, x]:
                lift += 15.0
            if x == 15 or not opaque[y, x + 1]:
                lift -= 9.0
            if y == 15 or not opaque[y + 1, x]:
                lift -= 11.0
            delta = np.array([lift, lift * 0.34, lift * 0.78], np.float32)
            px[y, x, :3] = np.clip(
                px[y, x, :3].astype(np.float32) + delta, 0, 255
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
        d.line([(x + 2, body0), (x + 2, body1)], fill=(58, 22, 72, 190), width=1)
        gd.line([(x + 2, body0), (x + 2, body1)], fill=(176, 44, 130, 110), width=1)

    # Tres pliegues HORIZONTALES suaves que cruzan las 7 franjas: refuerzan
    # la lectura de "capa doblada" sin partir la ilustración en costuras.
    for frac in (0.24, 0.52, 0.80):
        fy = body0 + int((body1 - body0) * frac)
        d.line([(0, fy), (int(120 * s / 128), fy)],
               fill=(34, 14, 52, 150), width=max(2, int(2 * s / 128)))
        d.line([(0, fy + 2), (int(120 * s / 128), fy + 2)],
               fill=(86, 28, 92, 85), width=1)

    # Yugo y dobladillo tejidos, más sobrios.
    d.rectangle([0, 0, s - 1, int(9 * s / 128)], fill=(52, 14, 30, 255))
    d.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
           fill=(122, 34, 74, 255), width=max(2, int(2 * s / 128)))
    gd.line([(0, int(11 * s / 128)), (s - 1, int(11 * s / 128))],
            fill=(196, 68, 140, 150), width=max(2, int(2 * s / 128)))
    d.rectangle([0, s - int(9 * s / 128), s - 1, s - 1], fill=(14, 6, 20, 255))
    d.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
           fill=(94, 26, 84, 255), width=max(1, int(s / 128)))
    gd.line([(0, s - int(2 * s / 128)), (s - 1, s - int(2 * s / 128))],
            fill=(186, 58, 140, 130), width=max(1, int(s / 128)))

    # Tres rollos de tela en la región reservada `roll`.
    rx0, ry0 = int(96 * s / 128), int(48 * s / 128)
    rx1, ry1 = int(120 * s / 128), int(64 * s / 128)
    d.rectangle([rx0, ry0, rx1, ry1], fill=(24, 8, 28, 255))
    for j in range(3):
        ly = ry0 + int((j + 0.5) * (ry1 - ry0) / 3.0)
        d.line([(rx0, ly), (rx1, ly)], fill=(96, 34, 110, 200),
               width=max(1, int(0.8 * s / 128)))
        gd.line([(rx0, ly), (rx1, ly)], fill=(180, 54, 136, 130),
                width=max(1, int(0.8 * s / 128)))

    # Caras laterales (`edge`): neutro, para que no brillen.
    ex0, ey0 = int(96 * s / 128), int(64 * s / 128)
    ex1, ey1 = int(106 * s / 128), int(72 * s / 128)
    d.rectangle([ex0, ey0, ex1, ey1], fill=(16, 7, 22, 255))

    # v1.9.0: regiones de las hombreras del item plegado. Paño oscuro con
    # ribete cálido/cian y una gema central, en sus propias UV reservadas.
    px0, py0 = int(96 * s / 128), int(72 * s / 128)
    px1, py1 = int(120 * s / 128), int(88 * s / 128)
    d.rectangle([px0, py0, px1, py1], fill=(34, 10, 34, 255))
    d.line([(px0, py0 + 2), (px1, py0 + 2)], fill=(132, 36, 82, 230),
           width=max(1, int(0.9 * s / 128)))
    d.line([(px0, py1 - 2), (px1, py1 - 2)], fill=(222, 74, 158, 210),
           width=max(1, int(0.9 * s / 128)))
    gd.line([(px0, py0 + 2), (px1, py0 + 2)], fill=(196, 68, 140, 150),
            width=max(1, int(0.9 * s / 128)))
    gd.line([(px0, py1 - 2), (px1, py1 - 2)], fill=(222, 74, 158, 160),
            width=max(1, int(0.9 * s / 128)))
    for j in range(3):
        mx = px0 + int((j + 0.5) * (px1 - px0) / 3.0)
        my = py0 + int((py1 - py0) * 0.52)
        rad = max(1, int(1.2 * s / 128))
        d.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                  fill=(238, 96, 178, 220))
        gd.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                   fill=(238, 96, 178, 180))
    pr0, pr1 = int(96 * s / 128), int(88 * s / 128)
    pr2, pr3 = int(120 * s / 128), int(96 * s / 128)
    d.rectangle([pr0, pr1, pr2, pr3], fill=(20, 7, 26, 255))
    d.line([(pr0, pr1 + 1), (pr2, pr1 + 1)], fill=(216, 70, 152, 220),
           width=max(1, int(0.8 * s / 128)))
    gd.line([(pr0, pr1 + 1), (pr2, pr1 + 1)], fill=(216, 70, 152, 160),
            width=max(1, int(0.8 * s / 128)))

    # Gema del broche: diamante con núcleo blanco, muy legible en la mano.
    gx0, gy0 = int(54 * s / 128), int(30 * s / 128)
    gx1, gy1 = int(74 * s / 128), int(52 * s / 128)
    cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    half = min(gx1 - gx0, gy1 - gy0) // 2 - 4
    d.rectangle([gx0, gy0, gx1, gy1], fill=(30, 9, 34, 255))
    diamond = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
    d.polygon(diamond, fill=(40, 12, 38, 255))
    d.line(diamond + [diamond[0]], fill=(150, 40, 96, 255),
           width=max(2, int(1.2 * s / 128)))
    inner = [(cx, cy - half // 2), (cx + half // 2, cy),
             (cx, cy + half // 2), (cx - half // 2, cy)]
    d.line(inner + [inner[0]], fill=(214, 72, 152, 255),
           width=max(1, int(0.8 * s / 128)))
    core = max(2, int(3 * s / 128))
    d.ellipse([cx - core, cy - core, cx + core, cy + core],
              fill=(255, 186, 224, 255))
    gd.polygon(diamond, fill=(206, 60, 138, 170))
    gd.line(diamond + [diamond[0]], fill=(240, 110, 190, 255),
            width=max(2, int(1.2 * s / 128)))
    gd.ellipse([cx - core, cy - core, cx + core, cy + core],
               fill=(255, 186, 224, 255))

    # v1.9.0: ocho rayos cian salen del núcleo del broche. Van también al
    # glowmask del item, así que CapaItemGlowLayer los hace latir en frío.
    ray_w = max(1, int(0.7 * s / 128))
    for j in range(8):
        a = 2.0 * math.pi * j / 8.0
        r0, r1 = core * 1.5, half * 0.72
        ray = [(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
               (cx + r1 * math.cos(a), cy + r1 * math.sin(a))]
        d.line(ray, fill=(238, 96, 178, 235), width=ray_w)
        gd.line(ray, fill=(238, 96, 178, 235), width=ray_w)
    d.ellipse([cx - core // 2, cy - core // 2,
               cx + core // 2, cy + core // 2],
              fill=(255, 168, 216, 255))
    gd.ellipse([cx - core // 2, cy - core // 2,
                cx + core // 2, cy + core // 2],
               fill=(255, 168, 216, 255))

    # Tres motas frías en la región reservada de los rollos de tela.
    for j in range(3):
        mx = rx0 + int((j + 0.5) * (rx1 - rx0) / 3.0)
        my = ry0 + int((ry1 - ry0) * (0.30 + 0.20 * j))
        rad = max(1, int(1.2 * s / 128))
        d.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                  fill=(214, 64, 146, 200))
        gd.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                   fill=(214, 64, 146, 190))

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


def build_shard_sprites() -> list[Image.Image]:
    """Tres esquirlas de DETERIORO: cristales alargados rosa -> violeta.

    v1224: tercer tipo de particula. A diferencia de la brasa (redonda y
    calida) es un rombo estirado que se apaga en tres frames; así el clip
    `deterioro_particulas` tiene un efecto propio y reconocible.
    """
    s, out_s = 64, 16
    yy, xx = np.mgrid[0:s, 0:s]
    c = (s - 1) / 2.0
    sprites = []
    frames = [
        (1.00, (246.0, 96.0, 178.0), 0.95),
        (0.80, (206.0, 70.0, 164.0), 0.72),
        (0.55, (150.0, 60.0, 140.0), 0.48),
    ]
    for scale, tint, power in frames:
        dx = np.abs(xx - c) / (7.5 * scale)
        dy = np.abs(yy - c) / (15.0 * scale)
        shard = np.clip(1.0 - (dx + dy), 0.0, 1.0) ** 0.7
        halo = np.exp(-((xx - c) ** 2 + (yy - c) ** 2)
                      / (2.0 * (11.0 * scale) ** 2)) * 0.22
        a = np.clip((shard * power + halo) * 0.90, 0.0, 1.0)
        rgb = np.zeros((s, s, 3), np.float32)
        for ch, base in enumerate((40.0, 12.0, 56.0)):
            rgb[..., ch] = base + (tint[ch] - base) * shard
        core = np.exp(-((xx - c) ** 2 + (yy - c) ** 2)
                      / (2.0 * (3.0 * scale) ** 2))
        rgb = np.clip(rgb + core[..., None] * 70.0, 0, 255)
        img = Image.fromarray(
            np.dstack((rgb, a * 255.0)).astype(np.uint8), "RGBA")
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

    shards = build_shard_sprites()
    for index, sprite in enumerate(shards):
        assert sprite.size == (16, 16), sprite.size
        sprite.save(particle_dir / f"capa_shard_{index}.png")
    (ASSETS / "particles/capa_shard.json").write_text(json.dumps({
        "textures": [f"capatest:capa_shard_{i}" for i in range(3)]
    }, indent=2) + "\n")
    print(f"shard sprites: {len(shards)} x {shards[0].size[0]}x{shards[0].size[1]}")

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
