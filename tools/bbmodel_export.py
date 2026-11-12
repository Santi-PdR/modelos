#!/usr/bin/env python3
"""Exporta el .geo.json de la capa a un proyecto .bbmodel de Blockbench.

v1.17.0: corrige DOS defectos graves de la entrega anterior.

1. UUID CANÓNICOS. Blockbench comprueba `isUUID()` (36 caracteres con
   guiones) para resolver los animadores de hueso. El exportador anterior
   usaba md5 hex de 32 caracteres: `Animation.extend()` no reconocía la
   clave, generaba un uuid aleatorio y los keyframes quedaban HUÉRFANOS.
   Ahora todos los uuid (elementos, grupos, animaciones y keyframes) son
   8-4-4-4-12 en minúsculas.

2. ANIMACIONES REALES. La entrega anterior tenía `animations: []`: el modelo
   en Blockbench era estático. Se exportan 4 animaciones en bucle con
   keyframes de rotación (y posición en los microvóxeles) sobre TODOS los
   huesos v16_* y los 27 paneles de paño: respiración del collar, ondeo de
   las cintas con retardo, pulso de las venas y deriva de las partículas.

v1.17.2: se ELIMINA el maniquí Steve/Alex. El exportador metía 6 cubos
(cabeza, torso, brazos, piernas) con un parche de textura en las filas
128..143 de una imagen 128x144. En el visor web pasaban desapercibidos, pero
al abrir el `.bbmodel` en Blockbench TAPABAN LA CAPA: el usuario veía un
muñeco blanco con brazos amarillos. Ahora hay una sola imagen 128x128 con
el atlas real, todas las UV <= 128 y SOLO los cubos de la capa.

Uso:  python3 tools/bbmodel_export.py
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"
ATLAS = ROOT / "src/main/resources/assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png"
OUT = ROOT / "preview/assets/capa_deteriorer_evilsaiyan.bbmodel"
DOC = ROOT / "docs/capa_v1170.bbmodel"

FACES = ("north", "south", "east", "west", "up", "down")


def uid(key: str) -> str:
    """UUID canónico 8-4-4-4-12 (Blockbench isUUID exige 36 caracteres)."""
    h = hashlib.md5(key.encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def data_url(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def neg_xy(vec) -> list:
    v = list(vec or [0, 0, 0])
    return [round(-v[0], 4), round(v[1], 4), round(v[2], 4)]


def face_uv(spec) -> dict | None:
    if not isinstance(spec, dict) or "uv" not in spec:
        return None
    u, v = spec["uv"]
    w, h = spec.get("uv_size", [0, 0])
    if not all(isinstance(q, (int, float)) for q in (u, v, w, h)):
        return None
    if w <= 0 or h <= 0 or u < 0 or v < 0 or u + w > 128 or v + h > 128:
        return None
    return {"uv": [round(u, 3), round(v, 3), round(u + w, 3), round(v + h, 3)],
            "texture": 0}


def atlas_texture() -> Image.Image:
    """Sólo el atlas real 128x128: nada de maniquí ni parches extra."""
    atlas = Image.open(ATLAS).convert("RGBA")
    assert atlas.size == (128, 128), atlas.size
    return atlas


def make_element(bone: dict, ci: int, cube: dict, key: str) -> dict:
    o, sz = cube["origin"], cube["size"]
    x, y, z = -(o[0] + sz[0]), o[1], o[2]
    f = [round(v, 4) for v in (x, y, z)]
    t = [round(v, 4) for v in (x + sz[0], y + sz[1], z + sz[2])]
    rot = neg_xy(cube.get("rotation", [0, 0, 0]))
    if "pivot" in cube:
        origin = list(cube["pivot"])
        origin[0] = -origin[0]
        origin = [round(q, 4) for q in origin]
    else:
        origin = [round((f[i] + t[i]) / 2.0, 4) for i in range(3)]
    faces = {}
    spec = cube.get("uv", {}) if isinstance(cube.get("uv"), dict) else {}
    for fn in FACES:
        fv = face_uv(spec.get(fn))
        if fv and fn in ("up", "down"):
            fv["uv"] = [fv["uv"][2], fv["uv"][3], fv["uv"][0], fv["uv"][1]]
        faces[fn] = fv or {"uv": [0, 0, 0, 0], "texture": None}
    return {
        "name": f"{bone['name']}_{ci}", "type": "cube", "uuid": uid(key),
        "from": f, "to": t, "origin": origin, "rotation": rot,
        "inflate": round(float(cube.get("inflate", 0.0)), 4),
        "autouv": 0, "color": 0, "visibility": True,
        "faces": faces, "box_uv": False,
    }


def make_group(name: str, pivot, rotation, children, key: str,
               is_open: bool = False) -> dict:
    p = list(pivot or [0, 0, 0])
    return {
        "name": name, "uuid": uid(key),
        "origin": [round(-p[0], 4), round(p[1], 4), round(p[2], 4)],
        "rotation": neg_xy(rotation),
        "visibility": True, "isOpen": is_open, "shade": True,
        "export": True, "locked": False, "autouv": 0,
        "children": children,
    }


def kf(channel: str, t: float, x: float, y: float, z: float, key: str,
       interp: str = "bezier", tangent: tuple[float, float, float] | None = None,
       effect: dict | None = None) -> dict:
    """Keyframe de Blockbench.

    v1.17.0 v1205: la interpolacion `linear` producia ESQUINAS visibles
    en la tela (la documentacion de Blockbench recomienda `catmullrom`
    o `bezier` para movimiento organico). Se usan curvas Bezier cuyas
    tangentes salen de la DERIVADA ANALITICA de la onda, asi la curva es
    C1-continua en todos los keyframes y el bucle no tiene salto.
    """
    if effect is not None:
        points = [dict(effect)]
    else:
        points = [{"x": str(round(x, 3)), "y": str(round(y, 3)),
                   "z": str(round(z, 3))}]
    if tangent is None:
        lt, rt = [-0.30] * 3, [0.30] * 3
        lv, rv = [0, 0, 0], [0, 0, 0]
    else:
        lt, rt = [-0.30] * 3, [0.30] * 3
        rv = [round(v * 0.30, 3) for v in tangent]
        lv = [round(-v * 0.30, 3) for v in tangent]
    return {
        "channel": channel,
        "data_points": points,
        "uuid": uid(key),
        "time": round(t, 4),
        "color": -1,
        "interpolation": interp,
        "bezier_linked": False,
        "bezier_left_time": lt,
        "bezier_left_value": lv,
        "bezier_right_time": rt,
        "bezier_right_value": rv,
    }


def _wave_derivative(f: float, phase: float, flutter: float = 1.0) -> float:
    """d(_wave)/df: tangente exacta de la onda, no una aproximacion.

    v1240: tercer armonico (3 ciclos por bucle) = FLUTTER de las puntas.
    Su derivada analitica mantiene la continuidad C1 en todos los kfs.
    """
    return (0.75 * 2.0 * math.pi * math.cos(2.0 * math.pi * f + phase)
            + 0.18 * 4.0 * math.pi * math.cos(4.0 * math.pi * f + phase * 1.7)
            + 0.055 * flutter * 6.0 * math.pi
            * math.cos(6.0 * math.pi * f + phase * 2.3))


STYLE_GAIN = {
    # tela, motas, venas, cuello, tejas
    "idle":      (0.55, 0.60, 0.70, 0.80, 0.55),
    "caminar":   (1.00, 1.00, 1.00, 1.00, 1.00),
    "correr":    (1.70, 1.60, 1.45, 1.40, 1.60),
    "deterioro": (0.35, 1.80, 2.50, 0.45, 0.45),
}

# Cada animacion arranca con una fase DISTINTA: al cambiar de clip la
# capa no salta desde la misma pose.
STYLE_PHASE = {"idle": 0.0, "caminar": 0.45,
               "correr": 0.95, "deterioro": 1.70}


def motion_for(name: str, idx: int, style: str) -> tuple[float, float, float, float]:
    """Amplitud (grados) y FASE por segmento/columna, por familia y estilo.

    v1.17.0: antes habia una rama `v17_ribbon_` INALCANZABLE (otra rama
    mas general la capturaba) y el estilo `deterioro` caia siempre en los
    valores de `idle`. Ahora la fase sale del SEGMENTO REAL del nombre,
    de modo que la onda baja por la capa en Java, visor y Blockbench.
    """
    g = STYLE_GAIN[style]
    col, seg = idx % 16, 0
    if name.startswith("v17_ribbon_"):
        parts = name.split("_")
        try:
            col = int(parts[2])
        except (ValueError, IndexError):
            col = idx % 16
        tail = parts[-1]
        seg = int(tail[3:]) if tail.startswith("seg") else 0
    phase = seg * 0.62 + col * 0.19 + STYLE_PHASE[style]
    if name.startswith(("v17_mote_", "v17_ash_", "v16_mote_", "v16_ash_")):
        a = 8.0 * g[1]
        return (a, a * 0.7, a * 0.5, phase)
    if name.startswith(("v17_cowl_", "v17_yoke_", "v16_collar_", "v16_yoke_")):
        a = 2.0 * g[3]
        return (a, 0.0, a * 0.6, phase * 0.4)
    if name.startswith(("v17_vein_", "v16_vein_")):
        a = 7.0 * g[2]
        return (a * 0.25, 0.0, a, phase * 2.4)
    if name.startswith("v17_shingle_"):
        a = 4.0 * g[4]
        return (a * 0.45, a * 0.20, a * 0.80, phase * 1.3)
    if name.startswith(("v17_ribbon_", "v16_fray_", "v16_hem_",
                        "v16_shred_", "v16_tatter_")):
        # La onda CRECE hacia las puntas (seg/6), no i%5.
        a = (2.2 + 6.5 * (seg / 6.0)) * g[0]
        return (a * 0.5, 0.0, a, phase)
    a = 2.4 * g[0]
    return (a * 0.5, 0.0, a, phase * 0.8)


ANIMATION_SPECS = (
    ("idle_respiracion", "loop", 4.0, "idle", 1.0),
    ("caminar", "loop", 1.2, "caminar", 1.0),
    ("correr_saltar", "loop", 0.8, "correr", 1.0),
    ("deterioro_particulas", "loop", 3.0, "deterioro", 1.15),
)

WAVE_SAMPLES = 11             # v1240: 12 muestras por hueso, C1 mas fino


def _wave(f: float, phase: float, flutter: float = 1.0) -> float:
    """Onda periodica que VALE 0 en f=0 y f=1: el bucle no pega un salto.

    `flutter` crece con el numero de tramo: los jirones bajos vibran mas
    que la bufanda, como tela rasgada y ligera.
    """
    return ((math.sin(2.0 * math.pi * f + phase) - math.sin(phase)) * 0.75
            + (math.sin(4.0 * math.pi * f + phase * 1.7)
               - math.sin(phase * 1.7)) * 0.18
            + (math.sin(6.0 * math.pi * f + phase * 2.3)
               - math.sin(phase * 2.3)) * 0.055 * flutter)


def build_animations(anim_bones: list[tuple[str, str]]) -> list[dict]:
    """4 animaciones diferenciadas: rotacion + posicion + ESCALA (venas)."""
    out = []
    for aname, loop, length, style, mult in ANIMATION_SPECS:
        animators = {}
        for idx, (bname, guuid) in enumerate(anim_bones):
            ax, ay, az, phase = motion_for(bname, idx, style)
            ax, ay, az = ax * mult, ay * mult, az * mult
            # v1240: el flutter es MAYOR en las puntas y en las motas.
            flutter = 1.0
            if bname.startswith("v17_ribbon_") and "seg" in bname:
                seg = int(bname.split("_")[-1][3:])
                flutter = 1.0 + 0.30 * seg
            elif bname.startswith(("v17_mote_", "v17_vein_")):
                flutter = 1.7
            keyframes = []
            for j in range(WAVE_SAMPLES + 1):
                f = j / WAVE_SAMPLES
                w = _wave(f, phase, flutter)
                dw = _wave_derivative(f, phase, flutter) / WAVE_SAMPLES
                keyframes.append(kf("rotation", round(length * f, 4),
                                    ax * w, ay * w, az * w,
                                    f"{aname}/{bname}/r{j}",
                                    tangent=(ax * dw, ay * dw, az * dw)))
            if bname.startswith(("v17_mote_", "v17_ash_",
                                 "v16_mote_", "v16_ash_")):
                drift = (1.6 if style == "deterioro" else 0.9) * mult
                rise = drift * 1.8 if style == "deterioro" else -drift
                keyframes += [
                    kf("position", 0.0, 0, 0, 0, f"{aname}/{bname}/p0"),
                    kf("position", round(length * 0.5, 4),
                       drift, rise, 0, f"{aname}/{bname}/p1"),
                    kf("position", length, 0, 0, 0, f"{aname}/{bname}/p2"),
                ]
            if bname.startswith(("v17_mote_", "v17_ash_",
                                 "v16_mote_", "v16_ash_")):
                # PARPADEO: las motas cambian de tamano, no solo giran.
                blink = 0.42 if style == "deterioro" else 0.24
                keyframes += [
                    kf("scale", 0.0, 1, 1, 1, f"{aname}/{bname}/b0"),
                    kf("scale", round(length * 0.5, 4),
                       1 + blink, 1 + blink, 1 + blink,
                       f"{aname}/{bname}/b1"),
                    kf("scale", length, 1, 1, 1, f"{aname}/{bname}/b2"),
                ]
            if (bname.startswith("v17_ribbon_") and bname[-4:-1] == "seg"
                    and bname[-1] in "456"):
                # TIRON POR TRAMO: la gravedad baja por la tela en vez de
                # actuar solo en la punta. La amplitud crece con el segmento.
                seg = int(bname[-1])
                pull = 0.055 * seg * mult
                keyframes += [
                    kf("position", 0.0, 0, 0, 0, f"{aname}/{bname}/t0"),
                    kf("position", round(length * 0.5, 4),
                       0, -pull, 0, f"{aname}/{bname}/t1"),
                    kf("position", length, 0, 0, 0, f"{aname}/{bname}/t2"),
                ]
            if bname.startswith(("v17_cowl_", "v17_yoke_",
                                 "v16_collar_", "v16_yoke_")):
                # RESPIRACION: la bufanda se hincha y se relaja con un
                # periodo LENTO y distinto del ondeo de los jirones.
                breath = 0.045 if style == "deterioro" else 0.022
                keyframes += [
                    kf("scale", 0.0, 1, 1, 1, f"{aname}/{bname}/h0"),
                    kf("scale", round(length * 0.5, 4),
                       1 + breath, 1 + breath * 0.55, 1 + breath * 0.3,
                       f"{aname}/{bname}/h1"),
                    kf("scale", length, 1, 1, 1, f"{aname}/{bname}/h2"),
                ]
            if bname.startswith(("v17_vein_", "v16_vein_")):
                pulse = 0.34 if style == "deterioro" else 0.18
                keyframes += [
                    kf("scale", 0.0, 1, 1, 1, f"{aname}/{bname}/s0"),
                    kf("scale", round(length * 0.5, 4),
                       1 + pulse, 1 + pulse, 1, f"{aname}/{bname}/s1"),
                    kf("scale", length, 1, 1, 1, f"{aname}/{bname}/s2"),
                ]
            animators[guuid] = {
                "name": bname,
                "type": "bone",
                "keyframes": keyframes,
            }
        # EffectAnimator: Blockbench usa la clave literal 'effects' y
        # canales 'particle'/'sound'/'timeline' con data_points de efecto.
        # EffectAnimator en los CUATRO clips. Dos emisores Snowstorm:
        # brasas vivas al correr / deteriorarse y un rescoldo tenue en
        # reposo y al caminar. Blockbench usa la clave literal 'effects'.
        times = {
            "idle": [0.0, length * 0.5],
            "caminar": [0.0, length * 0.5],
            "correr": [0.0, length * 0.5],
            "deterioro": [0.0, length * 0.25, length * 0.5, length * 0.75],
        }[style]
        hot = style in ("correr", "deterioro")
        effect_id = ("capatest:capa_embers" if hot
                     else "capatest:capa_embers_calm")
        effect_file = ("particles/capa_embers.json" if hot
                       else "particles/capa_embers_calm.json")
        fx = []
        for j, tt in enumerate(times):
            # v1224: en `deterioro` se alternan brasas y ESQUIRLAS, para
            # que el clip tenga su propio efecto y no sea una copia de correr.
            if style == "deterioro" and j % 2 == 1:
                eid, efile = "capatest:capa_shards", "particles/capa_shards.json"
            else:
                eid, efile = effect_id, effect_file
            fx.append(kf("particle", round(tt, 4), 0, 0, 0,
                         f"{aname}/effects/e{j}", interp="step",
                         effect={"effect": eid, "locator": "",
                                 "script": "", "file": efile,
                                 "bind_to_actor": True}))
        animators["effects"] = {
            "name": "Effects", "type": "effect", "keyframes": fx,
        }
        marker_names = {
            "idle": ["inhalar", "exhalar"],
            "caminar": ["paso_izquierdo", "paso_derecho"],
            "correr": ["brasas_1", "brasas_2"],
            "deterioro": ["brasas_1", "brasas_2", "brasas_3", "brasas_4"],
        }[style]
        markers = [{"color": -1, "time": round(tt, 4), "name": nm}
                   for tt, nm in zip(times, marker_names)]
        out.append({
            "uuid": uid(f"animation/{aname}"),
            "name": aname,
            "markers": markers,
            "loop": loop,
            "override": False,
            "length": length,
            "snapping": 24,
            "selected": False,
            "anim_time_update": "",
            "blend_weight": "",
            "start_delay": "",
            "loop_delay": "",
            "animators": animators,
        })
    return out


def build() -> dict:
    geo = json.loads(GEO.read_text())["minecraft:geometry"][0]
    # v1.17.2: el geo del mod conserva los 72 huesos PRISTINOS de la
    # armadura antigua (helmet, dedos, manos, arnes, broches) porque el
    # renderer Java los oculta con setHidden(true). Blockbench NO oculta
    # nada: al abrir el .bbmodel esos 126 cubos aparecian como CHATARRA
    # alrededor de la capa. El archivo de Blockbench exporta SOLO los
    # huesos de la capa nueva (v15_/v16_/v17_); el geo del mod no cambia.
    bones = geo["bones"]
    CAPE_BONES = ("v15_", "v16_", "v17_")

    elements, groups, node_by_name = [], [], {}
    anim_bones: list[tuple[str, str]] = []
    for b in bones:
        key = b["name"]
        kids = []
        # Los 72 huesos pristinos se mantienen como GRUPOS VACIOS: aportan
        # pivote y rotacion a la jerarquia (sin ellos el capuchon se
        # separaba del cuerpo) pero NO aportan cubos visibles.
        if key.startswith(CAPE_BONES):
            for ci, c in enumerate(b.get("cubes", [])):
                ek = f"{key}/cube/{ci}"
                elements.append(make_element(b, ci, c, ek))
                kids.append(uid(ek))
        gkey = key + "/group"
        node_by_name[key] = {"uuid": uid(gkey), "isOpen": False, "children": kids}
        groups.append(make_group(key, b.get("pivot") or [0, 0, 0],
                                 b.get("rotation") or [0, 0, 0],
                                 kids, gkey))
        if key.startswith(("v17_", "v16_")) or key.startswith(("v15_cloth_", "v15_hem_")):
            anim_bones.append((key, uid(gkey)))

    roots = []
    for b in bones:
        node = node_by_name[b["name"]]
        parent = b.get("parent")
        if parent and parent in node_by_name:
            node_by_name[parent]["children"].append(node)
        else:
            roots.append(node)

    # v1.17.2: NO se añade ningún maniquí. Blockbench debe mostrar la capa
    # y solamente la capa; los 340 cubos son los del geo del mod.

    texture = {
        "path": "", "name": "capa_deteriorer_evilsaiyan.png", "folder": "",
        "namespace": "", "id": "0", "width": 128, "height": 128,
        "uv_scale": [1, 1], "particle": False, "render_mode": "default",
        "visible": True, "enabled": True, "saved": True,
        "internal": True, "source": data_url(atlas_texture()),
    }

    return {
        "meta": {"format_version": "5.0", "model_format": "bedrock", "box_uv": False},
        "name": "capa_deteriorer_evilsaiyan_v1172",
        "model_identifier": "geometry.capa_deteriorer_evilsaiyan",
        "visible_box": [1, 1, 1],
        "resolution": {"width": 128, "height": 128},
        "elements": elements,
        "groups": groups,
        "outliner": roots,
        "textures": [texture],
        "animations": build_animations(anim_bones),
    }


def main() -> None:
    model = build()
    text = json.dumps(model, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(text)

    uuid_re = __import__("re").compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    ids = {e["uuid"] for e in model["elements"]}
    gids = {g["uuid"] for g in model["groups"]}
    assert len(ids) == len(model["elements"]) and len(gids) == len(model["groups"])
    assert all(uuid_re.match(u) for u in list(ids) + list(gids)), "uuid no canónico"
    assert all(n["uuid"] in gids for n in model["outliner"])
    assert len(model["textures"]) == 1 and model["textures"][0]["source"].startswith(
        "data:image/png;base64,")
    import re as _re
    _raw = base64.b64decode(model["textures"][0]["source"].split(",", 1)[1])
    _im = Image.open(io.BytesIO(_raw))
    assert _im.size == (128, 128), ("textura del .bbmodel", _im.size)
    assert model["resolution"] == {"width": 128, "height": 128}
    assert len(model["elements"]) == 214, len(model["elements"])
    assert not any(e["name"] in ("head", "torso", "arm_L", "arm_R", "leg_L", "leg_R")
                   for e in model["elements"]), "vuelve el maniquí"
    assert not any("Steve/Alex" in g["name"] for g in model["groups"])
    _visible = {e["uuid"] for e in model["elements"]}
    assert all(not ({c for c in g["children"] if isinstance(c, str)} & _visible)
               or g["name"].startswith(("v15_", "v16_", "v17_"))
               for g in model["groups"]), "un grupo viejo tiene cubos visibles"
    for e in model["elements"]:
        for f in e["faces"].values():
            assert max(f["uv"]) <= 128, (e["name"], f["uv"])
    anims = model["animations"]
    assert len(anims) == 4, len(anims)
    total = 0
    for a in anims:
        assert uuid_re.match(a["uuid"]), a["name"]
        assert a["loop"] == "loop" and a["length"] > 0
        for guuid, an in a["animators"].items():
            if guuid == "effects":
                assert an["keyframes"]
            else:
                assert uuid_re.match(guuid) and guuid in gids, (a["name"], guuid)
                assert an["type"] == "bone" and an["keyframes"]
            for k in an["keyframes"]:
                assert uuid_re.match(k["uuid"])
                assert k["channel"] in ("rotation", "position", "scale",
                                        "particle", "sound", "timeline")
                assert k["data_points"]
            total += len(an["keyframes"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(model['elements'])} cubos, "
          f"{len(model['groups'])} grupos, {len(anims)} animaciones, "
          f"{total} keyframes, {len(text)} bytes")
    print(f"  copia en {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
