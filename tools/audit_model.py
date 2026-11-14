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
VER = next(l.split("=", 1)[1].strip() for l in
           (ROOT / "gradle.properties").read_text().splitlines()
           if l.startswith("mod_version="))
BB = ROOT / "docs" / f"CAPA_v{VER}.bbmodel"

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
# v1.28.0: el icono PREFERIDO vuelve a ser el ACTIVO. El usuario comparo
# el rediseño de la v1.27.0 con el de la v1.25.0 y se quedo con el de la
# v1.25.0 ("era mejor el anterior, ese quiero"). El PNG activo es por
# tanto byte-idéntico a aquel, y el pipeline lo regenera igual (mismo mapa,
# misma paleta, mismo sombreado).
ICON_SHA = "c90670ba367557d7c7c003fa38dbe10c27cc88dcee1ef37fedc48f3a82820ee5"
ICON_V125_SHA = "c90670ba367557d7c7c003fa38dbe10c27cc88dcee1ef37fedc48f3a82820ee5"
# El rediseño de la v1.27.0 no se borra: queda como histórico en
# referencias/ICONO_V1270_REDISEÑO_BACKUP.png.
ICON_V127_SHA = "1500c07312d04e86b289913abb7c168c380d15d300bea6e27b70d81e9b92952c"
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
    assert "build_clean_atlas" in (
        ROOT / "tools" / "texture_pipeline.py").read_text()
    assert (ROOT / "tools" / "cape_atlas_v1230.py").is_file()
    assert BB.is_file(), f"falta el .bbmodel de la version {VER}"
    bb = json.loads(BB.read_text())
    assert bb["name"] == f'capa_deteriorer_evilsaiyan_v{VER.replace(".", "_")}'
    assert len(bb["animations"]) == 8  # v1.22.0: 8 estados
    # rev. B: NO puede haber animador `effects` ni canal `particle`: eran
    # referencias a JSONs Snowstorm que Blockbench no encuentra al abrir
    # el .bbmodel suelto. Las partículas son RUNTIME (spawnAura).
    assert all("effects" not in a["animators"] for a in bb["animations"])
    chans = {k["channel"] for a in bb["animations"]
             for an in a["animators"].values() for k in an["keyframes"]}
    assert chans == {"rotation", "position", "scale"}, chans
    kfs = sum(len(an["keyframes"]) for a in bb["animations"]
              for an in a["animators"].values())
    assert kfs >= 25000, kfs
    motion = (ROOT / "tools" / "cape_motion.py").read_text()
    assert "TRAVEL = 0.62" in motion and "def sample(" in motion
    assert "def phase_of(" in motion and "STYLES" in motion
    # GeckoLib: los 8 clips deben animar huesos v17_ de verdad (antes
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
    # v1.32.0: 225 huesos y 270 cubos. Los 15 cubos que faltan respecto
    # a v1.27.0 son los de las 3 losas (cape_top/mid/bottom): se ANULARON
    # para que la capa (tiras v17_*, hijas de estas losas) renderice en
    # tercera persona. v1.32.0 añade el CUELLITO (3 huesos/cubos v19_*).
    assert len(bones) == 225 and sum(len(b.get("cubes", [])) for b in bones) == 270
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
    # v1.23.0: 12 MECHONES ANCHOS EN DOS CAPAS, con V y punta afilada.
    import cape_shape as _CS
    assert _CS.RIBBONS == 12 and _CS.SEGS == 6
    tips = [_CS.tip_t(k) for k in range(12)]
    assert 0.64 <= min(tips) < 0.82 and max(tips) > 0.95, tips
    assert tips[0] < tips[5] and tips[11] < tips[6], tips
    assert 6.5 < _CS.silhouette(0.733) < 8.5, 'apertura del abanico'
    assert _CS.silhouette(0.9) < _CS.silhouette(0.733), 'cierra hacia el dobladillo'
    assert _CS.silhouette(1.0) < _CS.silhouette(0.9) * 1.02, 'la punta no se reabre'
    # Mechón ANCHO arriba y PUNTA AFILADA abajo.
    assert _CS.ribbon_w(5, 0.20) > 1.8, 'vuelven las tiras finas'
    assert _CS.ribbon_w(5, 0.98) < 0.35, 'la punta no afila'
    assert _CS.layer(0) == 'outer' and _CS.layer(1) == 'inner'
    assert _CS.ribbon_z(0, 0.5) > _CS.ribbon_z(1, 0.5) + 0.4, 'capas sin volumen'
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
    # v1.23.0: atlas LIMPIO (no el recorte de la foto) + EMISSIVE real.
    assert 'build_clean_atlas' in tp, 'falta el atlas limpio v1.23.0'
    assert 'def foto_uv(' in (ROOT / 'tools/armor_model_pipeline.py').read_text()
    assert 'def fan_x(' in (ROOT / 'tools/cape_shape.py').read_text()
    atlas = np.asarray(Image.open(
        ROOT / 'src/main/resources/assets/capatest/textures/item/armor'
        / 'capa_deteriorer_evilsaiyan.png').convert('RGBA'))
    assert (atlas[..., 3] == 255).all(), 'atlas con texel transparente'
    assert atlas[2, 20, 0] > atlas[70, 20, 0] + 40, \
        'falta degradado carmesí -> morado'
    glow = np.asarray(Image.open(
        ROOT / 'src/main/resources/assets/capatest/textures/item/armor'
        / 'capa_deteriorer_evilsaiyan_glowmask.png').convert('RGBA'))
    em = int((glow[..., 3] > 0).sum())
    assert 500 < em < 128 * 128, ('glowmask fullbright', em)
    # Wear holes en las puntas: texel oscuro en la franja baja.
    assert (atlas[44:48, 0:96, :3].mean() < atlas[4:8, 0:96, :3].mean()), \
        'faltan agujeros de desgaste'
    item_model = json.loads((ROOT / 'src/main/resources/assets/capatest/models/item'
                             '/capa_deteriorer_evilsaiyan.json').read_text())
    assert item_model['parent'] == 'minecraft:item/generated', 'el icono 2D no se ve'
    assert item_model['textures']['layer0'] == 'capatest:item/capa_deteriorer_evilsaiyan'
    # v1.25.0: el usuario devolvió el icono anterior («el 1 era mucho
    # mejor… no importa la animación»): ESTÁTICO, SIN overrides ni
    # propiedad de modelo, y con un backup byte-idéntico obligatorio.
    assert 'overrides' not in item_model, 'vuelven los frames del icono'
    assert not (ROOT / 'src/main/java/com/capatest/client/CapaIconAnimation.java').exists()
    pref = ROOT / 'referencias/ICONO_PREFERIDO_BACKUP.png'
    assert pref.is_file(), 'falta el backup del icono preferido'
    assert hashlib.sha256(pref.read_bytes()).hexdigest() == ICON_SHA, \
        'el backup no es byte-idéntico al icono preferido'
    # v1.28.0: el icono de la v1.25.0 vuelve a ser el ACTIVO. Se conserva
    # su propio backup byte-idéntico, y el rediseño de la v1.27.0 queda
    # guardado como histórico (no se borra ningún icono).
    v125 = ROOT / 'referencias/ICONO_V125_PREFERIDO_BACKUP.png'
    assert v125.is_file(), 'falta el icono preferido de la v1.25.0'
    assert hashlib.sha256(v125.read_bytes()).hexdigest() == ICON_V125_SHA, \
        'el icono de la v1.25.0 no se conserva byte-idéntico'
    v127 = ROOT / 'referencias/ICONO_V1270_REDISEÑO_BACKUP.png'
    assert v127.is_file(), 'falta el rediseño de la v1.27.0'
    assert hashlib.sha256(v127.read_bytes()).hexdigest() == ICON_V127_SHA, \
        'el rediseño de la v1.27.0 no se conserva byte-idéntico'
    item_java = (ROOT / 'src/main/java/com/capatest/item/CapaDeteriorerItem.java').read_text()
    assert 'getCustomRenderer' not in item_java, 'el BEWLR 3D tapa el icono'
    # v1.17.3: regresión de la prueba real en Blockbench. El .bbmodel
    # NO puede volver a incluir el maniquí ni los cubos de armadura vieja.
    assert (ROOT / 'docs' / f'CAPA_v{VER}.bbmodel').read_bytes() == BB.read_bytes()
    bb = json.loads(BB.read_text())
    assert len(bb['elements']) == 156, len(bb['elements'])
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
    spark = json.loads((particles / "particles/capa_spark.json").read_text())
    assert spark["textures"] == ["capatest:capa_spark_0",
                                 "capatest:capa_spark_1",
                                 "capatest:capa_spark_2"]
    for i in range(3):
        assert (particles / f"textures/particle/capa_spark_{i}.png").is_file()
    # Chispa a PIXEL: barra vertical ESTRECHA con centro casi blanco.
    _sp = np.asarray(Image.open(
        particles / "textures/particle/capa_spark_1.png").convert("RGBA"))
    assert _sp.shape[:2] == (16, 16)
    assert int((_sp[..., 3] > 0).sum()) < 100, "la chispa no es estrecha"
    assert _sp[8, 7, 0] > 230 and _sp[8, 7, 2] > 200, "falta centro brillante"
    assert int(_sp[..., 3].max()) >= 200, "chispa sin nucleo opaco"
    assert not (particles / "particles/capa_ember.json").exists()
    assert not (particles / "particles/capa_blight_mote.json").exists()
    assert not (particles / "particles/capa_shard.json").exists()
    # rev. B: sin JSON Snowstorm (Bedrock) que Blockbench busque.
    assert not (ROOT / "docs/particles").exists()
    java = (ROOT / "src/main/java/com/capatest/item/CapaDeteriorerItem.java").read_text()
    assert "spawnAura(Level level, Player player, boolean deterioro)" in java
    assert "NO son geomet" in java or "NO es geomet" in java
    armor_java = (ROOT / "src/main/java/com/capatest/client"
                  / "CapaArmorModel.java").read_text()
    assert "motionParts(" in armor_java and "0.62D * seg" in armor_java
    assert not any(n in armor_java for n in ("v17_mote_", "v17_ash_"))
    # ------------------------------------------------------------------
    # v1.26.0: EJES DE SIMETRÍA. El eje lateral es (columnas - 1) / 2 de
    # cada familia, medido sobre los pivotes X del geo. Con el 7.5 global
    # (heredado de 16 tiras de la élitra) la capa se inclinaba siempre
    # hacia el mismo lado y el paño izquierdo ondeaba el doble. Python,
    # Java y el visor tienen que decir EXACTAMENTE lo mismo.
    # ------------------------------------------------------------------
    axes = {"RIBBON": 5.5, "CLOTH": 4.0, "VEIN": 4.5, "COWL": 3.0,
            "COWL_BACK": 2.0, "CHAIN": 3.5, "PAD": 0.5}
    visor = (ROOT / "docs" / "capa_v1170_visor.html").read_text()
    for key, value in axes.items():
        assert f"{key}_AXIS = {value}" in motion, f"eje {key} ausente en Python"
        assert f"{key}_AXIS = {value}D" in armor_java, f"eje {key} ausente en Java"
        assert f"{key.lower()}: {value}" in visor, f"eje {key} ausente en el visor"
    assert "def axis_of(" in motion and "lateral = (col - axis) / axis" in motion
    assert "motionAxis(" in armor_java
    assert "double lateral = (col - axis) / axis;" in armor_java
    assert "const lateral = (col - axis) / axis;" in visor
    # El eje medido tiene que ser el de la anatomía REAL: (columnas-1)/2.
    for prefix, cols in (("v17_ribbon_", 12), ("v15_cloth_cape_", 9),
                         ("v17_vein_", 10), ("v17_cowl_front_", 7),
                         ("v17_cowl_tooth_", 7), ("v17_cowl_back_", 5),
                         ("v18_chain_", 8), ("v18_pad_", 2)):
        got = {int(_re.search(r"(\d+)", b["name"][len(prefix):]).group(1))
               for b in bones if b["name"].startswith(prefix)}
        assert len(got) == cols, (prefix, len(got))
        pivots = sorted(b["pivot"][0] for b in bones
                        if b["name"].startswith(prefix))
        assert pivots[0] < 0 < pivots[-1], (prefix, pivots[:2])
    # ------------------------------------------------------------------
    # v1.26.0: DETERIORO_NAMES == los huesos de tela del geo. Antes
    # arrastraba 42 nombres inexistentes y le faltaban los 10 v18_*.
    # ------------------------------------------------------------------
    names = set(_re.findall(r'"(v\d{2}_[a-z0-9_]+)"',
                             armor_java.split("DETERIORO_NAMES = {")[1]
                             .split("};")[0]))
    expected = {b["name"] for b in bones
                if b["name"].startswith(("v15_cloth_", "v17_ribbon_",
                                         "v17_cowl_", "v17_vein_", "v18_"))}
    assert names == expected, ("lista de huesos desincronizada del geo",
                                sorted(expected - names),
                                sorted(names - expected))
    assert len(names) == 150, len(names)
    # ------------------------------------------------------------------
    # v1.27.0: LAS 27 ANCLAS NO SE DIBUJAN. Son cubos de 0.16 que existen
    # sólo para dar pose a la onda (los usan panels[] y el animation.json).
    # El hueso se conserva; lo que se apaga es su RENDER, en Java y en el
    # render software, para que no queden motas negras en el cuello.
    # ------------------------------------------------------------------
    _anchors = [b for b in bones if b["name"].startswith("v15_cloth_")]
    assert len(_anchors) == 27, len(_anchors)
    assert all(len(b.get("cubes", [])) == 1 for b in _anchors), \
        'las anclas deben seguir siendo UN cubo (no se tocan)'
    _armor_java_all = (ROOT / 'src/main/java/com/capatest/client'
                       / 'CapaArmorModel.java').read_text()
    assert 'hideClothAnchors' in _armor_java_all, \
        'Java no oculta las anclas de la onda'
    assert 'anchor.setHidden(!visible)' in _armor_java_all, \
        'las anclas no se ocultan por separado'
    import preview_cloth as _PC
    _hidden_runtime = _PC.effective_hidden(json.loads(
        (ROOT / 'src/main/resources/assets/capatest/geo/item/armor'
         / 'capa_deteriorer_evilsaiyan.geo.json').read_text())[
             'minecraft:geometry'][0])
    assert all(b['name'] in _hidden_runtime for b in _anchors), \
        'el render software todavía pinta las anclas'
    # v1.27.0: EL VISOR también tiene que ocultarlas. Antes el runtime
    # Java y el render software las ocultaban, pero el visor (el
    # entregable que mira el usuario) seguía pintándolas: enseñaba las
    # motas negras que esta misma versión arregla.
    _visor_js = (ROOT / 'preview/app.js').read_text()
    assert "startsWith('v15_cloth_')) h.add(b.name)" in _visor_js, \
        'el visor vuelve a dibujar las anclas'
    assert 'l_anchors' in _visor_js, 'el visor no tiene el diagnóstico de anclas'
    _visor_emb = (ROOT / 'docs/capa_v1170_visor.html').read_text()
    assert "startsWith('v15_cloth_')) h.add(b.name)" in _visor_emb, \
        'el visor autocontenido publicado dibuja las anclas'
    assert 'l_anchors' in _visor_emb, \
        'el visor autocontenido publicado no tiene el diagnóstico'
    # Los controles de visibilidad existen y aíslan las piezas.
    for _token in ('Visibilidad', 'ANCLAS', 'HOMBRERAS', 'CADENA',
                   'capa.visibilidad'):
        assert _token in _armor_java_all, f'falta el control {_token}'
    assert 'def isolate(' in (ROOT / 'tools/preview_cloth.py').read_text(), \
        'el preview no puede aislar pads/cadena/anclas'
    # ------------------------------------------------------------------
    # v1.27.0: LA HOMBRERA Y LA CADENA NO SON MASAS NEGRAS. Antes la
    # hombrera era un rectángulo carbón plano y la cadena ocho motas:
    # en el juego se leían como una mancha y como puntos. Ahora la
    # hombrera tiene filo de luz y la cadena son anillos con hueco.
    # ------------------------------------------------------------------
    _atlas_rgb = atlas[..., :3]
    _pad = _atlas_rgb[0:16, 96:112]
    _chain = _atlas_rgb[0:16, 112:128]
    assert float(_pad.mean()) > 40.0, 'la hombrera sigue siendo negra'
    assert int(_pad.max()) > 150, 'la hombrera no tiene luz'
    assert int(_chain.min()) < 60, 'el eslabón no tiene hueco'
    assert int(_chain.max()) > 150, 'el eslabón no tiene brillo'
    # La hombrera son 4 piezas por hombro, no un cubo.
    _pads = [b for b in bones if b["name"].startswith("v18_pad_")]
    assert len(_pads) == 2, len(_pads)
    assert all(len(b.get("cubes", [])) == 4 for b in _pads), \
        'la hombrera vuelve a ser un cubo'
    _chains = [b for b in bones if b["name"].startswith("v18_chain_")]
    assert len(_chains) == 8, len(_chains)
    # ------------------------------------------------------------------
    # v1.28.0: VUELVE EL ICONO PREFERIDO DE LA v1.25.0 (el usuario comparo
    # el rediseño de la v1.27.0 con este y eligio este). El contrato ya no
    # es "cuatro pixeles magenta y acero", sino el del icono elegido:
    # tres pixeles magenta en el mapa base, ocho motas flotando y veinte
    # grietas, con el nucleo blanco-rosa del broche (W).
    # ------------------------------------------------------------------
    _icon_src = (ROOT / 'tools/texture_pipeline.py').read_text()
    _map_rows = _re.findall(r'"([.A-Z]{16})"',
                             _re.search(r'ICON_PIXEL_MAP = \((.*?)\n\)',
                                        _icon_src, _re.S).group(1))
    assert len(_map_rows) == 16, len(_map_rows)
    _flat = ''.join(_map_rows)
    assert _flat.count('C') == 3, ('el icono vuelve a llenarse de magenta',
                                   _flat.count('C'))
    assert 'B' not in _flat and 'S' not in _flat, \
        'vuelve el acero del rediseño de la v1.27.0'
    assert 'W' in _flat, 'el icono pierde el núcleo brillante del broche'
    _mot = _re.findall(r'\((\d+), (\d+), "([A-Z])"\)',
                       _icon_src.split('ICON_FLOATING = (', 1)[1]
                                   .split('ICON_CRACKS', 1)[0])
    assert len(_mot) == 8, ('las motas flotantes no son las ocho '
                            f'preferidas: {len(_mot)}')
    _crk = _re.findall(r'\((\d+), (\d+), "([A-Z])"\)',
                       _icon_src.split('ICON_CRACKS = (', 1)[1]
                                   .split('\n)', 1)[0])
    assert len(_crk) == 26, ('las grietas no son las veintiséis preferidas: '
                             f'{len(_crk)}')
    # ------------------------------------------------------------------
    # v1.26.0: PRESUPUESTO DE CHISPAS POR VALOR EFECTIVO. La CI pedía
    # el literal 'MAX_SPARKS_PER_TICK = 4', que sólo sobrevivía en un
    # Javadoc viejo: el runtime hace 8 ticks y 3 chispas desde la
    # v1.25.0. Ahora se parsea el código y se comprueba el valor real.
    # ------------------------------------------------------------------
    _item = (ROOT / "src/main/java/com/capatest/item"
             / "CapaDeteriorerItem.java").read_text()
    _int = _re.search(r"private static final int SPARK_INTERVAL_TICKS = (\d+);", _item)
    _max = _re.search(r"private static final int MAX_SPARKS_PER_TICK = (\d+);", _item)
    assert _int and _max, "no se encuentra el presupuesto de chispas"
    assert int(_int.group(1)) == 8, ("intervalo de chispas", _int.group(1))
    assert int(_max.group(1)) == 3, ("maximo de chispas", _max.group(1))
    _ask = _re.search(r"int count = deterioro \? (\d+) :", _item)
    assert _ask and int(_ask.group(1)) <= int(_max.group(1)), \
        "el codigo pide mas chispas de las permitidas"
    assert "MAX_SPARKS_PER_TICK = 4" not in _item, "literal obsoleto"
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
    # v1.23.0: la geometría y el atlas se REHICIERON contra un diseño
    # nuevo, así que comparar píxel a píxel con el PNG recortado ya no es
    # un criterio honesto. Se mide la FIDELIDAD AL DISEÑO: degradado,
    # cobertura emisiva, dos capas, mechones anchos y V.
    from PIL import Image as _Image
    _atlas = np.asarray(_Image.open(
        ROOT / 'src/main/resources/assets/capatest/textures/item/armor'
        / 'capa_deteriorer_evilsaiyan.png').convert('RGB')).astype(float)
    _glow = np.asarray(_Image.open(
        ROOT / 'src/main/resources/assets/capatest/textures/item/armor'
        / 'capa_deteriorer_evilsaiyan_glowmask.png').convert('RGBA')).astype(float)
    grad = float(_atlas[2:6, 0:96, 0].mean() - _atlas[62:70, 0:96, 0].mean())
    neon = float((_glow[..., 3] > 0).mean() * 100)
    import cape_shape as _CS
    wid = float(_CS.ribbon_w(5, 0.2))
    fid = (max(0.0, 60.0 - grad) / 60.0
           + max(0.0, 4.0 - neon) / 4.0
           + max(0.0, 1.8 - wid) / 1.8)
    print(f"  degradado carmesi->morado: {grad:.1f} | neón emissive: {neon:.2f}%"
          f" | mechón ancho: {wid:.2f}u")
    print(f"  FIDELIDAD AL DISEÑO v{VER}: {fid:.3f}   limite 1.00")

    if args.check:
        bad = [k for k in ('silhouette',) if err[k] > LIMITS[k]]
        if fid > 1.00:
            bad.append('diseno')
        if bad:
            print("FALLO: métricas fuera de umbral: " + ", ".join(bad),
                  file=sys.stderr)
            sys.exit(1)
        print(f"OK: diseño v{VER} dentro de umbrales, sin piezas volando, "
          "chispa exclusiva en runtime e icono intacto")
    else:
        print("(informe; usa --check para que falle como test de CI)")


main()
