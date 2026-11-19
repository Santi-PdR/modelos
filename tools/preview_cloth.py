#!/usr/bin/env python3
"""Previsualización software (aproximada) de la capa. NO es una captura in-game.

Uso:
    python -m pip install Pillow numpy
    python tools/preview_cloth.py --out preview/assets/renders

Genera vistas del bulto plegado, la capa equipada (frente/3-4/espalda),
un perfil para el relieve 3D y el arnés delantero aislado, la superficie de
tela, el canvas 96x48, el icono 64x64 ampliado, el glowmask del item, los seis
sprites de partículas y el detalle original que queda visible. Sirve para
detectar cortes de UV, costuras y silueta boxy sin abrir Minecraft. El
sombreado y la orientación de caras son aproximaciones.
"""

from __future__ import annotations

import argparse

import cape_animation_pipeline as animations
from cape_icon import ICON, SIZE as ICON_SIZE, first_frame
import cape_tracks as tracks
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
FOLDED_GLOW = ASSETS / "textures/item/cape_folded_glowmask.png"
PARTICLE_DIR = ASSETS / "textures/particle"


def mod_version() -> str:
    """La versión sale de gradle.properties, NO se hardcodea.

    v1.26.0: el rótulo del composite decía "bulto v1.17.0" desde la
    v1.17.0 y era la ÚNICA etiqueta de versión obsoleta que sobrevivía
    en las previews: el resto ya se derivaba del fichero de versión.
    """
    for line in (ROOT / "gradle.properties").read_text().splitlines():
        if line.startswith("mod_version="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("falta mod_version en gradle.properties")

# Debe coincidir con CapaArmorModel.SECTIONS + HIDDEN_DETAILS.
SECTION_BONES = {"cape_top", "cape_mid", "cape_bottom"}
# v1.21.0: Java oculta el maniquí con setHidden(true) y el .bbmodel NO lo
# incluye. El render software lo seguía dibujando (cubo blanco + brazos
# violetas) y eso es justo lo que hacía ver "fea" la comparativa. La capa
# se muestra SOLA, como se abre en Blockbench.
MANNEQUIN = {"helmet", "chestplate", "rightArm", "leftArm",
             "rightLeg", "leftLeg", "rightBoot", "leftBoot"}
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
        offset = np.array(b.get("offset", [0, 0, 0])) * [-1, 1, 1]
        scale = b.get("scale", [1, 1, 1])
        local = (T(B + offset) @ rotmat(b.get("rotation", [0, 0, 0]))
                 @ np.diag([*scale, 1]) @ T(-B))
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


def cube_points(c, matrix, *, inflate=True):
    origin, size = np.array(c["origin"], float), np.array(c["size"], float)
    x, y, z = origin
    d = c.get("inflate", 0.0) if inflate else 0.0
    lo = np.array([-x - size[0], y, z]) - d
    vertices = lo + CORNERS * (size + 2 * d)
    p = np.array(c.get("pivot", (0, 0, 0))) * [-1, 1, 1]
    transform = matrix @ T(p) @ rotmat(c.get("rotation", (0, 0, 0))) @ T(-p)
    return (transform @ np.c_[vertices, np.ones(8)].T).T[:, :3]


def collect(geo, hidden):
    mats = matrices(geo)
    faces = []
    for b in geo["bones"]:
        if b["name"] in hidden:
            continue
        for c in b.get("cubes", []):
            VT = cube_points(c, mats[b["name"]])
            for name, idx in FACE_ORDER.items():
                spec = c["uv"].get(name)
                if spec:
                    faces.append((VT[idx], face_uv(spec), name))
    return faces


# Maniquí neutro para presentar la holgura, nunca exportado a Blockbench.
MANNEQUIN_BOXES = (
    ((-4, 24, -4), (8, 8, 8), (113, 120, 139)),
    ((-4, 12, -2), (8, 12, 4), (70, 76, 99)),
    ((-8, 12, -2), (4, 12, 4), (82, 88, 112)),
    ((4, 12, -2), (4, 12, 4), (82, 88, 112)),
    ((-4, 0, -2), (4, 12, 4), (53, 59, 78)),
    ((0, 0, -2), (4, 12, 4), (53, 59, 78)),
)


def render(geo, atlas_path, hidden, yaw=0, pitch=8, size=700, bg=(20, 16, 27),
           *, frame=None, mannequin=False, mannequin_pose=None,
           ambient=1.0, emission=None, tint=(.89,.60,.77), bloom=None, halo_gains=None):
    faces = [(p, uv, None) for p, uv, _ in collect(geo, hidden)]
    if mannequin:
        parts = MANNEQUIN_BOXES if mannequin is True else mannequin
        transforms = [np.eye(4)] * len(parts) if mannequin_pose is None else mannequin_pose
        for (origin, dim, color), matrix in zip(parts, transforms, strict=True):
            points = (np.asarray(origin) + CORNERS * np.asarray(dim)) @ matrix[:3,:3].T + matrix[:3,3]
            faces.extend((points[idx], np.zeros((4, 2)), color) for idx in FACE_ORDER.values())
    atlas = np.asarray((atlas_path if isinstance(atlas_path, Image.Image)
                        else Image.open(atlas_path)).convert("RGBA"))
    AH, AW = atlas.shape[:2]
    light = None if emission is None else np.asarray((emission if isinstance(emission, Image.Image)
                                                    else Image.open(emission)).convert('RGBA'))
    if light is not None:
        assert light.shape == atlas.shape
    halo = None
    if bloom is not None:
        assert light is not None, 'el halo sólo acompaña la emisión'
        halo = np.asarray((bloom if isinstance(bloom, Image.Image) else Image.open(bloom)).convert('RGB'))
        assert halo.shape == atlas[..., :3].shape
    view = R("x", pitch) @ R("y", yaw)
    prepared, pts_all = [], []
    for pts, uvs, color in faces:
        pv = (view @ np.c_[pts, np.ones(4)].T).T[:, :3]
        n = np.cross(pv[1] - pv[0], pv[2] - pv[0])
        ln = np.linalg.norm(n)
        shade = 0.45
        if ln > 1e-6:
            n /= ln
            lamp = np.array([-0.35, 0.65, 0.68])
            lamp /= np.linalg.norm(lamp)
            shade = 0.40 + 0.60 * abs(float(np.dot(n, lamp)))
        prepared.append((pv, uvs, shade * ambient, color))
        pts_all.append(pv)
    if frame is None:
        allv = np.concatenate(pts_all, axis=0)
        x0, x1 = allv[:, 0].min(), allv[:, 0].max()
        y0, y1 = allv[:, 1].min(), allv[:, 1].max()
        frame = ((x0 + x1) / 2, (y0 + y1) / 2,
                 (size - 46) / max(x1 - x0, y1 - y0))
    cx, cy, scale = frame

    def proj(p):
        return np.array([size / 2 + (p[0] - cx) * scale, size / 2 - (p[1] - cy) * scale])

    img = np.zeros((size, size, 3), float)
    img[:] = np.array(bg, float)
    depth = np.full((size, size), -1e9, float)
    for pv, uvs, shade, solid in prepared:
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
            if solid is None:
                uu = uvs[i, 0] + a * (uvs[j, 0] - uvs[i, 0]) + b * (uvs[k, 0] - uvs[i, 0])
                vv = uvs[i, 1] + a * (uvs[j, 1] - uvs[i, 1]) + b * (uvs[k, 1] - uvs[i, 1])
                ui = np.clip(np.floor(uu).astype(int), 0, AW - 1)
                vi = np.clip(np.floor(vv).astype(int), 0, AH - 1)
                tex = atlas[vi, ui].astype(float)
                col = tex[:, :, :3] * shade
                if light is not None:
                    e = light[vi, ui].astype(float)
                    a_glow = np.where(e[..., 3:] >= 26, e[..., 3:]/255., 0.)
                    col = col * (1-a_glow) + e[...,:3] * tint * a_glow
                    if halo is not None:
                        # GL linear sampling interpolates between texel centers.
                        ux, vy = np.clip(uu-.5, 0, AW-1), np.clip(vv-.5, 0, AH-1)
                        x, y = np.minimum(np.floor(ux).astype(int), AW-2), np.minimum(np.floor(vy).astype(int), AH-2)
                        t, s = (ux-x)[..., None], (vy-y)[..., None]
                        nearby = (1-t)*halo[y,x] + t*halo[y,x+1]
                        far = (1-t)*halo[y+1,x] + t*halo[y+1,x+1]
                        spill = (1-s)*nearby + s*far
                        gain = 1.0
                        if halo_gains is not None:
                            edge, inner, lo, hi = halo_gains
                            close = np.clip((spill[..., :1]/255 - lo)/(hi - lo), 0, 1)
                            gain = edge + (inner - edge)*close*close*(3-2*close)
                        col += spill * (1-a_glow) * (.45 + .55*tint[0]) * tint * gain
                alpha = tex[:, :, 3:4] / 255.0
            else:
                col = np.broadcast_to(np.asarray(solid) * shade, inside.shape + (3,))
                alpha = np.ones(inside.shape + (1,))
            region = img[by0:by1, bx0:bx1]
            dr = depth[by0:by1, bx0:bx1]
            mask = inside & (zz > dr) & (alpha[:, :, 0] > 0.03)
            if not mask.any():
                continue
            region[mask] = region[mask] * (1 - alpha[mask]) + col[mask] * alpha[mask]
            dr[mask] = zz[mask]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def pose_at(geo, channels, t, overlay=None):
    """Composición de tracks con el rig, incluyendo position/scale bloqueados.

    `overlay` son deltas Euler extra en el espacio del .geo, para sondear
    holgura con un margen de la respuesta rotacional de Java.
    """
    bones = []
    for b in geo["bones"]:
        n = b["name"]
        ch = channels.get(n, {})
        rot, pos, scale = (tracks.sample(ch[key], t) if key in ch else d
                           for key, d in tracks.DEFAULTS.items())
        extra = overlay(n) if overlay else (0, 0, 0)
        bones.append(dict(b, rotation=[a + c + d for a, c, d in
                          zip(b.get("rotation", (0, 0, 0)), rot, extra)],
                          offset=pos, scale=scale))
    return dict(geo, bones=bones)


def posed(geo):
    """Pose tomada del animation.json que se empaqueta en el JAR."""
    clip = json.loads(animations.ANIM.read_text())["animations"]["animation.moving"]
    return pose_at(geo, tracks.prepare_clip(clip), clip["animation_length"] * .31)


def load(p):
    return json.loads(p.read_text())["minecraft:geometry"][0]


def effective_hidden(geo):
    """Lo que NO se dibuja en runtime.

    setHidden(true) pone childrenHidden=true en ese hueso, así que sus
    descendientes tampoco se renderizan. Pero las tres secciones se ocultan
    con setChildrenHidden(false): sus cubos desaparecen y sus hijos (la tela
    v15_*) siguen visibles.

    v1.27.0: las 27 ANCLAS `v15_cloth_*` también se ocultan. Son cubos de
    0.16 que existen sólo para dar pose a la onda (los usa `panels[]` y el
    animation.json): el hueso se conserva, pero NO se dibuja. Antes el
    render software los pintaba y el runtime también, así que las motas
    negras de la parte alta podían venir de ahí.
    """
    parent = {b["name"]: b.get("parent") for b in geo["bones"]}
    hidden = set(HIDDEN_DETAILS) | set(SECTION_BONES) | MANNEQUIN
    hidden |= {b["name"] for b in geo["bones"]
               if b["name"].startswith("v15_cloth_")}
    # OJO: `chestplate` es PADRE de los huesos v17_* de la capa. Se ocultan
    # SUS CUBOS, pero NO se propaga a los hijos: si no, desaparece la capa
    # entera. La propagación sigue siendo sólo para HIDDEN_DETAILS.
    roots = set(HIDDEN_DETAILS)
    for name in list(parent):
        cur = parent.get(name)
        while cur:
            if cur in roots:
                hidden.add(name)
                break
            cur = parent.get(cur)
    return hidden


def isolate(geo, family):
    """Deja SÓLO una familia visible (diagnóstico).

    `family` puede ser "pads", "chain", "anchors" o None (todo).
    """
    names = {b["name"] for b in geo["bones"]}
    if not family:
        return set()
    prefixes = {"pads": "v18_pad_", "chain": "v18_chain_",
                "anchors": "v15_cloth_"}
    keep = prefixes[family]
    hidden = set(effective_hidden(geo))
    for name in names:
        if name.startswith(keep):
            hidden.discard(name)
        else:
            hidden.add(name)
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


def particle_sheet(path):
    """Las tres fases de la misma chispa (sprites de 16x16 ampliados)."""
    names = [f"capa_spark_{i}.png" for i in range(3)]
    labels = ["BRASA", "DESTELLO", "CENIZA"]
    cell = 128
    sheet = Image.new("RGB", (3 * (cell + 10) + 5, cell + 33), (13, 11, 18))
    d = ImageDraw.Draw(sheet)
    for i, (name, label) in enumerate(zip(names, labels)):
        sprite = Image.open(PARTICLE_DIR / name).convert("RGBA").resize(
            (cell, cell), Image.NEAREST)
        x = 5 + i * (cell + 10)
        sheet.paste(sprite, (x, 28), sprite)
        d.text((x, 8), label, fill=(220, 235, 245))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ROOT / "preview/assets/renders", type=pathlib.Path)
    ap.add_argument("--uv-test", action="store_true",
                    help="pinta franjas de colores en el canvas para validar el orden UV")
    ap.add_argument("--isolate", default="none",
                    choices=("none", "pads", "chain", "anchors"),
                    help="deja SÓLO esa familia visible (diagnóstico)")
    ap.add_argument("--show-anchors", action="store_true",
                    help="vuelve a pintar las 27 anclas v15_cloth_* (diagnóstico)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    armor = load(ARMOR_GEO)
    folded = load(FOLDED_GEO)
    runtime_hidden = effective_hidden(armor)
    if args.show_anchors:
        # v1.27.0: las anclas están OCULTAS en runtime. Con esta bandera
        # se vuelven a pintar para ver de dónde salían las motas.
        runtime_hidden = {n for n in runtime_hidden
                          if not n.startswith("v15_cloth_")}
    # rev. B: la "piel nueva" son las anclas v15_* y el abanico v17_*.
    # NO hay motas ni ceniza: son partículas de runtime.
    cloth_only = {b["name"] for b in armor["bones"]
                  if not b["name"].startswith(("v15_", "v16_", "v17_", "v18_"))}
    original_only = cloth_only | runtime_hidden

    if args.uv_test:
        test_atlas = args.out / "uv_test_atlas.png"
        uv_test_atlas(test_atlas)
        render(armor, test_atlas, cloth_only, yaw=0, pitch=8, size=800).save(
            args.out / "uv_test_front.png")
        print("UV test:", test_atlas, args.out / "uv_test_front.png")

    # v1.9.0: vistas extra para el relieve 3D y el arnés delantero.
    # v1.12.0: ya NO mostramos el arnes aislado (parecian "piezas sueltas
    # flotando", que es exactamente lo que el usuario reprocho). En su lugar
    # el rig se ve MONTADO sobre la tela, desde el frente.
    front_rig_only = runtime_hidden
    side_relief = render(armor, ARMOR_TEX, runtime_hidden,
                         yaw=-62, pitch=14, size=520)
    front_rig = render(armor, ARMOR_TEX, front_rig_only,
                       yaw=180, pitch=8, size=520)
    side_relief.save(args.out / "side_relief.png")
    front_rig.save(args.out / "front_rig.png")

    views = [
        (render(folded, FOLDED_TEX, set(), yaw=-28, pitch=14, size=520),
         f"FOLDED ITEM 3D - bulto v{mod_version()}"),
        # v1.27.0: los rótulos estaban CAMBIADOS. En este geo el exterior
        # de la capa mira a +Z (el arnés del pecho está a -Z), así que la
        # vista yaw=0 es la ESPALDA (F5) y yaw=180 el INTERIOR de la capa.
        (render(armor, ARMOR_TEX, runtime_hidden, yaw=0, pitch=8, size=520),
         "CAPA - espalda (render software)"),
        (render(posed(armor), ARMOR_TEX, runtime_hidden, yaw=-28, pitch=10, size=520),
         "DETERIORO - flujo de jirones 3/4"),
        (render(armor, ARMOR_TEX, runtime_hidden, yaw=180, pitch=8, size=520),
         "DETERIORO - interior (cara del pecho)"),
        (side_relief, "JIRONES 3D - perfil"),
        (render(armor, ARMOR_TEX, runtime_hidden, yaw=205, pitch=14, size=520),
         "CUELLO Y FORRO - 3/4"),
    ]
    compose([v for v, _ in views], [l for _, l in views], 3, 520).save(args.out / "full.png")
    compose([
        render(armor, ARMOR_TEX, cloth_only, yaw=0, pitch=8, size=700),
        render(posed(armor), ARMOR_TEX, cloth_only, yaw=-28, pitch=10, size=700),
    ], ["TELA SOLA - frente", "TELA SOLA - 3/4"], 2, 700).save(args.out / "cloth_only.png")
    render(armor, ARMOR_TEX, original_only, yaw=0, pitch=8, size=700).save(
        args.out / "original_detail.png")
    Image.open(ARMOR_TEX).convert("RGBA").crop((0, 0, 96, 48)).resize(
        (768, 384), Image.LANCZOS).save(args.out / "canvas.png")
    # v1.17.0: icono pixel art 16x16 conservando la forma aprobada, con
    # paleta Rosé, grietas, 5 puntas y microvóxeles; NEAREST sin AA.
    first_frame().resize((ICON_SIZE*3, ICON_SIZE*3), Image.Resampling.NEAREST).save(args.out / "icon.png")
    Image.open(FOLDED_GLOW).convert("RGBA").resize(
        (256, 256), Image.LANCZOS).save(args.out / "folded_glowmask.png")
    particle_sheet(args.out / "particles.png")
    visible = [b["name"] for b in armor["bones"]
               if not b["name"].startswith(("v15_", "v16_", "v17_", "v18_"))
               and b["name"] not in runtime_hidden and b.get("cubes")]
    (args.out / "visible_original_bones.txt").write_text("\n".join(visible) + "\n")
    # v1.27.0: AISLAMIENTO. Deja SÓLO una familia visible para ver qué
    # pinta de verdad (la hombrera, la cadena o las anclas de la onda).
    if args.isolate != "none":
        iso_hidden = isolate(armor, args.isolate)
        render(armor, ARMOR_TEX, iso_hidden, yaw=0, pitch=8, size=700).save(
            args.out / f"isolate_{args.isolate}.png")
        print(f"isolate {args.isolate}: {args.out / f'isolate_{args.isolate}.png'}")
    print(f"wrote {len(list(args.out.iterdir()))} files to {args.out}")
    print("visible original bones:", len(visible))
    print("anclas v15_cloth_* ocultas:",
          sum(1 for b in armor["bones"] if b["name"].startswith("v15_cloth_")
              and b["name"] in runtime_hidden))


if __name__ == "__main__":
    main()
