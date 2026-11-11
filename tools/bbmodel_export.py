#!/usr/bin/env python3
"""Exporta el .geo.json de la capa a un proyecto .bbmodel de Blockbench.

El visor web (preview/) es cómodo para girar el modelo, pero el usuario
trabaja en Blockbench: este script genera un proyecto REAL con

  * la jerarquía completa de huesos (grupos con pivot/rotación),
  * un elemento por cubo con `from`/`to`, `inflate` y UV POR CARA,
  * el atlas 128x128 incrustado como data URL,
  * un grupo "PLAYER · Steve/Alex (referencia)" con el maniquí a escala
    para juzgar cómo el collar envuelve cuello y hombros.

Detalles de formato (verificados contra el código de Blockbench):

* `bedrock.js:parseCube()` calcula `from[0] = -(origin[0] + size[0])` y
  niega los ejes X e Y de la rotación; `parseBone()` hace lo mismo con el
  pivot y la rotación del hueso. La rotación del HUESO va en el grupo y la
  rotación PROPIA del cubo (61 detalles boxy la tienen) va en el elemento:
  ponerla en ambos sitios la aplicaría dos veces.
* `bedrock` es `single_texture: true`: `Cube.init()` fuerza la textura por
  defecto en TODAS las caras. Por eso el .bbmodel lleva UNA sola textura de
  128x144: las 128 primeras filas son el atlas del mod (intacto) y las 16
  últimas son un parche sólido reservado para el maniquí. Ningún UV de la
  capa pasa de v=128, así que el parche no pisa ninguna cara del modelo.
* `bedrock.js:parseCube()` invierte las esquinas UV de `up`/`down`; se
  replica aquí para que el .bbmodel muestre la misma orientación.

Uso:  python3 tools/bbmodel_export.py
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"
ATLAS = ROOT / "src/main/resources/assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png"
OUT = ROOT / "preview/assets/capa_deteriorer_evilsaiyan.bbmodel"
DOC = ROOT / "docs/capa_v1140.bbmodel"

FACES = ("north", "south", "east", "west", "up", "down")
PLAYER_V = 128  # fila donde empieza el parche del maniquí


def uid(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()


def data_url(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def neg_xy(vec) -> list:
    """Bedrock -> Blockbench: se niegan X e Y, no Z."""
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


def combined_texture() -> Image.Image:
    """Atlas del mod + parche sólido para el maniquí, en una sola textura."""
    atlas = Image.open(ATLAS).convert("RGBA")
    assert atlas.size == (128, 128), atlas.size
    im = Image.new("RGBA", (128, 144), (0, 0, 0, 0))
    im.paste(atlas, (0, 0))
    for x in range(16):
        for y in range(16):
            # 8 px gris claro (cabeza) + 8 px violeta (cuerpo).
            im.putpixel((x, PLAYER_V + y),
                        (216, 214, 222, 255) if x < 8 else (66, 48, 86, 255))
    return im


def make_element(bone: dict, ci: int, cube: dict, key: str) -> dict:
    o, sz = cube["origin"], cube["size"]
    x, y, z = -(o[0] + sz[0]), o[1], o[2]
    f = [round(v, 4) for v in (x, y, z)]
    t = [round(v, 4) for v in (x + sz[0], y + sz[1], z + sz[2])]
    # La rotación del hueso NO se repite aquí: va en el grupo.
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
        "name": f"{bone['name']}_{ci}",
        "type": "cube",
        "uuid": uid(key),
        "from": f,
        "to": t,
        "origin": origin,
        "rotation": rot,
        "inflate": round(float(cube.get("inflate", 0.0)), 4),
        "autouv": 0,
        "color": 0,
        "visibility": True,
        "faces": faces,
        "box_uv": False,
    }


def make_group(name: str, pivot, rotation, children, key: str,
               is_open: bool = False) -> dict:
    p = list(pivot or [0, 0, 0])
    return {
        "name": name,
        "uuid": uid(key),
        "origin": [round(-p[0], 4), round(p[1], 4), round(p[2], 4)],
        "rotation": neg_xy(rotation),
        "visibility": True,
        "isOpen": is_open,
        "shade": True,
        "export": True,
        "locked": False,
        "autouv": 0,
        "children": children,
    }


def build() -> dict:
    geo = json.loads(GEO.read_text())["minecraft:geometry"][0]
    bones = geo["bones"]

    elements, groups, node_by_name = [], [], {}
    for b in bones:
        key = b["name"]
        kids = []
        for ci, c in enumerate(b.get("cubes", [])):
            ek = f"{key}/cube/{ci}"
            elements.append(make_element(b, ci, c, ek))
            kids.append(uid(ek))
        node_by_name[key] = {"uuid": uid(key + "/group"),
                            "isOpen": False, "children": kids}
        groups.append(make_group(key, b.get("pivot", [0, 0, 0]) or [0, 0, 0],
                                 b.get("rotation", [0, 0, 0]) or [0, 0, 0],
                                 kids, key + "/group"))

    # Árbol: cada grupo con padre se cuelga del nodo de su padre.
    roots = []
    for b in bones:
        node = node_by_name[b["name"]]
        parent = b.get("parent")
        if parent and parent in node_by_name:
            node_by_name[parent]["children"].append(node)
        else:
            roots.append(node)

    # ---- Maniquí Steve/Alex (sólo referencia, no runtime) ----------------
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
                             [0, 0, 0], pkids, pgkey, is_open=False))
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
        "name": "capa_deteriorer_evilsaiyan_v1140",
        "model_identifier": "geometry.capa_deteriorer_evilsaiyan",
        "visible_box": [1, 1, 1],
        "resolution": {"width": 128, "height": 144},
        "elements": elements,
        "groups": groups,
        "outliner": roots,
        "textures": [texture],
        "animations": [],
    }


def main() -> None:
    model = build()
    text = json.dumps(model, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(text)

    # Validación estructural.
    ids = {e["uuid"] for e in model["elements"]}
    gids = {g["uuid"] for g in model["groups"]}
    assert len(ids) == len(model["elements"]), "uuid de elemento duplicado"
    assert len(gids) == len(model["groups"]), "uuid de grupo duplicado"
    assert all(n["uuid"] in gids for n in model["outliner"]), "raíz sin grupo"
    assert len(model["textures"]) == 1 and model["textures"][0]["source"].startswith(
        "data:image/png;base64,")
    assert model["resolution"] == {"width": 128, "height": 144}
    # Ningún UV de la capa pisa el parche del maniquí.
    player_names = {"head", "torso", "arm_L", "arm_R", "leg_L", "leg_R"}
    for e in model["elements"]:
        if e["name"] in player_names:
            continue
        for face in e["faces"].values():
            assert face["uv"][3] <= 128 and face["uv"][1] <= 128, e["name"]
    # La rotación del hueso vive en el grupo, NO duplicada en cada cubo.
    geo = json.loads(GEO.read_text())["minecraft:geometry"][0]
    for b in geo["bones"]:
        if any(b.get("rotation") or [0, 0, 0]) and b.get("cubes"):
            g = next(x for x in model["groups"] if x["name"] == b["name"])
            assert g["rotation"] == neg_xy(b["rotation"]), b["name"]
            break
    print(f"wrote {OUT.relative_to(ROOT)}: {len(model['elements'])} cubos, "
          f"{len(model['groups'])} grupos, {len(text)} bytes")
    print(f"  copia en {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
