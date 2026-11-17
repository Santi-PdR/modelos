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
from cape_atlas_v1230 import build_clean_atlas
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
ENERGY_GAIN = ((0.00, 1.0), (0.05, 1.0), (0.15, 1.0), (0.25, 1.0), (0.35, 1.0), (0.45, 1.0), (0.55, 1.0), (0.65, 1.0), (0.75, 1.0), (0.85, 1.0), (0.95, 1.0), (1.00, 1.0))


def energy_gain(t: float) -> float:
    t = max(0.0, min(1.0, t))
    for i in range(len(ENERGY_GAIN) - 1):
        t0, g0 = ENERGY_GAIN[i]
        t1, g1 = ENERGY_GAIN[i + 1]
        if t <= t1:
            return g0 + (g1 - g0) * (t - t0) / max(1e-6, t1 - t0)
    return ENERGY_GAIN[-1][1]


def build_armor_cloth_canvas(glow_alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """v1.18.0: el atlas ES la capa de la IMAGEN, sin inventar nada.

    Se limpia el PNG de referencia, se recorta a la capa y se reduce a
    96x48 (`tools/reference_canvas.py`). No hay paleta sintética, ni grano,
    ni Bayer, ni des-abanicado: cada tramo 3D toma por UV local el píxel
    de esta foto que le corresponde (ver `armor_model_pipeline.py`).

    Devuelve también las tintas emisiva/fría derivadas de las cuchilladas
    rosa REALES, para que el glowmask siga encendiendo la energía sin
    alterar el RGB de la foto.
    """
    from reference_canvas import canvas as foto
    rgb = foto().astype(np.float32)
    assert rgb.shape == (48, 96, 3), rgb.shape
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    energy = (r > 135) & (b > 85) & (r > g + 50) & (b > g + 18)
    ink = energy.astype(np.float32) * 0.85
    cool = np.asarray(Image.fromarray((energy * 110).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.9)), dtype=np.float32) / 255.0

    # v1.53.0: VOLUMEN DEL PANÓ. La foto de referencia es un recorte
    # 2D; en 3D el paño pierde la sensación de tela colgando. Añadimos
    # SÓLO RGB (alfa y glowmask intactos): un degradado vertical de
    # caída (el paño se oscurece hacia la punta), pliegues horizontales
    # sutiles y un grano de tela muy fino. Las zonas ENERGÍA (las
    # cuchilladas emisivas) se protegen para no apagar el glow.
    v = np.linspace(0.0, 1.0, 48, dtype=np.float32)[:, None, None]
    # Degradado de caída: más oscuro hacia abajo, débil en la energía.
    drape = 1.0 - 0.10 * v
    shade_mask = ((1.0 - energy.astype(np.float32)) * 0.85 + 0.15)[..., None]
    rgb = rgb * (drape * shade_mask + (1.0 - shade_mask))
    # Pliegues horizontales: ondulaciones de tela cada 6 texels.
    fold = 1.0 - 0.045 * np.sin(np.linspace(0.0, 34.0 * np.pi, 48,
                                            dtype=np.float32))[:, None, None]
    rgb = rgb * (fold * shade_mask + (1.0 - shade_mask))
    # Grano de tela muy fino (determinista, no aleatorio): añade
    # textura sin alterar los colores de forma apreciable.
    rng = np.random.default_rng(0x53)
    grain = 1.0 + rng.standard_normal(rgb.shape).astype(np.float32) * 0.012
    rgb = np.clip(rgb * grain, 0.0, 255.0)

    # v1.54.0: TRAMA DE TELA (warp/weft) + RESALTE DE BORDE (rim).
    # Gracias al estudio de UV/atlas: la densidad de texel debe ser
    # CONSISTENTE y alineada al sentido de las cintas (las cintas
    # caen en V; la trama vertical sigue esa dirección). Sólo RGB:
    # alfa y glowmask intactos.
    # Trama vertical: hilos de urdimbre (verticales, a lo largo del
    # paño) y trama (horizontales) con contraste sutil, protegiendo
    # la energia emisiva para no apagar el glow.
    _shade = ((1.0 - energy.astype(np.float32)) * 0.80 + 0.20)[..., None]
    warp = 1.0 - 0.030 * np.sin(np.arange(96, dtype=np.float32) * 1.4)
    weft = 1.0 - 0.022 * np.sin(np.arange(48, dtype=np.float32) * 1.1)
    rgb = rgb * (warp[None, :, None] * _shade + (1.0 - _shade))
    rgb = rgb * (weft[:, None, None] * _shade + (1.0 - _shade))
    # Resalte de borde (rim light): un brillo frío en el canto superior
    # del paño (donde la luz debackground pega), para volumen. Sólo
    # en las primeras filas y protegiendo la energia.
    _full = np.linspace(0.0, 1.0, 48, dtype=np.float32)
    _rim = np.clip(1.0 - _full / 0.10, 0.0, 1.0)   # (48,) 1..0 en 10 filas
    rim = 1.0 + (_rim[:, None, None] * 0.10) * (1.0 - energy.astype(np.float32))[..., None]
    rgb = np.clip(rgb * rim, 0.0, 255.0)
    return rgb, ink, cool


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
        np.array([84.0, 82.0, 100.0], np.float32) * grey)
    out[18:21, 108:109, :3] = np.array([62.0, 60.0, 78.0])
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

    # v1306: el CAPUCHON y las alas de hombro muestrean esta region
    # reservada `yoke` (57..71, 76..93), FUERA del canvas 96x48.
    # YUGO / CAPUCHÓN v1.17.2: antes era un rectángulo liso color ciruela
    # que en el juego parecía una LOSA de plástico. Ahora lleva pliegues
    # radiales cosidos (sombra de 1 texel + ribete cálido), un borde
    # inferior rasgado en onda y el carmesí MEDIDO de la referencia, con
    # el viraje a violeta hacia abajo. Sólo RGB: alfa intacto.
    import cape_shape as CS
    y = np.linspace(0.0, 1.0, 17, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, 14, dtype=np.float32)[None, :]
    top = np.array([116.0, 30.0, 40.0], np.float32)
    low = np.array([84.0, 42.0, 68.0], np.float32)
    yoke = top[None, None, :] * (1.0 - y[..., None]) + low[None, None, :] * y[..., None]
    yoke = np.broadcast_to(yoke, (17, 14, 3)).copy()
    # Pliegues radiales: 5 hendiduras que se inclinan ligeramente al bajar.
    cols = np.arange(14, dtype=np.float32)[None, :]
    for j in range(3):
        c = 2.2 + j * 4.4 + 0.8 * np.sin(j * 1.7)
        centre = c + 0.9 * y[:, 0:1]          # (17,1): pliegue inclinado
        shade = np.exp(-((cols - centre) / 1.15) ** 2)   # (17,14)
        yoke *= (1.0 - 0.08 * shade[..., None])
        glow = np.roll(shade, -1, axis=1) * 0.10
        yoke[..., 0] += glow * 26.0
        yoke[..., 2] += glow * 10.0
    # Borde inferior rasgado: dos últimas filas se comen en onda.
    edge = np.sin(np.linspace(0.0, 5.2 * np.pi, 14, dtype=np.float32))
    yoke[15:, :, :] *= (0.70 + 0.22 * edge)[None, :, None]
    yoke[16:, :, :] *= (0.55 + 0.28 * edge)[None, :, None]
    out[76:93, 57:71, :3] = np.clip(yoke, 0, 255)

    # MOTAS 3D: sprites de 3x3 con centro encendido y bordes apagados.
    # Antes muestreaban UN texel plano y parecían bloques bugeados
    # flotando; ahora cada cara del cubo es una brasa con degradado.
    kernel = np.array([[0.30, 0.66, 0.30],
                       [0.66, 1.00, 0.66],
                       [0.30, 0.66, 0.30]], np.float32)[..., None]
    for (v0, hot, dim) in ((109, (232, 78, 166), (46, 16, 52)),
                           (119, (168, 52, 132), (34, 14, 44))):
        h = np.array(hot, np.float32); d0 = np.array(dim, np.float32)
        out[v0:v0 + 3, 69:72, :3] = d0 + kernel * (h - d0)
    # Relleno de la rampa: violeta apagado, sin franjas de neón.
    ramp = np.linspace(0.0, 1.0, 15, dtype=np.float32).reshape(15, 1, 1)
    colours = (np.array([226.0, 82.0, 164.0], np.float32) * (1.0 - ramp)
               + np.array([74.0, 34.0, 76.0], np.float32) * ramp)
    out[112:127, 72:75, :3] = colours
    return out


def assert_cloth_uvs() -> None:
    """Ninguna UV de la tela nueva puede samplear un texel transparente."""
    geometry = json.loads(GEO.read_text())["minecraft:geometry"][0]
    checked = 0
    for bone in geometry.get("bones", []):
        if not bone["name"].startswith(("v15_", "v16_", "v17_", "v18_")):
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
        pos = {(y, x): i for i, (y, x) in enumerate(seq)}
        acc = ((v0 * 7 + u0 * 13 + len(cells)) % 7) / 7.0
        keep_idx = set()
        for i, (y, x) in enumerate(seq):
            acc += min(1.0, gain)
            if acc >= 1.0:
                acc -= 1.0
                keep_idx.add(i)
        # v1323: GUION ALARGADO. La captura tiene cuchilladas finas de
        # 2-3 texeles, no cuadrados aislados. Cada guion conservado se
        # extiende un texel hacia abajo SI ese texel pertenece al mismo
        # trazo, asi la grieta se lee como linea y no como confeti.
        for i in list(keep_idx):
            y, x = seq[i]
            # v1327: dos de cada tres guiones se alargan: mezcla de
            # cuchilladas cortas y motas, como en la captura, y evita
            # duplicar la densidad de energia de golpe.
            if (y * 31 + x * 17 + v0 * 7) % 3 == 0:
                continue
            j = pos.get((y + 1, x))
            if j is not None:
                keep_idx.add(j)
        kept = []
        for i, (y, x) in enumerate(seq):
            if i in keep_idx:
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
    """v1.23.0: atlas LIMPIO, creado a mano, con glowmask FULLBRIGHT.

    Hasta v1.22.0 `build_armor` recortaba la foto del usuario y le añadía
    grano/twill/bloom: el ruido se leía como motas y cuadros en Blockbench.
    Ahora `cape_atlas_v1230.build_clean_atlas()` pinta un degradado
    carmesí -> morado oscuro definido, agujeros de desgaste en las puntas,
    grietas y bordes neón, y un glowmask que GeckoLib renderiza emisivo.
    El icono 2D y el item plegado siguen usando su arte propio.
    """
    atlas, glowmask = build_clean_atlas()
    assert atlas.size == (SIZE, SIZE) and glowmask.size == (SIZE, SIZE)
    # Cobertura de UV de la geometría nueva: se calcula para no perder la
    # regresión de "ningún UV fuera del atlas".
    assert used.shape == (SIZE, SIZE)
    return atlas, glowmask


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
        frac = 0.04 + 0.05 * (v - 43)          # 10% .. 62% de huecos
        for u in range(96):
            # Estela vertical: el hueco se mantiene de una fila a la
            # siguiente en vez de convertirse en confeti de píxeles.
            h = ((u * 37 + (u // 4) * 13 + v * 3 + (u // 7) * 29) % 101) / 101.0
            if h < frac and not energy[v, u] and c[v, u].mean() > 34.0:
                c[v, u] = np.array([16.0, 9.0, 18.0], np.float32)
    # v1324: costuras rasgadas entre lobulos en la mitad inferior.
    for v in range(26, 43):
        for k in (2, 5, 8, 11, 14):
            u = min(95, int(round(k * 6.4)) + (1 if (v * 7 + k) % 11 < 3 else 0))
            if (not energy[v, u] and c[v, u].mean() > 34.0
                    and ((v * 13 + u * 7 + k) % 17) / 17.0 < 0.25):
                c[v, u] = np.array([15.0, 9.0, 19.0], np.float32)
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

# Icono ACTIVO v1.28.0.
#
# v1.28.0: VUELVE EL ICONO PREFERIDO DE LA v1.25.0. El usuario comparo el
# icono de la v1.27.0 (el rediseño con hombrera y cadena de acero) con
# este, y se quedo con ESTE: "era mejor el anterior, ese quiero". El mapa
# activo es por tanto el mismo de la v1.25.0 (rose_v1140), byte a byte.
#
# La v1.27.0 no se borra: queda como histórico en
# referencias/ICONO_V1270_REDISEÑO_BACKUP.png.
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
    # v1.28.0: las ocho motas de la v1.25.0 (este es el icono que el
    # usuario ha elegido). La v1.27.0 las redujo a tres: ya no aplica.
    (1, 2, "P"), (14, 3, "G"), (0, 8, "P"), (15, 10, "P"),
    (2, 14, "C"), (13, 15, "G"), (0, 12, "P"), (15, 5, "P"),
)

# Grietas de energia en guiones CORTOS y costuras oscuras entre jirones:
# la referencia no es un bloque liso, son hebras separadas con rosa dentro.
ICON_CRACKS = (
    # v1.28.0: la lista de la v1.25.0 (el icono elegido por el usuario).
    # Cuchilladas diagonales de 2-3 px: el icono cuenta lo mismo que
    # la capa 3D, no una lluvia de cuadrados magenta.
    (4, 7, "C"), (5, 8, "C"), (5, 9, "E"), (6, 10, "C"),
    (10, 7, "C"), (10, 8, "E"), (9, 9, "C"), (9, 10, "C"),
    (3, 11, "C"), (4, 12, "E"), (12, 11, "C"), (12, 12, "E"),
    (6, 12, "C"), (7, 13, "E"), (9, 12, "C"), (8, 13, "E"),
    (3, 14, "C"), (12, 14, "C"), (11, 13, "C"), (5, 13, "E"),
    # Costuras oscuras entre lóbulos.
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
        # v1.28.0: tonos de la v1.25.0 (el icono elegido por el usuario).
        # El contraste extra de la v1.27.0 ya no aplica.
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


def build_spark_sprites() -> list[Image.Image]:
    """v1.23.0: 3 sprites de CHISPA rectangular vertical semi-transparente.

    Barra estrecha (4x13) magenta/rosa con centro casi blanco y bordes
    translúcidos. Tres frames con altura/alpha distintos para un parpadeo
    suave. NO son partículas vanilla: `CapaSparkParticle` las usa con su
    propio `SpriteSet` registrado en `CapaParticleRegistration`.
    """
    out = []
    for frame in range(3):
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        px = img.load()
        h = 12 - frame
        y0 = (16 - h) // 2
        for y in range(y0, y0 + h):
            fade = 1.0 - abs(y - (y0 + h / 2.0)) / (h / 2.0 + 0.5)
            for x in range(5, 11):
                q = 1.0 - abs(x - 7.5) / 3.0
                if x in (5, 10):
                    a = int(70 * fade)
                    px[x, y] = (236, 46, 178, a)
                elif x in (6, 9):
                    a = int(185 * fade)
                    px[x, y] = (255, 96, 210, a)
                else:
                    a = int(235 * fade)
                    px[x, y] = (255, 214, 244, a)
        out.append(img)
    return out


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
        a *= np.clip((30.0 - np.sqrt(r2)) / 8.0, 0.0, 1.0)  # sin borde cuadrado
        a[a < 0.02] = 0.0

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
    r2 = (xx - c) ** 2 + (yy - c) ** 2
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
        a *= np.clip((30.0 - np.sqrt(r2)) / 8.0, 0.0, 1.0)
        a[a < 0.02] = 0.0
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
        a *= np.clip((30.0 - np.sqrt(r2)) / 8.0, 0.0, 1.0)
        a[a < 0.02] = 0.0

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
    # v1.23.0: UNA SOLA partícula exclusiva, con textura propia. Se
    # retiran las brasas/motas/esquirlas y las partículas vanilla.
    sparks = build_spark_sprites()
    for index, sprite in enumerate(sparks):
        assert sprite.size == (16, 16), sprite.size
        sprite.save(particle_dir / f"capa_spark_{index}.png")
    (ASSETS / "particles/capa_spark.json").write_text(json.dumps({
        "textures": [f"capatest:capa_spark_{i}" for i in range(3)]
    }, indent=2) + "\n")
    print(f"spark sprites: {len(sparks)} x 16x16 (rectangulares, centro brillante)")

    # El atlas es NUEVO: todo opaco, y el glowmask enciende SÓLO el neón.
    armor_alpha = np.asarray(armor)[..., 3]
    assert (armor_alpha == 255).all(), "atlas con texel transparente"
    glow_alpha = np.asarray(glowmask)[..., 3]
    emissive = int((glow_alpha > 0).sum())
    assert 200 < emissive < SIZE * SIZE, emissive
    assert np.asarray(armor)[0:48, 0:96, 0].mean() > \
        np.asarray(armor)[48:96, 0:96, 0].mean(), "falta degradado carmesi->morado"
    print(f"atlas limpio v1.23.0: {emissive} texels EMISSIVE (fullbright)")

    # El glowmask del item plegado sigue siendo independiente.
    fg = np.asarray(folded_glow)[..., 3]
    assert folded_glow.size == (SIZE, SIZE), folded_glow.size
    assert 0 < (fg > 0).sum() < SIZE * SIZE, "glowmask del item vacío o total"
    print(f"folded glowmask texels: {(fg > 0).sum()}")


if __name__ == "__main__":
    main()
