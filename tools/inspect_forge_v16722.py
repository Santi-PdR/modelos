"""Export a small, quantized subset from the archived Forge reference for fitting."""
import argparse
from base64 import b64encode
import json
import zlib
from pathlib import Path
import numpy as np
from cape_fit import fixed_wearer_pose
from preview_cloth import ARMOR_GEO, load
from verify_v1660 import WornModel, contacts
from verify_forge_postures import read_boxes, ACTOR

p=argparse.ArgumentParser()
p.add_argument('base',type=Path); p.add_argument('slot')
a=p.parse_args()
rig=WornModel(fixed_wearer_pose(load(ARMOR_GEO),0.))
b=read_boxes(a.base/f'revision-alex-{a.slot}-cubos.tsv')
names=rig.names + list(ACTOR)
assert sorted(b)==list(range(76))
xyz=[]
for frame in b.values():
 xyz.append([frame[n].pop(0) for n in names])
v=np.array(xyz)
n=len(rig.names)
arm=contacts(v[52:,:n],v[52:,n+4:n+6])
print('::notice title=Intersecciones .22::Pico de brazos '+str([(int(i)+52,names[int(k)],float(-arm[i,j,k]))
         for j in range(2) for i,k in [np.unravel_index(np.argmin(arm[:,j,:]),arm[:,j,:].shape)]]))
frames=sorted(set([0,8,16,20,24,32,44,52,55,58,61,64,67,70,73,75,
                   *[arm[:,j][:,rig.cloth].min(1).argmin()+52 for j in range(2)]]))
sample=np.rint(v[frames][:,:,[0,1,3,4]]*512)
assert np.abs(sample).max()<32767
packed=b64encode(zlib.compress(sample.astype('<i2').tobytes(),9)).decode('ascii')
print(f'::notice title=Referencia {a.slot} resumen::'+json.dumps(dict(frames=list(map(int,frames)),parts=len(names),bytes=len(packed)),separators=(',',':')))
for i in range(0,len(packed),12000):
 print(f'::notice title=Referencia {a.slot} {i//12000:03d}::{packed[i:i+12000]}')
