#!/usr/bin/env python3
"""Genera la textura del aura de la reliquia (64x64 RGBA, sin dependencias).

El aura es un *billboard* aditivo: el codigo dibuja un quad que mira a camara y
suma esta textura al framebuffer. Por eso el PNG no es un circulo perfecto: lleva
tres arcos tenues (las "estelas orbitales") para que, al girar y contra-girar los
dos primeros quads, se note el movimiento en vez de parecer una mancha fija.

<b>Nada de blanco en el centro.</b> La version 1.0.10 tenia el centro a RGB
(254,255,255) con alpha 254: sumado tres veces y encima de nieve, el resultado
clipa a blanco y el aura se ve como una nube. Aqui el nucleo es azul-cian
saturado y el degradado es mas corto, para que sume luz de color en vez de
quemar el fondo.

Uso:  python3 tools/make_aura.py [salida]
Por defecto escribe assets/holocore/textures/relic/relic_aura.png
"""

import math
import pathlib
import struct
import sys
import zlib

SIZE = 64
CENTER = (SIZE - 1) / 2.0

# (radio normalizado del arco, grosor normalizado, angulo inicial, barrido, peso)
ARCS = (
    (0.62, 0.045, math.radians(15.0), math.radians(120.0), 0.85),
    (0.80, 0.035, math.radians(150.0), math.radians(95.0), 0.65),
    (0.46, 0.030, math.radians(250.0), math.radians(70.0), 0.55),
)


def smoothstep(edge0, edge1, x):
    if edge1 == edge0:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def pixel(nx, ny):
    """Devuelve (r, g, b, a) con nx, ny en [-1, 1] respecto al centro."""
    dist = math.hypot(nx, ny)

    # Nucleo: degradado radial mas cerrado que antes (2.2 -> 3.0) y con el pico
    # recortado: el quad ya es mas pequeno, no hace falta que llene el PNG.
    core = smoothstep(1.0, 0.0, dist) ** 3.0 * 0.92
    # Halo estrecho y muy suave, solo para que no se vea el borde del quad.
    halo = smoothstep(1.0, 0.55, dist) * 0.18

    alpha = max(core, halo)

    # Arcos: solo suman, y solo dentro del radio util.
    if 0.15 < dist < 1.0:
        angle = math.atan2(ny, nx) % (2.0 * math.pi)
        for radius, width, start, sweep, weight in ARCS:
            if abs(dist - radius) > width * 2.2:
                continue
            delta = (angle - start) % (2.0 * math.pi)
            if delta > sweep:
                continue
            radial = smoothstep(width * 2.2, 0.0, abs(dist - radius))
            # Se apaga en los extremos del arco para que no corte de golpe.
            ends = smoothstep(0.0, 0.18, delta) * smoothstep(0.0, 0.18, sweep - delta)
            alpha += radial * ends * weight * 0.55

    alpha = max(0.0, min(1.0, alpha))
    # Azul frio de verdad: el rojo sube poco en el centro, asi que el nucleo se
    # queda cian y no blanco (que es lo que hacia que el aura pareciera una nube).
    warm = smoothstep(0.55, 0.0, dist)
    red = 0.22 + 0.30 * warm
    green = 0.62 + 0.24 * warm
    blue = 1.0
    return (
        int(round(red * 255)),
        int(round(green * 255)),
        int(round(blue * 255)),
        int(round(alpha * 255)),
    )


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
    raw = b"".join(b"\x00" + row for row in rows)  # filtro 0 (None) por fila
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8 bits, RGBA
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
        root / "src/main/resources/assets/holocore/textures/relic/relic_aura.png"
    )
    rows = build_rgba()
    size = write_png(out, rows)
    opaque = sum(1 for row in rows for i in range(3, len(row), 4) if row[i] > 0)
    print(f"{out} ({SIZE}x{SIZE}, {size} bytes, {opaque} px con alfa)")


if __name__ == "__main__":
    main()
