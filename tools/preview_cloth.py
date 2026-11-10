#!/usr/bin/env python3
"""Previsualización software (aproximada) de la capa. NO es una captura in-game.

Uso:
    python -m pip install Pillow numpy
    python tools/preview_cloth.py --out /tmp/capa_preview

Genera vistas del item plegado, la capa equipada (frente/3-4/espalda), la
superficie de tela aislada, el canvas 96x48 y el detalle original que queda
visible. Sirve para detectar cortes de UV, costuras y silueta boxy sin abrir
Minecraft. El sombreado y la orientación de caras son aproximaciones.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/main/resources/assets/capatest"
ARMOR_GEO = ASSETS / "geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"
FOLDED_GEO = ASSETS / "geo/item/cape_folded.geo.json"
ARMOR_TEX = ASSETS / "textures/item/armor/capa_deteriorer_evilsaiyan.png"
FOLDED_TEX = ASSETS / "textures/item/cape_folded.png"

# Debe coincidir con CapaArmorModel.SECTIONS + HIDDEN_DETAILS.
SECTION_BONES = {"cape_top", "cape_mid", "cape_bottom"}
HIDDEN_DETAILS = {
    "arnes_frontal", "collar_dentado", "yugo",
    "espina_0", "espina_1", "espina_2",
    "mano_hombro_R", "dedo_hR_0", "dedo_hR_1", "dedo_hR_2", "dedo_hR_3", "dedo_hR_4",
    "mano_hombro_L", "dedo_hL_0", "dedo_hL_1", "dedo_hL_2", "dedo_hL_3", "dedo_hL_4",
    "cristal_top_L", "flujo_violeta_0", "esquirla_0", "esquirla_1",
    "nucleo_sigilo", "mano_sigilo", "dedo_sigilo_0", "dedo_sigilo_1",
    "dedo_sigilo_2", "dedo_sigilo_3", "dedo_sigilo_4",
    "cinturon_oxidado", "lengueta", "colgajo_R", "colgajo_L",
    "cristal_mid_R", "cristal_mid_L", "flujo_violeta_1", "flujo_violeta_2",
    "esquirla_2", "esquirla_3",
    "jiron_0", "jiron_1", "jiron_2", "jiron_3", "jiron_4",
    "faldon_R", "faldon_R_tip", "faldon_L", "faldon_L_tip",
    "cristal_bot_R", "flujo_violeta_3", "flujo_violeta_4",
    "esquirla_4", "esquirla_5", "esquirla_6", "esquirla_7",
    "hombrera_der", "tira_der_0", "tira_der_1",
    "hombrera_izq", "tira_izq_0", "tira_izq_1",
}


def T(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def R(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4)
    if axis == "x":
        m[1:3, 1:3] = [[c, -s], [s, c]]
    elif axis == "y":
        m[0, 0] = m[2, 2] = c
        m[0, 2] = s
        m[2, 0] = -s
    else:
        m[0:2, 0:2] = [[c, -s], [s, c]]
    return m


def rotmat(r):
    return R("z", r[2]) @ R("y", -r[1]) @ R("x", -r[0])


def matrices(geo):
    by = {b["name"]: b for b in geo["bones"]}
    out = {}

    def calc(n):
        if n in out:
            return out[n]
        b = by[n]
        p = b.get("pivot", [0, 0, 0]) or [0, 0, 0]
        B = np.array([-p[0], p[1], p[2]], float)
        local = T(B) @ rotmat(b.get("rotation", [0, 0, 0]) or [0, 0, 0]) @ T(-B)
        out[n] = (calc(b["parent"]) if b.get("parent") else np.eye(4)) @ local
        return out[n]

    for n in by:
        calc(n)
    return out


CORNERS = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
FACE_ORDER = {"west": [7, 3, 0, 4], "east": [2, 6, 5, 1],
              "north": [3, 2, 1, 0], "south": [6, 7, 4, 5],
              "up": [7, 6, 2, 3], "down": [0, 1, 5, 4]}


def face_uv(s):
    u, v = s["uv"]
    w, h = s["uv_size"]
    return np.array([[u + w, v], [u, v], [u, v + h], [u + w, v + h]], float)


def collect(geo, hidden):
    mats = matrices(geo)
    faces = []
    for b in geo["bones"]:
        if b["name"] in hidden:
            continue
        M = mats[b["name"]]
        for c in b.get("cubes", []):
            o, sz = np.array(c["origin"], float), np.array(c["size"], float)
            O = np.array([-(o[0] + sz[0]), o[1], o[2]], float)
            cp = np.array(c.get("pivot", [0, 0, 0]) or [0, 0, 0], float)
            P = np.array([-cp[0], cp[1], cp[2]], float)
            M2 = M @ T(P) @ rotmat(c.get("rotation", [0, 0, 0]) or [0, 0, 0]) @ T(-P)
            V = O[None, :] + CORNERS * sz[None, :]
            VT = (M2 @ np.c_[V, np.ones(8)].T).T[:, :3]
            for name, idx in FACE_ORDER.items():
                spec = c["uv"].get(name)
                if spec:
                    faces.append((VT[idx], face_uv(spec), name))
    return faces


def render(geo, atlas_path, hidden, yaw=0, pitch=8, size=700, bg=(20, 16, 27)):
    faces = collect(geo, hidden)
    atlas = np.asarray(Image.open(atlas_path).convert("RGBA"))
    AH, AW = atlas.shape[:2]
    view = R("x", pitch) @ R("y", yaw)
    prepared, pts_all = [], []
    for pts, uvs, _ in faces:
        pv = (view @ np.c_[pts, np.ones(4)].T).T[:, :3]
        n = np.cross(pv[1] - pv[0], pv[2] - pv[0])
        ln = np.linalg.norm(n)
        shade = 0.45
        if ln > 1e-6:
            n /= ln
            light = np.array([-0.35, 0.65, 0.68])
            light /= np.linalg.norm(light)
            shade = 0.40 + 0.60 * abs(float(np.dot(n, light)))
        prepared.append((pv, uvs, shade))
        pts_all.append(pv)
    allv = np.concatenate(pts_all, axis=0)
    x0, x1 = allv[:, 0].min(), allv[:, 0].max()
    y0, y1 = allv[:, 1].min(), allv[:, 1].max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    scale = min((size - 46) / (x1 - x0), (size - 46) / (y1 - y0))

    def proj(p):
        return np.array([size / 2 + (p[0] - cx) * scale, size / 2 - (p[1] - cy) * scale])

    img = np.zeros((size, size, 3), float)
    img[:] = np.array(bg, float)
    depth = np.full((size, size), -1e9, float)
    for pv, uvs, shade in prepared:
        scr = np.array([proj(p) for p in pv])
        z = pv[:, 2]
        for i, j, k in ((0, 1, 2), (0, 2, 3)):
            p0, p1, p2 = scr[i], scr[j], scr[k]
            M = np.array([[p1[0] - p0[0], p2[0] - p0[0]],
                          [p1[1] - p0[1], p2[1] - p0[1]]])
            det = np.linalg.det(M)
            if abs(det) < 1e-6:
                continue
            inv = np.linalg.inv(M)
            bx0 = max(0, int(np.floor(min(p0[0], p1[0], p2[0]))))
            bx1 = min(size, int(np.ceil(max(p0[0], p1[0], p2[0]))) + 1)
            by0 = max(0, int(np.floor(min(p0[1], p1[1], p2[1]))))
            by1 = min(size, int(np.ceil(max(p0[1], p1[1], p2[1]))) + 1)
            if bx1 <= bx0 or by1 <= by0:
                continue
            yy, xx = np.mgrid[by0:by1, bx0:bx1]
            dx, dy = xx - p0[0], yy - p0[1]
            a = inv[0, 0] * dx + inv[0, 1] * dy
            b = inv[1, 0] * dx + inv[1, 1] * dy
            inside = (a >= -1e-6) & (b >= -1e-6) & (a + b <= 1 + 1e-6)
            if not inside.any():
                continue
            zz = z[i] + a * (z[j] - z[i]) + b * (z[k] - z[i])
            uu = uvs[i, 0] + a * (uvs[j, 0] - uvs[i, 0]) + b * (uvs[k, 0] - uvs[i, 0])
            vv = uvs[i, 1] + a * (uvs[j, 1] - uvs[i, 1]) + b * (uvs[k, 1] - uvs[i, 1])
            ui = np.clip(np.round(uu).astype(int), 0, AW - 1)
            vi = np.clip(np.round(vv).astype(int), 0, AH - 1)
            tex = atlas[vi, ui].astype(float)
            col = tex[:, :, :3] * shade
            alpha = tex[:, :, 3:4] / 255.0
            region = img[by0:by1, bx0:bx1]
            dr = depth[by0:by1, bx0:bx1]
            mask = inside & (zz > dr) & (alpha[:, :, 0] > 0.03)
            if not mask.any():
                continue
            region[mask] = region[mask] * (1 - alpha[mask]) + col[mask] * alpha[mask]
            dr[mask] = zz[mask]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def posed(geo):
    """Muestra estática de la onda Java (los ángulos del geo van en grados)."""
    out = copy.deepcopy(geo)
    secs = {"cape_top": 0, "cape_mid": 1, "cape_bottom": 2}
    for b in out["bones"]:
        n = b["name"]
        if n.startswith("v15_cloth_"):
            sec, col = n[len("v15_cloth_"):].rsplit("_", 1)
            si, ci = secs[sec], int(col)
            share = 0.30 + 0.35 * si
            wave = math.sin(1.9 - si * 0.55 - ci * 0.045)
            b["rotation"][0] -= 6.0 * share * (0.55 + 0.45 * wave)
            b["rotation"][1] += (ci - 6) * 0.30 * share
            b["rotation"][2] += math.sin(ci * 0.62) * 1.0 * share
        elif n.startswith("v15_hem_"):
            ci = int(n.rsplit("_", 1)[1])
            b["rotation"][2] += math.sin(2.3 - ci * 0.55) * 2.2
    return out


def load(p):
    return json.loads(p.read_text())["minecraft:geometry"][0]


def effective_hidden(geo):
    """Lo que NO se dibuja en runtime.

    setHidden(true) pone childrenHidden=true en ese hueso, así que sus
    descendientes tampoco se renderizan. Pero las tres secciones se ocultan
    con setChildrenHidden(false): sus cubos desaparecen y sus hijos (la tela
    v15_*) siguen visibles.
    """
    parent = {b["name"]: b.get("parent") for b in geo["bones"]}
    hidden = set(HIDDEN_DETAILS) | set(SECTION_BONES)
    for name in list(parent):
        cur = parent.get(name)
        while cur:
            if cur in HIDDEN_DETAILS:
                hidden.add(name)
                break
            cur = parent.get(cur)
    return hidden


def uv_test_atlas(path):
    """Atlas de diagnóstico: 9 franjas de colores + marcas asimétricas."""
    arr = np.asarray(Image.open(ARMOR_TEX).convert("RGBA")).copy()
    colors = [(230, 50, 50), (240, 140, 40), (235, 225, 45), (70, 210, 80),
              (45, 215, 205), (55, 110, 240), (140, 70, 235), (235, 70, 200),
              (245, 245, 245)]
    from cloth_spec import COLUMNS, STRIP_W
    for col, rgb in enumerate(colors):
        x0 = int(round(col * STRIP_W))
        x1 = int(round((col + 1) * STRIP_W))
        arr[0:48, x0:x1, :3] = rgb
        arr[0:48, x0:x1, 3] = 255
    arr[0:48, 0:2, :3] = (255, 255, 255)      # marca en u=0
    arr[0:48, 94:96, :3] = (0, 0, 0)          # marca en u=95
    for v in (0, 16, 32, 47):
        arr[v:v + 1, 0:96, :3] = (255, 255, 255)
    Image.fromarray(arr, "RGBA").save(path)


def compose(images, labels, cols, size, bg=(13, 11, 18)):
    rows = math.ceil(len(images) / cols)
    canvas = Image.new("RGB", (cols * (size + 10) + 5, rows * (size + 30) + 5), bg)
    d = ImageDraw.Draw(canvas)
    for i, (im, label) in enumerate(zip(images, labels)):
        x = 5 + (i % cols) * (size + 10)
        y = 25 + (i // cols) * (size + 30)
        canvas.paste(im, (x, y))
        d.text((x, y - 17), label, fill=(235, 232, 245))
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/capa_preview", type=pathlib.Path)
    ap.add_argument("--uv-test", action="store_true",
                    help="pinta franjas de colores en el canvas para validar el orden UV")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    armor = load(ARMOR_GEO)
    folded = load(FOLDED_GEO)
    runtime_hidden = effective_hidden(armor)
    cloth_only = {b["name"] for b in armor["bones"] if not b["name"].startswith("v15_")}
    original_only = cloth_only | runtime_hidden

    if args.uv_test:
        test_atlas = args.out / "uv_test_atlas.png"
        uv_test_atlas(test_atlas)
        render(armor, test_atlas, cloth_only, yaw=0, pitch=8, size=800).save(
            args.out / "uv_test_front.png")
        print("UV test:", test_atlas, args.out / "uv_test_front.png")

    views = [
        (render(folded, FOLDED_TEX, set(), yaw=-28, pitch=14, size=520),
         "FOLDED ITEM 3D - 7 pliegues"),
        (render(armor, ARMOR_TEX, runtime_hidden, yaw=0, pitch=8, size=520),
         "EQUIPPED - frente"),
        (render(posed(armor), ARMOR_TEX, runtime_hidden, yaw=-28, pitch=10, size=520),
         "EQUIPPED - onda 3/4"),
        (render(armor, ARMOR_TEX, runtime_hidden, yaw=180, pitch=8, size=520),
         "EQUIPPED - espalda"),
    ]
    compose([v for v, _ in views], [l for _, l in views], 2, 520).save(args.out / "full.png")
    compose([
        render(armor, ARMOR_TEX, cloth_only, yaw=0, pitch=8, size=700),
        render(posed(armor), ARMOR_TEX, cloth_only, yaw=-28, pitch=10, size=700),
    ], ["TELA SOLA - frente", "TELA SOLA - 3/4"], 2, 700).save(args.out / "cloth_only.png")
    render(armor, ARMOR_TEX, original_only, yaw=0, pitch=8, size=700).save(
        args.out / "original_detail.png")
    Image.open(ARMOR_TEX).convert("RGBA").crop((0, 0, 96, 48)).resize(
        (768, 384), Image.LANCZOS).save(args.out / "canvas.png")
    visible = [b["name"] for b in armor["bones"]
               if not b["name"].startswith("v15_") and b["name"] not in runtime_hidden
               and b.get("cubes")]
    (args.out / "visible_original_bones.txt").write_text("\n".join(visible) + "\n")
    print(f"wrote {len(list(args.out.iterdir()))} files to {args.out}")
    print("visible original bones:", len(visible))


if __name__ == "__main__":
    main()
