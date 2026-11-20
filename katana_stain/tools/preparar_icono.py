#!/usr/bin/env python3
"""Make a transparent, high-contrast inventory icon from the user's reference.
Requires Pillow; keeps the supplied original untouched.
"""
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).resolve().parents[1]
im = Image.open(root / 'referencias/icono_suministrado.png').convert('RGBA')
pixels = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = pixels[x, y]
        # The supplied image has a white background. Keep dark grey metal,
        # outlines and the dark sheath; feather only nearly-white edge pixels.
        white = min(r, g, b)
        alpha = 0 if white >= 249 else min(255, max(0, (249-white)*32))
        pixels[x, y] = (r, g, b, alpha)
# Restrained blood on the blade, not on the sheath: inspect at inventory size.
d = ImageDraw.Draw(im)
d.line([(514, 513), (530, 505), (548, 488)], fill=(140, 13, 28, 230), width=7)
d.line([(662, 341), (675, 335)], fill=(171, 24, 37, 230), width=6)
im.thumbnail((62,62), Image.Resampling.LANCZOS)
out = Image.new('RGBA', (64,64)); out.alpha_composite(im, ((64-im.width)//2,(64-im.height)//2))
out.save(root / 'forge/resources/assets/stainkatana/textures/item/katana_stain_icon.png')
