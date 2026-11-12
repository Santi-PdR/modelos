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

# v1240: umbrales REAJUSTADOS tras la ronda de forma/energía/color. El
# estado medido es total 139.0 (paño 73.5, energía 32.8, color 98,
# silueta 1.41x); se deja ~15% de holgura para diferencias de versión de
# Pillow/numpy entre el sandbox y Ubuntu. Antes el límite era 205 sobre
# 190.8: ahora el test PROTEGE la mejora conseguida.
LIMITS = {
    "total": 165.0,
    "color": 120.0,
    "cloth": 95.0,
    "energy": 55.0,
    "silhouette": 1.60,
}
ICON_SHA = "25133aee71c2e46e3995855aa5df601827c26ae26b384394f2b696312d20151c"
ICON_BACKUP_SHA = "e88ccec0a0c67b1ad0982ed781f0d684ae4662660c545fa134574781967e4840"


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
    ids = {k["data_points"][0]["effect"] for a in bb["animations"]
           for k in a["animators"]["effects"]["keyframes"]}
    assert len(ids) == 3, ids
    kfs = sum(len(an["keyframes"]) for a in bb["animations"]
              for an in a["animators"].values())
    assert kfs >= 11900, kfs
    # v1240: forma y efectos de la ronda, verificados como contrato.
    tp = (ROOT / "tools" / "texture_pipeline.py").read_text()
    assert "def shape_energy_density" in tp
    assert "def _energy_strokes" in tp
    cal_e = ROOT / "tools" / "energy_calibration.py"
    assert cal_e.is_file() and "ENERGY_GAIN" in cal_e.read_text()
    import re as _re
    knots = _re.findall(r"\(([\d.]+),\s*([\d.]+)\)",
                        _re.search(r"ENERGY_GAIN = \((.*?)\)\n", tp,
                                   _re.S).group(1))
    assert len(knots) == 12, len(knots)
    geo = json.loads((ROOT / "src/main/resources/assets/capatest/geo/item"
                      "/armor/capa_deteriorer_evilsaiyan.geo.json").read_text())
    bones = geo["minecraft:geometry"][0]["bones"]
    assert len(bones) == 286 and sum(len(b.get("cubes", [])) for b in bones) == 340
    # v1283: la V se verifica por PROPIEDADES, no por los numeros de una
    # ronda concreta. Todos los lobulos llegan al dobladillo (paño en
    # t=0.8), sus puntas son desiguales y la envolvente CIERRA de forma
    # monotona hasta t=1.0 en vez de reabrirse en abanico.
    import cape_shape as _CS
    tips = [_CS.tip_t(k) for k in range(16)]
    assert min(tips) >= 0.90 and max(tips) - min(tips) > 0.03, tips
    assert 6.5 < _CS.silhouette(0.733) < 8.5, 'apertura del abanico'
    assert _CS.silhouette(0.9) < _CS.silhouette(0.733), 'cierra hacia el dobladillo'
    assert _CS.silhouette(1.0) < _CS.silhouette(0.9) * 1.02, 'la punta no se reabre'
    assert 'def charred_hem' in tp, 'falta el deshilachado del dobladillo'
    assert 'BEST-SO-FAR' in cal_e.read_text(), 'falta el mejor-perfil conservado'
    icon = ROOT / "src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png"
    assert hashlib.sha256(icon.read_bytes()).hexdigest() == ICON_SHA, "icono alterado"
    # El icono APROBADO sigue disponible, byte-identico, por si la
    # remasterizacion no convence: tools/restore_icon.py lo restaura.
    for backup in ("referencias/ICONO_APROBADO_BACKUP.png",
                   "tools/originals/icono_aprobado_v1130.png"):
        bp = ROOT / backup
        assert bp.is_file(), backup
        assert hashlib.sha256(bp.read_bytes()).hexdigest() == ICON_BACKUP_SHA, backup
    assert (ROOT / "tools/restore_icon.py").is_file()
    particles = ROOT / "src/main/resources/assets/capatest"
    assert (particles / "particles/capa_shard.json").is_file()
    for i in range(3):
        assert (particles / f"textures/particle/capa_shard_{i}.png").is_file()
    assert (ROOT / "docs/particles/capa_shards.json").is_file()
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
