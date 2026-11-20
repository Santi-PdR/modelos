#!/usr/bin/env python3
"""Export the editable katana to GeckoLib 4's Bedrock geometry; no cape assets touched."""
import base64,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]; model=json.loads((R/'katana_stain/Katana_de_Stain.bbmodel').read_text()); root=R/'katana_stain/forge/resources/assets/stainkatana'
groups={g['uuid']:g for g in model['groups']}; els={e['uuid']:e for e in model['elements']}; bones=[]
def mirror(v): return [-v[0],v[1],v[2]]
def cube(e):
 f,t=e['from'],e['to']; item={'origin':[-t[0],f[1],f[2]],'size':[round(t[i]-f[i],5) for i in range(3)],'uv':{}}
 if any(e.get('rotation',[0,0,0])):
  item['pivot']=mirror(e['origin']);r=e['rotation'];item['rotation']=[-r[0],-r[1],r[2]]
 if e.get('inflate',0):item['inflate']=e['inflate']
 for name,face in e['faces'].items():
  if face.get('texture') is None or not face.get('enabled',True):continue
  a,b,c,d=face['uv']
  if name in ('up','down'):a,b,c,d=c,d,a,b
  item['uv'][name]={'uv':[a,b],'uv_size':[round(c-a,5),round(d-b,5)]}
 return item
def walk(ns,parent=None):
 for n in ns:
  if isinstance(n,str): continue
  g=groups[n['uuid']]
  if not g.get('visibility',True) or not g.get('export',True):continue
  bone={'name':g['name'],'pivot':mirror(g['origin'])}
  if parent:bone['parent']=parent
  if any(g.get('rotation',[0,0,0])):
   x,y,z=g['rotation'];bone['rotation']=[-x,-y,z]
  cubes=[cube(els[u]) for u in n['children'] if isinstance(u,str) and els[u].get('visibility',True) and els[u].get('export',True)]
  if cubes:bone['cubes']=cubes
  bones.append(bone);walk(n['children'],g['name'])
walk(model['outliner'])
geo={'format_version':'1.12.0','minecraft:geometry':[{'description':{'identifier':'geometry.katana_stain','texture_width':512,'texture_height':512,'visible_bounds_width':4,'visible_bounds_height':4,'visible_bounds_offset':[0,1,0]},'bones':bones}]}
path=root/'geo/item/katana_stain.geo.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(geo,indent=2)+'\n')
path=root/'textures/item/katana_stain.png';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(model['textures'][0]['source'].split(',',1)[1]))
print('Wrote',sum(len(b.get('cubes',[])) for b in bones),'cubes,',len(bones),'bones')
