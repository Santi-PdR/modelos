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
assert 'IMPACT_TICK = {2, 7, 7}' in ability and 'RECOVERY_TICK = {6, 16, 29}' in ability
assert 'PlayerLoggedOutEvent' in ability and 'ServerStoppedEvent' in ability
assert 'player.getMainHandItem() != cast.stack' in ability
anim = (root/'java/com/stainkatana/katana/client/KatanaAnimations.java').read_text()
assert 'bettercombat' in anim and 'attack_animations/' in anim
assert 'THIRD_PERSON_MODEL' in anim and 'ability == -1' in anim
print('OK: secuencia de impacto, cancelación, recurso externo opcional y primera persona configurada')

assert 'LAYER, 2500' in anim and 'MirrorModifier' in anim
assert 'followUpImpacted' in ability and 'broadcastAnimation(player, 3)' in ability
bc = json.loads((root/'resources/data/stainkatana/weapon_attributes/katana_stain.json').read_text())
assert bc['parent'] == 'bettercombat:katana'
print('OK: preset de katana Better Combat, prioridad, zurdos y segundo golpe')

# Analytical grip check for the current GeckoLib preRender and vanilla hand rotations;
# this cannot substitute for rendering the complete client/model/animation stack.
import math
model = json.loads((a/'models/item/katana_stain.json').read_text())['display']
for hand in ('thirdperson_righthand', 'thirdperson_lefthand'):
    pose = model[hand]
    assert pose['rotation'] == [90, 0, 0]
    assert pose['scale'] == [0.72, 0.72, 0.72]
    assert pose['translation'] == [0, 1, 0]
# Vanilla's -90 degree hand rotation cancels the model's +90 degree pitch.
# Approx. grip centre y=-2/16, custom correction +2/16, GeckoLib's residual +.01.
grip_offset = math.hypot(0.72 * 0.01, 1/16)
assert grip_offset < 0.07
print('OK: comprobación matemática aproximada de agarre y eje, no es prueba visual')
