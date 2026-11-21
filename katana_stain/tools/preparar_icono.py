#!/usr/bin/env python3
"""Use the user-supplied picture as-is, removing only exterior white background.
Requires Pillow. Original stays in referencias/icono_sangre_usuario.png.
"""
from collections import deque
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parents[1]
im = Image.open(root / 'referencias/icono_sangre_usuario.png').convert('RGBA')
w,h=im.size
src=im.load(); seen=bytearray(w*h); q=deque()
def white(x,y):
    r,g,b,a=src[x,y]
    return min(r,g,b)>=246 and max(r,g,b)-min(r,g,b)<=7
for x in range(w):
    for y in (0,h-1):
        if white(x,y) and not seen[y*w+x]: seen[y*w+x]=1;q.append((x,y))
for y in range(h):
    for x in (0,w-1):
        if white(x,y) and not seen[y*w+x]: seen[y*w+x]=1;q.append((x,y))
while q:
    x,y=q.popleft()
    for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
        if 0<=xx<w and 0<=yy<h and not seen[yy*w+xx] and white(xx,yy):
            seen[yy*w+xx]=1;q.append((xx,yy))
for y in range(h):
    for x in range(w):
        if seen[y*w+x]: src[x,y]=(0,0,0,0)
bbox=im.getbbox()
if not bbox: raise ValueError('Empty reference')
im=im.crop(bbox)
im.thumbnail((60,60), Image.Resampling.LANCZOS)
out=Image.new('RGBA',(64,64)); out.alpha_composite(im,((64-im.width)//2,(64-im.height)//2))
out.save(root/'forge/resources/assets/stainkatana/textures/item/katana_stain_icon.png')
