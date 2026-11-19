#!/usr/bin/env python3
"""Original hand-shaped, animated pixel-art FX for the independent katana mod.
Requires Pillow. Never reads or copies third-party mod assets.
"""
import json,math,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[2]/'katana_stain/forge/resources/assets/stainkatana'
T=ROOT/'textures/particle';T.mkdir(parents=True,exist_ok=True)
P=ROOT/'particles';P.mkdir(parents=True,exist_ok=True)
S=256

def out(name,frames):
 for i,im in enumerate(frames):im.resize((64,64),Image.Resampling.LANCZOS).save(T/f'{name}_{i}.png')
 (P/f'{name}.json').write_text(json.dumps({'textures':[f'stainkatana:{name}_{i}' for i in range(len(frames))]},indent=2)+'\n')
def blend(base,overlay):return Image.alpha_composite(base,overlay)
# A blade-shaped arc whose tail recedes while the leading point advances.
frames=[]
for frame in range(8):
 layer=Image.new('RGBA',(S,S));d=ImageDraw.Draw(layer)
 start=max(0,(frame-2)/8);end=min(1,(frame+3)/8)
 def pos(t):return (int(26+204*t),int(211-169*t+34*math.sin(t*math.pi)))
 segments=100
 for i in range(segments):
  t=start+(end-start)*i/segments;t2=start+(end-start)*(i+1)/segments
  taper=max(.1,math.sin(math.pi*(t-start)/max(.001,end-start)))
  width=int(8+19*taper)
  d.line([pos(t),pos(t2)],fill=(105,8,24,135),width=width+18)
  d.line([pos(t),pos(t2)],fill=(164,23,35,205),width=width)
 glow=layer.filter(ImageFilter.GaussianBlur(14)); layer=blend(glow,layer);d=ImageDraw.Draw(layer)
 for i in range(segments):
  t=start+(end-start)*i/segments;t2=start+(end-start)*(i+1)/segments
  taper=max(.07,math.sin(math.pi*(t-start)/max(.001,end-start)))
  d.line([pos(t),pos(t2)],fill=(228,211,211,245),width=max(2,int(2+6*taper)))
  if .2<t<.85:
   x,y=pos(t);d.point((x-4,y-5),fill=(255,255,244,190))
 frames.append(layer)
out('slash_arc',frames)
# Blood-like angular fragments, fade over time, not vanilla particles.
frames=[]
for frame in range(6):
 a=max(0,int(235*(1-frame/6)))
 im=Image.new('RGBA',(S,S));d=ImageDraw.Draw(im)
 d.polygon([(111,24),(139,39),(155,102),(138,206),(112,228),(95,145),(91,76)], fill=(103,7,16,a))
 d.polygon([(111,36),(128,53),(133,100),(121,168),(108,142),(105,77)], fill=(205,30,39,a))
 d.polygon([(111,45),(117,52),(116,105),(109,115)],fill=(247,124,117,a))
 frames.append(im)
out('blood_shard',frames)
# A broken circular pulse, not an occult symbol, for a blood-mark activation.
frames=[]
for frame in range(8):
 im=Image.new('RGBA',(S,S));d=ImageDraw.Draw(im);radius=25+frame*11;alpha=max(0,220-frame*24)
 for start,end in ((-15,58),(76,139),(160,237),(258,323)):
  box=(128-radius,128-radius,128+radius,128+radius)
  d.arc(box,start,end,fill=(179,19,29,alpha),width=9)
  inner=radius-5;d.arc((128-inner,128-inner,128+inner,128+inner),start+3,end-3,fill=(245,96,87,alpha),width=3)
 frames.append(im)
out('blood_pulse',frames)
print('FX originales:',len(list(T.glob('*.png'))),'sprites')
