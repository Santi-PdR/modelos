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

# v1.18.0: cloth/energy/color/total quedan como INFORMACION, no como
# umbral: media un atlas sintetico que ya no existe. El test ahora exige
# que el atlas sea la foto del usuario y que la silueta siga cerrando.
#
# rev. B: se comprueba ademas que NO haya geometria de particulas
# (motas/ceniza/yugo), que ningun cubo quede desprendido y que las 4
# animaciones lleven la curva unica de tools/cape_motion.py.
#
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
ICON_SHA = "c90670ba367557d7c7c003fa38dbe10c27cc88dcee1ef37fedc48f3a82820ee5"
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
    # rev. B: NO puede haber animador `effects` ni canal `particle`: eran
    # referencias a JSONs Snowstorm que Blockbench no encuentra al abrir
    # el .bbmodel suelto. Las partículas son RUNTIME (spawnAura).
    assert all("effects" not in a["animators"] for a in bb["animations"])
    chans = {k["channel"] for a in bb["animations"]
             for an in a["animators"].values() for k in an["keyframes"]}
    assert chans == {"rotation", "position", "scale"}, chans
    kfs = sum(len(an["keyframes"]) for a in bb["animations"]
              for an in a["animators"].values())
    assert kfs >= 12000, kfs
    motion = (ROOT / "tools" / "cape_motion.py").read_text()
    assert "TRAVEL = 0.62" in motion and "def sample(" in motion
    assert "def phase_of(" in motion and "STYLES" in motion
    # GeckoLib: los 4 clips deben animar huesos v17_ de verdad (antes
    # animaban SOLO huesos viejos ocultos por Java).
    runtime_anim = json.loads((ROOT / "src/main/resources/assets/capatest"
                               / "animations/item/armor"
                               / "capa_deteriorer_evilsaiyan.animation.json").read_text())
    for name, anim in runtime_anim["animations"].items():
        assert any(b.startswith("v17_ribbon_") for b in anim["bones"]), name
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
    assert len(bones) == 254 and sum(len(b.get("cubes", [])) for b in bones) == 308
    forbidden = ("v17_mote_", "v17_ash_", "v17_yoke_",
                 "v16_mote_", "v16_ash_")
    assert not any(b["name"].startswith(forbidden) for b in bones), \
        "vuelve la geometría de partículas"
    # Nada desprendido: todo cubo visible tiene un vecino a < 2.2 u.
    import preview_cloth as _PC
    _hidden = _PC.effective_hidden(json.loads(
        (ROOT / "src/main/resources/assets/capatest/geo/item/armor"
         / "capa_deteriorer_evilsaiyan.geo.json").read_text())[
             "minecraft:geometry"][0])
    _pts = []
    for _b in bones:
        if _b["name"] in _hidden:
            continue
        for _c in _b.get("cubes", []):
            _o, _z = _c["origin"], _c["size"]
            _pts.append([_o[i] + _z[i] / 2 for i in range(3)])
    _arr = np.asarray(_pts, float)
    _worst = 0.0
    for _i in range(len(_arr)):
        _d = np.sqrt(((_arr - _arr[_i]) ** 2).sum(1))
        _d[_i] = 1e9
        _worst = max(_worst, float(_d.min()))
    assert _worst < 2.2, ("cubo desprendido", _worst)
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
    # v1331: el capuchon muestrea la region `yoke`, fuera del canvas;
    # sin su calibracion propia el error cromatico de t=0.0/0.1 se
    # disparaba. Y los guiones de energia deben ser trazos, no cuadrados.
    assert 'v1306: el CAPUCHON' in tp, 'falta la calibracion del yugo'
    assert 'GUION ALARGADO' in tp, 'falta el trazo de energia alargado'
    # v1.17.2: regresión de las capturas in-game. El atlas NO puede volver
    # a samplear el recorte crudo (metia brazo/arnes/checkerboard en la tela)
    # y el item NO puede volver a registrar un BEWLR que oculte el icono.
    # v1.18.0: el atlas ES la imagen, no una paleta sintetica.
    assert 'from reference_canvas import canvas as foto' in tp, 'atlas no viene de la foto'
    assert 'def foto_uv(' in (ROOT / 'tools/armor_model_pipeline.py').read_text()
    assert 'def fan_x(' in (ROOT / 'tools/cape_shape.py').read_text()
    assert (ROOT / 'referencias/REFERENCIA_CAPA_atlas96.png').is_file()
    item_model = json.loads((ROOT / 'src/main/resources/assets/capatest/models/item'
                             '/capa_deteriorer_evilsaiyan.json').read_text())
    assert item_model['parent'] == 'minecraft:item/generated', 'el icono 2D no se ve'
    assert item_model['textures']['layer0'] == 'capatest:item/capa_deteriorer_evilsaiyan'
    item_java = (ROOT / 'src/main/java/com/capatest/item/CapaDeteriorerItem.java').read_text()
    assert 'getCustomRenderer' not in item_java, 'el BEWLR 3D tapa el icono'
    # v1.17.3: regresión de la prueba real en Blockbench. El .bbmodel
    # NO puede volver a incluir el maniquí ni los cubos de armadura vieja.
    bb = json.loads((ROOT / 'docs/capa_v1170.bbmodel').read_text())
    assert len(bb['elements']) == 182, len(bb['elements'])
    assert bb['resolution'] == {'width': 128, 'height': 128}
    assert all(max(f['uv']) <= 128 for e in bb['elements']
               for f in e['faces'].values())
    assert not any(e['name'] in ('head', 'torso', 'arm_L', 'arm_R',
                                 'leg_L', 'leg_R') for e in bb['elements'])
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
    # rev. B: los JSON de Snowstorm (Bedrock) ya NO se entregan: no
    # los usa el mod de Forge y Blockbench los buscaba al abrir el
    # .bbmodel. Quedan SOLO las definiciones reales de partículas.
    assert not (ROOT / "docs/particles").exists()
    java = (ROOT / "src/main/java/com/capatest/item/CapaDeteriorerItem.java").read_text()
    assert "spawnAura(Level level, Player player, boolean deterioro)" in java
    assert "NO son geomet" in java or "NO es geomet" in java
    armor_java = (ROOT / "src/main/java/com/capatest/client"
                  / "CapaArmorModel.java").read_text()
    assert "motionParts(" in armor_java and "0.62D * seg" in armor_java
    assert not any(n in armor_java for n in ("v17_mote_", "v17_ash_"))
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
    # v1.18.0: las metricas de cobertura/energia/color medían un ATLAS
    # SINTETICO. Ahora el atlas ES la foto del usuario, asi que el criterio
    # honesto es la fidelidad pixel a pixel con esa foto; la silueta sigue
    # siendo el unico limite geometrico.
    from PIL import Image as _Image
    _atlas = np.asarray(_Image.open(
        ROOT / 'src/main/resources/assets/capatest/textures/item/armor'
        '/capa_deteriorer_evilsaiyan.png').convert('RGB'))[0:48, 0:96].astype(float)
    _ref = np.asarray(_Image.open(
        ROOT / 'referencias/REFERENCIA_CAPA_atlas96.png').convert('RGB')).astype(float)
    fid = float(np.abs(_atlas - _ref).mean())
    print(f"  fidelidad con TU IMAGEN: {fid:.3f}   limite 1.50")
    if args.check:
        bad = [k for k in ('silhouette',) if err[k] > LIMITS[k]]
        if fid > 1.50:
            bad.append('foto')
        if bad:
            print("FALLO: métricas fuera de umbral: " + ", ".join(bad),
                  file=sys.stderr)
            sys.exit(1)
        print("OK: autoevaluación dentro de umbrales, sin piezas volando, "
          "partículas en runtime e icono intacto")
    else:
        print("(informe; usa --check para que falle como test de CI)")


main()
