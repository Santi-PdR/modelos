#!/usr/bin/env python3
"""Prepare the MIT-licensed Better Combat Particle topslash360 frames.

Usage: python importar_anillo.py /path/to/upstream/textures/particle
Requires Pillow; see META-INF/BETTER_COMBAT_PARTICLE_LICENSE.txt for provenance.
This touches only blood_ring assets, never the other attributed particle frames.
"""
import json
import sys
from pathlib import Path
from PIL import Image

source = Path(sys.argv[1]) if len(sys.argv) == 2 else None
if source is None:
    raise SystemExit('Usage: importar_anillo.py /path/to/upstream/textures/particle')
assets = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana'
texture_dir = assets / 'textures/particle'
for i in range(1, 8):
    path = source / f'topslash360_{i}.png'
    with Image.open(path) as image:
        if image.size != (128, 128):
            raise ValueError(f'Unexpected upstream texture size: {path} {image.size}')
        image.convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS).save(
            texture_dir / f'blood_ring_{i-1}.png', optimize=True)
particles = assets / 'particles/blood_ring.json'
particles.write_text(json.dumps({'textures': [f'stainkatana:blood_ring_{i}' for i in range(7)]}, indent=2) + '\n')
print('Prepared 7 Better Combat Particle ring frames at 64x64.')
