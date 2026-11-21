#!/usr/bin/env python3
"""Genera el icono 2D del item (16x16, alfa) sin dependencias externas.

Uso: python3 tools/make_icon.py
Salida: src/main/resources/assets/holocore/textures/item/holographic_core.png
"""
from __future__ import annotations

import math
import pathlib
import struct
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/assets/holocore/textures/item/holographic_core.png"

SIZE = 16

# Paleta del nucleo (azul holografico): de dentro hacia fuera.
CORE = (238, 255, 255, 255)
CYAN = (108, 232, 255, 255)
BLUE = (46, 150, 235, 255)
DEEP = (20, 62, 150, 255)
RIM = (10, 28, 78, 255)
SPARK = (255, 255, 255, 255)


def px(x: int, y: int, image: list[list[tuple[int, int, int, int] | None]], color) -> None:
    if 0 <= x < SIZE and 0 <= y < SIZE:
        image[y][x] = color


def build() -> list[list[tuple[int, int, int, int] | None]]:
    image: list[list[tuple[int, int, int, int] | None]] = [
        [None for _ in range(SIZE)] for _ in range(SIZE)
    ]
    cx = cy = 7.5

    # Nucleo y anillos concentricos con borde duro (pixel art, sin AA).
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x - cx, y - cy)
            if r < 2.0:
                px(x, y, image, CORE)
            elif r < 3.6:
                px(x, y, image, CYAN)
            elif r < 4.8:
                px(x, y, image, BLUE)
            elif r < 5.9:
                # Anillo exterior con huecos: se lee como esfera armilar.
                angle = math.atan2(y - cy, x - cx)
                if int((angle + math.pi) * 7) % 5 != 0:
                    px(x, y, image, DEEP)
                else:
                    px(x, y, image, RIM)

    # Orbita inclinada (estela de luz) y dos destellos de esquina.
    for x, y in ((2, 6), (3, 5), (4, 4), (11, 11), (12, 12), (13, 13)):
        px(x, y, image, BLUE)
    px(2, 6, image, CYAN)
    px(13, 13, image, CYAN)
    px(12, 3, image, SPARK)
    px(3, 12, image, SPARK)

    return image


def write_png(path: pathlib.Path, image) -> None:
    raw = bytearray()
    for row in image:
        raw.append(0)  # filtro None
        for pixel in row:
            raw.extend(pixel if pixel is not None else (0, 0, 0, 0))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


if __name__ == "__main__":
    write_png(OUT, build())
    print(f"Escrito {OUT} ({OUT.stat().st_size} bytes)")
