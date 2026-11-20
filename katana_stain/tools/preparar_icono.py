#!/usr/bin/env python3
"""Pixel-art inventory adaptation of the user's icon, tuned for 16px GUI sampling.
Requires Pillow. Source reference is retained in referencias/.
"""
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).resolve().parents[1]
im = Image.new('RGBA', (32,32))
d = ImageDraw.Draw(im)
# Sheath, separated from the blade, with restrained highlights and dark outline.
d.line([(3,22),(22,2)], fill=(12,13,18,255), width=4)
d.line([(3,22),(22,2)], fill=(51,52,60,255), width=2)
d.point([(5,19),(10,14),(15,9),(20,4)], fill=(102,92,88,255))
# Blade: dark silhouette, steel body and silver cutting edge.
d.line([(9,23),(28,3)], fill=(15,18,24,255), width=5)
d.line([(9,23),(28,3)], fill=(126,139,152,255), width=3)
d.line([(10,22),(28,3)], fill=(222,232,238,255), width=1)
# Blood on the edge; no white bindings or dangling straps.
d.line([(16,17),(18,15)], fill=(157,17,34,255), width=1)
d.point((22,11), fill=(205,30,39,255))
# Compact guard and dark-crimson, wrapped handle.
d.line([(7,22),(11,26)], fill=(23,22,24,255), width=3)
d.point((9,23), fill=(176,149,108,255))
d.line([(3,30),(8,25)], fill=(15,14,19,255), width=4)
d.line([(3,30),(8,25)], fill=(161,28,43,255), width=2)
d.point([(4,28),(6,26)], fill=(42,16,23,255))
d.point((2,30), fill=(172,180,186,255))
im.resize((64,64),Image.Resampling.NEAREST).save(root / 'forge/resources/assets/stainkatana/textures/item/katana_stain_icon.png')
