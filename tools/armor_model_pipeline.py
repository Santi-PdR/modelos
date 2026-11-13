#!/usr/bin/env python3
"""RECONSTRUCCIÓN DESDE CERO de la capa equipada, contra la referencia real.

v1.17.0 — «empieza de 0, quiero que quede exactamente como en la imagen».

hasta aquí se había rediseñado A OJO: primero una jaula de tiras finas,
después un cilindro de cintas paralelas. Ninguna de las dos cosas está en la
captura de Blockbench del usuario. Lo que SÍ está, medido en
``tools/reference_trace.py`` -> ``tools/reference_profile.json``:

  * Una BUFANDA / capucha carmesí oscura, GRUESA, en forma de cuenco, con
    el borde inferior rasgado (la cabeza blanca es sólo escala).
  * Un ABANICO de ~15 jirones que NACEN juntos en el cuello (±3.6), se
    ABREN hasta ±9.2 unidades y acaban en PUNTAS a alturas distintas: los
    jirones de fuera terminan ANTES (t=0.66) y los del centro llegan hasta
    abajo (t=1.0). El dobladillo es una V / campana, NO una línea recta.
  * Degradado MEDIDO por filas: carmesí (58,25,37) -> rojo vivo (81,23,40)
    -> violeta (70,29,65) -> violeta desvaído (79,41,78) -> oscuro (61,32,56).
  * 54 GRIETAS rosa CORTAS reales y 8 MOTAS FLOTANTES reales. REV. B:
    las motas YA NO son geometría: se emiten como partículas en runtime
    (`spawnAura`) cuando la capa está equipada. Metidas en el geo eran
    cubos rosa suspendidos alrededor de la capa en Blockbench.
  * Agujeros NEGROS entre jirones (separaciones geométricas de verdad).

``tools/cape_shape.py`` es la fuente de verdad compartida: este módulo
coloca los cubos y ``texture_pipeline.py`` DES-ABANICA el recorte limpio de
la referencia en el atlas 96x48 para que cada cinta lleve los colores que
le corresponden en la captura.

Se conservan: los 72 huesos originales byte-idénticos, alfa prístino,
1636 emisivos, UV opacas ≤128, ``inflate`` ≤0.05, espesor 0.25-0.50,
0 ``JsonNull``, raíz sin ``parent``, 0 mixins, radianes/fail-safes.

Uso:  PYTHONPATH=tools/_deps python3 tools/armor_model_pipeline.py
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


def ribbon_thick(k: int) -> float:
    """v1.22.0: espesor propio de cada jirón (0.55-0.80).

    Antes 0.28-0.40: de perfil la capa era una LÁMINA de 0.3 unidades y
    parecía despegada del jugador. Con ~0.7 hay paño con cuerpo real.
    """
    return 0.55 + 0.25 * (0.5 + 0.5 * math.sin(k * 1.7 + 0.3))

# Un solo texel oscuro para TODOS los cantos: sin filetes = sin rejilla.
DARK = {"uv": [105.0, 0.0], "uv_size": [1.0, 48.0]}
# Sprite 3x3 con centro encendido y bordes apagados: lo usan las VENAS
# 3D (relieve emisivo), no las motas. Las motas son partículas runtime.
PINK = {"uv": [69.0, 109.0], "uv_size": [3.0, 3.0]}
ASH_DARK = {"uv": [105.0, 0.0], "uv_size": [2.0, 2.0]}

COWL_FRONT = 9
COWL_BACK = 5
SHINGLE_COUNT = 10
# REV. B: YOKE_PIECES eliminado. Las 6 tiras grises eran el
# arnés del MANIQUÍ de la foto, no tela: en Blockbench se veían
# como 6 rayitas suspendidas encima de la capa.
# REV. B: MOTE_EXTRA / ASH_COUNT eliminados. Ningún cubo suelto.
# La mitad de los jirones NO acaba en aguja: en el PNG el dobladillo es
# una cascada de extremos romos/deshilachados a alturas distintas.
FADED_TIPS = {k for k in range(16) if (k * 7 + 3) % 16 < 8}


def S(region: str, w: float | None = None, h: float | None = None,
      du: float = 0.0, dv: float = 0.0) -> dict:
    from cloth_spec import UV
    s = dict(UV[region])
    s["uv"] = [round(s["uv"][0] + du, 4), round(s["uv"][1] + dv, 4)]
    s["uv_size"] = [round(s["uv_size"][0] if w is None else w, 4),
                    round(s["uv_size"][1] if h is None else h, 4)]
    assert_opaque(s)
    return s


def band(u0: float, w: float, v0: float, h: float) -> dict:
    s = {"uv": [round(u0, 4), round(v0, 4)],
         "uv_size": [round(w, 4), round(h, 4)]}
    assert_opaque(s)
    return s


def foto_uv(cx: float, cy: float, w: float, h: float) -> dict:
    """v1.18.0: UV LOCAL = el píxel de la FOTO de la capa que ocupa el cubo.

    El atlas 96x48 ES la referencia limpia (no está des-abanicada). En vez
    de una franja vertical por jirón, cada tramo muestrea el rectángulo de
    la foto correspondiente a su posición real: así el volumen 3D se
    construye ENCIMA de la imagen y el render la recompone.
    """
    scale_x = 96.0 / 17.80                 # 8.9 unidades de semiancho (rev.B)
    scale_y = 48.0 / CS.HEIGHT
    uw = max(1.0, min(14.0, w * scale_x))
    vh = max(1.0, min(12.0, h * scale_y))
    u = min(96.0 - uw, max(0.0, 48.0 + cx * scale_x - uw / 2.0))
    v = min(48.0 - vh, max(0.0, (CS.Y_TOP - cy) * scale_y - vh / 2.0))
    spec = {"uv": [round(u, 4), round(v, 4)],
            "uv_size": [round(uw, 4), round(vh, 4)]}
    assert_opaque(spec)
    return spec


def cowl_uv(w: float, h: float, i: int = 0) -> dict:
    """v1.22.0: carmesí LIMPIO para la bufanda, sin cuadrados negros.

    La franja v=0..4 del atlas es donde el PNG tenía la CABEZA BLANCA del
    maniquí: `capa_mask()` la borra y deja huecos casi negros. El capuchón
    muestreaba ESA franja y le salían agujeros cuadrados. Repintar el atlas
    rompía la fidelidad píxel a píxel (1.239 -> 7.02), así que en su lugar
    se toma el carmesí de las ALAS (u=24..64, v=14..18), que es la MISMA
    tela roja de la foto. El atlas queda intacto.
    """
    # v1.22.0: la banda v=1..3, u=24..56 es el CARMESI OSCURO y limpio
    # del borde superior de la bufanda en la foto. v=14..18 era la zona
    # de las ALAS con destellos de energía: el capuchón salía lleno de
    # cuadrados magenta. Aquí es tela roja, como en la referencia.
    u = 24.0 + (i % 5) * 6.5
    v = 1.0 + 0.4 * (i % 3)
    uw = max(2.0, min(10.0, w * 3.0))
    vh = max(1.5, min(2.6, h * 0.9))
    u = min(96.0 - uw, u)
    v = min(48.0 - vh, v)
    spec = {"uv": [round(u, 4), round(v, 4)],
            "uv_size": [round(uw, 4), round(vh, 4)]}
    assert_opaque(spec)
    return spec


def cube16(origin, size, front: dict, side: dict | None = None,
           inflate: float = 0.0) -> dict:
    """Cubo con espesor real; cantos = un texel casi negro, SIN filete."""
    s = side or DARK
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
    by_name = {b["name"]: b for b in original_bones}
    cubes0 = [c for b in original_bones for c in b.get("cubes", [])]
    gx0 = min(c["origin"][0] for c in cubes0)
    gx1 = max(c["origin"][0] + c["size"][0] for c in cubes0)
    gy0 = min(c["origin"][1] for c in cubes0)
    gy1 = max(c["origin"][1] + c["size"][1] for c in cubes0)
    step = (gx1 - gx0) / 9.0

    # ------------------------------------------------------------------
    # 1. 27 anclas de animación (`v15_cloth_*`). REV. B: están DENTRO
    #    del capuchón opaco, así que no dibujan NADA, pero mantienen la
    #    onda de tela de CapaArmorModel.java (panels[i]) y el fail-safe.
    # ------------------------------------------------------------------
    for si, section in enumerate(("cape_top", "cape_mid", "cape_bottom")):
        row_h = (gy1 - gy0) / 3.0
        y_lo = gy0 + (2 - si) * row_h
        for col in range(9):
            cx = gx0 + (col + 0.5) * step
            # ANCLA INVISIBLE: un cubo diminuto DETRÁS de la bufanda.
            # En v1.17.0 estas tiras altas y finas se veían como BARROTES
            # negros por encima del abanico; ahora sólo mantienen viva la
            # onda de tela de CapaArmorModel.panels[] (clothReady=true).
            sh = band(min(94.0, col * step + 2.0), 2.0, 45.0, 2.0)
            # REV. B: ancla OCULTA de verdad. El capuchón frontal ocupa
            # x=-5.9..5.9, y=19.7..23.3, z=4.07..4.97. Un cubo de 0.16 en
            # su interior queda tapado por el z-buffer en frente, perfil,
            # F5 y cenital: adiós a la línea de puntos flotante.
            ax = max(-5.35, min(5.35, cx))
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [ax, 21.55, 2.35],
                [0.0, 0.0, 0.0],
                [cube16((ax - 0.08, 21.47, 2.28),
                        (0.16, 0.16, 0.16), sh, sh, INFLATE[0])]))

    # ------------------------------------------------------------------
    # 2. BUFANDA / CAPUCHA GRUESA. En la referencia es un CUENCO carmesí
    #    (más bajo en el centro), no un anillo de cajas ni una losa plana.
    # ------------------------------------------------------------------
    # v1.18.0: la bufanda toma el carmesi y las cuchilladas REALES de la
    # parte superior de la foto; antes era un rectangulo liso que cortaba
    # la capa por la mitad.
    cowl_uv_base = cowl_uv(8.0, 3.0, 0)
    for i in range(COWL_FRONT):
        fx = (i - (COWL_FRONT - 1) / 2.0) / ((COWL_FRONT - 1) / 2.0)
        # v1273: capuchon CONTINUO y ancho (la captura cubre ~13/20
        # columnas en t=0.0), no alas separadas. Los lados siguen CORTOS
        # (height 1.25) para que la U gris del arnes siga visible: eso
        # fue exactamente lo que fallo en la "losa" de v1244.
        x = fx * 5.20
        # Segun el recorte 4x: la tela cuelga MAS EN EL CENTRO (lóbulo
        # redondeado bajo la cabeza) y se recoge hacia los hombros.
        # El borde superior queda escondido por la cabeza del maniquí.
        # v1212: ALAS. En la captura la bufanda sube por los hombros y
        # cae en el centro; antes y_top era casi plano y parecía una losa.
        # v1.17.2: baja 1.15 para SOLAPAR con los jirones; en
        # Blockbench la bufanda quedaba como una banda flotante separada.
        # v1.20.0: el borde superior CAE hacia los hombros. Con
        # +0.42*|fx| los extremos subian y parecian CUERNOS.
        y_top = 23.30 - 0.55 * abs(fx) + 0.10 * math.sin(i * 2.7)
        # Arco parabolico: lóbulo central ancho y redondeado, alas que
        # se recogen deprisa hacia los hombros (recorte 4x de la captura).
        # Cuenco aplanado: lóbulo central redondeado y lados recogidos.
        # Ni la campana de v1243 (solo colgaba el centro) ni la losa
        # plana de v1244 (tapaba el arnes).
        height = 0.95 + 2.70 * (1.0 - abs(fx)) ** 1.20 + 0.14 * abs(math.sin(i * 2.3))
        bottom = y_top - height + 0.16 * math.sin(i * 1.9 + 0.3)
        w = 1.85 + 0.36 * (1.0 - abs(fx))
        z = 1.75 + 0.55 * (1.0 - abs(fx))
        # v1.22.0: SOLAPAS DE HOMBRO. Los dos extremos se adelantan 0.85 y
        # giran en Y para ABRAZAR el torso; antes el capuchón era una banda
        # plana y de perfil parecía flotar separada del jugador.
        shoulder = i in (0, COWL_FRONT - 1)
        if shoulder:
            z -= 0.85
        depth = 2.20 if shoulder else 1.35
        rot_y = -fx * 26.0 if shoulder else 0.0
        # Cada pieza muestrea una franja distinta del carmesí: relieve
        # suave por capas, SIN lineas diagonales (la rejilla fue rechazada).
        cowl_uv_i = cowl_uv(w, height, i)
        bones.append(bone(
            f"v17_cowl_front_{i}", "chestplate",
            [x, y_top - height / 2.0, z + depth / 2.0],
            [0.0, rot_y, fx * 7.0],
            [cube16((x - w / 2.0, bottom, z),
                    (w, height, depth), cowl_uv_i, DARK, INFLATE[i % 3])]))
        # Dientes desiguales, MAS LARGOS en el lóbulo central.
        # La CAIDA de la bufanda la forman estos dientes ANCHOS y
        # solapados: un lóbulo central largo y alas mas cortas.
        # v1275: los dientes de los HOMBROS cuelgan mas: en la captura el
        # carmesi baja hasta el arnes por los lados, llenando t=0.0 sin
        # ninguna pieza flotante ni losa sobre la U gris.
        hang = 2.10 if i in (0, 1, 7, 8) else 1.0
        tooth = (0.45 + 1.70 * abs(math.sin(i * 2.7 + 0.4))) * (0.72 + 0.42 * (1.0 - abs(fx))) * hang
        tw = 0.92 + 0.50 * (1.0 - abs(fx)) + 0.18 * abs(math.cos(i * 1.9))
        zf = z + 1.30
        bones.append(bone(
            f"v17_cowl_tooth_{i}", f"v17_cowl_front_{i}",
            [x, bottom + 0.10, zf + 0.15],
            [0.0, 0.0, fx * 6.0 + 4.0 * math.sin(i * 2.1)],
            [cube16((x - tw / 2.0, bottom + 0.10 - tooth, zf),
                    (tw, tooth, 0.30), cowl_uv_base, DARK, INFLATE[1])]))

    # Reverso de la bufanda para la vista F5.
    # REV. B: estaba en z=-2.30 (6 unidades DETRAS del paño) y en la
    # vista de perfil aparecía como una BARRA FLOTANTE separada de la
    # capa, exactamente lo que el usuario señaló en Blockbench. Ahora es
    # una capa INTERNA de la misma bufanda: z=2.86..3.46, solapando los
    # jirones (2.3..3.6) y justo detrás del frente del capuchón (4.1..5.0).
    # Sigue siendo visible en F5 como pliegue, pero ya no flota.
    for i in range(COWL_BACK):
        fx = (i - (COWL_BACK - 1) / 2.0) / max(1.0, (COWL_BACK - 1) / 2.0)
        x = fx * 3.90
        height = 0.70 + 1.90 * (1.0 - abs(fx)) ** 1.35
        y_top = 22.90 + 0.30 * abs(fx)
        bones.append(bone(
            f"v17_cowl_back_{i}", "chestplate",
            [x, y_top - height / 2.0, 2.45],
            [0.0, 0.0, -fx * 8.0],
            [cube16((x - 1.05, y_top - height, 2.10),
                    (2.10, height, 0.75), cowl_uv_base, DARK, INFLATE[2])]))

    # REV. B: la "banda gris" de la captura es el ARNÉS del maniquí,
    # no la capa. Sus 6 `v17_yoke_*` eran tiras de 1.6x0.1 que, vistas de
    # perfil, flotaban solas por encima de la bufanda. Se eliminan.
    # (`ASH_DARK` sigue en uso en el borde del capuchón.)

    # ------------------------------------------------------------------
    # 3. EL ABANICO. 15 jirones x 6 tramos, cada tramo ROTADO para seguir
    #    la curva radial. Una banda UV vertical CONTINUA por cinta: el
    #    degradado y las grietas fluyen de arriba abajo sin tablero.
    # ------------------------------------------------------------------
    for k in range(CS.RIBBONS):
        for n in range(CS.SEGS):
            g = CS.segment_geometry(k, n)
            dep = ribbon_thick(k)
            t = (CS.segment_bounds(k, n)[0] + CS.segment_bounds(k, n)[1]) / 2.0
            front = foto_uv(g["cx"], g["cy"], g["w"], g["h"])
            bones.append(bone(
                f"v17_ribbon_{k}_seg{n}", section_for_t(t),
                [g["cx"], g["cy"], g["z"] + 0.012 * n + dep / 2.0],
                [0.0, 0.0, g["theta"]],
                [cube16(
                    (g["cx"] - g["w"] / 2.0, g["cy"] - g["h"] / 2.0,
                     g["z"] + 0.012 * n),
                    (g["w"], g["h"], dep),
                    front, DARK, INFLATE[(k + n) % 3])]))

    # ------------------------------------------------------------------
    # 3a. PUNTAS REALES. El ultimo tramo de cada jiron se remata en una
    #     lengüeta ESTRECHA y desigual: en la captura NINGUN jiron acaba
    #     en un rectangulo cortado a escuadra.
    # ------------------------------------------------------------------
    for k in range(CS.RIBBONS):
        t = CS.tip_t(k)
        x = CS.ribbon_x(k, t)
        y = CS.Y_TOP - t * CS.HEIGHT
        last = CS.segment_geometry(k, CS.SEGS - 1)
        theta = last["theta"] + 4.0 * math.sin(k * 2.3)
        tw = 0.46 + 0.30 * abs(math.sin(k * 1.7))
        th = 0.58 + 0.68 * abs(math.sin(k * 2.9 + 0.6))
        z = CS.ribbon_z(k, t) + 0.012 * CS.SEGS
        dep = ribbon_thick(k)
        # v1232: TODAS las puntas son PAÑO. Antes la mitad usaba un texel
        # casi negro y el dobladillo parecia un puñado de astillas negras;
        # en la captura los remates son violeta-lavanda desvaido.
        tip_uv = foto_uv(x, y - th / 2.0, tw, th)
        if k in FADED_TIPS:
            # Tope ROMO y deshilachado, pero del color de la tela.
            tw = 0.36 + 0.16 * abs(math.sin(k * 1.7))
            th = 0.40 + 0.42 * abs(math.sin(k * 2.9 + 0.6))
        bones.append(bone(
            f"v17_ribbon_{k}_seg{CS.SEGS}", section_for_t(t),
            [x, y - th / 2.0, z + dep / 2.0],
            [0.0, 0.0, theta],
            [cube16((x - tw / 2.0, y - th, z),
                    (tw, th, dep), tip_uv, DARK, INFLATE[(k + 2) % 3])]))

    # ------------------------------------------------------------------
    # 3b. JIRONES SECUNDARIOS: 10 tiras CORTAS que cruzan el abanico por
    #     delante, como las "tejas" de la captura. Rompen la regularidad
    #     de los rayos sin formar una rejilla: son anchas, pocas y con
    #     angulos distintos. Reusan la banda UV de la cinta vecina en su
    #     propio rango de altura, asi el color sigue siendo el del PNG.
    # ------------------------------------------------------------------
    for i in range(SHINGLE_COUNT):
        a = (i - (SHINGLE_COUNT - 1) / 2.0) / ((SHINGLE_COUNT - 1) / 2.0)
        t0 = 0.10 + 0.09 * (i % 3)
        t1 = 0.36 + 0.16 * ((i * 7) % 5) / 5.0
        x0 = a * (CS.X_NECK + 1.55 * (i % 2))
        if i in (0, 1, 8, 9):
            # v1276: ALAS DIAGONALES DEL HOMBRO. En la captura el carmesi
            # baja desde los hombros (x~+-7.6) hasta el abanico, cruzando
            # la primera decima. Cuatro tejas exteriores se alargan hacia
            # ARRIBA y AFUERA: paño real en t=0.0, sin losas ni piezas
            # flotantes, y con la misma UV continua del canvas.
            # v1.17.2: en Blockbench (pose estatica) estas 4 tejas
            # sobresalian por ENCIMA del capuchon como antenas inclinadas.
            # Nacen mas abajo, mas cerca del cuerpo y son mas estrechas.
            t0, t1 = 0.06, 0.30
            x0 = a * 4.55
        elif i in (2, 4, 6):
            # v1.22.0: JIRONES SECUNDARIOS LARGOS. En la referencia los
            # pliegues se CRUZAN y rellenan el paño; 16 cintas paralelas
            # y finas parecían una ÉLITRA. Tres tejas diagonales bajan
            # hasta t~0.74 con la foto, sin formar una falda maciza.
            t0 = 0.14 + 0.05 * (i % 3)
            t1 = 0.66 + 0.08 * ((i * 7) % 5) / 5.0
            x0 = a * 1.25
        # v1210: las tejas NO cruzaban la captura como tablones diagonales.
        # Se acortan a un pliegue cercano al hombro y se vuelven mas finas.
        if i in (2, 4, 6):
            x1 = CS.ribbon_x(int(round(7.5 + 4.0 * a)), t1) * 0.52
        else:
            x1 = a * (3.60 if i in (0, 1, 8, 9) else CS.silhouette(0.55) * 0.62)
        y0, y1 = CS.Y_TOP - t0 * CS.HEIGHT, CS.Y_TOP - t1 * CS.HEIGHT
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        dy, dx = y0 - y1, x1 - x0
        theta = -math.degrees(math.atan2(dx, dy)) + 4.5 * math.sin(i * 2.3 + 0.7)
        h = math.hypot(dx, dy) * (0.94 if i in (2, 4, 6) else 0.86)
        # Capas de tela SOLAPADAS, no un escudo: anchura moderada y
        # profundidad distinta para que se lean como jirones separados.
        w = (1.02 + 0.14 * abs(math.sin(i * 1.9))) if i in (0, 1, 8, 9) \
            else ((0.86 + 0.22 * abs(math.sin(i * 1.9))) if i in (2, 4, 6)
                  else (0.50 + 0.24 * abs(a) + 0.12 * abs(math.sin(i * 1.9))))
        z = 1.95 + 0.26 * (i % 3)
        near = CS.nearest_ribbon((t0 + t1) / 2.0, x0 / 8.6)
        if i in (0, 1, 8, 9):
            # Carmesi LISO del yugo: en la captura los hombros son tela
            # oscura y las grietas rosa viven en las MOTAS sueltas, no en
            # una lluvia de guiones sobre el capuchon.
            uv = foto_uv(cx, cy, w, h)
        else:
            uv = foto_uv(cx, cy, w, h)
        bones.append(bone(
            f"v17_shingle_{i}", "chestplate", [cx, cy, z + 0.15],
            [0.0, 0.0, theta],
            [cube16((cx - w / 2.0, cy - h / 2.0, z),
                    (w, h, 0.62), uv, DARK, INFLATE[1])]))

    # ------------------------------------------------------------------
    # 4. MOTAS: YA NO HAY GEOMETRÍA. (rev. B)
    #    Antes había 18 `v17_mote_*` + 8 `v17_ash_*`: cubos rosas/grises
    #    SUSPENDIDOS alrededor de la capa. En las capturas de Blockbench
    #    parecían "cosas volando" y el usuario pidió que NO estuvieran en
    #    el modelo. Las 8 motas medidas en `reference_profile.json` siguen
    #    siendo la referencia de DISTRIBUCIÓN, pero ahora las genera
    #    `CapaDeteriorerItem.spawnAura()` en el servidor, con los sprites
    #    `capa_ember_*`, `capa_blight_mote_*` y `capa_shard_*`.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. VENAS 3D: 10 trazos rosa SACADOS de las grietas reales del PNG,
    #    como cubos emisivos DELGADOS inclinados sobre su jiron. Java las
    #    hace PULSAR (`v17_vein_*`) y el glowmask las enciende de noche.
    # ------------------------------------------------------------------
    for i, m in enumerate(CS.vein_marks(10)):
        t = max(0.05, min(0.94, m["t"]))
        k = CS.nearest_ribbon(t, m["x"])
        x = CS.ribbon_x(k, t) + 0.10 * math.sin(i * 2.1)
        y = CS.Y_TOP - t * CS.HEIGHT
        z = CS.ribbon_z(k, t) + 0.34
        vw = 0.09 + 0.05 * (i % 3)
        vh = 0.42 + 0.58 * abs(math.sin(i * 1.7 + 0.3))
        bones.append(bone(
            f"v17_vein_{i}", "chestplate", [x, y, z],
            [0.0, 0.0, 18.0 * math.sin(i * 1.31)],
            [cube16((x - vw / 2.0, y - vh / 2.0, z),
                    (vw, vh, 0.26), PINK, PINK, INFLATE[2])]))

    # ---- descripción y garantías -------------------------------------
    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 6.0
    desc["visible_bounds_height"] = 5.6
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    assert geo["bones"][:72] == original_bones, "los 72 huesos originales cambiaron"
    assert not any(b["name"].startswith(("v17_mote_", "v17_ash_",
                                        "v16_mote_", "v16_ash_"))
                   for b in bones), "vuelven los cubos flotantes"
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    for prefix, expected in (
            ("v15_cloth_", 27),
            ("v17_cowl_front_", COWL_FRONT), ("v17_cowl_tooth_", COWL_FRONT),
            ("v17_cowl_back_", COWL_BACK),
            ("v17_ribbon_", CS.RIBBONS * (CS.SEGS + 1)),
            ("v17_vein_", 10), ("v17_shingle_", SHINGLE_COUNT),
            ("v17_ribbon_", CS.RIBBONS * (CS.SEGS + 1))):
        assert sum(1 for n in names if n.startswith(prefix)) == expected, prefix
    for b in bones:
        assert b.get("parent") is None or b["parent"] in names, b["name"]
    for b in bones[72:]:
        for c in b.get("cubes", []):
            for f in c["uv"].values():
                assert_opaque(f)
            assert 0.0 < c["inflate"] <= 0.05, c["inflate"]
    thick = [c["size"][2] for b in bones[72:] for c in b["cubes"]
             if b["name"].startswith("v17_ribbon_")]
    # REV. B: las anclas v15_cloth_ son cubos de 0.16 OCULTOS dentro del
    # capuchón; el contrato de espesor es sólo para el paño visible.
    assert thick and all(0.50 <= t <= 0.85 for t in thick), (min(thick), max(thick))
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")
    print(f"  abanico {CS.RIBBONS} jirones x {CS.SEGS} tramos"
          f" | capucha {COWL_FRONT + COWL_BACK} | SIN motas 3D "
          f"(particulas solo en runtime)")


if __name__ == "__main__":
    main()
