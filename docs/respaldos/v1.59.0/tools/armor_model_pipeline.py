#!/usr/bin/env python3
"""Silueta equipada v1.59.0, en dos capas con dobladillo partido.

El árbol conserva los 225 huesos y la armadura original oculta. Las tres
bisagras viven en la costura y los tercios del paño. Cada cola articula
sus tres últimos cubos desde el mismo pivote. El cuello asimétrico cubre
la raíz, con acero estratificado y cadena arqueada sobre el tejido.

Uso: python3 tools/armor_model_pipeline.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cape_shape as CS
from cloth_spec import COWL_TEXELS_PER_UNIT, COWL_TILES, assert_opaque

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

INFLATE = (0.01, 0.03, 0.05)

COLLAR_FRONT = 7
COLLAR_FLAPS = 7
COLLAR_BACK = 5
CUEILLO = 3  # v1.32.0: 3 bloques chiquitos junto a la nuca (cuellito)
PADS = 2
CHAIN_LINKS = 8
CRACKS = 10
TAIL_JOINT = 4  # los últimos tres cubos comparten el último pivote visible

# Holgura estática en el +Z del .geo (texels de modelo, 16 por bloque).
# No se añade un canal de posición: se desplazan juntos los mechones y
# las grietas que llevan cosidas. El torso acaba en Z=2.
CLOTH_SETBACK = 1.98

# Parches del atlas limpio (ver tools/cape_atlas_v1230.py).
OUTER_V, INNER_V = 0.0, 48.0
STRIPE_W = 96.0 / (CS.RIBBONS // 2)          # 16 texels por mechón


def legacy_element(bone_name: str, cube_index: int) -> tuple[str, int]:
    """Nombre original del elemento en Blockbench tras coser la punta."""
    if bone_name.startswith("v17_ribbon_") and bone_name.endswith(f"_seg{TAIL_JOINT}"):
        return bone_name.rsplit("_seg", 1)[0] + f"_seg{TAIL_JOINT + cube_index}", 0
    return bone_name, cube_index


def ribbon_thick(k: int) -> float:
    """Mechón PLANO pero con cuerpo: 0.68-0.84 unidades de fondo."""
    return 0.76 + 0.08 * math.sin(k * 1.7 + 0.3)


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
CUEILLO_UV = band(97.5, 28.0, 65.0, 13.0)  # parche del cuellito (ruff)


def cowl_uv(tile: str, w: float, h: float) -> dict:
    """Recorte a 4 texels/u en ambos ejes, con margen contra bleeding."""
    u0, v0, u1, v1 = COWL_TILES[tile]
    uw, vh = w * COWL_TEXELS_PER_UNIT, h * COWL_TEXELS_PER_UNIT
    assert uw <= u1 - u0 - 2 and vh <= v1 - v0 - 2, (tile, w, h)
    return band((u0 + u1 - uw) / 2, uw, v0 + 1, vh)


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
    return band(j * STRIPE_W + 4.0, 8.0, base + min(44.0, 48.0 * t - 2.6), 3.4)


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


def cowl_cube(origin, size, tile: str, inflate: float) -> dict:
    w, h, d = size
    face = cowl_uv(tile, w, h)
    side = cowl_uv("canto", d, h)
    edge = cowl_uv("canto", w, d)
    return cube_faces(origin, size, {"north": face, "south": face,
                                     "east": side, "west": side,
                                     "up": edge, "down": edge}, inflate)


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
                if _slab == "cape_top":
                    # Bisagra en la costura externa, no dentro del torso.
                    # El borde alto gira fuera del volumen de la cabeza.
                    _b["pivot"] = [0.0, 23.40, 4.66]
                elif _slab == "cape_mid":
                    _b["pivot"] = [0.0, CS.Y_TOP - CS.HEIGHT * 0.34, 4.60]
                else:
                    _b["pivot"] = [0.0, CS.Y_TOP - CS.HEIGHT * 0.67, 5.14]

    # ------------------------------------------------------------------
    # 1. 27 anclas INVISIBLES: dentro del cuello grueso. Java las necesita
    #    para panels[]. v1.53.0: se ponen VISIBLE=FALSE en Blockbench:
    #    antes quedaban apiladas en la parte superior del paño (los
    #    cubos `bottom`/`mid` flotando sueltos donde no deberían verse).
    #    Los huesos SE PRESERVAN (Java los sigue necesitando para
    #    panels[]); solo se oculta la geometría del cubo en Blockbench.
    # ------------------------------------------------------------------
    for si, section in enumerate(("cape_top", "cape_mid", "cape_bottom")):
        for col in range(9):
            ax = (col - 4) * 0.95
            _anchor = cube16((ax - 0.08, 23.52, 2.32), (0.16, 0.16, 0.16),
                             band(2.0 + col * 2.0, 2.0, 100.0, 2.0),
                             DARK, INFLATE[0])
            _anchor["visibility"] = False
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [ax, 23.60, 2.40], [0.0, 0.0, 0.0], [_anchor]))

    # ------------------------------------------------------------------
    # 2. Cuello alto con solapas oblicuas, y faldones en cascada. Se
    # reutilizan los grupos: cada solapa gira desde la costura superior.
    # ------------------------------------------------------------------
    flap_heights = (2.28, 3.15, 4.36, 3.45, 4.08, 3.22, 2.18)
    for i in range(COLLAR_FRONT):
        fx = (i - 3.0) / 3.0
        center = 1.0 - abs(fx)
        x = fx * 5.78
        w = 2.18 + 0.25 * center
        height = 1.56 + 0.58 * center
        y_top = 23.18 - 0.59 * center + 0.10 * fx
        z, depth = 3.46 + 0.42 * center, 1.32
        bottom = y_top - height
        bones.append(bone(
            f"v17_cowl_front_{i}", "chestplate",
            [x, y_top, z + depth / 2],
            [1.8, -fx * 15.0, -fx * 11.5],
            [cowl_cube((x - w / 2, bottom, z), (w, height, depth), "base", INFLATE[i % 3])]))
        fw, fh = 2.43 + 0.29 * center, flap_heights[i]
        fy, fz = bottom + 0.56, z + depth - 0.36
        fd = 0.94 + 0.43 * center
        bones.append(bone(
            f"v17_cowl_tooth_{i}", f"v17_cowl_front_{i}",
            [x, fy, fz + fd / 2],
            [6.0, -fx * 6.0, fx * 35.0 + (3.4 if i % 2 else -2.5)],
            [cowl_cube((x - fw / 2.0, fy - fh, fz), (fw, fh, fd),
                       "estrella" if i == COLLAR_FRONT // 2 else "faldon", INFLATE[1])]))

    for i in range(COLLAR_BACK):
        fx = (i - 2.0) / 2.0
        center = 1.0 - abs(fx)
        x = fx * 5.60
        w = 3.10 - 0.10 * center
        height = 2.10 + 1.22 * center
        y_top = 23.02 + 1.06 * center
        z, depth = 3.56 + 0.99 * center, 0.93
        bones.append(bone(
            f"v17_cowl_back_{i}", "chestplate",
            [x, y_top - 0.38, z + depth / 2.0],
            [-1.0, -fx * 15.0, fx * 15.0],
            [cowl_cube((x - w / 2.0, y_top - height, z), (w, height, depth), "dorsal", INFLATE[2])]))

    # ------------------------------------------------------------------
    # 2b. CUELLITO (v1.32.0): 3 bloques chiquitos junto a la NUCA.
    #
    # Para que la capa parezca ATADA al jugador: un pequeño ruff de
    # tres bloques por debajo de la nuca que enganchan el cape_top.
    # ------------------------------------------------------------------
    for i in range(CUEILLO):
        fx = (i - (CUEILLO - 1) / 2.0) / max(1.0, (CUEILLO - 1) / 2.0)
        x = fx * 1.60
        y = 23.14 + 0.25 * (1.0 - abs(fx))
        z = 3.55
        bones.append(bone(
            f"v19_cuellito_{i}", "chestplate",
            [x, y, z], [0.0, 0.0, fx * -5.0],
            [cube16((x - 0.45, y - 0.45, z - 0.30),
                    (0.90, 0.90, 0.60), CUEILLO_UV,
                    COLLAR_UV, INFLATE[1])]))

    # ------------------------------------------------------------------
    # 3. Hombreras de tres estratos y labio. El acero abre la silueta
    # hacia los lados y la cadena sigue un arco bajo la nuca.
    # ------------------------------------------------------------------
    for i in range(PADS):
        side = -1.0 if i == 0 else 1.0
        x, y, z = side * 5.85, 23.07, 3.63
        span = 3.66 if i == 0 else 3.40
        bones.append(bone(f"v18_pad_{i}", "chestplate", [x, y, z],
                          [1.0, -side * 12.0, -side * 15.0], [
            cube16((x - span / 2, y - 0.56, z - 0.62), (span, 0.58, 2.08),
                   PAD_SIDE_UV, PAD_UV, INFLATE[0]),
            cube_faces((x - span * 0.44, y + 0.02, z - 0.56), (span * 0.88, 0.29, 1.88),
                       {"up": PAD_UV, "north": PAD_SIDE_UV, "south": CREST_UV,
                        "east": PAD_SIDE_UV, "west": PAD_SIDE_UV, "down": DARK}, INFLATE[1]),
            cube16((x + side * (span / 2 - 0.62) - 0.22, y - 0.25, z - 0.48),
                   (0.44, 0.66, 1.86), CREST_UV, PAD_SIDE_UV, INFLATE[2]),
            cube16((x - span * 0.41, y - 0.94, z + 0.96), (span * 0.82, 0.78, 0.47),
                   PAD_SIDE_UV, DARK, INFLATE[0]),
        ]))

    chain_depths = (5.56, 5.55, 5.56, 5.99, 6.01, 5.99, 5.71, 5.60)
    for i in range(CHAIN_LINKS):
        t = i / (CHAIN_LINKS - 1)
        x = -3.66 + t * 7.32
        sag = math.sin(math.pi * t)
        y = 22.68 - 0.35 * t - 1.32 * sag
        z = chain_depths[i]
        angle = 29.0 * math.cos(math.pi * t) + (6.0 if i % 2 else -6.0)
        twist = -22.0 * (chain_depths[min(7, i + 1)] - chain_depths[max(0, i - 1)])
        bones.append(bone(f"v18_chain_{i}", "chestplate", [x, y, z], [0.0, twist, angle], [
            cube_faces((x - 0.63, y - 0.21, z - 0.18), (1.26, 0.42, 0.36),
                       {"north": CHAIN_UV, "south": CHAIN_UV, "up": CHAIN_TOP_UV,
                        "down": CHAIN_TOP_UV, "east": CHAIN_TOP_UV, "west": CHAIN_TOP_UV},
                       INFLATE[1]),
        ]))

    # ------------------------------------------------------------------
    # 4. 12 MECHONES ANCHOS, PLANOS, CURVADOS Y SUPERPUESTOS, EN 2 CAPAS.
    #    7 huesos por mechón (6 tramos + punta afilada).
    # ------------------------------------------------------------------
    for k in range(CS.RIBBONS):
        dep = ribbon_thick(k)
        ribbon = []
        for n in range(CS.SEGS + 1):
            if n == CS.SEGS:
                # Punta corta e irregular, alineada al último tramo.
                t = CS.tip_t(k)
                last = CS.segment_geometry(k, n - 1)
                x, y = CS.ribbon_x(k, t), CS.Y_TOP - t * CS.HEIGHT
                z = CS.ribbon_z(k, t) + 0.06 + CLOTH_SETBACK
                w, h = 0.14 + 0.015 * (k % 4), 0.62 + 0.18 * (k % 3)
                pivot = [x, y - h / 2, z + dep / 2]
                angle = [last["bend"], last["twist"], last["theta"] + 3.0 * math.sin(k * 2.3)]
                c = cube16((x - w / 2, y - h, z), (w, h, dep * .8), tip_uv(k, t),
                           DARK, INFLATE[(k + 2) % 3])
            else:
                g = CS.segment_geometry(k, n)
                t0, t1 = CS.segment_bounds(k, n)
                t = (t0 + t1) / 2
                x, y, z = g["cx"], g["cy"], g["z"] + 0.012 * n + CLOTH_SETBACK
                w, h = g["w"] + (0.12 if 2 <= n <= 4 else 0.0), g["h"]
                pivot = [x, y, z + dep / 2]
                angle = [g["bend"], g["twist"], g["theta"]]
                c = cube16((x - w / 2, y - h / 2, z), (w, h, dep),
                           lock_uv(k, t0, t1, w, h), DARK, INFLATE[(k + n) % 3])
            # Una cola continua, no tres dados que se sueltan en el aire:
            # la inclinación de cada sección vive en el cubo. Se preservan
            # nombres y tracks de los dos huesos terminales como anclas.
            if n >= TAIL_JOINT:
                c.update(pivot=[round(v, 4) for v in pivot], rotation=[round(v, 4) for v in angle])
                angle = [0.0, 0.0, 0.0]
            new_bone = bone(f"v17_ribbon_{k}_seg{n}", section_for_t(t), pivot, angle,
                            [c] if n <= TAIL_JOINT else [])
            if n > TAIL_JOINT:
                ribbon[TAIL_JOINT]["cubes"].append(c)
            ribbon.append(new_bone)
        bones.extend(ribbon)

    # ------------------------------------------------------------------
    # 5. GRIETAS 3D NEÓN: trazos CORTOS sobre la capa externa. Son
    #    relieves emisivos (glowmask), NO tiras colgantes ni motas.
    # ------------------------------------------------------------------
    for i, m in enumerate(CS.vein_marks(CRACKS)):
        k, t = m["k"], m["t"]
        # El trazo se planta en el espacio local de su cubo, no en la
        # curva global: así sigue adherido incluso en un gajo retorcido.
        seg = next(n for n in range(CS.SEGS) if t <= CS.segment_bounds(k, n)[1])
        g = CS.segment_geometry(k, seg)
        x = g["cx"] + g["w"] * 0.26 * math.sin(i * 2.1 + 0.4)
        y = CS.Y_TOP - CS.HEIGHT * t
        z = g["z"] + 0.012 * seg + CLOTH_SETBACK + ribbon_thick(k) - 0.15
        vw = 0.12
        vh = 0.63 + 0.41 * abs(math.sin(i * 1.7 + 0.3))
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
            ("v19_cuellito_", CUEILLO),
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
