#!/usr/bin/env python3
"""Build the isolated first-pass Blockbench model for Brazalete Ascua.

This deliberately does not add the accessory to the cape's GeckoLib geometry,
item registry, Curios slots, or runtime render path. The output is for fit review.
"""
from __future__ import annotations

import base64
import json
import struct
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/prototypes/brazalete_ascua"
NAMESPACE = uuid.UUID("8024d123-2ac2-4ab1-9e22-641be39c62c5")

# Small pixel-art atlas: charcoal shell, a restrained garnet bridge, and one
# four-step pink fracture. No glowmask or emissive pass in this prototype.
COLORS = {
    "charcoal": (35, 32, 39),
    "charcoal_hi": (65, 57, 66),
    "charcoal_low": (22, 20, 26),
    "garnet": (113, 23, 53),
    "garnet_hi": (174, 43, 82),
    "pink": (237, 92, 174),
    "pink_hi": (255, 137, 204),
    "lining": (48, 39, 49),
}


def png_rgb(width: int, height: int, pixels: list[tuple[int, int, int]]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG filter: None
        for r, g, b in pixels[y * width : (y + 1) * width]:
            rows.extend((r, g, b))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


def texture() -> bytes:
    w = h = 32
    pixels = [COLORS["charcoal"]] * (w * h)

    def rect(x0: int, y0: int, x1: int, y1: int, color: str) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[y * w + x] = COLORS[color]

    # Eight reusable material swatches, each 8×8 and deliberately legible when
    # Blockbench scales the atlas on narrow cube faces.
    rect(0, 0, 8, 8, "charcoal")
    rect(0, 0, 8, 1, "charcoal_hi")
    rect(0, 7, 8, 8, "charcoal_low")
    rect(8, 0, 16, 8, "charcoal_hi")
    rect(8, 0, 16, 1, "pink")
    rect(8, 7, 16, 8, "charcoal_low")
    rect(16, 0, 24, 8, "charcoal")
    rect(16, 0, 17, 8, "garnet")
    rect(23, 0, 24, 8, "garnet")
    rect(24, 0, 32, 8, "garnet")
    rect(24, 0, 32, 1, "garnet_hi")
    rect(24, 7, 32, 8, "charcoal_low")
    rect(0, 8, 8, 16, "pink")
    rect(2, 8, 6, 16, "pink_hi")
    rect(8, 8, 16, 16, "lining")
    rect(8, 8, 16, 9, "charcoal_hi")
    rect(16, 8, 24, 16, "charcoal_low")
    rect(16, 8, 24, 9, "charcoal_hi")
    rect(24, 8, 32, 16, "charcoal")
    rect(24, 15, 32, 16, "charcoal_low")
    # A few printed seams in the lower half; no random noise or accidental
    # color specks outside the intended materials.
    rect(0, 16, 8, 24, "lining")
    rect(0, 16, 8, 17, "charcoal_hi")
    rect(8, 16, 16, 24, "charcoal")
    rect(8, 23, 16, 24, "charcoal_low")
    rect(16, 16, 24, 24, "garnet")
    rect(16, 16, 24, 17, "garnet_hi")
    rect(24, 16, 32, 24, "charcoal_hi")
    rect(24, 23, 32, 24, "charcoal_low")
    rect(0, 24, 8, 32, "charcoal_low")
    rect(0, 24, 8, 25, "charcoal_hi")
    rect(8, 24, 16, 32, "lining")
    rect(16, 24, 24, 32, "charcoal")
    rect(24, 24, 32, 32, "garnet")
    return png_rgb(w, h, pixels)


def stable_id(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def face_uv(u: int, v: int, width: int = 8, height: int = 8) -> dict:
    return {face: {"uv": [u, v, u + width, v + height], "texture": 0}
            for face in ("north", "south", "east", "west", "up", "down")}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tex = texture()
    (OUT / "brazalete_ascua.png").write_bytes(tex)

    group_id = stable_id("left_forearm")
    # Local coordinate convention for the fit prototype: +X is the character's
    # outward left-arm side; +Z is the front. An eventual adapter must confirm
    # this against both Steve and Alex before a runtime slot is selected.
    parts = [
        ("shell_lower_front", [-1.98, 0.00, 2.00], [1.98, .72, 2.30], 0, 0),
        ("shell_lower_back", [-1.98, 0.00, -2.30], [1.98, .72, -2.00], 0, 0),
        ("shell_lower_outer", [2.00, 0.00, -1.98], [2.30, .72, 1.98], 0, 0),
        ("shell_lower_inner", [-2.30, 0.00, -1.98], [-2.00, .72, 1.98], 0, 0),
        ("shell_upper_front", [-1.98, 1.78, 2.00], [1.98, 2.50, 2.30], 0, 0),
        ("shell_upper_back", [-1.98, 1.78, -2.30], [1.98, 2.50, -2.00], 0, 0),
        ("shell_upper_outer", [2.00, 1.78, -1.98], [2.30, 2.50, 1.98], 0, 0),
        ("shell_upper_inner", [-2.30, 1.78, -1.98], [-2.00, 2.50, 1.98], 0, 0),
        # One small, solid bridge joins the two shell segments on the outside.
        ("outer_bridge", [2.12, .68, -.62], [2.38, 1.82, .62], 16, 0),
        ("garnet_bridge", [2.38, .86, -.22], [2.43, 1.64, .22], 24, 0),
        # Four flush, individually selectable plates read as one short crack.
        ("crack_01", [2.43, .94, .11], [2.47, 1.12, .25], 0, 8),
        ("crack_02", [2.43, 1.10, -.01], [2.47, 1.28, .13], 0, 8),
        ("crack_03", [2.43, 1.26, -.14], [2.47, 1.44, 0.00], 0, 8),
        ("crack_04", [2.43, 1.42, -.27], [2.47, 1.60, -.13], 0, 8),
        # A low-profile inner closure, intentionally matte and hidden from the
        # front three-quarter view.
        ("inner_clasp", [-2.36, .86, -.38], [-2.27, 1.64, .38], 8, 8),
    ]
    elements = []
    child_ids = []
    for name, start, end, u, v in parts:
        element_id = stable_id(name)
        child_ids.append(element_id)
        elements.append({
            "name": name,
            "type": "cube",
            "uuid": element_id,
            "from": start,
            "to": end,
            "origin": [(a + b) / 2 for a, b in zip(start, end)],
            "rotation": [0, 0, 0],
            "inflate": 0,
            "autouv": 0,
            "color": 0,
            "visibility": True,
            "faces": face_uv(u, v),
            "box_uv": False,
        })
    group = {
        "name": "left_forearm",
        "uuid": group_id,
        "origin": [0, 0, 0],
        "rotation": [0, 0, 0],
        "visibility": True,
        "isOpen": True,
        "shade": True,
        "export": True,
        "locked": False,
        "autouv": 0,
        "children": child_ids,
    }
    model = {
        "meta": {"format_version": "5.0", "model_format": "bedrock", "box_uv": False},
        "name": "brazalete_ascua_fit_prototype_v0",
        "model_identifier": "geometry.brazalete_ascua_fit_prototype",
        "visible_box": [4.9, 3.0, 4.9],
        "resolution": {"width": 32, "height": 32},
        "elements": elements,
        "groups": [group],
        "outliner": [{"uuid": group_id, "isOpen": True, "children": child_ids}],
        "textures": [{
            "path": "",
            "name": "brazalete_ascua.png",
            "folder": "",
            "namespace": "",
            "id": "0",
            "width": 32,
            "height": 32,
            "uv_scale": [1, 1],
            "particle": False,
            "render_mode": "default",
            "visible": True,
            "enabled": True,
            "saved": True,
            "internal": True,
            "source": "data:image/png;base64," + base64.b64encode(tex).decode("ascii"),
        }],
        "animations": [],
    }
    # Keep this prototype honest about its scope and millimeter-free dimensions.
    assert len(elements) == 15
    assert sum(element["name"].startswith("crack_") for element in elements) == 4
    assert not model["animations"] and len(model["textures"]) == 1
    assert max(element["to"][1] for element in elements) - min(element["from"][1] for element in elements) == 2.5
    assert set(group["children"]) == {element["uuid"] for element in elements}
    assert set(model["outliner"][0]["children"]) == set(group["children"])
    assert base64.b64decode(model["textures"][0]["source"].split(",", 1)[1]) == tex
    (OUT / "Brazalete_Ascua_fit_v0.bbmodel").write_text(
        json.dumps(model, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
