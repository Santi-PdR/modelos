#!/usr/bin/env python3
"""Emit a compact JPEG preview as GitHub check annotations for visual review."""
import argparse
import base64
import hashlib
import io
from pathlib import Path

from PIL import Image

MAX_BYTES = 12_600
CHUNK_SIZE = 3_500


def encode_preview(path: Path) -> tuple[bytes, tuple[int, int]]:
    with Image.open(path) as source:
        image = source.convert('RGB')
    width = min(560, image.width)
    while width >= 96:
        height = max(1, round(width * image.height / image.width))
        preview = image.resize((width, height), Image.Resampling.LANCZOS)
        for quality in (68, 56, 44, 32, 20):
            output = io.BytesIO()
            preview.save(output, format='JPEG', quality=quality, optimize=True)
            payload = output.getvalue()
            if len(payload) <= MAX_BYTES:
                return payload, (width, height)
        width = round(width * .78)
    raise RuntimeError(f'No se pudo comprimir {path} por debajo de {MAX_BYTES} bytes')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    payload, size = encode_preview(args.image)
    encoded = base64.b64encode(payload).decode('ascii')
    digest = hashlib.sha256(payload).hexdigest()
    print(f'Vista de saltos: {size[0]}x{size[1]}, {len(payload)} bytes, SHA-256 {digest}.')
    for index, offset in enumerate(range(0, len(encoded), CHUNK_SIZE)):
        chunk = encoded[offset:offset + CHUNK_SIZE]
        print(f'::notice title=JUMP_PREVIEW_{index:02}::{chunk}')


if __name__ == '__main__':
    main()
