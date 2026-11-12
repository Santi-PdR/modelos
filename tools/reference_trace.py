#!/usr/bin/env python3
"""TRAZA la referencia del usuario y la convierte en datos de modelo.

Esto es lo que faltaba en v1.14/v1.15/v1.16: se rediseñaba "a ojo" y se
terminaba pareciendo a una rejilla. Aquí se mide EL PNG que subió el usuario
(``referencias/REFERENCIA_CAPA.png``) y se guarda:

  * ``tools/reference_profile.json``  -> silueta, paleta por fila, grietas.
  * ``referencias/REFERENCIA_CAPA_recorte.png`` -> recorte LIMPIO de la capa
    (fondo/ cabeza/ brazo/ suelo sustituidos por tela casi negra), que
    ``texture_pipeline.py`` des-abanica en el atlas 96x48.
  * ``docs/referencia_analizada.png`` -> prueba visual de que se usó la
    referencia: recorte, máscara, envolvente y paleta medida.

La cabeza blanca del maniquí es sólo escala: NO se modela.

Uso:  PYTHONPATH=tools/_deps python3 tools/reference_trace.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "referencias" / "REFERENCIA_CAPA.png"
CLEAN = ROOT / "referencias" / "REFERENCIA_CAPA_recorte.png"
PROFILE = ROOT / "tools" / "reference_profile.json"
DEBUG = ROOT / "docs" / "referencia_analizada.png"

# Recorte medido sobre la captura de Blockbench (1024x572).
X0, X1 = 385, 695          # ancho de trabajo de la capa
Y0, Y1 = 150, 525          # alto: incluye bufanda y puntas
CX = 518                   # eje de simetría (centro de la cabeza)
Y_TOP, Y_BOT = 205, 505    # de donde cuelgan los jirones hasta las puntas
PX_PER_UNIT = 14.3         # 300 px de alto <-> 21 unidades del modelo


def masks(im: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    R = im[..., 0].astype(np.int32)
    G = im[..., 1].astype(np.int32)
    B = im[..., 2].astype(np.int32)
    sat = np.dstack([R, G, B]).max(2) - np.dstack([R, G, B]).min(2)

    # Paño carmesí / violeta: rojo dominante, saturado, oscuro.
    cloth = ((R > G + 10) & (R > 38) & (G < 118) & (sat > 16)
             & (R > B * 0.82) & (B > G * 0.85))
    # Energía rosa/magenta (también las motas que flotan).
    pink = ((R > 145) & (B > 95) & (G < 140)
            & (R > G + 55) & (B > G + 25))

    # El brazo del maniquí es MARRÓN (B/G ~ 0.74); el paño carmesí tiene
    # B/G > 1.1. Se elimina por color, no con un rectángulo, para no
    # borrar los jirones reales que pasan por esa zona.
    arm = np.zeros(cloth.shape, bool)
    arm[235:345, 395:490] = True
    cloth &= ~(arm & (B < G * 1.10))
    # Parches de suelo / pierna del maniquí abajo a los lados.
    cloth[440:525, 385:452] = False
    cloth[440:525, 625:695] = False

    roi = np.zeros(cloth.shape, bool)
    roi[Y0:Y1, X0:X1] = True
    return cloth & roi & ~pink, pink & roi


def components(mask: np.ndarray, min_px: int = 6) -> list[dict]:
    """Componentes conexos 4-vecinos (sin scipy), con caja y tamaño."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        stack = [(int(y0), int(x0))]
        seen[y0, x0] = True
        xs, ys = [], []
        while stack:
            y, x = stack.pop()
            xs.append(x)
            ys.append(y)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(xs) < min_px:
            continue
        out.append(dict(x0=min(xs), y0=min(ys), x1=max(xs) + 1, y1=max(ys) + 1,
                        w=max(xs) - min(xs) + 1, h=max(ys) - min(ys) + 1,
                        n=len(xs)))
    return out


def main() -> None:
    src = np.asarray(Image.open(SRC).convert("RGB"))
    cloth, pink = masks(src)

    # --- Recorte limpio: lo que NO es paño ni energía pasa a tela negra.
    # Así el atlas no hereda el ajedrez, la cabeza ni el suelo de Blockbench.
    clean = np.empty((Y1 - Y0, X1 - X0, 3), np.uint8)
    clean[:] = (11, 7, 17)
    rng = np.random.default_rng(20261111)
    clean += rng.integers(0, 5, clean.shape, dtype=np.uint8)
    sub_c, sub_p = cloth[Y0:Y1, X0:X1], pink[Y0:Y1, X0:X1]
    clean[sub_c] = src[Y0:Y1, X0:X1][sub_c]
    clean[sub_p] = src[Y0:Y1, X0:X1][sub_p]
    Image.fromarray(clean).save(CLEAN)

    # --- Envolvente de silueta: percentiles robustos por fila, lado derecho
    # (el izquierdo está tapado por el brazo del maniquí en y 240-340).
    silhouette = []
    for y in range(Y_TOP, Y_BOT + 1, 10):
        band = cloth[max(Y0, y - 4):y + 5]
        xs = np.where(band.any(0))[0]
        xs = xs[xs >= CX]
        if len(xs) < 6:
            continue
        half = float(np.percentile(xs - CX, 97))
        t = (y - Y_TOP) / float(Y_BOT - Y_TOP)
        silhouette.append([round(t, 4), round(half / PX_PER_UNIT, 3)])
    # Suavizado ligero para que los jirones no hereden el ruido del PNG.
    smooth = []
    for i, (t, hw) in enumerate(silhouette):
        lo, hi = max(0, i - 1), min(len(silhouette), i + 2)
        smooth.append([t, round(sum(s[1] for s in silhouette[lo:hi]) / (hi - lo), 3)])

    # --- Paleta REAL por fila (mediana del paño, sin energía).
    palette = []
    for y in range(Y_TOP, Y_BOT + 1, 15):
        m = cloth[max(Y0, y - 6):y + 7]
        px = src[max(Y0, y - 6):y + 7][m]
        if len(px) < 40:
            continue
        t = (y - Y_TOP) / float(Y_BOT - Y_TOP)
        palette.append([round(t, 4), [int(v) for v in np.median(px, axis=0)]])

    # --- Marcas rosa REALES de la referencia. Una marca que cae FUERA de
    # la envolvente medida es una MOTA FLOTANTE (vóxel 3D separado); las que
    # caen dentro son GRIETAS sobre el paño.
    def half_at(t: float) -> float:
        if t <= smooth[0][0]:
            return smooth[0][1]
        for i in range(len(smooth) - 1):
            t0, h0 = smooth[i]
            t1, h1 = smooth[i + 1]
            if t <= t1:
                f = (t - t0) / max(1e-6, t1 - t0)
                return h0 + (h1 - h0) * f
        return smooth[-1][1]

    marks = []
    for c in components(pink, min_px=5):
        t = (c["y0"] - Y_TOP) / float(Y_BOT - Y_TOP)
        xrel = ((c["x0"] + c["x1"]) / 2.0 - CX) / (PX_PER_UNIT * 8.6)
        rec = dict(t=round(t, 4), x=round(xrel, 4),
                   w=round(c["w"] / PX_PER_UNIT, 3),
                   h=round(c["h"] / PX_PER_UNIT, 3), n=c["n"])
        rec["floating"] = bool(abs(xrel) > half_at(max(0.0, min(1.0, t))) / 8.6 + 0.02
                               or t < -0.02 or t > 1.02)
        marks.append(rec)
    dashes = [m for m in marks if not m["floating"]]
    motes = [m for m in marks if m["floating"]]

    profile = {
        "source": "referencias/REFERENCIA_CAPA.png (captura Blockbench del usuario)",
        "note": "La cabeza blanca es escala del maniquí, NO parte de la capa.",
        "roi": [X0, Y0, X1, Y1], "center_x": CX,
        "y_top": Y_TOP, "y_bottom": Y_BOT, "px_per_unit": PX_PER_UNIT,
        "silhouette": smooth,
        "palette": palette,
        "energy_marks": marks,
        "energy_dashes": dashes,
        "floating_motes": motes,
    }
    PROFILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"perfil: {len(smooth)} puntos de silueta, {len(palette)} filas de paleta, "
          f"{len(dashes)} grietas, {len(motes)} motas flotantes")

    # --- Prueba visual de que la referencia se usó de verdad.
    W, H = 310, 375
    dbg = Image.new("RGB", (W * 4 + 50, H + 150), (14, 12, 20))
    d = ImageDraw.Draw(dbg)
    raw = Image.fromarray(src[Y0:Y1, X0:X1])
    dbg.paste(raw, (10, 60))
    mimg = np.zeros((H, W, 3), np.uint8)
    mimg[..., :] = (18, 16, 22)
    mimg[sub_c] = (150, 35, 55)
    mimg[sub_p] = (255, 70, 190)
    dbg.paste(Image.fromarray(mimg), (W + 20, 60))
    dbg.paste(Image.fromarray(clean), (2 * W + 30, 60))
    # curva de silueta sobre el recorte limpio
    curve = Image.fromarray(clean).copy()
    cd = ImageDraw.Draw(curve)
    pts = [(int(CX - X0 + s[1] * PX_PER_UNIT), int(Y_TOP - Y0 + s[0] * (Y_BOT - Y_TOP)))
           for s in smooth]
    pts2 = [(int(CX - X0 - s[1] * PX_PER_UNIT), int(Y_TOP - Y0 + s[0] * (Y_BOT - Y_TOP)))
            for s in smooth]
    cd.line(pts, fill=(90, 220, 160), width=2)
    cd.line(pts2, fill=(90, 220, 160), width=2)
    dbg.paste(curve, (3 * W + 40, 60))
    for i, label in enumerate(("REFERENCIA (usuario)", "MÁSCARA paño / energía",
                               "RECORTE LIMPIO", "ENVOLVENTE medida")):
        d.text((10 + i * (W + 10), 40), label, fill=(235, 228, 245))
    # muestras de paleta
    for i, (t, rgb) in enumerate(palette):
        x = 14 + i * 40
        d.rectangle([x, H + 80, x + 34, H + 112], fill=tuple(rgb))
        d.text((x, H + 116), f"t{t:.2f}", fill=(170, 160, 185))
    d.text((14, H + 68), "PALETA MEDIDA del PNG (mediana del paño por fila)",
           fill=(235, 228, 245))
    DEBUG.parent.mkdir(exist_ok=True)
    dbg.save(DEBUG)
    print("debug:", DEBUG)


if __name__ == "__main__":
    main()
