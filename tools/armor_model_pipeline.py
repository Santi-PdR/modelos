#!/usr/bin/env python3
"""v1.23.0 — GEOMETRÍA REHECHA DESDE CERO (Blockbench).

El usuario: «Rehace la geometría, textura y partículas de esta capa en
Blockbench para que deje de parecer hecha de tiras finas y sueltas. Agrega
un cuello alto y grueso de tela roja oscura (estilo bufanda) conectado a
dos hombreras pequeñas color carbón y una cadena oscura en la parte
superior de la espalda. Reemplaza las tiras delgadas por 10 a 14 mechones
anchos, planos y superpuestos en dos capas (una interna morada oscura y
una externa rojo carmesí) que se curven orgánicamente y terminen en punta
afilada para dar volumen».

Qué hay ahora (``tools/cape_shape.py`` es la fuente de verdad):

  * 72 huesos prístinos, BYTE-IDÉNTICOS, SIN cubos en el .bbmodel (Java
    los oculta; Blockbench los conserva como grupos vacíos por la jerarquía).
  * 27 anclas `v15_cloth_*`, diminutas y ENTERRADAS dentro del cuello:
    mantienen viva la onda de `CapaArmorModel.panels[]` sin dibujar nada.
  * CUELLO ALTO Y GRUESO: 7 piezas frontales carmesí oscuro (2.6 de alto,
    1.5 de fondo) + 7 faldones anchos que lo conectan con la tela +
    5 piezas de reverso. Forma de U que abraza el cuello, no una banda.
  * 2 HOMBRERAS CARBÓN (`v18_pad_*`) y una CADENA OSCURA de 8 eslabones
    (`v18_chain_*`) sobre la parte alta de la espalda.
  * 12 MECHONES (`v17_ribbon_k_seg0..6`): 6 externos carmesí y 6 internos
    morado oscuro, intercalados, ~1.8-2.6 de ancho con SOLAPE real,
    curvados en X y en Z, con punta afilada de 0.10. Dos capas con
    profundidad distinta ⇒ volumen, no élitra.
  * 10 GRIETAS 3D neón (`v17_vein_*`) sobre los mechones externos, con
    textura del parche NEÓN y glowmask fullbright.

Uso:  PYTHONPATH=tools:tools/_deps python3 tools/armor_model_pipeline.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cape_shape as CS
from cloth_spec import assert_opaque

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

INFLATE = (0.01, 0.03, 0.05)

COLLAR_FRONT = 7
COLLAR_FLAPS = 7
COLLAR_BACK = 5
PADS = 2
CHAIN_LINKS = 8
CRACKS = 10

# Parches del atlas limpio (ver tools/cape_atlas_v1230.py).
OUTER_V, INNER_V = 0.0, 48.0
STRIPE_W = 96.0 / (CS.RIBBONS // 2)          # 16 texels por mechón


def ribbon_thick(k: int) -> float:
    """Mechón PLANO pero con cuerpo: 0.52-0.72 unidades de fondo."""
    return 0.62 + 0.10 * math.sin(k * 1.7 + 0.3)


def band(u0: float, w: float, v0: float, h: float) -> dict:
    s = {"uv": [round(u0, 4), round(v0, 4)],
         "uv_size": [round(max(0.5, w), 4), round(max(0.5, h), 4)]}
    assert_opaque(s)
    return s


# Cantos: un parche oscuro y opaco (carbón / sombra), sin filetes.
DARK = band(120.0, 2.0, 100.0, 2.0)
# v1.27.0: la hombrera y la cadena tienen parches PROPIOS. Antes ambas
# muestreaban un gris carbón plano: la hombrera se leía como una masa
# negra y la cadena como una fila de puntos.
PAD_UV = band(97.0, 13.0, 1.0, 13.0)        # cara superior de la placa
PAD_SIDE_UV = band(97.0, 13.0, 65.0, 13.0)  # lateral de la placa
CREST_UV = band(113.0, 13.0, 65.0, 13.0)    # cresta exterior
CHAIN_UV = band(113.0, 13.0, 1.0, 13.0)     # anillo del eslabón
CHAIN_TOP_UV = band(97.0, 13.0, 81.0, 13.0)  # canto superior del eslabón
COLLAR_UV = band(97.0, 28.0, 17.0, 21.0)
NEON_UV = band(98.0, 28.0, 41.0, 21.0)


def cowl_uv(w: float, h: float, i: int = 0) -> dict:
    """v1.23.0: el cuello es UNA bufanda continua, no 7 cajas rayadas.

    Todas las piezas muestrean el MISMO parche carmesí oscuro; el relieve
    lo dan los pliegues del atlas y la rotación Y de las solapas.
    """
    return band(97.5, 28.0, 17.5, min(21.0, max(5.0, h * 6.0)))


def foto_uv(cx: float, cy: float, w: float, h: float) -> dict:
    """Compatibilidad: UV del degradado externo según la altura real.

    v1.23.0 ya NO usa el PNG de la referencia: el atlas es un degradado
    limpio. Esta función se conserva para el item plegado / auditorías y
    para las piezas que no son mechón (faldones del cuello).
    """
    t = max(0.0, min(1.0, (CS.Y_TOP - cy) / CS.HEIGHT))
    v = OUTER_V + t * 47.0
    u = 48.0 + cx * (96.0 / 17.80) - min(14.0, w * 5.0) / 2.0
    u = max(0.5, min(95.5 - min(14.0, w * 5.0), u))
    return band(u, min(14.0, w * 5.0), v, min(10.0, max(1.5, h * 0.8)))


def lock_uv(k: int, t0: float, t1: float, w: float, h: float) -> dict:
    """Franja vertical CONTINUA de un mechón en SU capa del atlas.

    6 mechones por capa comparten 96 texels de ancho (16 cada uno). La
    externa usa v=0..48; la interna v=48..96. Así el degradado y las
    grietas fluyen de arriba abajo sin tablero ni costuras.
    """
    j = k // 2
    u = j * STRIPE_W + 0.5
    base = OUTER_V if CS.layer(k) == "outer" else INNER_V
    v = base + t0 * 48.0
    vh = max(1.0, min(base + 47.8 - v, (t1 - t0) * 48.0 * 1.10))
    return band(u, STRIPE_W - 1.0, v, vh)


def tip_uv(k: int, t: float) -> dict:
    """La punta muestrea la franja de DESGASTE (agujeros) de su capa."""
    j = k // 2
    base = OUTER_V if CS.layer(k) == "outer" else INNER_V
    return band(j * STRIPE_W + 1.0, STRIPE_W - 2.0, base + 40.0, 7.5)


def cube16(origin, size, front: dict, side: dict | None = None,
           inflate: float = 0.0) -> dict:
    s = side or DARK
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": {"north": dict(front), "south": dict(front),
               "east": dict(s), "west": dict(s),
               "up": dict(s), "down": dict(s)},
        "inflate": round(inflate, 4),
    }


def cube_faces(origin, size, faces: dict, inflate: float = 0.0) -> dict:
    """v1.27.0: cubo con UV POR CARA.

    La hombrera necesita que su cara superior sea la placa de acero
    iluminada y sus laterales el acero oscuro con filete: con el
    `cube16()` antiguo (dos parches) era imposible.
    """
    missing = {"north", "south", "east", "west", "up", "down"} - set(faces)
    assert not missing, f"faltan caras: {missing}"
    out = {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": {k: dict(v) for k, v in faces.items()},
        "inflate": round(inflate, 4),
    }
    return out


def bone(name: str, parent: str | None, pivot, rotation, cubes) -> dict:
    out = {"name": name,
           "pivot": [round(v, 4) for v in pivot],
           "rotation": [round(v, 4) for v in rotation],
           "cubes": cubes}
    if parent:
        out["parent"] = parent
    return out


def section_for_t(t: float) -> str:
    if t < 0.34:
        return "cape_top"
    if t < 0.67:
        return "cape_mid"
    return "cape_bottom"


def build() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)

    # ------------------------------------------------------------------
    # v1.30.0: SE ANULA LOS CUBOS DE LAS LOSAS cape_top/mid/bottom.
    #
    # Las tiras v17_* (la capa nueva) son HIJAS de estas tres losas.
    # Antes Java las ocultava con setHidden(true), pero en tercera
    # persona (F5) GeckoLib NO renderiza a los hijos de un hueso
    # oculto: la capa entera desaparecía al mirarla desde atrás.
    #
    # Ahora se quitan los cubos de la losa (queda visible, sin cubos)
    # y Java NO las oculta. Las tiras, al ser hijas de un hueso
    # visible, renderizan desde cualquier ángulo. La "masa negra" de
    # la losa original tampoco se ve: no tiene cubos.
    for _slab in ("cape_top", "cape_mid", "cape_bottom"):
        for _b in bones:
            if _b["name"] == _slab:
                _b["cubes"] = []

    # ------------------------------------------------------------------
    # 1. 27 anclas INVISIBLES: dentro del cuello grueso. Java las necesita
    #    para panels[]; en Blockbench quedan tapadas por el paño opaco.
    # ------------------------------------------------------------------
    for si, section in enumerate(("cape_top", "cape_mid", "cape_bottom")):
        for col in range(9):
            ax = (col - 4) * 0.95
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [ax, 23.60, 2.40], [0.0, 0.0, 0.0],
                [cube16((ax - 0.08, 23.52, 2.32), (0.16, 0.16, 0.16),
                        band(2.0 + col * 2.0, 2.0, 100.0, 2.0),
                        DARK, INFLATE[0])]))

    # ------------------------------------------------------------------
    # 2. CUELLO ALTO Y GRUESO (bufanda carmesí oscuro) en forma de U.
    # ------------------------------------------------------------------
    for i in range(COLLAR_FRONT):
        fx = (i - (COLLAR_FRONT - 1) / 2.0) / ((COLLAR_FRONT - 1) / 2.0)
        x = fx * 4.30
        w = 1.55 + 0.18 * (1.0 - abs(fx))
        height = 2.35 + 0.55 * (1.0 - abs(fx)) + 0.10 * math.sin(i * 2.3)
        y_top = 24.55 + 0.42 * abs(fx)   # U:_sube hacia los hombros
        bottom = y_top - height
        z = 1.85 + 0.45 * (1.0 - abs(fx))
        depth = 1.50
        rot_y = -fx * 22.0
        bones.append(bone(
            f"v17_cowl_front_{i}", "chestplate",
            [x, y_top - height / 2.0, z + depth / 2.0],
            [0.0, rot_y, fx * 3.0],
            [cube16((x - w / 2.0, bottom, z), (w, height, depth),
                    cowl_uv(w, height, i), COLLAR_UV, INFLATE[i % 3])]))
        # Faldón ANCHO y solapado: el cuello se CONECTA con los mechones.
        fw = w * 1.08
        fh = 1.45 + 0.35 * (1.0 - abs(fx))
        fz = z + depth + 0.05
        bones.append(bone(
            f"v17_cowl_tooth_{i}", f"v17_cowl_front_{i}",
            [x, bottom + fh / 2.0 - 0.15, fz + 0.40],
            [0.0, 0.0, fx * 5.0],
            [cube16((x - fw / 2.0, bottom - fh + 0.10, fz),
                    (fw, fh, 0.85), cowl_uv(fw, fh, i + 2),
                    COLLAR_UV, INFLATE[1])]))

    for i in range(COLLAR_BACK):
        fx = (i - (COLLAR_BACK - 1) / 2.0) / max(1.0, (COLLAR_BACK - 1) / 2.0)
        x = fx * 3.70
        height = 2.05 + 0.45 * (1.0 - abs(fx))
        y_top = 24.60
        bones.append(bone(
            f"v17_cowl_back_{i}", "chestplate",
            [x, y_top - height / 2.0, 1.35],
            [0.0, 0.0, -fx * 6.0],
            [cube16((x - 0.90, y_top - height, 1.15),
                    (1.80, height, 0.80), cowl_uv(1.8, height, i),
                    COLLAR_UV, INFLATE[2])]))

    # ------------------------------------------------------------------
    # 3. HOMBRERAS (pauldron de 3 piezas) + CADENA de 8 eslabones.
    #
    # v1.27.0: la hombrera era UN cubo 2.40x0.90x1.80 de gris carbón
    # plano: en el juego se leía como una MASA NEGRA en el hombro. Ahora
    # son tres piezas encajadas (placa + cresta exterior + labio
    # delantero) con filete de luz en el borde: se lee como una
    # hombrera de verdad. La cadena son ocho ANILLOS (no ocho motas)
    # que se solapan y se cruzan, y van POR DETRÁS del cuello para que
    # se lean como una cadena y no como puntos.
    # ------------------------------------------------------------------
    for i in range(PADS):
        side = -1.0 if i == 0 else 1.0
        x = side * 5.20
        bones.append(bone(
            f"v18_pad_{i}", "chestplate",
            [x, 23.10, 2.70], [0.0, 0.0, side * -16.0],
            [
                # PLACA base: la superficie del hombro.
                cube_faces((x - 1.25, 22.70, 1.60), (2.50, 0.42, 2.10),
                           {"up": PAD_UV, "north": PAD_SIDE_UV,
                            "south": PAD_SIDE_UV, "east": PAD_SIDE_UV,
                            "west": PAD_SIDE_UV, "down": PAD_SIDE_UV},
                           INFLATE[0]),
                # LAM superior: un escalón más arriba y más corto.
                cube_faces((x - 1.09, 23.00, 1.76), (2.18, 0.34, 1.78),
                           {"up": PAD_UV, "north": PAD_SIDE_UV,
                            "south": PAD_SIDE_UV, "east": PAD_SIDE_UV,
                            "west": PAD_SIDE_UV, "down": PAD_SIDE_UV},
                           INFLATE[1]),
                # FILO exterior: el canto que atrapa la luz del sol.
                cube_faces((x + side * 0.95 - 0.21, 22.80, 1.68),
                           (0.42, 0.52, 2.05),
                           {"up": CREST_UV, "north": PAD_SIDE_UV,
                            "south": PAD_SIDE_UV, "east": PAD_SIDE_UV,
                            "west": PAD_SIDE_UV, "down": PAD_SIDE_UV},
                           INFLATE[2]),
                # LABIO delantero: el borde que baja hacia el pecho.
                cube_faces((x - 1.08, 22.06, 1.42), (2.16, 0.74, 0.52),
                           {"up": PAD_SIDE_UV, "north": PAD_SIDE_UV,
                            "south": PAD_SIDE_UV, "east": PAD_SIDE_UV,
                            "west": PAD_SIDE_UV, "down": PAD_SIDE_UV},
                           INFLATE[0]),
            ]))

    for i in range(CHAIN_LINKS):
        x = -3.30 + i * 0.94
        y = 22.52 - 0.13 * math.sin(i * 0.85)
        z = 3.96 + (0.05 if i % 2 else -0.05)
        bones.append(bone(
            f"v18_chain_{i}", "chestplate",
            [x, y, z], [0.0, 0.0, 14.0 if i % 2 else -14.0],
            [cube_faces((x - 0.48, y - 0.19, z - 0.10), (0.96, 0.38, 0.20),
                        {"north": CHAIN_UV, "south": CHAIN_UV,
                         "up": CHAIN_TOP_UV, "down": CHAIN_TOP_UV,
                         "east": CHAIN_TOP_UV, "west": CHAIN_TOP_UV},
                        INFLATE[1])]))

    # ------------------------------------------------------------------
    # 4. 12 MECHONES ANCHOS, PLANOS, CURVADOS Y SUPERPUESTOS, EN 2 CAPAS.
    #    7 huesos por mechón (6 tramos + punta afilada).
    # ------------------------------------------------------------------
    for k in range(CS.RIBBONS):
        dep = ribbon_thick(k)
        for n in range(CS.SEGS):
            g = CS.segment_geometry(k, n)
            t0, t1 = CS.segment_bounds(k, n)
            tm = (t0 + t1) / 2.0
            z = g["z"] + 0.012 * n
            front = lock_uv(k, t0, t1, g["w"], g["h"])
            bones.append(bone(
                f"v17_ribbon_{k}_seg{n}", section_for_t(tm),
                [g["cx"], g["cy"], z + dep / 2.0],
                [0.0, 0.0, g["theta"]],
                [cube16((g["cx"] - g["w"] / 2.0,
                         g["cy"] - g["h"] / 2.0, z),
                        (g["w"], g["h"], dep),
                        front, DARK, INFLATE[(k + n) % 3])]))
        # PUNTA AFILADA: 0.10 de ancho, 0.80 de largo, con desgaste en UV.
        t = CS.tip_t(k)
        x = CS.ribbon_x(k, t)
        y = CS.Y_TOP - t * CS.HEIGHT
        z = CS.ribbon_z(k, t) + 0.06
        last = CS.segment_geometry(k, CS.SEGS - 1)
        theta = last["theta"] + 3.0 * math.sin(k * 2.3)
        tw, th = 0.10, 0.80
        bones.append(bone(
            f"v17_ribbon_{k}_seg{CS.SEGS}", section_for_t(t),
            [x, y - th / 2.0, z + dep / 2.0],
            [0.0, 0.0, theta],
            [cube16((x - tw / 2.0, y - th, z), (tw, th, dep * 0.8),
                    tip_uv(k, t), DARK, INFLATE[(k + 2) % 3])]))

    # ------------------------------------------------------------------
    # 5. GRIETAS 3D NEÓN: trazos CORTOS sobre la capa externa. Son
    #    relieves emisivos (glowmask), NO tiras colgantes ni motas.
    # ------------------------------------------------------------------
    for i, m in enumerate(CS.vein_marks(CRACKS)):
        k, t = m["k"], m["t"]
        x = CS.ribbon_x(k, t) + 0.12 * math.sin(i * 2.1)
        y = CS.Y_TOP - t * CS.HEIGHT
        # v1.25.0: EMBEBIDA en el mechón (no flotando delante)...
        z = CS.ribbon_z(k, t) + ribbon_thick(k) - 0.14
        vw = 0.12
        vh = 0.65 + 0.45 * abs(math.sin(i * 1.7 + 0.3))
        # ...y HIJA del tramo del mechón que la sostiene: hereda su
        # rotación y su position, así que viaja con la tela en vez de
        # quedarse clavada en el aire cuando la capa se mueve.
        seg = CS.SEGS - 1
        for nseg in range(CS.SEGS):
            t0, t1 = CS.segment_bounds(k, nseg)
            if t0 <= t <= t1:
                seg = nseg
                break
        parent = f"v17_ribbon_{k}_seg{seg}"
        bones.append(bone(
            f"v17_vein_{i}", parent,
            [x, y, z], [0.0, 0.0, m["angle"]],
            [cube16((x - vw / 2.0, y - vh / 2.0, z),
                    (vw, vh, 0.20), NEON_UV, NEON_UV, INFLATE[2])]))

    # ---- descripción y garantías -------------------------------------
    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 6.0
    desc["visible_bounds_height"] = 5.6
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    assert geo["bones"][:72] == original_bones, "los 72 huesos originales cambiaron"
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    new = [b for b in bones[72:]]
    assert not any(b["name"].startswith(("v17_mote_", "v17_ash_",
                                        "v16_mote_", "v16_ash_",
                                        "v17_shingle_", "v17_yoke_"))
                   for b in new), "vuelven las tiras / motas sueltas"
    for prefix, expected in (
            ("v15_cloth_", 27),
            ("v17_cowl_front_", COLLAR_FRONT),
            ("v17_cowl_tooth_", COLLAR_FLAPS),
            ("v17_cowl_back_", COLLAR_BACK),
            ("v18_pad_", PADS), ("v18_chain_", CHAIN_LINKS),
            ("v17_ribbon_", CS.RIBBONS * (CS.SEGS + 1)),
            ("v17_vein_", CRACKS)):
        got = sum(1 for n in names if n.startswith(prefix))
        assert got == expected, (prefix, got, expected)
    for b in bones:
        assert b.get("parent") is None or b["parent"] in names, b["name"]
    for b in new:
        for c in b["cubes"]:
            for f in c["uv"].values():
                assert_opaque(f)
            assert 0.0 < c["inflate"] <= 0.05, c["inflate"]
    thick = [c["size"][2] for b in new for c in b["cubes"]
             if b["name"].startswith("v17_ribbon_")]
    assert thick and all(0.40 <= v <= 0.85 for v in thick), (min(thick), max(thick))
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")
    print(f"  {CS.RIBBONS} MECHONES ANCHOS x {CS.SEGS + 1} tramos en 2 capas"
          f" | cuello alto {COLLAR_FRONT}+{COLLAR_BACK} | hombreras {PADS}"
          f" | cadena {CHAIN_LINKS} | grietas neón {CRACKS}"
          f" | SIN tiras finas ni motas 3D")


if __name__ == "__main__":
    main()
