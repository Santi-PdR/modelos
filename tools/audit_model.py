#!/usr/bin/env python3
"""Contratos de recursos y comparación registrada con la imagen original.

`--check` exige una mejora de silueta y color con la misma cámara para
las dos versiones. verify_v1620 hace además la prueba de ajuste y rig.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

import preview_cloth as P

ROOT = Path(__file__).resolve().parents[1]
VER = next(l.split("=", 1)[1].strip() for l in
           (ROOT / "gradle.properties").read_text().splitlines()
           if l.startswith("mod_version="))
BB = ROOT / "docs" / f"CAPA_v{VER}.bbmodel"

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


def static_checks() -> None:
    cal = json.loads((ROOT / "tools" / "color_calibration.json").read_text())
    assert len(cal["rows"]) == 10, "falta el perfil de calibración medido"
    assert (ROOT / 'tools/cape_surface.py').is_file()
    assert (ROOT / f"docs/capa_v{VER.replace('.', '')}_registro.png").is_file()
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
    import cape_motion as motion
    assert len(motion.STYLES) == 8
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
    from armor_model_pipeline import FIT_BONE, relief
    n_fragments = sum(map(len, relief()['fragments'].values()))
    assert len(bones) == 226 and sum(len(b.get('cubes', [])) for b in bones) == 260+n_fragments
    rig = next(b for b in bones if b['name'] == FIT_BONE)
    assert rig['parent'] == 'chestplate' and not rig['cubes']
    forbidden = ("v17_mote_", "v17_ash_", "v17_yoke_",
                 "v16_mote_", "v16_ash_")
    assert not any(b["name"].startswith(forbidden) for b in bones), \
        "vuelve la geometría de partículas"
    # El contacto y la continuidad se miden sobre el rig, no sobre el
    # ancho de la V antigua ni sobre un gradiente global del atlas.
    import cape_shape as _CS
    assert _CS.RIBBONS == 12 and _CS.SEGS == 6
    tips = [_CS.tip_t(k) for k in range(12)]
    assert max(tips[1::2]) > .92 and min(tips[::2]) < .34
    assert sorted(tips)[-1]-sorted(tips)[-3] > .03, 'puntas alineadas'
    assert not any(c['uv']['north']==c['uv']['south'] for b in bones
                   if b['name'].startswith('v17_ribbon_') for c in b['cubes'])
    atlas = np.asarray(Image.open(P.ARMOR_TEX).convert('RGBA'))
    glow = np.asarray(Image.open(P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem+'_glowmask')).convert('RGBA'))
    assert atlas.shape == glow.shape == (512,512,4)
    assert (atlas[...,3] == 255).all() and np.count_nonzero(glow[...,3]) > 1500
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
    assert len(bb['elements']) == 149+n_fragments and sum(e['visibility'] for e in bb['elements']) == 122+n_fragments
    assert bb['resolution'] == {'width': 512, 'height': 512}
    assert all(max(f['uv']) <= 512 for e in bb['elements']
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
    # Chispa a PIXEL: barra vertical ESTRECHA con centro rosa y halo débil.
    _sp = np.asarray(Image.open(
        particles / "textures/particle/capa_spark_1.png").convert("RGBA"))
    assert _sp.shape[:2] == (16, 16)
    assert int((_sp[..., 3] >= 64).sum()) < 100, "la chispa no es estrecha"
    assert _sp[8, 7, 0] > 230 and _sp[8, 7, 2] > 175 and _sp[8, 7, 1] < 150, "falta centro brillante"
    assert int(_sp[..., 3].max()) >= 200, "chispa sin nucleo opaco"
    assert not (particles / "particles/capa_ember.json").exists()
    assert not (particles / "particles/capa_blight_mote.json").exists()
    assert not (particles / "particles/capa_shard.json").exists()
    # rev. B: sin JSON Snowstorm (Bedrock) que Blockbench busque.
    assert not (ROOT / "docs/particles").exists()
    java = (ROOT / "src/main/java/com/capatest/item/CapaDeteriorerItem.java").read_text()
    assert "spawnAura(Level level, Player player, ItemStack equipped)" in java
    armor_java = (ROOT / "src/main/java/com/capatest/client"
                  / "CapaArmorModel.java").read_text()
    assert "applyClothResponse(" in armor_java and "0.62D * seg" in armor_java
    assert not any(n in armor_java for n in ("v17_mote_", "v17_ash_"))
    # ------------------------------------------------------------------
    # El eje Python se deriva de la familia. El visor consume el bake y
    # sólo Java conserva su respuesta adicional al giro del portador.
    # El eje medido tiene que ser el de la anatomía REAL: (columnas-1)/2.
    for prefix, cols in (("v17_ribbon_", 12), ("v15_cloth_cape_", 9),
                         ("v17_cowl_front_", 7),
                         ("v17_cowl_tooth_", 7), ("v17_cowl_back_", 5),
                         ("v18_chain_", 8), ("v18_pad_", 2)):
        got = {int(_re.search(r"(\d+)", b["name"][len(prefix):]).group(1))
               for b in bones if b["name"].startswith(prefix)}
        assert len(got) == cols, (prefix, len(got))
        pivots = sorted(b["pivot"][0] for b in bones
                        if b["name"].startswith(prefix))
        assert pivots[0] < 0 < pivots[-1], (prefix, pivots[:2])
    vestiges = [b for b in bones if b['name'].startswith('v17_vein_')]
    assert len(vestiges) == 10 and all(not b['cubes'] for b in vestiges)
    assert 'RIBBONS = 12' in armor_java and 'LAST_SEGMENT = 4' in armor_java
    assert 'b.getRotX() +' in armor_java and not _re.search(r'\bsetPos[XYZ]\(', armor_java)
    assert 'rearPadBaseX' not in armor_java, 'la onda antigua sobreescribe la hombrera'
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
    _visor_emb = (ROOT / 'docs/capa_v1170_visor.html').read_text()
    assert "startsWith('v15_cloth_')) h.add(b.name)" in _visor_emb, \
        'el visor autocontenido publicado dibuja las anclas'
    # Los controles de visibilidad existen y aíslan las piezas.
    for _token in ('Visibilidad', 'ANCLAS', 'HOMBRERAS', 'CADENA',
                   'capa.visibilidad'):
        assert _token in _armor_java_all, f'falta el control {_token}'
    assert 'def isolate(' in (ROOT / 'tools/preview_cloth.py').read_text(), \
        'el preview no puede aislar pads/cadena/anclas'
    # Los datos de cada cara se verifican en verify_v1600. El acero
    # blanco de la versión anterior no es criterio para la placa de carbón.
    _pads = [b for b in bones if b["name"].startswith("v18_pad_")]
    assert len(_pads) == 2, len(_pads)
    assert all(len(b["cubes"]) == 4 + len(relief()["fragments"].get(b["name"], [])) for b in _pads), \
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
    assert "Math.min(aura.count(), MAX_SPARKS_PER_TICK)" in _item
    curios = (ROOT / "src/main/java/com/capatest/compat/CuriosCompat.java").read_text()
    assert "spawnAura(player.level(), player, stack)" in curios


def main() -> None:
    from verify_v1630 import GEO_BASE, TEX_BASE, GLOW, registered_metrics, similarity

    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check',action='store_true',help='aplica los mínimos de fidelidad')
    args=ap.parse_args()
    static_checks()
    now=P.load(P.ARMOR_GEO)
    if args.check:
        similarity(now,P.ARMOR_TEX,GLOW)
        print(f'OK: contorno y color registrados de v{VER}; recursos protegidos')
    else:
        (a,b),pink=registered_metrics(P.load(GEO_BASE),now,P.ARMOR_TEX,baseline_atlas=TEX_BASE)
        print(f"IoU: {a['all']:.1%} → {b['all']:.1%}; RGB {a['mae']:.1f} → {b['mae']:.1f}; "
              f"rosa intenso: {b['pink']:.1%} (referencia {pink:.1%})")


if __name__ == '__main__':
    main()
