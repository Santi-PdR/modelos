#!/usr/bin/env python3
"""Genera los iconos de REFERENCIA que muestra el visor (preview/index.html).

El visor enseña cuatro imágenes fijas: el icono rechazado de la v1.12.0, el
APROBADO de la v1.13.0, el icono ACTIVO y el GIF animado. Antes vivían sólo
en `preview/assets/`, que está ignorado por git, así que el visor no se podía
reconstruir desde un clon limpio.

  icon_v1120.png  : el mapa ICON_PIXEL_MAP de la v1.12.0 (el rechazado).
  icon_fiel.png   : el icono APROBADO de la v1.13.0 (ICON_ALTERNATIVE).
  icon_active.png : el icono ACTIVO de este repo, reescalado a 64x64.
  icon_animado.gif: el icono animado (pulso de la estrella y del broche).

Uso:
    PYTHONPATH=tools:tools/_deps python3 tools/make_reference_icons.py
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "preview/assets"
RES = ROOT / "src/main/resources/assets/capatest"

# El mapa del icono RECHAZADO de la v1.12.0 (commit 6c1bcff). Vive aquí
# porque el historial de git no es un input del build: si el mapa se
# regenera, el visor sigue mostrando la misma referencia.
ICON_V1120_MAP = (
    "...KGG....GGK...",
    "....KLHMLHLK....",
    "KWWKLHKGLKHMKWWK",
    "KCCKLHGWGLHMKCCK",
    "KHHKLHMGLLHMKHHK",
    "..MLLHMCCLHMML..",
    "..MGLHMMLLHMML..",
    ".DMLLHMMELHMMLD.",
    ".DMELHMEWEHMELD.",
    "KGMLLHMMELHMMLGK",
    "KDMLLHMMLLHMMLDK",
    "KDMLEHMMLLHEMLDK",
    "KGMLLHMMELHMMLGK",
    "GGMLGHGMLGHMGLGG",
    "KKDDKKKDDKKKDDKK",
    "..GW...GW...GW..",
)


# La paleta ORIGINAL del icono de la v1.12.0 (commit 6c1bcff): cian y
# vetas frías, nada de magenta. Se usa SU paleta, no la actual: si no, el
# "icono rechazado" de la v1.12.0 saldría con los colores de la v1.27.0 y
# no sería la referencia que el visor pretende mostrar.
ICON_V1120_PALETTE = {
    ".": (0, 0, 0, 0),
    "K": (15, 8, 22, 255),
    "H": (43, 14, 54, 255),
    "D": (72, 22, 78, 255),
    "M": (97, 31, 96, 255),
    "L": (126, 47, 116, 255),
    "G": (232, 194, 118, 255),
    "W": (226, 250, 255, 255),
    "C": (110, 216, 240, 255),
    "E": (58, 150, 184, 255),
}

# La paleta del icono APROBADO de la v1.13.0 (commit d1e373f): carmesí y
# morado, con el magenta Evil Saiyan. Es la que estaba activa entonces.
ICON_V1130_PALETTE = {
    ".": (0, 0, 0, 0),
    "K": (12, 5, 18, 255),
    "H": (42, 11, 28, 255),
    "D": (66, 24, 70, 255),
    "M": (88, 30, 84, 255),
    "L": (112, 52, 108, 255),
    "G": (232, 104, 172, 255),
    "W": (255, 222, 238, 255),
    "C": (214, 34, 138, 255),
    "E": (96, 22, 72, 255),
    "P": (140, 20, 96, 255),
}


def _palette_actual() -> dict[str, tuple[int, int, int, int]]:
    """El ICON_PALETTE del texture_pipeline (el del icono ACTIVO)."""
    src = (ROOT / "tools/texture_pipeline.py").read_text()
    m = re.search(r"^ICON_PALETTE = \{(.*?)^\}", src, re.S | re.M)
    assert m, "no se encontró ICON_PALETTE en tools/texture_pipeline.py"
    out: dict[str, tuple[int, int, int, int]] = {}
    for key, r, g, b, a in re.findall(
            r'"(\w)":\s*\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', m.group(1)):
        out[key] = (int(r), int(g), int(b), int(a))
    return out


def _render(rows: tuple[str, ...], palette: dict, scale: int = 4) -> Image.Image:
    assert len(rows) == 16, len(rows)
    for r in rows:
        assert len(r) == 16, (len(r), r)
    px = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            assert ch in palette, f"letra de paleta desconocida: {ch!r}"
            px.putpixel((x, y), palette[ch])
    return px.resize((16 * scale, 16 * scale), Image.NEAREST)


# El mapa del icono APROBADO de la v1.13.0 (commit d1e373f). Se fija aquí
# para que la referencia no cambie si el texture_pipeline regenera el
# alternativo: el visor muestra un histórico, no el icono de hoy.
ICON_V1130_MAP = (
    "..KKGG....GGKK..",
    "...HGHHHKKHGH...",
    "....HHHHHHKKK...",
    "...HMLMGKKLLLK..",
    "...HELGWGMLEDK..",
    "...GDLLGMMLLGK..",
    "...HDLLMHLLLLK..",
    "...HMLLMHLLMLHK.",
    "...HMLMCKLMDLDK.",
    "..HEMLECEHMDLDHK",
    ".HDMLDMEKKMDEDDK",
    ".HDMDDMDKHMLMDDK",
    "KHMDDMLDKDMDDDDK",
    "KHDDMDDHKLDDDDK.",
    ".KKGHDHGKDHKGK..",
    "...KK.KKK.KK....",
)


def _animado(icon: Image.Image, frames: int = 8) -> Image.Image:
    """GIF animado: el icono activo con un pulso de brillo."""
    base = icon.convert("RGBA")
    out = []
    for i in range(frames):
        factor = 0.72 + 0.28 * (1.0 + (1 if i % 2 == 0 else -1) * 0.35)
        r, g, b, a = base.split()
        rgb = Image.merge("RGB", (r, g, b)).point(
            lambda v: min(255, int(v * factor)))
        frame = Image.merge("RGBA", (*rgb.split(), a))
        out.append(frame)
    out[0].save(A / "icon_animado.gif", save_all=True, append_images=out[1:],
                duration=90, loop=0, optimize=False)
    return out[0]


def main() -> None:
    A.mkdir(parents=True, exist_ok=True)

    _render(ICON_V1120_MAP, ICON_V1120_PALETTE).save(A / "icon_v1120.png")
    _render(ICON_V1130_MAP, ICON_V1130_PALETTE).save(A / "icon_fiel.png")

    activo = Image.open(RES / "textures/item/capa_deteriorer_evilsaiyan.png").convert("RGBA")
    activo.resize((64, 64), Image.NEAREST).save(A / "icon_active.png")

    _animado(activo.resize((64, 64), Image.NEAREST))
    print("iconos de referencia: icon_v1120.png, icon_fiel.png, "
          "icon_active.png, icon_animado.gif")


if __name__ == "__main__":
    main()
