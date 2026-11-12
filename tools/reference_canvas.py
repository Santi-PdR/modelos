#!/usr/bin/env python3
"""v1.18.0 — EMPEZAR DE 0: el atlas ES la capa de TU IMAGEN.

Limpia `REFERENCIA_CAPA_recorte.png` (fuera checkerboard, cabeza blanca,
brazo beige, arnés gris, suelo y rejilla), recorta al bounding box de la
capa y lo reduce a 96x48 pixel art. NO se des-abanica ni se añade ruido:
cada tramo 3D toma, por UV local, el píxel de esta foto que le corresponde,
así el volumen se construye ENCIMA de la imagen en vez de reemplazarla.

Uso: python3 tools/reference_canvas.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "referencias" / "REFERENCIA_CAPA_recorte.png"
OUT = ROOT / "referencias" / "REFERENCIA_CAPA_atlas96.png"
BG = np.array([11.0, 8.0, 18.0], np.float32)


def capa_mask(a: np.ndarray) -> np.ndarray:
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    energy = (r > 135) & (b > 85) & (r > g + 50) & (b > g + 18)
    cloth = (r > g + 10) & (r > 32) & (b > g - 8) & (r < 205)
    beige = (g > 90) & (r > 120) & (b < 155) & (r > b + 40)
    neutral = (np.abs(r - g) < 26) & (np.abs(g - b) < 30) & (r > 52)
    pale = (r > 165) & (g > 150) & (b > 150)
    floor = (g > 60) & (np.abs(r - g) < 30) & (b > 55) & (b < 160) & (r < 175)
    return (cloth | energy) & ~beige & ~neutral & ~pale & ~floor


def canvas() -> np.ndarray:
    a = np.asarray(Image.open(SRC).convert("RGB"), dtype=np.float32)
    keep = capa_mask(a)
    clean = np.zeros_like(a) + BG
    clean[keep] = a[keep]
    ys, xs = np.nonzero(keep)
    crop = clean[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    img = Image.fromarray(crop.astype(np.uint8), "RGB").resize(
        (96, 48), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32)


if __name__ == "__main__":
    c = canvas()
    Image.fromarray(c.astype(np.uint8), "RGB").save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}: {c.shape[1]}x{c.shape[0]}")
