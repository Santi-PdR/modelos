#!/usr/bin/env python3
"""Fail closed if the standalone build loses FX, keys or isolation."""
import json, struct
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'build-katana-input'
a=root/'resources/assets/stainkatana'
for effect, count in [('slash_arc',6),('blood_shard',6),('blood_pulse',6)]:
 data=json.loads((a/'particles'/f'{effect}.json').read_text())
 assert len(data['textures'])==count
 for entry in data['textures']:
  ns,name=entry.split(':'); assert ns=='stainkatana'
  image=(a/'textures/particle'/f'{name}.png').read_bytes()
  assert image[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',image[16:24])==(128,128)
for lang in ('es_es','en_us'):
 d=json.loads((a/'lang'/f'{lang}.json').read_text(encoding='utf8'))
 assert all(k in d for k in ('key.stainkatana.stun','key.stainkatana.slash','key.stainkatana.ultimate','effect.stainkatana.blood_paralysis'))
java='\n'.join(p.read_text() for p in (root/'java').rglob('*.java'))
assert 'ParticleTypes.' not in java and 'DustParticleOptions' not in java
assert 'NetworkDirection.PLAY_TO_SERVER' in java and 'player.canHarmPlayer' in java
assert 'capatest' not in java
assert 'paralysis' in (a/'lang/en_us.json').read_text().lower()
print('OK: 18 fotogramas de Better Combat Particle, tres teclas, seguridad de red e independencia de capatest')
