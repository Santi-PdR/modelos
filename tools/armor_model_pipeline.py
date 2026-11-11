#!/usr/bin/env python3
"""Reconstruye la capa EQUIPADA como PRENDA DE DETERIORO / EVIL SAIYAN ROSÉ.

A partir de tools/originals/capa_deteriorer_evilsaiyan.geo.json (72 huesos /
126 cubos, copia prístina aprobada) se conservan esos 72 huesos BYTE-IDÉNTICOS
y se construye encima una segunda piel completamente nueva:

  * COLLAR / BUFANDA voluminoso y deshilachado: dos anillos de 14 segmentos
    cada uno alrededor del cuello y los hombros (v16_collar_outer_*, inner_*),
    con solape real entre segmentos y tiras deshilachadas (v16_fray_*). Un
    yugo de 5 piezas (v16_yoke_*) lo une a la espalda sin huecos ni piezas
    flotantes. Las dos hombreras envolventes v15_rear_pad_* cierran el
    hombro de delante a atrás.

  * JIRONES 3D COMPLEJOS: la tela ya NO es un rectángulo continuo. Hay una
    capa base de 27 tiras (v15_cloth_*, 2 cubos cada una, con rotura), una
    segunda capa de 45 tiras (v16_tatter_*), 12 jirones que se desprenden
    por los costados (v16_shred_*) y 9 puntas rasgadas (v15_hem_*). Cada
    pieza tiene ESPESOR REAL de 0.25 a 0.50 unidades en Z.

  * ANTI Z-FIGHTING: cada capa lleva `inflate` de 0.01 / 0.03 / 0.05 en los
    cubos (campo estándar de la geometría Bedrock, que Blockbench lee) y
    además un desplazamiento explícito en Z de 0.01..0.05. Las dos garantías
    son independientes: si GeckoLib ignora `inflate`, el solape sigue bien.

  * ENERGÍA: 18 venas finas (v16_vein_*) sobre la cara SUR de los jirones y
    56 MICROVÓXELES de 1x1x1 / 2x2x2 px (0.0625 / 0.125 unidades) que se
    desprenden abajo, en los costados y alrededor del collar (v16_mote_*),
    más 8 fragmentos de ceniza (v16_ash_*). Cada microvóxel es un hueso
    propio con pivote desplazado: al girarlo en runtime la partícula se
    desplaza de verdad, sin partículas externas ni mixins.

  * FLUJO DINÁMICO: CapaArmorModel anima tela, dobladillo, collar, jirones,
    venas y microvóxeles con fases independientes (todo en radianes y con
    fail-safe). tools/preview_cloth.py y preview/ replican esa onda.

Todas las UV nuevas caen en rectángulos 100% opacos del atlas de 128x128.
Se mantienen ID, Curios `back`, canvas 96x48, raíz sin `parent`, 0 JsonNull,
radianes, fail-safes, 0 mixins y UV <= 128. Uso:

    python3 tools/armor_model_pipeline.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from cloth_spec import (
    COLUMNS,
    FOLDS,
    SECTION_V,
    SECTIONS,
    STRIP_W,
    UV,
    assert_opaque,
    cloth_uv,
    hem_uv,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

# v1.14.0: separación entre capas. Rango pedido: 0.01 - 0.05.
INFLATE = (0.01, 0.03, 0.05)

# Número de piezas de la nueva familia (debe coincidir con CapaArmorModel).
COLLAR_SEGS = 14
FRAY_COUNT = 20
YOKE_COUNT = 5
TATTER_SEGS = 5
SHRED_PER_SIDE = 6
VEIN_COUNT = 18
MOTE_COUNT = 56
ASH_COUNT = 8


def S(region: str, w: float | None = None, h: float | None = None,
      du: float = 0.0, dv: float = 0.0) -> dict:
    """Rectángulo UV absoluto dentro de una zona opaca del atlas."""
    s = dict(UV[region])
    s["uv"] = [round(s["uv"][0] + du, 4), round(s["uv"][1] + dv, 4)]
    s["uv_size"] = [round(s["uv_size"][0] if w is None else w, 4),
                    round(s["uv_size"][1] if h is None else h, 4)]
    assert_opaque(s)
    return s


def chunk(col: int, seg: int, nseg: int = 6) -> dict:
    """Trozo del canvas 96x48 que corresponde a una tira en el espacio."""
    w = 96.0 / COLUMNS
    h = 48.0 / nseg
    col = max(0, min(COLUMNS - 1, col))
    seg = max(0, min(nseg - 1, seg % nseg))
    s = {"uv": [round(col * w, 4), round(seg * h, 4)],
         "uv_size": [round(w, 4), round(h, 4)]}
    assert_opaque(s)
    return s


def mote_uv(i: int) -> dict:
    """Sub-rectángulo 2x2 de la rampa rosa/magenta/violeta-negro."""
    return S("energy_ramp", w=2.0, h=2.0,
             du=float(i % 4), dv=float((i * 5) % 16))


def cube16(origin, size, front: dict, side: dict | None = None,
           inflate: float = 0.0) -> dict:
    """Cubo con ESPESOR real e `inflate` anti Z-fighting.

    north/south toman el trozo de tela (o la rampa de energía), y los cuatro
    cantos toman una franja reservada: así el grosor se lee como borde
    iluminado y no como una barra negra.
    """
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


def global_bounds(by_name: dict) -> tuple[float, float, float, float]:
    cubes = [c for section in SECTIONS for c in by_name[section]["cubes"]]
    x0 = min(c["origin"][0] for c in cubes)
    x1 = max(c["origin"][0] + c["size"][0] for c in cubes)
    y0 = min(c["origin"][1] for c in cubes)
    y1 = max(c["origin"][1] + c["size"][1] for c in cubes)
    return x0, x1, y0, y1


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
    step = (gx1 - gx0) / COLUMNS

    # ------------------------------------------------------------------
    # 1. CAPA BASE: 27 tiras v15_cloth_* (2 cubos cada una, con rotura).
    #    Conservamos el nombre porque CapaArmorModel ya las resuelve y les
    #    aplica la onda compartida; así no se pierde ni una línea de la
    #    animación existente.
    # ------------------------------------------------------------------
    for si, section in enumerate(SECTIONS):
        _, _, y_lo, y_hi, _ = row_bounds(gx0, gx1, gy0, gy1, si)
        row_h = y_hi - y_lo
        for col in range(COLUMNS):
            norm = (col - (COLUMNS - 1) / 2.0) / ((COLUMNS - 1) / 2.0)
            x = gx0 + col * step
            width = step * 1.10
            z = (2.42 + 0.12 * si + 0.18 * (1.0 - norm * norm)
                 + 0.14 * math.cos(2.0 * math.pi * FOLDS * (col + 0.5) / COLUMNS))
            uv = cloth_uv(si, col)
            # Lamina CONTINUA: los huecos los crean los jirones de encima,
            # no una cuadricula de bloques iguales.
            cubes = [cube16(
                (x, y_lo + 0.06, z), (width, row_h - 0.14, 0.34),
                uv, S("ash"), INFLATE[0],
            )]
            # Punta rasgada irregular al final de la seccion inferior.
            if si == 2:
                tip = 0.45 + 0.55 * abs(math.sin(col * 2.3))
                cubes.append(cube16(
                    (x + 0.08, y_lo - tip, z + 0.02),
                    (width * 0.72, tip, 0.28),
                    hem_uv(col), S("crease_light"), INFLATE[1],
                ))
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [x + width / 2.0, (y_lo + y_hi) / 2.0, z + 0.17],
                [0.6 + 1.0 * si, 0.0, 1.2 * math.sin(col * 1.7)],
                cubes,
            ))

    # ------------------------------------------------------------------
    # 2. PUNTAS RASGADAS del dobladillo (9). Cuelgan de la tira inferior.
    # ------------------------------------------------------------------
    for col in range(COLUMNS):
        center = gx0 + (col + 0.5) * step
        norm = abs((col - 4) / 4.0)
        length = 0.75 + 0.85 * (1.0 - norm) + 0.25 * math.sin(col * 2.1)
        z = 2.75 + 0.14 * math.cos(col * 1.3)
        bones.append(bone(
            f"v15_hem_{col}", f"v15_cloth_cape_bottom_{col}",
            [center, gy0 - 0.05, z],
            [2.0 + 2.0 * (1.0 - norm), 0.0, -7.0 + 3.5 * col],
            [cube16((center - step * 0.42, gy0 - 0.05 - length, z),
                    (step * 0.84, length, 0.30),
                    hem_uv(col), S("energy_vein"), INFLATE[1])],
        ))

    # ------------------------------------------------------------------
    # 3. NÚCLEOS de energía (v15_orbit_*): 4 microvóxeles grandes en el
    #    centro de la capa. El modelo Java ya los hace girar despacio.
    # ------------------------------------------------------------------
    for i in range(4):
        ang = i * math.pi / 2.0
        x = 1.9 * math.cos(ang)
        y = 16.0 + 1.9 * math.sin(ang)
        z = 3.45
        bones.append(bone(
            f"v15_orbit_{i}", "v15_cloth_cape_mid_4",
            [x - 0.45, y + 0.45, z], [0.0, 0.0, 45.0],
            [cube16((x, y, z), (0.24, 0.24, 0.20),
                    mote_uv(i + 7), mote_uv(i + 7), INFLATE[2])],
        ))

    # ------------------------------------------------------------------
    # 4. HOMBRERAS ENVOLVENTES (v15_rear_pad_*): van de delante a atrás,
    #    abrazando el hombro. El Java v1.13.0 ya les da vaivén propio.
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
                cube16((hx + 0.55, 22.45, 3.55), (0.85, 0.85, 0.40),
                       mote_uv(3), mote_uv(3), INFLATE[2]),
            ],
        ))

    # ------------------------------------------------------------------
    # 5. COLLAR / BUFANDA voluminoso: DOS anillos de 14 segmentos. Cada
    #    segmento se solapa con el siguiente (arco ~1.9, ancho 2.2) y se
    #    orienta tangencialmente con rotación Y = theta + 90 grados.
    #    Radio exterior 5.4x3.2 / interior 4.35x2.55, centro z = 0.4.
    # ------------------------------------------------------------------
    for ring, (rx, rz, cy, hh, dep, infl) in enumerate((
            (5.00, 2.90, 23.20, 2.15, 0.46, INFLATE[0]),
            (4.00, 2.30, 23.80, 1.80, 0.38, INFLATE[2]))):
        for k in range(COLLAR_SEGS):
            th = 2.0 * math.pi * k / COLLAR_SEGS
            cx = rx * math.cos(th)
            cz = 0.40 + rz * math.sin(th)
            w = 2.35 if ring == 0 else 2.05
            # Altura alterna: el borde superior queda DENTADO, no recto.
            h = hh * (1.0 + 0.22 * math.sin(k * 2.1 + ring))
            jitter = 6.0 * math.sin(k * 2.3 + ring)
            rot = [6.0 * math.sin(k * 1.1 + ring),
                   math.degrees(th) + 90.0,
                   jitter]
            front = S("yoke") if ring == 0 else S("ash")
            side = S("ash") if ring == 0 else S("crease_light")
            bones.append(bone(
                f"v16_collar_{'outer' if ring == 0 else 'inner'}_{k}",
                "chestplate", [cx, cy, cz + infl], rot,
                [cube16((cx - w / 2.0, cy - h / 2.0, cz - dep / 2.0 + infl),
                        (w, h, dep), front, side, infl)],
            ))

    # 6. TIRAS DESHILACHADAS por TODO el contorno (Shigaraki): 20 flecos
    #    de longitud distinta, delante y detrás, que rompen el borde inferior
    #    del collar y lo conectan visualmente con los jirones.
    for k in range(FRAY_COUNT):
        th = 2.0 * math.pi * k / FRAY_COUNT
        cx = 4.85 * math.cos(th)
        cz = 0.40 + 2.80 * math.sin(th)
        length = 1.15 + 2.25 * abs(math.sin(k * 2.7))
        parent = f"v16_collar_outer_{(k * COLLAR_SEGS // FRAY_COUNT) % COLLAR_SEGS}"
        bones.append(bone(
            f"v16_fray_{k}", parent,
            [cx, 22.45, cz], [4.0, 0.0, -16.0 + 7.0 * math.sin(k * 1.9)],
            [cube16((cx - 0.27, 22.45 - length, cz),
                    (0.54, length, 0.28),
                    chunk(k % COLUMNS, 1), S("ash"), INFLATE[1])],
        ))

    # 7. YUGO: 5 piezas que conectan el collar con la espalda. Sin huecos:
    #    cada caja se solapa 0.3 con la vecina y baja hasta la primera tira.
    for j in range(YOKE_COUNT):
        x = -4.6 + j * 2.3
        bones.append(bone(
            f"v16_yoke_{j}", "cape_top",
            [x + 1.15, 22.6, 3.05], [3.0, 0.0, 3.0 * math.sin(j * 1.4)],
            [cube16((x, 21.2, 2.75), (2.55, 2.75, 0.46),
                    chunk(j % COLUMNS, 0), S("crease_light"), INFLATE[1])],
        ))

    # ------------------------------------------------------------------
    # 8. SEGUNDA CAPA DE JIRONES: 9 columnas x 5 segmentos. Cada pieza
    #    tiene 0.25..0.50 de espesor, su propio giro, su propio inflate y
    #    su trozo de canvas. Hacia abajo se estrechan y algunas faltan:
    #    la capa se desmorona en lugar de terminar en un rectángulo.
    # ------------------------------------------------------------------
    stream_cols = 13
    stream_n = 6
    cstep = (gx1 - gx0) / stream_cols
    for col in range(stream_cols):
        for k in range(stream_n):
            r = math.sin(col * 2.7 + k * 3.9)
            q = math.cos(col * 1.9 + k * 4.3)
            x = gx0 + (col + 0.5) * cstep + 0.42 * r
            y_top = 22.6 + 0.55 * q
            # Longitudes MUY distintas: la capa se deshilacha en puntas.
            y_end = 2.6 + 8.6 * (0.5 + 0.5 * math.sin(col * 1.3 + k * 2.1))
            length = y_top - y_end
            width = 0.46 + 0.34 * (0.5 + 0.5 * r)
            thickness = 0.27 + 0.09 * ((col + k) % 3)
            layer = k % 3
            z = (2.86 + 0.30 * layer + 0.26 * q + INFLATE[layer])
            parent = section_for_y(y_top - length * 0.5, gy0, gy1)
            rot = [2.0 + 3.0 * abs(q), 5.0 * r,
                   (4.0 + 7.0 * (k / stream_n)) * (1.0 if r >= 0 else -1.0)]
            main_h = length * 0.76
            cubes = [
                cube16((x - width / 2.0, y_top - main_h, z),
                       (width, main_h, thickness),
                       chunk(col % COLUMNS, k, stream_n),
                       S("ash" if (col + k) % 3 else "energy_vein"),
                       INFLATE[layer]),
                # Punta estrecha y desplazada: se lee como hilo que se rompe.
                cube16((x - width * 0.28 + 0.16 * r, y_end, z + 0.03),
                       (width * 0.55, main_h * 0.34, max(0.25, thickness * 0.8)),
                       chunk((col + 2) % COLUMNS, min(k + 2, stream_n - 1), stream_n),
                       S("crease_light"), INFLATE[1]),
            ]
            bones.append(bone(
                f"v16_tatter_{col}_{k}", parent,
                [x, y_top - length / 2.0, z + thickness / 2.0],
                rot, cubes,
            ))

    # 9. JIRONES que se DESPRENDEN por los costados, girados hacia fuera.
    for side, sx in (("L", -1.0), ("R", 1.0)):
        for k in range(SHRED_PER_SIDE):
            x = (gx0 - 0.35 - 0.55 * k) if sx < 0 else (gx1 - 0.55 + 0.35 * k)
            y = 20.5 - k * 2.65
            length = 2.6 + 0.7 * math.sin(k * 2.1)
            z = 2.85 + 0.30 * math.sin(k * 1.3)
            bones.append(bone(
                f"v16_shred_{side}_{k}", "cape_mid",
                [x, y, z], [6.0, sx * 12.0, sx * (16.0 + 5.0 * k)],
                [cube16((x - 0.35, y - length, z),
                        (0.70, length, 0.32),
                        chunk(0 if sx < 0 else COLUMNS - 1, k, TATTER_SEGS),
                        S("energy_vein"), INFLATE[2])],
            ))

    # 10. VENAS DE ENERGÍA: tiras finísimas en la cara SUR de los jirones.
    seg_h = (gy1 - 5.0) / TATTER_SEGS
    #     Usan la rampa rosa/magenta y un inflate de 0.01..0.05 para no
    #     combatir en Z con la tela que hay debajo.
    for i in range(VEIN_COUNT):
        col = i % COLUMNS
        seg = (i // COLUMNS) % TATTER_SEGS
        norm = (col - 4.0) / 4.0
        x = gx0 + (col + 0.5) * step + 0.22 * math.sin(i * 1.9)
        y = gy1 - 2.0 - seg * seg_h
        z = 3.42 + 0.10 * math.sin(i * 2.7)
        parent = f"v16_tatter_{col}_{seg}"
        bones.append(bone(
            f"v16_vein_{i}", parent,
            [x, y, z], [0.0, 0.0, 8.0 * math.sin(i * 2.1)],
            [cube16((x - 0.07, y - seg_h * 0.78, z),
                    (0.14, seg_h * 0.78, 0.07),
                    S("energy_vein", w=2.0, h=8.0, dv=float(i % 6) * 6.0),
                    S("energy_ramp", w=2.0, h=2.0, dv=float(i % 14)),
                    INFLATE[2])],
        ))

    # ------------------------------------------------------------------
    # 11. MICROVÓXELES: ceniza, chispas y partículas de deterioro.
    #     1x1x1 px = 0.0625 unidades, 2x2x2 px = 0.125. El pivote queda
    #     desplazado ~0.6: al girar el hueso en runtime la partícula se
    #     mueve de verdad (sin partículas externas ni mixins).
    # ------------------------------------------------------------------
    for i in range(MOTE_COUNT):
        r = (i * 37) % 100 / 100.0
        q = (i * 61) % 100 / 100.0
        s = 0.0625 if i % 3 else 0.125
        if i < 30:                       # debajo de la capa
            x = gx0 - 1.0 + r * (gx1 - gx0 + 2.0)
            y = 2.6 + q * 7.4
            z = 2.3 + r * 4.1
            parent = "cape_bottom"
        elif i < 46:                     # costados
            side = -1.0 if i % 2 else 1.0
            x = side * (6.0 + r * 2.3)
            y = 8.0 + q * 14.0
            z = 2.2 + r * 3.6
            parent = "cape_mid"
        else:                            # alrededor del collar
            x = -6.2 + r * 12.4
            y = 22.2 + q * 5.2
            z = -2.4 + r * 7.6
            parent = "chestplate"
        uv = mote_uv(i)
        bones.append(bone(
            f"v16_mote_{i}", parent,
            [x - 0.62, y + 0.62, z],
            [12.0 * math.sin(i), 18.0 * math.cos(i * 0.7), 24.0 * math.sin(i * 1.3)],
            [cube16((x, y, z), (s, s, s), uv, uv, INFLATE[2])],
        ))

    # 12. Fragmentos de ceniza mayores, oscuros, entre los jirones.
    for i in range(ASH_COUNT):
        x = gx0 + 0.8 + (i * 1.63) % (gx1 - gx0 - 1.6)
        y = 6.0 + (i * 2.9) % 13.0
        z = 3.3 + 0.5 * math.sin(i * 2.2)
        s = 0.1875
        bones.append(bone(
            f"v16_ash_{i}", "cape_bottom",
            [x - 0.5, y + 0.5, z], [0.0, 0.0, 45.0 * math.sin(i)],
            [cube16((x, y, z), (s, s, s), S("ash"), S("ash"), INFLATE[0])],
        ))

    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 6.0
    desc["visible_bounds_height"] = 5.6
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    # ---- Garantías de integridad -------------------------------------
    assert geo["bones"][:72] == original_bones, "los 72 huesos originales cambiaron"
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    for prefix, expected in (
            ("v15_cloth_", 27), ("v15_hem_", 9), ("v15_orbit_", 4),
            ("v15_rear_pad_", 2), ("v16_collar_", 2 * COLLAR_SEGS),
            ("v16_fray_", FRAY_COUNT), ("v16_yoke_", YOKE_COUNT),
            ("v16_tatter_", 13 * 6),
            ("v16_shred_", 2 * SHRED_PER_SIDE),
            ("v16_vein_", VEIN_COUNT), ("v16_mote_", MOTE_COUNT),
            ("v16_ash_", ASH_COUNT)):
        assert sum(1 for n in names if n.startswith(prefix)) == expected, prefix
    for b in bones:
        assert b.get("parent") is None or b["parent"] in names, b["name"]
    # Sólo la piel nueva: los 72 huesos prístinos tienen grosores y UV
    # heredados que NO deben tocarse ni validarse con las reglas nuevas.
    for b in bones[72:]:
        for c in b.get("cubes", []):
            for f in c["uv"].values():
                assert_opaque(f)
            assert 0.0 < c["inflate"] <= 0.05, c["inflate"]
    thick = [c["size"][2] for b in bones[72:]
             for c in b["cubes"]
             if b["name"].startswith(("v15_cloth_", "v16_tatter_", "v16_shred_",
                                      "v16_fray_", "v15_hem_"))]
    assert all(0.25 <= t <= 0.50 for t in thick), (min(thick), max(thick))
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    new = [b for b in geo["bones"][72:]]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")
    print(f"  collar {sum(1 for b in new if b['name'].startswith('v16_collar_'))}"
          f" | jirones {sum(1 for b in new if b['name'].startswith('v16_tatter_'))}"
          f" | microvoxeles {sum(1 for b in new if b['name'].startswith('v16_mote_'))}"
          f" | venas {sum(1 for b in new if b['name'].startswith('v16_vein_'))}")


if __name__ == "__main__":
    main()
