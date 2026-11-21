#!/usr/bin/env python3
"""Downsample runtime textures; editable .bbmodel and supplied icon remain untouched.
Requires Pillow. Existing 64/256 images are not resampled again.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/textures'

def resize(path: Path, size: int, resample: int) -> None:
    with Image.open(path) as original:
        if original.size == (size, size):
            return
        if original.width != original.height or original.width < size:
            raise ValueError(f'Unexpected texture dimensions for {path}: {original.size}')
        original.convert('RGBA').resize((size, size), resample).save(path, optimize=True)

def optimize_model() -> None:
    resize(ROOT / 'item/katana_stain.png', 256, Image.Resampling.NEAREST)

def main() -> None:
    optimize_model()
    resize(ROOT / 'item/katana_stain_glow.png', 256, Image.Resampling.NEAREST)
    resize(ROOT / 'item/katana_stain_icon.png', 64, Image.Resampling.LANCZOS)
    for path in (ROOT / 'particle').glob('*.png'):
        resize(path, 64, Image.Resampling.LANCZOS)
    print('Texturas de juego reducidas; originales editables conservados.')

if __name__ == '__main__':
    main()
