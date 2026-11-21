#!/usr/bin/env python3
"""Check downsampled model against its editable source. Requires Pillow."""
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageChops

root = Path(__file__).resolve().parents[1]
model = json.loads((root / 'Katana_de_Stain.bbmodel').read_text())
data = base64.b64decode(model['textures'][0]['source'].split(',', 1)[1], validate=True)
source = Image.open(io.BytesIO(data)).convert('RGBA')
expected = source.resize((256, 256), Image.Resampling.NEAREST)
textures = root / 'forge/resources/assets/stainkatana/textures'
actual = Image.open(textures / 'item/katana_stain.png').convert('RGBA')
assert actual.size == expected.size
# Check all RGBA channels, including hidden RGB in transparent texels.
assert all(band.getbbox() is None for band in ImageChops.difference(actual, expected).split())
for path in [textures / 'item/katana_stain_glow.png']:
    assert Image.open(path).size == (256, 256), path
for path in [textures / 'item/katana_stain_icon.png', *(textures / 'particle').glob('*.png')]:
    assert Image.open(path).size == (64, 64), path
print('OK: reducción reproducible y dimensiones de texturas de juego')
