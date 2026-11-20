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
clips = ('eating_right', 'sword_attack', 'sword_attack2')
for clip in clips:
    animation = json.loads((a/'player_animation'/f'{clip}.json').read_text())['animations'][clip]
    assert animation.get('loop', False) is False and animation['animation_length'] > 0
assert 'PLAY_TO_CLIENT' in java and 'TRACKING_ENTITY_AND_SELF' in java
assert 'playeranimator' in (root/'resources/META-INF/mods.toml').read_text()
assert (root/'resources/META-INF/SERIOUS_PLAYER_ANIMATIONS_LICENSE.txt').is_file()
print('OK: tres clips externos no cíclicos, mensaje de animación y licencia')

ability = (root/'java/com/stainkatana/katana/KatanaAbilities.java').read_text()
assert 'IMPACT_TICK = {2, 7, 7}' in ability and 'RECOVERY_TICK = {6, 19, 20}' in ability
assert 'PlayerLoggedOutEvent' in ability and 'ServerStoppedEvent' in ability
assert 'player.getMainHandItem() != cast.stack' in ability
anim = (root/'java/com/stainkatana/katana/client/KatanaAnimations.java').read_text()
assert 'bettercombat' in anim and 'attack_animations/' in anim
assert 'THIRD_PERSON_MODEL' in anim and 'ability == -1' in anim
print('OK: secuencia de impacto, cancelación, recurso externo opcional y primera persona configurada')
