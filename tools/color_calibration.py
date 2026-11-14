#!/usr/bin/env python3
"""Calibración cromática MEDIDA de la capa v1.17.0 (v1211).

Compara, décima a décima, la mediana RGB del paño en el render frontal del
modelo con la mediana del paño en `referencias/REFERENCIA_CAPA.png`, usando
exactamente la misma máscara en ambas imágenes. La diferencia se ACUMULA en
`tools/color_calibration.json`, que `texture_pipeline.py` interpola sobre las
48 filas del canvas 96x48 del atlas.

Es un lazo cerrado: ejecutar este script y después `texture_pipeline.py`
reduce el error; repetir 2-3 veces converge sin crear franjas horizontales
(la tabla se suaviza con un kernel [1,2,1]/4 antes de guardarse).

Uso:  PYTHONPATH=tools:tools/_deps python3 tools/color_calibration.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

import preview_cloth as P

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "tools" / "color_calibration.json"
GAIN = 0.92          # paso del lazo (el sombreado del render atenúa ~8%)
MAX_STEP = 34.0      # ninguna iteración mueve un canal más de esto
MAX_TOTAL = 68.0     # límite de la corrección acumulada
CENTERS = [round((j + 0.5) / 10, 3) for j in range(10)]


def cloth(a: np.ndarray) -> np.ndarray:
    """Paño (excluye checkerboard, cabeza blanca, brazo, arnés y fondo)."""
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    return ((R > G + 8) & (B > G + 3) & (R > 42) & (R < 205)
            & ~((R > 175) & (G > 165) & (B > 165)))


def medians(a: np.ndarray) -> list[float]:
    m = cloth(a)
    if m.sum() < 30:
        return []
    return [float(np.median(a[m, i])) for i in range(3)]


def measure() -> list[list[float]]:
    armor = P.load(P.ARMOR_GEO)
    front = P.render(armor, P.ARMOR_TEX, P.effective_hidden(armor),
                     yaw=0, pitch=8, size=700)
    rc = np.asarray(Image.open(ROOT / "referencias" / "REFERENCIA_CAPA.png")
                    .convert("RGB").crop((385, 150, 695, 525)), float)
    rn = np.asarray(front, float)
    steps: list[list[float]] = []
    for j in range(10):
        t0, t1 = j / 10, (j + 1) / 10
        ref = medians(rc[int(t0 * 375):int(t1 * 375)])
        got = medians(rn[int(120 + t0 * 540):int(120 + t1 * 540)])
        if not ref or not got:
            steps.append([0.0, 0.0, 0.0])
            continue
        d = [float(np.clip((ref[i] - got[i]) * GAIN, -MAX_STEP, MAX_STEP))
             for i in range(3)]
        steps.append(d)
    # Suavizado [1,2,1]/4: una corrección escalonada por décimas crearía
    # franjas horizontales visibles en el atlas.
    smooth = []
    for j in range(10):
        a, b, c = steps[max(0, j - 1)], steps[j], steps[min(9, j + 1)]
        smooth.append([round((a[i] + 2 * b[i] + c[i]) / 4, 2) for i in range(3)])
    return smooth


def main() -> None:
    if CAL.is_file():
        rows = json.loads(CAL.read_text())["rows"]
    else:
        rows = [[t, 0.0, 0.0, 0.0] for t in CENTERS]
    steps = measure()
    out = []
    total_err = 0.0
    for (t, *old), step in zip(rows, steps):
        new = [round(float(np.clip(old[i] + step[i], -MAX_TOTAL, MAX_TOTAL)), 2)
               for i in range(3)]
        total_err += sum(abs(s) for s in step) / 3
        out.append([t, *new])
    CAL.write_text(json.dumps({
        "note": ("Corrección acumulada por altura, medida contra "
                 "referencias/REFERENCIA_CAPA.png con la misma máscara "
                 "en el render y en el PNG. La interpola "
                 "texture_pipeline.build_armor() sobre las 48 filas del canvas."),
        "method": "mediana del paño por décima, lazo GAIN=0.92, kernel [1,2,1]/4",
        "rows": out,
    }, indent=2) + "\n")
    print(f"error residual medio por banda: {total_err / 10:.1f}")
    print("     t      dR      dG      dB   (corrección acumulada en el atlas)")
    for row, step in zip(out, steps):
        print(f"  {row[0]:.2f}  {row[1]:+7.1f} {row[2]:+7.1f} {row[3]:+7.1f}"
              f"   paso {step[0]:+6.1f} {step[1]:+6.1f} {step[2]:+6.1f}")


main()
