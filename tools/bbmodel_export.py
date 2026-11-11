#!/usr/bin/env python3
"""Exporta el .geo.json de la capa a un proyecto .bbmodel de Blockbench.

v1.15.0: corrige DOS defectos graves de la entrega anterior.

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

Además el maniquí Steve/Alex deja de ser un cubo blanco: lleva una textura
16x16 con cara, pelo y túnica, incrustada en la MISMA textura del atlas
(formato `bedrock` = `single_texture: true`, una sola imagen 128x144).

Uso:  python3 tools/bbmodel_export.py
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"
ATLAS = ROOT / "src/main/resources/assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png"
OUT = ROOT / "preview/assets/capa_deteriorer_evilsaiyan.bbmodel"
DOC = ROOT / "docs/capa_v1150.bbmodel"

FACES = ("north", "south", "east", "west", "up", "down")
PLAYER_V = 128


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


def player_patch() -> Image.Image:
    """Textura 16x16 del maniquí: cabeza con cara (x 0-7) y túnica (x 8-15)."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Cabeza: piel pálida con pelo gris y sombreado a pixeles.
    d.rectangle([0, 0, 7, 7], fill=(214, 211, 221, 255))
    d.rectangle([0, 0, 7, 1], fill=(150, 147, 163, 255))
    d.rectangle([0, 2, 7, 2], fill=(176, 172, 188, 255))
    d.point((1, 0), fill=(126, 123, 140, 255))
    d.point((5, 1), fill=(126, 123, 140, 255))
    d.point((3, 0), fill=(236, 233, 242, 255))
    # Ojos, cejas y boca.
    d.rectangle([1, 3, 2, 3], fill=(38, 34, 52, 255))
    d.rectangle([5, 3, 6, 3], fill=(38, 34, 52, 255))
    d.point((2, 3), fill=(92, 122, 176, 255))
    d.point((5, 3), fill=(92, 122, 176, 255))
    d.rectangle([1, 4, 2, 4], fill=(188, 184, 198, 255))
    d.rectangle([5, 4, 6, 4], fill=(188, 184, 198, 255))
    d.rectangle([3, 5, 4, 5], fill=(128, 96, 112, 255))
    d.point((0, 6), fill=(186, 182, 196, 255))
    d.point((7, 6), fill=(186, 182, 196, 255))
    # Túnica: violeta oscuro con cuello dorado y hombros (eco de la foto).
    d.rectangle([8, 0, 15, 15], fill=(58, 38, 78, 255))
    d.rectangle([8, 0, 15, 1], fill=(176, 128, 58, 255))
    d.rectangle([8, 2, 15, 3], fill=(78, 50, 96, 255))
    d.rectangle([8, 6, 9, 15], fill=(72, 46, 92, 255))
    d.rectangle([14, 6, 15, 15], fill=(42, 28, 62, 255))
    d.rectangle([10, 7, 13, 7], fill=(120, 30, 96, 255))
    d.point((11, 10), fill=(150, 40, 116, 255))
    d.point((12, 12), fill=(150, 40, 116, 255))
    return im


def combined_texture() -> Image.Image:
    atlas = Image.open(ATLAS).convert("RGBA")
    assert atlas.size == (128, 128), atlas.size
    im = Image.new("RGBA", (128, 144), (0, 0, 0, 0))
    im.paste(atlas, (0, 0))
    im.paste(player_patch(), (0, PLAYER_V))
    return im


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


def kf(channel: str, t: float, x: float, y: float, z: float, key: str) -> dict:
    """Keyframe de Blockbench. Los valores de molang se guardan como texto."""
    return {
        "channel": channel,
        "data_points": [{"x": str(round(x, 3)), "y": str(round(y, 3)),
                         "z": str(round(z, 3))}],
        "uuid": uid(key),
        "time": round(t, 4),
        "color": -1,
        "interpolation": "linear",
        "bezier_linked": True,
        "bezier_left_time": [-0.1, -0.1, -0.1],
        "bezier_left_value": [0, 0, 0],
        "bezier_right_time": [0.1, 0.1, 0.1],
        "bezier_right_value": [0, 0, 0],
    }


def motion_for(name: str, idx: int, style: str) -> tuple[float, float, float, float]:
    """Amplitud (grados) por familia y estilo de animación."""
    phase = idx * 0.37
    if name.startswith(("v16_mote_", "v16_ash_")):
        a = 14.0 if style == "correr" else (10.0 if style == "caminar" else 7.0)
        return (a, a * 0.7, a * 0.5, phase)
    if name.startswith("v16_collar_") or name.startswith("v16_yoke_"):
        a = 3.2 if style == "correr" else (2.2 if style == "caminar" else 1.6)
        return (a, 0.0, a * 0.6, phase * 0.4)
    if name.startswith("v16_vein_"):
        a = 6.0 if style == "correr" else 3.5
        return (0.0, 0.0, a, phase * 2.0)
    if name.startswith(("v16_fray_", "v16_hem_", "v16_shred_")):
        a = 11.0 if style == "correr" else (7.0 if style == "caminar" else 4.0)
        return (a * 0.5, 0.0, a, phase)
    if name.startswith("v16_tatter_"):
        a = 9.0 if style == "correr" else (6.0 if style == "caminar" else 3.5)
        return (a * 0.45, a * 0.30, a, phase)
    # v15_cloth_* / v15_hem_*: onda del paño con retardo por columna.
    a = 5.0 if style == "correr" else (3.2 if style == "caminar" else 1.8)
    return (a * 0.5, 0.0, a, phase * 0.8)


ANIMATION_SPECS = (
    ("idle_respiracion", "loop", 4.0, "idle", 1.0),
    ("caminar", "loop", 1.2, "caminar", 1.0),
    ("correr_saltar", "loop", 0.8, "correr", 1.0),
    ("deterioro_particulas", "loop", 3.0, "deterioro", 1.35),
)


def build_animations(anim_bones: list[tuple[str, str]]) -> list[dict]:
    """Un animador por hueso, 5 keyframes en bucle para cada animación."""
    out = []
    for aname, loop, length, style, mult in ANIMATION_SPECS:
        animators = {}
        for idx, (bname, guuid) in enumerate(anim_bones):
            ax, ay, az, phase = motion_for(bname, idx, style)
            ax, ay, az = ax * mult, ay * mult, az * mult
            keyframes = [
                kf("rotation", 0.0, 0, 0, 0, f"{aname}/{bname}/0"),
                kf("rotation", length * 0.25, ax, ay, az, f"{aname}/{bname}/1"),
                kf("rotation", length * 0.50, 0, 0, 0, f"{aname}/{bname}/2"),
                kf("rotation", length * 0.75, -ax, -ay, -az, f"{aname}/{bname}/3"),
                kf("rotation", length, 0, 0, 0, f"{aname}/{bname}/4"),
            ]
            if bname.startswith(("v16_mote_", "v16_ash_")):
                drift = 0.9 * mult
                keyframes += [
                    kf("position", 0.0, 0, 0, 0, f"{aname}/{bname}/p0"),
                    kf("position", length * 0.5, drift, -drift, 0, f"{aname}/{bname}/p1"),
                    kf("position", length, 0, 0, 0, f"{aname}/{bname}/p2"),
                ]
            animators[guuid] = {
                "name": bname,
                "type": "bone",
                "keyframes": keyframes,
            }
        out.append({
            "uuid": uid(f"animation/{aname}"),
            "name": aname,
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
    bones = geo["bones"]

    elements, groups, node_by_name = [], [], {}
    anim_bones: list[tuple[str, str]] = []
    for b in bones:
        key = b["name"]
        kids = []
        for ci, c in enumerate(b.get("cubes", [])):
            ek = f"{key}/cube/{ci}"
            elements.append(make_element(b, ci, c, ek))
            kids.append(uid(ek))
        gkey = key + "/group"
        node_by_name[key] = {"uuid": uid(gkey), "isOpen": False, "children": kids}
        groups.append(make_group(key, b.get("pivot") or [0, 0, 0],
                                 b.get("rotation") or [0, 0, 0],
                                 kids, gkey))
        if key.startswith("v16_") or key.startswith(("v15_cloth_", "v15_hem_")):
            anim_bones.append((key, uid(gkey)))

    roots = []
    for b in bones:
        node = node_by_name[b["name"]]
        parent = b.get("parent")
        if parent and parent in node_by_name:
            node_by_name[parent]["children"].append(node)
        else:
            roots.append(node)

    player_parts = [
        ("head",  [-4, 24, -4, 8, 8, 8],  [0, PLAYER_V, 8, PLAYER_V + 8]),
        ("torso", [-4, 12, -2, 8, 12, 4], [8, PLAYER_V, 16, PLAYER_V + 8]),
        ("arm_L", [-8, 12, -2, 4, 12, 4], [8, PLAYER_V, 16, PLAYER_V + 8]),
        ("arm_R", [ 4, 12, -2, 4, 12, 4], [8, PLAYER_V, 16, PLAYER_V + 8]),
        ("leg_L", [-4,  0, -2, 4, 12, 4], [8, PLAYER_V, 16, PLAYER_V + 8]),
        ("leg_R", [ 0,  0, -2, 4, 12, 4], [8, PLAYER_V, 16, PLAYER_V + 8]),
    ]
    pkids = []
    for name, (x0, y0, z0, w, h, d), uv in player_parts:
        ek = f"player/{name}"
        elements.append({
            "name": name, "type": "cube", "uuid": uid(ek),
            "from": [x0, y0, z0], "to": [x0 + w, y0 + h, z0 + d],
            "origin": [x0 + w / 2, y0 + h / 2, z0 + d / 2],
            "rotation": [0, 0, 0], "inflate": 0.0, "autouv": 0,
            "color": 0, "visibility": True, "box_uv": False,
            "faces": {fn: {"uv": list(uv), "texture": 0} for fn in FACES},
        })
        pkids.append(uid(ek))
    pgkey = "player/group"
    groups.append(make_group("PLAYER · Steve/Alex (referencia)", [0, 0, 0],
                             [0, 0, 0], pkids, pgkey))
    roots.append({"uuid": uid(pgkey), "isOpen": False, "children": pkids})

    texture = {
        "path": "", "name": "capa_deteriorer_evilsaiyan.png", "folder": "",
        "namespace": "", "id": "0", "width": 128, "height": 144,
        "uv_scale": [1, 1], "particle": False, "render_mode": "default",
        "visible": True, "enabled": True, "saved": True,
        "internal": True, "source": data_url(combined_texture()),
    }

    return {
        "meta": {"format_version": "5.0", "model_format": "bedrock", "box_uv": False},
        "name": "capa_deteriorer_evilsaiyan_v1150",
        "model_identifier": "geometry.capa_deteriorer_evilsaiyan",
        "visible_box": [1, 1, 1],
        "resolution": {"width": 128, "height": 144},
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
    anims = model["animations"]
    assert len(anims) == 4, len(anims)
    total = 0
    for a in anims:
        assert uuid_re.match(a["uuid"]), a["name"]
        assert a["loop"] == "loop" and a["length"] > 0
        for guuid, an in a["animators"].items():
            assert uuid_re.match(guuid) and guuid in gids, (a["name"], guuid)
            assert an["type"] == "bone" and an["keyframes"]
            for k in an["keyframes"]:
                assert uuid_re.match(k["uuid"])
                assert k["channel"] in ("rotation", "position")
                assert k["data_points"] and len(k["data_points"][0]) == 3
            total += len(an["keyframes"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(model['elements'])} cubos, "
          f"{len(model['groups'])} grupos, {len(anims)} animaciones, "
          f"{total} keyframes, {len(text)} bytes")
    print(f"  copia en {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
