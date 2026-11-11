#!/usr/bin/env python3
"""Reconstruye la capa EQUIPADA como PRENDA DE DETERIORO / EVIL SAIYAN ROSÉ.

v1.15.0 (corrección visual tras el rechazo de v1.14.0): el rediseño anterior
había producido una JAULA de 78 tiras finas y brillantes, todas verticales y
del mismo ancho, con un cubo blanco por cabeza. La referencia de Blockbench
es otra cosa: una BUFANDA/SHIGARAKI gruesa y deshilachada que envuelve cuello
y hombros, y debajo un paño OSCURO, ancho y solapado que se rompe en jirones
irregulares, con vetas rosa sólo en algunos puntos.

Desde los 72 huesos prístinos (byte-idénticos) se construye:

  * BASE: mosaico 9x3 de 27 paneles de paño grueso (v15_cloth_*), sin huecos.
  * 11 CINTAS ANCHAS (v16_tatter_*), cada una de 3 segmentos que se solapan,
    se estrechan y se curvan: de arriba abajo el paño se DESHACE. Ya NO hay
    una rejilla de barrotes; las cintas se pisan unas a otras en 3 capas Z.
  * 18 FLECOS de dobladillo (v16_hem_*), cortos y de largo distinto, sólo en
    el borde inferior: es ahí donde la tela se deshilacha.
  * BUFANDA VOLUMINOSA: dos anillos de 16 segmentos (v16_collar_*), con
    altura muy irregular (borde superior dentado), más 24 v16_fray_* de los
    que 8 son TIRAS LARGAS que cuelgan por delante y por los costados.
  * Yugo de 5 piezas (v16_yoke_*) y 2 hombreras envolventes (v15_rear_pad_*).
  * 12 venas finas (v16_vein_*), 56 microvóxeles (v16_mote_*), 8 cenizas
    (v16_ash_*) y 10 jirones laterales (v16_shred_*).

Reglas que no se tocan: `inflate` 0.01/0.03/0.05 + desplazamiento Z real,
espesor 0.25-0.50 en la tela, UV 100% opacas, alfa prístino, 1636 emisivos,
0 JsonNull, raíz sin `parent`, 0 mixins, radianes y fail-safes en Java.

Uso:  python3 tools/armor_model_pipeline.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from cloth_spec import (
    COLUMNS,
    FOLDS,
    SECTIONS,
    assert_opaque,
    cloth_uv,
    hem_uv,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

INFLATE = (0.01, 0.03, 0.05)

COLLAR_SEGS = 16
FRAY_COUNT = 24
YOKE_COUNT = 5
RIBBONS = 11
HEM_COUNT = 18
SHRED_PER_SIDE = 5
VEIN_COUNT = 12
MOTE_COUNT = 56
ASH_COUNT = 8


def S(region: str, w: float | None = None, h: float | None = None,
      du: float = 0.0, dv: float = 0.0) -> dict:
    """Rectángulo UV absoluto dentro de una zona opaca del atlas."""
    from cloth_spec import UV
    s = dict(UV[region])
    s["uv"] = [round(s["uv"][0] + du, 4), round(s["uv"][1] + dv, 4)]
    s["uv_size"] = [round(s["uv_size"][0] if w is None else w, 4),
                    round(s["uv_size"][1] if h is None else h, 4)]
    assert_opaque(s)
    return s


def chunk(col: int, seg: int, nseg: int = 3) -> dict:
    """Trozo del canvas 96x48 (opaquísimo y OSCURO) para un paño."""
    w = 96.0 / COLUMNS
    h = 48.0 / nseg
    col = max(0, min(COLUMNS - 1, col))
    seg = max(0, min(nseg - 1, seg % nseg))
    s = {"uv": [round(col * w, 4), round(seg * h, 4)],
         "uv_size": [round(w, 4), round(h, 4)]}
    assert_opaque(s)
    return s


def mote_uv(i: int) -> dict:
    return S("energy_ramp", w=2.0, h=2.0,
             du=float(i % 4), dv=float((i * 5) % 16))


def cube16(origin, size, front: dict, side: dict | None = None,
           inflate: float = 0.0) -> dict:
    """Cubo con espesor real. north/south = paño; cantos = ceniza/violeta."""
    s = side or S("ash")
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": {
            "north": dict(front), "south": dict(front),
            "east": dict(s), "west": dict(s),
            "up": dict(s), "down": dict(s),
        },
        "inflate": round(inflate, 4),
    }


def bone(name: str, parent: str | None, pivot, rotation, cubes) -> dict:
    out = {
        "name": name,
        "pivot": [round(v, 4) for v in pivot],
        "rotation": [round(v, 4) for v in rotation],
        "cubes": cubes,
    }
    if parent:
        out["parent"] = parent
    return out


def global_bounds(by_name: dict):
    cubes = [c for section in SECTIONS for c in by_name[section]["cubes"]]
    return (min(c["origin"][0] for c in cubes),
            max(c["origin"][0] + c["size"][0] for c in cubes),
            min(c["origin"][1] for c in cubes),
            max(c["origin"][1] + c["size"][1] for c in cubes))


def row_bounds(gx0, gx1, gy0, gy1, section: int):
    row_h = (gy1 - gy0) / len(SECTIONS)
    y_lo = gy0 + (len(SECTIONS) - 1 - section) * row_h
    return gx0, gx1, y_lo, y_lo + row_h, (gx1 - gx0) / COLUMNS


def section_for_y(y, gy0, gy1) -> str:
    row_h = (gy1 - gy0) / 3.0
    if y >= gy0 + 2 * row_h:
        return "cape_top"
    if y >= gy0 + row_h:
        return "cape_mid"
    return "cape_bottom"


def build() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)
    by_name = {b["name"]: b for b in original_bones}
    gx0, gx1, gy0, gy1 = global_bounds(by_name)

    # ------------------------------------------------------------------
    # 1. PAÑO BASE continuo: 27 paneles gruesos, sin rendijas.
    # ------------------------------------------------------------------
    step = (gx1 - gx0) / COLUMNS
    for si, section in enumerate(SECTIONS):
        _, _, y_lo, y_hi, _ = row_bounds(gx0, gx1, gy0, gy1, si)
        row_h = y_hi - y_lo
        for col in range(COLUMNS):
            norm = (col - 4.0) / 4.0
            x = gx0 + col * step
            z = (2.42 + 0.10 * si + 0.16 * (1.0 - norm * norm)
                 + 0.10 * math.cos(2.0 * math.pi * FOLDS * (col + 0.5) / COLUMNS))
            cubes = [cube16((x, y_lo + 0.04, z), (step * 1.02, row_h - 0.10, 0.42),
                            cloth_uv(si, col), S("ash"), INFLATE[0])]
            if si == 2:
                tip = 0.30 + 0.45 * abs(math.sin(col * 2.3))
                cubes.append(cube16((x + 0.14, y_lo - tip, z + 0.02),
                                    (step * 0.70, tip, 0.30),
                                    hem_uv(col), S("ash"), INFLATE[1]))
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [x + step / 2.0, (y_lo + y_hi) / 2.0, z + 0.21],
                [0.6 + 0.8 * si, 0.0, 1.2 * math.sin(col * 1.7)], cubes))

    # ------------------------------------------------------------------
    # 2. PUNTAS del dobladillo (9), oscuras y cortas.
    # ------------------------------------------------------------------
    for col in range(COLUMNS):
        r = math.sin(col * 2.31)
        bones.append(bone(
            f"v15_hem_{col}", "cape_bottom",
            [gx0 + (col + 0.5) * step, gy0 - 0.5, 2.75],
            [0.0, 0.0, 6.0 * r],
            [cube16((gx0 + col * step + 0.12, gy0 - 0.95 - 0.35 * abs(r), 2.70),
                    (step * 0.78, 0.95 + 0.35 * abs(r), 0.28),
                    hem_uv(col), S("ash"), INFLATE[1])]))

    # ------------------------------------------------------------------
    # 3. NÚCLEOS orbitales (4), discretos.
    # ------------------------------------------------------------------
    for i in range(4):
        ang = i * math.pi / 2.0
        x, y, z = 1.9 * math.cos(ang), 16.0 + 1.9 * math.sin(ang), 3.25
        bones.append(bone(
            f"v15_orbit_{i}", "v15_cloth_cape_mid_4",
            [x - 0.45, y + 0.45, z], [0.0, 0.0, 45.0],
            [cube16((x, y, z), (0.24, 0.24, 0.20),
                    mote_uv(i + 7), mote_uv(i + 7), INFLATE[2])]))

    # ------------------------------------------------------------------
    # 4. HOMBRERAS ENVOLVENTES: de delante a atrás, OSCURAS (no neón).
    # ------------------------------------------------------------------
    for side, sx in (("L", -1.0), ("R", 1.0)):
        hx = -7.15 if sx < 0 else 3.55
        bones.append(bone(
            f"v15_rear_pad_{side}", "chestplate",
            [hx + 1.8, 23.0, 0.9], [3.0, sx * 8.0, -sx * 7.0],
            [
                cube16((hx, 22.10, -1.35), (3.60, 1.95, 5.10),
                       S("yoke"), S("ash"), INFLATE[0]),
                cube16((hx - 0.16, 23.80, -1.50), (3.92, 0.36, 5.40),
                       S("yoke"), S("ash"), INFLATE[1]),
            ]))

    # ------------------------------------------------------------------
    # 5. BUFANDA / COLLAR: dos anillos de 16 segmentos, MUY irregular.
    #    El borde superior queda dentado; el peso cae sobre los hombros.
    # ------------------------------------------------------------------
    for ring, (rx, rz, cy, base_h, dep, infl) in enumerate((
            (5.30, 3.10, 23.30, 2.45, 0.48, INFLATE[0]),
            (4.20, 2.45, 23.75, 1.95, 0.40, INFLATE[2]))):
        for k in range(COLLAR_SEGS):
            th = 2.0 * math.pi * k / COLLAR_SEGS
            cx, cz = rx * math.cos(th), 0.40 + rz * math.sin(th)
            w = 2.70 if ring == 0 else 2.25
            # Borde superior MUY dentado: la bufanda se rompe, no es un anillo
            # rectangular. Altura y centro varian por segmento.
            h = base_h * (0.55 + 0.95 * abs(math.sin(k * 1.9 + ring * 0.7)))
            yc = cy + 0.55 * math.sin(k * 2.7 + ring)
            rot = [7.0 * math.sin(k * 1.1 + ring),
                   math.degrees(th) + 90.0,
                   11.0 * math.sin(k * 2.3 + ring)]
            front = S("yoke") if ring == 0 else S("ash")
            side = S("ash") if ring == 0 else S("crease_light")
            bones.append(bone(
                f"v16_collar_{'outer' if ring == 0 else 'inner'}_{k}",
                "chestplate", [cx, yc, cz + infl], rot,
                [cube16((cx - w / 2.0, yc - h / 2.0, cz - dep / 2.0 + infl),
                        (w, h, dep), front, side, infl)]))

    # ------------------------------------------------------------------
    # 6. FLECOS DE LA BUFANDA: 24. Ocho son TIRAS LARGAS que cuelgan por
    #    delante y por los costados (el borde roto de la referencia).
    # ------------------------------------------------------------------
    for k in range(FRAY_COUNT):
        th = 2.0 * math.pi * k / FRAY_COUNT
        cx, cz = 5.10 * math.cos(th), 0.40 + 2.95 * math.sin(th)
        long_tail = k % 3 == 0
        length = (4.2 + 2.8 * abs(math.sin(k * 2.7))) if long_tail else (
            0.85 + 1.55 * abs(math.sin(k * 3.1)))
        width = (1.15 + 0.45 * abs(math.cos(k * 1.7))) if long_tail else (
            0.42 + 0.26 * abs(math.cos(k * 2.9)))
        parent = f"v16_collar_outer_{(k * COLLAR_SEGS // FRAY_COUNT) % COLLAR_SEGS}"
        front = S("yoke") if long_tail else S("ash")
        side = S("ash")
        bones.append(bone(
            f"v16_fray_{k}", parent,
            [cx, 22.35, cz], [3.0, 0.0, -10.0 + 9.0 * math.sin(k * 1.9)],
            [cube16((cx - width / 2.0, 22.35 - length, cz),
                    (width, length, 0.32), front, side, INFLATE[1])]))

    # ------------------------------------------------------------------
    # 7. YUGO: 5 piezas anchas que unen bufanda y espalda. Sin huecos.
    # ------------------------------------------------------------------
    for k in range(YOKE_COUNT):
        x = -3.6 + k * 1.8
        bones.append(bone(
            f"v16_yoke_{k}", "chestplate",
            [x + 0.9, 22.05, 2.15], [0.0, 0.0, 2.0 * math.sin(k)],
            [cube16((x, 21.55, 1.95), (1.85, 1.05, 0.48),
                    S("yoke"), S("ash"), INFLATE[0])]))

    # ------------------------------------------------------------------
    # 8. CINTAS ANCHAS: 11 paños que se SOLAPAN y se deshacen en 3 tramos.
    #    Éste es el cambio clave: anchura > paso, así que NO hay rejilla.
    # ------------------------------------------------------------------
    cstep = (gx1 - gx0 - 0.6) / RIBBONS
    for k in range(RIBBONS):
        r = math.sin(k * 2.7)
        q = math.cos(k * 1.9)
        x = gx0 + 0.30 + (k + 0.5) * cstep
        width = 1.45 + 0.62 * (0.5 + 0.5 * math.sin(k * 1.3))
        layer = k % 3
        z = 2.88 + 0.16 * layer + 0.12 * q
        y_top = 22.35 + 0.35 * q
        y_end = 2.4 + 4.6 * (0.5 + 0.5 * math.sin(k * 1.7 + 0.8))
        # Tres tramos con deriva lateral y estrechamiento progresivo.
        ys = (y_top, y_top - (y_top - y_end) * 0.42, y_top - (y_top - y_end) * 0.76, y_end)
        widths = (width, width * 0.88, width * 0.66, width * 0.42)
        drift = (0.0, 0.24 * r, 0.52 * r, 0.78 * r)
        cubes = []
        for s in range(3):
            h = ys[s] - ys[s + 1]
            cubes.append(cube16(
                (x + drift[s] - widths[s] / 2.0, ys[s + 1], z + 0.02 * s),
                (widths[s], h, 0.34 + 0.04 * layer),
                chunk((k * 2 + s) % COLUMNS, s, 3),
                S("ash") if (k + s) % 3 else S("crease_light"),
                INFLATE[layer]))
        bones.append(bone(
            f"v16_tatter_{k}", section_for_y(y_top - 6.0, gy0, gy1),
            [x, (y_top + y_end) / 2.0, z + 0.18],
            [2.0 + 2.5 * abs(q), 3.0 * r, (3.0 + 4.0 * k / RIBBONS) * (1.0 if r >= 0 else -1.0)],
            cubes))

    # ------------------------------------------------------------------
    # 9. FLECOS DEL DOBLADILLO: 18, cortos, sólo en el borde inferior.
    # ------------------------------------------------------------------
    for k in range(HEM_COUNT):
        x = gx0 + 0.25 + (k + 0.5) * (gx1 - gx0 - 0.5) / HEM_COUNT
        r = math.sin(k * 2.9)
        length = 0.9 + 2.2 * abs(r)
        z = 3.02 + 0.10 * (k % 3)
        bones.append(bone(
            f"v16_hem_{k}", "cape_bottom",
            [x, 3.3, z], [0.0, 0.0, 9.0 * r],
            [cube16((x - 0.28, 3.3 - length, z), (0.56, length, 0.28),
                    hem_uv(k % COLUMNS), S("ash"), INFLATE[k % 3])]))

    # ------------------------------------------------------------------
    # 10. JIRONES LATERALES: nacen del borde del paño, no flotan.
    # ------------------------------------------------------------------
    for side, sx in (("L", -1.0), ("R", 1.0)):
        for k in range(SHRED_PER_SIDE):
            y = 9.0 + k * 2.6
            x = (gx0 if sx < 0 else gx1) - sx * 0.15
            z = 2.95 + 0.12 * (k % 3)
            length = 2.2 + 1.5 * abs(math.sin(k * 2.1))
            bones.append(bone(
                f"v16_shred_{side}_{k}", section_for_y(y, gy0, gy1),
                [x, y, z], [0.0, 0.0, sx * (18.0 + 7.0 * k / SHRED_PER_SIDE)],
                [cube16((x - (0.45 if sx > 0 else 0.0), y - length, z),
                        (0.82, length, 0.30),
                        chunk(k % COLUMNS, 2, 3), S("ash"), INFLATE[1])]))

    # ------------------------------------------------------------------
    # 11. VENAS: 12 filetes finos y BRILLANTES sobre las cintas. Sólo ellas
    #     llevan la rampa rosa; el paño circundante queda oscuro.
    # ------------------------------------------------------------------
    for i in range(VEIN_COUNT):
        k = (i * 3) % RIBBONS
        x = gx0 + 0.30 + (k + 0.5) * cstep + 0.35 * math.sin(i * 2.3)
        y = 8.0 + (i % 4) * 3.1
        z = 3.30 + 0.05 * (i % 3)
        h = 2.6 + 1.9 * abs(math.sin(i * 1.7))
        bones.append(bone(
            f"v16_vein_{i}", f"v16_tatter_{k}",
            [x, y + h / 2.0, z], [0.0, 0.0, 5.0 * math.sin(i)],
            [cube16((x - 0.06, y, z), (0.12, h, 0.08),
                    S("energy_vein"), S("energy_vein"), INFLATE[2])]))

    # ------------------------------------------------------------------
    # 12. MICROVÓXELES: 56 de 1x1x1 / 2x2x2 px, repartidos abajo, costados
    #     y alrededor de la bufanda. Pivote desplazado 0.6 para que al girar
    #     se DESPLACEN de verdad.
    # ------------------------------------------------------------------
    rng = math.sin
    for i in range(MOTE_COUNT):
        s = 0.0625 if i % 2 else 0.125
        band = i % 3
        if band == 0:      # alrededor del cuello
            ang = i * 2.399
            x, y, z = 5.6 * math.cos(ang), 21.5 + 3.2 * abs(rng(i)), 0.4 + 3.4 * math.sin(ang)
        elif band == 1:    # desprendiéndose abajo
            x = gx0 + 0.4 + (gx1 - gx0 - 0.8) * ((i * 7) % 19) / 19.0
            y = 1.4 + 6.0 * abs(rng(i * 1.7))
            z = 3.0 + 1.0 * rng(i * 2.9)
        else:              # costados
            x = (gx0 - 0.6) if i % 2 else (gx1 + 0.6)
            y = 5.0 + 14.0 * abs(rng(i * 1.3))
            z = 2.6 + 1.4 * rng(i * 2.1)
        bones.append(bone(
            f"v16_mote_{i}", "chestplate",
            [x + 0.6, y + 0.6, z + 0.6],
            [12.0 * rng(i), 9.0 * rng(i * 1.3), 7.0 * rng(i * 1.9)],
            [cube16((x, y, z), (s, s, s), mote_uv(i), mote_uv(i), INFLATE[2])]))

    # 13. Ceniza: 8 fragmentos oscuros mayores.
    for i in range(ASH_COUNT):
        x = gx0 + 0.8 + (gx1 - gx0 - 1.6) * (i + 0.5) / ASH_COUNT
        y = 3.0 + 3.5 * abs(rng(i * 2.7))
        z = 2.75 + 0.35 * rng(i)
        bones.append(bone(
            f"v16_ash_{i}", "cape_bottom",
            [x, y, z], [0.0, 0.0, 14.0 * rng(i)],
            [cube16((x, y, z), (0.22, 0.28, 0.22),
                    S("ash"), S("ash"), INFLATE[1])]))

    # ---- descripción y garantías -------------------------------------
    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 6.0
    desc["visible_bounds_height"] = 5.6
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    assert geo["bones"][:72] == original_bones, "los 72 huesos originales cambiaron"
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    for prefix, expected in (
            ("v15_cloth_", 27), ("v15_hem_", 9), ("v15_orbit_", 4),
            ("v15_rear_pad_", 2), ("v16_collar_", 2 * COLLAR_SEGS),
            ("v16_fray_", FRAY_COUNT), ("v16_yoke_", YOKE_COUNT),
            ("v16_tatter_", RIBBONS), ("v16_hem_", HEM_COUNT),
            ("v16_shred_", 2 * SHRED_PER_SIDE),
            ("v16_vein_", VEIN_COUNT), ("v16_mote_", MOTE_COUNT),
            ("v16_ash_", ASH_COUNT)):
        assert sum(1 for n in names if n.startswith(prefix)) == expected, prefix
    for b in bones:
        assert b.get("parent") is None or b["parent"] in names, b["name"]
    for b in bones[72:]:
        for c in b.get("cubes", []):
            for f in c["uv"].values():
                assert_opaque(f)
            assert 0.0 < c["inflate"] <= 0.05, c["inflate"]
    thick = [c["size"][2] for b in bones[72:]
             for c in b["cubes"]
             if b["name"].startswith(("v15_cloth_", "v16_tatter_", "v16_shred_",
                                      "v16_fray_", "v16_hem_", "v15_hem_"))]
    assert thick and all(0.25 <= t <= 0.50 for t in thick), (min(thick), max(thick))
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    new = geo["bones"][72:]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")
    print(f"  collar {sum(1 for b in new if b['name'].startswith('v16_collar_'))}"
          f" | cintas {sum(1 for b in new if b['name'].startswith('v16_tatter_'))}"
          f" | flecos {sum(1 for b in new if b['name'].startswith(('v16_fray_', 'v16_hem_')))}"
          f" | microvoxeles {sum(1 for b in new if b['name'].startswith('v16_mote_'))}")


if __name__ == "__main__":
    main()
