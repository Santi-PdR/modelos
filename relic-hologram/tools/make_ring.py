#!/usr/bin/env python3
"""Genera la textura del anillo de estado de la reliquia (64x64 RGBA).

El anillo es un billboard aditivo mas (`RelicAura.renderRing`): se dibuja del
mismo modo que el aura, pero con esta textura. Para que el giro se note no es un
anillo perfecto: lleva tres cortes y un arco mas brillante, asi que al girar se
ve como si una energia recorriera la orbita.

Uso:  python3 tools/make_ring.py [salida]
Por defecto escribe assets/holocore/textures/relic/relic_ring.png
"""

import math
import pathlib
import struct
import sys
import zlib

SIZE = 64
CENTER = (SIZE - 1) / 2.0

RING_RADIUS = 0.70      # radio del anillo principal (1.0 = borde del quad)
RING_WIDTH = 0.030      # semiancho del anillo principal
GHOST_RADIUS = 0.86     # segundo anillo, mas fino y tenue
GHOST_WIDTH = 0.012

# Cortes del anillo: (angulo central, medio ancho) en radianes.
GAPS = (
    (math.radians(40.0), math.radians(9.0)),
    (math.radians(160.0), math.radians(6.0)),
    (math.radians(265.0), math.radians(12.0)),
)


def smoothstep(edge0, edge1, x):
    if edge1 == edge0:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def gap_mask(angle):
    mask = 1.0
    for center, half in GAPS:
        delta = abs((angle - center + math.pi) % (2.0 * math.pi) - math.pi)
        if delta < half:
            mask = min(mask, smoothstep(half, half * 0.55, delta))
    return mask


def ring_alpha(dist, angle, radius, width):
    band = smoothstep(width, 0.0, abs(dist - radius))
    if band <= 0.0:
        return 0.0
    return band * gap_mask(angle)


def pixel(nx, ny):
    dist = math.hypot(nx, ny)
    angle = math.atan2(ny, nx) % (2.0 * math.pi)

    alpha = ring_alpha(dist, angle, RING_RADIUS, RING_WIDTH)
    # Arco que recorre el anillo: da la sensacion de energia circulando.
    if alpha > 0.0:
        lead = smoothstep(1.2, 0.0, abs((angle - math.radians(20.0) + math.pi) % (2.0 * math.pi) - math.pi))
        alpha *= 1.0 + 0.9 * lead

    alpha += ring_alpha(dist, angle, GHOST_RADIUS, GHOST_WIDTH) * 0.30

    alpha = max(0.0, min(1.0, alpha))
    # Blanco: el color lo pone el color de vertice segun el estado.
    return (255, 255, 255, int(round(alpha * 255)))


def build_rgba():
    rows = []
    for y in range(SIZE):
        ny = (y - CENTER) / CENTER
        row = bytearray()
        for x in range(SIZE):
            nx = (x - CENTER) / CENTER
            row.extend(pixel(nx, ny))
        rows.append(bytes(row))
    return rows


def png_chunk(tag, payload):
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_png(path, rows):
    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
        root / "src/main/resources/assets/holocore/textures/relic/relic_ring.png"
    )
    rows = build_rgba()
    size = write_png(out, rows)
    painted = sum(1 for row in rows for i in range(3, len(row), 4) if row[i] > 0)
    print(f"{out} ({SIZE}x{SIZE}, {size} bytes, {painted} px con alfa)")


if __name__ == "__main__":
    main()
