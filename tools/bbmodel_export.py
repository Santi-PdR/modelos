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

rev. B: se ELIMINAN las motas/ceniza 3D, el animador `effects` de
Bedrock (referenciaba JSONs de partículas que Blockbench no encuentra)
y las cuatro ondas distintas. Ahora `tools/cape_motion.py` es la única
curva: retardo real por tramo, vaivén de paso, barrido al correr y
estremecimiento, todo con tangentes Bézier C1.

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

import cape_motion as M

ROOT = Path(__file__).resolve().parents[1]

def mod_version() -> str:
    """La versión del .bbmodel sale de gradle.properties, NO se hardcodea.

    v1.20.0: el usuario señaló que el archivo seguía llamándose
    `CAPA_v1.17.0.bbmodel` aunque el mod ya era v1.19.0. Ahora el
    nombre del archivo, el `name` interno de Blockbench y el asset de
    la Release cambian SOLOS con cada subida de versión.
    """
    for line in (ROOT / "gradle.properties").read_text().splitlines():
        if line.startswith("mod_version="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("falta mod_version en gradle.properties")

VER = mod_version()
VER_TAG = VER.replace(".", "_")
BB_NAME = f"CAPA_v{VER}.bbmodel"

GEO = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"
ATLAS = ROOT / "src/main/resources/assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png"
OUT = ROOT / "preview/assets/capa_deteriorer_evilsaiyan.bbmodel"
DOC = ROOT / "docs" / BB_NAME     # ej. docs/CAPA_v1.21.0.bbmodel

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


def kf(channel: str, t: float, values, key: str,
       derivative, length: float) -> dict:
    """Keyframe Bézier con tangentes de la DERIVADA ANALÍTICA.

    El mango dura un tercio del intervalo entre muestras: antes era 0.30 s
    fijo, que en el clip de 0.8 s se metía dentro de cuatro keyframes
    vecinos y producía rebotes. Con `dt = intervalo/3` la curva es C1 y
    no invade el tramo siguiente.
    """
    vals = [round(float(v), 4) for v in values]
    dt = length / M.WAVE_SAMPLES / 3.0
    slope = [round(float(d) / length * dt, 5) for d in derivative]
    return {
        "channel": channel,
        "data_points": [{"x": str(vals[0]), "y": str(vals[1]),
                         "z": str(vals[2])}],
        "uuid": uid(key),
        "time": round(t, 4),
        "color": -1,
        "interpolation": "bezier",
        "bezier_linked": False,
        "bezier_left_time": [round(-dt, 5)] * 3,
        "bezier_left_value": [-v for v in slope],
        "bezier_right_time": [round(dt, 5)] * 3,
        "bezier_right_value": slope,
    }


# Cada clip arranca con fase distinta y tiene su propio carácter en
# `cape_motion.STYLES`. Ya NO hay pista `effects`: las partículas son
# runtime (`CapaDeteriorerItem.spawnAura`), no geometría ni keyframes.
ANIMATION_SPECS = (
    ("idle_respiracion", "idle"),
    ("caminar", "caminar"),
    ("correr", "correr"),
    ("volar_elytra", "volar"),
    ("caida_libre", "caer"),
    ("agacharse", "agachado"),
    ("agua_flotar", "agua"),
    ("deterioro_tela", "deterioro"),
)
MARKERS = {
    "idle": ("inhalar", "exhalar"),
    "caminar": ("paso_izquierdo", "paso_derecho"),
    "correr": ("impulso", "recogida"),
    "volar": ("extension", "aleteo"),
    "caer": ("ascenso", "estela"),
    "agachado": ("recogida", "reposo"),
    "agua": ("deriva", "flote"),
    "deterioro": ("estremecimiento_1", "estremecimiento_2",
                  "estremecimiento_3", "estremecimiento_4"),
}
MARKER_TIMES = {"idle": (0.0, 0.5), "caminar": (0.0, 0.5),
                "correr": (0.0, 0.5), "volar": (0.0, 0.5),
                "caer": (0.0, 0.5), "agachado": (0.0, 0.5),
                "agua": (0.0, 0.5),
                "deterioro": (0.0, 0.25, 0.5, 0.75)}


def build_animations(anim_bones: list[tuple[str, str]]) -> list[dict]:
    """8 clips (uno por estado) con rotación, posición y escala C1."""
    out = []
    for aname, style in ANIMATION_SPECS:
        length = M.STYLES[style]["length"]
        animators = {}
        for bname, guuid in anim_bones:
            keyframes = []
            for j in range(M.WAVE_SAMPLES + 1):
                f = j / M.WAVE_SAMPLES
                t = round(length * f, 4)
                pose = M.sample(bname, style, f)
                keyframes.append(kf("rotation", t, pose["rot"],
                                    f"{aname}/{bname}/r{j}",
                                    pose["drot"], length))
                if pose["has_pos"]:
                    keyframes.append(kf("position", t, pose["pos"],
                                        f"{aname}/{bname}/p{j}",
                                        pose["dpos"], length))
                if pose["has_scale"]:
                    keyframes.append(kf("scale", t, pose["scale"],
                                        f"{aname}/{bname}/s{j}",
                                        pose["dscale"], length))
            animators[guuid] = {"name": bname, "type": "bone",
                                "keyframes": keyframes}
        times = MARKER_TIMES[style]
        markers = [{"color": -1, "time": round(length * t, 4), "name": nm}
                   for t, nm in zip(times, MARKERS[style])]
        out.append({
            "uuid": uid(f"animation/{aname}"),
            "name": aname,
            "markers": markers,
            "loop": "loop",
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
    CAPE_BONES = ("v15_", "v16_", "v17_", "v18_")

    elements, groups, node_by_name = [], [], {}
    anim_bones: list[tuple[str, str]] = []
    for b in bones:
        key = b["name"]
        kids = []
        # Los 72 huesos pristinos se mantienen como GRUPOS VACIOS: aportan
        # pivote y rotacion a la jerarquia (sin ellos el capuchon se
        # separaba del cuerpo) pero NO aportan cubos visibles.
        if key.startswith(CAPE_BONES) and not key.startswith(
                ("v17_mote_", "v17_ash_", "v16_mote_", "v16_ash_")):
            for ci, c in enumerate(b.get("cubes", [])):
                ek = f"{key}/cube/{ci}"
                elements.append(make_element(b, ci, c, ek))
                kids.append(uid(ek))
        gkey = key + "/group"
        node_by_name[key] = {"uuid": uid(gkey), "isOpen": False, "children": kids}
        groups.append(make_group(key, b.get("pivot") or [0, 0, 0],
                                 b.get("rotation") or [0, 0, 0],
                                 kids, gkey))
        if key.startswith(("v17_", "v16_", "v18_")) or key.startswith(("v15_cloth_", "v15_hem_")):
            anim_bones.append((key, uid(gkey)))

    roots = []
    for b in bones:
        node = node_by_name[b["name"]]
        parent = b.get("parent")
        if parent and parent in node_by_name:
            node_by_name[parent]["children"].append(node)
        else:
            roots.append(node)

    # rev. B: NO se añade maniquí, ni motas/ceniza 3D, ni animador de
    # efectos. Blockbench muestra SOLO tela y NO busca archivos externos:
    # la única textura está embebida y las partículas son runtime.

    texture = {
        "path": "", "name": "capa_deteriorer_evilsaiyan.png", "folder": "",
        "namespace": "", "id": "0", "width": 128, "height": 128,
        "uv_scale": [1, 1], "particle": False, "render_mode": "default",
        "visible": True, "enabled": True, "saved": True,
        "internal": True, "source": data_url(atlas_texture()),
    }

    return {
        "meta": {"format_version": "5.0", "model_format": "bedrock", "box_uv": False},
        "name": f"capa_deteriorer_evilsaiyan_v{VER_TAG}",
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
    assert model["name"] == f"capa_deteriorer_evilsaiyan_v{VER_TAG}", model["name"]
    import re as _re
    _raw = base64.b64decode(model["textures"][0]["source"].split(",", 1)[1])
    _im = Image.open(io.BytesIO(_raw))
    assert _im.size == (128, 128), ("textura del .bbmodel", _im.size)
    assert model["resolution"] == {"width": 128, "height": 128}
    assert len(model["elements"]) == 150, len(model["elements"])
    assert not any(e["name"].startswith(("v17_mote_", "v17_ash_",
                                       "v16_mote_", "v16_ash_"))
                   for e in model["elements"]), "vuelven las motas 3D"
    assert not any(e["name"] in ("head", "torso", "arm_L", "arm_R", "leg_L", "leg_R")
                   for e in model["elements"]), "vuelve el maniquí"
    assert not any("Steve/Alex" in g["name"] for g in model["groups"])
    _visible = {e["uuid"] for e in model["elements"]}
    assert all(not ({c for c in g["children"] if isinstance(c, str)} & _visible)
               or g["name"].startswith(("v15_", "v16_", "v17_", "v18_"))
               for g in model["groups"]), "un grupo viejo tiene cubos visibles"
    for e in model["elements"]:
        for f in e["faces"].values():
            assert max(f["uv"]) <= 128, (e["name"], f["uv"])
    anims = model["animations"]
    assert len(anims) == 8, len(anims)
    total = 0
    for a in anims:
        assert uuid_re.match(a["uuid"]), a["name"]
        assert a["loop"] == "loop" and a["length"] > 0
        assert "effects" not in a["animators"], "Blockbench busca JSONs que no existen"
        assert len(a["markers"]) >= 2
        for guuid, an in a["animators"].items():
            assert uuid_re.match(guuid) and guuid in gids, (a["name"], guuid)
            assert an["type"] == "bone" and an["keyframes"]
            for k in an["keyframes"]:
                assert uuid_re.match(k["uuid"])
                assert k["channel"] in ("rotation", "position", "scale")
                assert k["interpolation"] == "bezier"
                assert k["data_points"]
                assert all(abs(x + y) < 0.002 for x, y in zip(
                    k["bezier_left_value"], k["bezier_right_value"]))
            total += len(an["keyframes"])
    # Ojo: el flag `"particle": false` de la textura SÍ es legítimo (es un
    # campo de Blockbench). Lo que no puede aparecer es un canal de efectos
    # ni una ruta a JSONs externos que Blockbench intente resolver al abrir.
    assert '"channel":"particle"' not in text and '"effects"' not in text \
        and 'particles/' not in text, \
        "el .bbmodel no puede referenciar partículas externas"
    assert total >= 11000, total
    print(f"wrote {OUT.relative_to(ROOT)}: {len(model['elements'])} cubos, "
          f"{len(model['groups'])} grupos, {len(anims)} animaciones, "
          f"{total} keyframes, {len(text)} bytes")
    print(f"  copia en {DOC.relative_to(ROOT)} (version {VER})")


if __name__ == "__main__":
    main()
