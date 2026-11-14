#!/usr/bin/env python3
"""Calibración por lazo cerrado de la DENSIDAD DE ENERGÍA rosa (v1.17.0 v1231).

`texture_pipeline.shape_energy_density()` controla, fila a fila del canvas
96x48, cuántos píxeles del atlas acaban leyéndose como energía. Este script
mide la energía por décima en el RENDER real (geo + atlas, misma máscara que
`audit_model.py` y que el PNG de referencia) y ajusta los 10 nudos del perfil
`ENERGY_GAIN` hasta acercarlos a la densidad medida en
`referencias/REFERENCIA_CAPA.png`. Suavizado [1,2,1]/4 para no crear franjas.

  PYTHONPATH=tools python3 tools/energy_calibration.py [--iters 4]

El resultado queda grabado en `tools/texture_pipeline.py`; en CI lo verifica
`tools/audit_model.py --check`. Hermano de `color_calibration.py`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import preview_cloth as P

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "tools" / "texture_pipeline.py"
PATTERN = re.compile(r"ENERGY_GAIN = \((.*?)\)\n", re.S)


def cloth(a: np.ndarray) -> np.ndarray:
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return ((r > g + 8) & (b > g + 3) & (r > 42) & (r < 205)
            & ~((r > 175) & (g > 165) & (b > 165)))


def energy(a: np.ndarray) -> np.ndarray:
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 105) & (b > 75) & (r > g + 48) & (b > g + 22)


def read_gains() -> list[float]:
    m = PATTERN.search(PIPELINE.read_text())
    assert m, "no se encontró ENERGY_GAIN"
    g = [float(b) for _, b in re.findall(r"\(([\d.]+),\s*([\d.]+)\)", m.group(1))]
    assert len(g) == 12, g
    return g


def write_gains(g: list[float]) -> None:
    ts = (0.00, 0.05, 0.15, 0.25, 0.35, 0.45, 0.55,
          0.65, 0.75, 0.85, 0.95, 1.00)
    table = ", ".join(f"({t:.2f}, {v:.3f})" for t, v in zip(ts, g))
    src = PIPELINE.read_text()
    m = PATTERN.search(src)
    assert m
    PIPELINE.write_text(src[:m.start()] + f"ENERGY_GAIN = ({table})\n" + src[m.end():])


def rebuild() -> None:
    p = subprocess.run([sys.executable, str(PIPELINE)], cwd=ROOT,
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stdout[-2000:] + p.stderr[-2000:])


def bands(a: np.ndarray, y0: float, h: float) -> np.ndarray:
    out = []
    for j in range(10):
        sl = a[int(y0 + j * h / 10):int(y0 + (j + 1) * h / 10)]
        c = cloth(sl)
        out.append(100 * (energy(sl) & c).sum() / max(1, c.sum()))
    return np.array(out, float)


def target() -> np.ndarray:
    rc = np.asarray(Image.open(ROOT / "referencias" / "REFERENCIA_CAPA.png")
                    .convert("RGB").crop((385, 150, 695, 525)), float)
    return bands(rc, 0, 375)


def measured() -> np.ndarray:
    armor = P.load(P.ARMOR_GEO)
    rn = np.asarray(P.render(armor, P.ARMOR_TEX, P.effective_hidden(armor),
                             yaw=0, pitch=8, size=700), float)
    return bands(rn, 120, 540)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=3)
    args = ap.parse_args()
    tgt = target()
    g = read_gains()
    # v1246: BEST-SO-FAR. El descarte por trazo es escalonado y el lazo
    # puede oscilar; se conserva el perfil con menor error, no el ultimo.
    best_g, best_err = g[:], float("inf")
    print("objetivo :", " ".join(f"{v:5.1f}" for v in tgt))
    for it in range(args.iters):
        rebuild()
        e0 = measured()
        print(f"iter {it} base :", " ".join(f"{v:5.1f}" for v in e0),
              f"| error {np.abs(e0 - tgt).sum():5.1f} pp")
        # JACOBIANO MEDIDO: cada nudo alimenta DOS bandas (los tramos del
        # abanico se solapan y rotan), así que un ajuste 1 nudo = 1 banda
        # deja un suelo de energía que no se puede quitar. Se baja cada
        # nudo 0.5 y se mide la respuesta REAL de las 10 bandas.
        delta = 0.50
        J = np.zeros((10, 10), float)
        for j in range(10):
            trial = g.copy()
            trial[j + 1] = max(0.01, trial[j + 1] - delta)
            write_gains(trial)
            rebuild()
            J[:, j] = (e0 - measured()) / max(1e-6, g[j + 1] - trial[j + 1])
        write_gains(g)
        A = J.T @ J + 0.10 * np.eye(10)
        step = np.linalg.solve(A, J.T @ (tgt - e0))
        step = np.clip(step, -1.6, 1.6)
        new = g.copy()
        for j in range(10):
            new[j + 1] = float(np.clip(g[j + 1] + 0.90 * step[j], 0.02, 3.4))
        raw = new[1:11]
        for j in range(1, 11):
            i = j - 1
            smooth = (raw[max(0, i - 1)] + 2 * raw[i]
                      + raw[min(9, i + 1)]) / 4
            new[j] = 0.75 * raw[i] + 0.25 * smooth
        new[0], new[-1] = new[1], new[-2]
        g = new
        write_gains(g)
        rebuild()
        e1 = measured()
        print(f"iter {it} nueva:", " ".join(f"{v:5.1f}" for v in e1),
              f"| error {np.abs(e1 - tgt).sum():5.1f} pp")
        print("  perfil :", " ".join(f"{v:.2f}" for v in g[1:-1]))
        err1 = float(np.abs(e1 - tgt).sum())
        if err1 < best_err:
            best_g, best_err = g[:], err1
    rebuild()
    e2 = measured()
    if float(np.abs(e2 - tgt).sum()) > best_err:
        g = best_g
        write_gains(g)
        rebuild()
        e2 = measured()
    print(f"MEJOR perfil conservado: error {np.abs(e2 - tgt).sum():.1f} pp")
    print("  ENERGY_GAIN:", " ".join(f"{v:.2f}" for v in g[1:-1]))


if __name__ == "__main__":
    main()
