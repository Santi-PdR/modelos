#!/usr/bin/env python3
"""Test de autoevaluación visual de la capa contra la referencia del usuario.

Se ejecuta LOCALMENTE y en GITHUB ACTIONS. Mide, décima a décima de altura,
la mediana RGB del paño, la cobertura de tela, la densidad de energía rosa y
el semiancho de silueta, usando la MISMA máscara en el PNG de referencia y en
el render del geo+atlas reales. No es una opinión: es una regresión numérica.

  PYTHONPATH=tools python3 tools/audit_model.py            # solo informe
  PYTHONPATH=tools python3 tools/audit_model.py --check    # falla si empeora

Requiere numpy y Pillow (en CI los instala el workflow antes de este paso).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import preview_cloth as P

ROOT = Path(__file__).resolve().parents[1]

# Márgenes sobre el estado medido v1220 (total 190.8). Se deja holgura para
# diferencias menores de versión de Pillow/numpy entre el sandbox y Ubuntu.
LIMITS = {
    "total": 205.0,
    "color": 130.0,
    "cloth": 110.0,
    "energy": 90.0,
    "silhouette": 1.75,
}
ICON_SHA = "e88ccec0a0c67b1ad0982ed781f0d684ae4662660c545fa134574781967e4840"


def cloth(a: np.ndarray) -> np.ndarray:
    """Paño: excluye checkerboard, cabeza blanca, brazo, arnés y fondo."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return ((r > g + 8) & (b > g + 3) & (r > 42) & (r < 205)
            & ~((r > 175) & (g > 165) & (b > 165)))


def energy(a: np.ndarray) -> np.ndarray:
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 105) & (b > 75) & (r > g + 48) & (b > g + 22)


def medians(a: np.ndarray) -> list[float]:
    m = cloth(a)
    if m.sum() < 30:
        return [0.0, 0.0, 0.0]
    return [float(np.median(a[m, i])) for i in range(3)]


def render_front() -> np.ndarray:
    armor = P.load(P.ARMOR_GEO)
    front = P.render(armor, P.ARMOR_TEX, P.effective_hidden(armor),
                     yaw=0, pitch=8, size=700)
    return np.asarray(front, float)


def measure() -> dict:
    rc = np.asarray(Image.open(ROOT / "referencias" / "REFERENCIA_CAPA.png")
                    .convert("RGB").crop((385, 150, 695, 525)), float)
    rn = render_front()
    err = dict(cloth=0.0, energy=0.0, color=0.0)
    rows = []
    for j in range(10):
        t0, t1 = j / 10, (j + 1) / 10
        ref = medians(rc[int(t0 * 375):int(t1 * 375)])
        got = medians(rn[int(120 + t0 * 540):int(120 + t1 * 540)])
        cr = cloth(rc[int(t0 * 375):int(t1 * 375)])
        cg = cloth(rn[int(120 + t0 * 540):int(120 + t1 * 540)])
        er = energy(rc[int(t0 * 375):int(t1 * 375)]) & cr
        eg = energy(rn[int(120 + t0 * 540):int(120 + t1 * 540)]) & cg
        cover_r, cover_g = 100 * cr.mean(), 100 * cg.mean()
        eng_r = 100 * er.sum() / max(1, cr.sum())
        eng_g = 100 * eg.sum() / max(1, cg.sum())
        err["cloth"] += abs(cover_r - cover_g)
        err["energy"] += abs(eng_r - eng_g)
        err["color"] += sum(abs(ref[i] - got[i]) for i in range(3))
        rows.append((t0, ref, got, cover_r, cover_g, eng_r, eng_g))
    ratios = []
    for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        vals = []
        for a, h, y0 in ((rc, 375, 0), (rn, 540, 120)):
            y = int(y0 + t * h)
            cols = cloth(a[max(0, y - 4):min(a.shape[0], y + 5)]).sum(0)
            xs = np.where(cols >= 2)[0]
            vals.append((np.percentile(xs, 98) - np.percentile(xs, 2)) / 2 / h
                        if len(xs) >= 8 else 0.0)
        ratios.append(vals[1] / max(1e-6, vals[0]))
    err["silhouette"] = float(np.mean(ratios))
    err["total"] = (err["cloth"] + err["energy"] + err["color"] / 3.0)
    return dict(err=err, rows=rows)


def static_checks() -> None:
    cal = json.loads((ROOT / "tools" / "color_calibration.json").read_text())
    assert len(cal["rows"]) == 10, "falta el perfil de calibración medido"
    assert "color_calibration.json" in (
        ROOT / "tools" / "texture_pipeline.py").read_text()
    bb = json.loads((ROOT / "docs" / "CAPA_v1.17.0.bbmodel").read_text())
    assert len(bb["animations"]) == 4
    kfs = sum(len(an["keyframes"]) for a in bb["animations"]
              for an in a["animators"].values())
    assert kfs >= 11000, kfs
    icon = ROOT / "src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png"
    assert hashlib.sha256(icon.read_bytes()).hexdigest() == ICON_SHA, "icono alterado"
    java = (ROOT / "src/main/java/com/capatest/item/CapaDeteriorerItem.java").read_text()
    assert "spawnAura(Level level, Player player, boolean deterioro)" in java
    curios = (ROOT / "src/main/java/com/capatest/compat/CuriosCompat.java").read_text()
    assert "spawnAura(player.level(), player, deterioro)" in curios


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="falla con exit 1 si alguna métrica supera su umbral")
    args = ap.parse_args()
    static_checks()
    res = measure()
    err = res["err"]
    print("  BANDA | REFERENCIA (mediana / tela% / energia%) | MODELO")
    for t, ref, got, cr, cg, er, eg in res["rows"]:
        print(f"  t={t:.1f} | {[int(x) for x in ref]} {cr:5.1f}% {er:5.1f}%"
              f" | {[int(x) for x in got]} {cg:5.1f}% {eg:5.1f}%")
    print("\n  ERROR ACUMULADO (menor es mejor):")
    for key in ("cloth", "energy", "color", "silhouette", "total"):
        lim = LIMITS[key]
        print(f"    {key:<11} {err[key]:7.2f}   limite {lim:6.2f}")
    print(f"  ratio de silueta t=0.2..0.7: {err['silhouette']:.2f}x")
    if args.check:
        bad = [k for k in LIMITS if err[k] > LIMITS[k]]
        if bad:
            print("FALLO: métricas fuera de umbral: " + ", ".join(bad),
                  file=sys.stderr)
            sys.exit(1)
        print("OK: autoevaluación dentro de umbrales, icono y runtime intactos")
    else:
        print("(informe; usa --check para que falle como test de CI)")


main()
