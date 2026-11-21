#!/usr/bin/env python3
"""Reopen the editable model and check standalone Gecko geometry/embedded texture parity."""
import base64, json, math, struct
from pathlib import Path
R = Path(__file__).resolve().parents[2]
m = json.loads((R/'katana_stain/Katana_de_Stain.bbmodel').read_text())
a = R/'katana_stain/forge/resources/assets/stainkatana'
g = json.loads((a/'geo/item/katana_stain.geo.json').read_text())['minecraft:geometry'][0]
assert m['resolution'] == {'width':512, 'height':512}
embedded = base64.b64decode(m['textures'][0]['source'].split(',',1)[1], validate=True)
assert struct.unpack('>II', embedded[16:24]) == (512,512)
runtime = (a/'textures/item/katana_stain.png').read_bytes()
assert runtime[:8] == b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II', runtime[16:24]) == (256,256)
assert (g['description']['texture_width'], g['description']['texture_height']) == (512,512)
by_id={e['uuid']:e for e in m['elements']}; groups={g['uuid']:g for g in m['groups']}
bones={b['name']:b for b in g['bones']}
assert {'hoja','guarda','empunadura'} <= set(bones)
assert all(bones[name]['parent'] == bones['hoja']['parent'] for name in ('guarda','empunadura'))
assert not any('venda' in e['name'].lower() for e in m['elements'])
seen=set(); visible=0
def walk(nodes):
    global visible
    for node in nodes:
        if isinstance(node,str):
            assert node in by_id and node not in seen
            seen.add(node)
        else:
            group=groups[node['uuid']]
            if not group.get('visibility',True) or not group.get('export',True): continue
            cubes=[by_id[x] for x in node['children'] if isinstance(x,str) and by_id[x].get('visibility',True) and by_id[x].get('export',True)]
            exported=bones[group['name']].get('cubes',[])
            assert len(cubes)==len(exported), group['name']
            for e,c in zip(cubes,exported):
                f,t=e['from'],e['to']
                for actual,want in zip(c['origin'],[-t[0],f[1],f[2]]): assert math.isclose(actual,want,abs_tol=1e-5)
                for actual,want in zip(c['size'],[t[i]-f[i] for i in range(3)]): assert math.isclose(actual,want,abs_tol=1e-4)
                assert all(t[i]>=f[i] for i in range(3))
                visible+=1
            walk(node['children'])
walk(m['outliner'])
assert visible==82
assert not any(b['name']=='vaina' for b in g['bones'])
print('OK: .bbmodel reabierto; textura editable 512, textura de juego 256 y 82 cubos exportados; vaina oculta')
