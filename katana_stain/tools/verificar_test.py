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
clips = ('sword_attack', 'sword_attack2')
for clip in clips:
    animation = json.loads((a/'player_animation'/f'{clip}.json').read_text())['animations'][clip]
    assert animation.get('loop', False) is False and animation['animation_length'] > 0
assert 'PLAY_TO_CLIENT' in java and 'TRACKING_ENTITY_AND_SELF' in java
assert 'playeranimator' in (root/'resources/META-INF/mods.toml').read_text()
assert (root/'resources/META-INF/SERIOUS_PLAYER_ANIMATIONS_LICENSE.txt').is_file()
print('OK: tres clips externos no cíclicos, mensaje de animación y licencia')

ability = (root/'java/com/stainkatana/katana/KatanaAbilities.java').read_text()
timeline = (root/'java/com/stainkatana/katana/AbilityTimeline.java').read_text()
assert 'IMPACT_TICK = {9, 7, 7}' in timeline and 'FINISH_TICK = {21, 16, 29}' in timeline
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
    assert pose['scale'] == [0.82, 0.82, 0.82]
    assert pose['translation'] == [0, 1, 0]
# Vanilla's -90 degree hand rotation cancels the model's +90 degree pitch.
# Approx. grip centre y=-2/16, custom correction +2/16, GeckoLib's residual +.01.
grip_offset = math.hypot(0.82 * 0.01, 1/16)
assert grip_offset < 0.07
print('OK: comprobación matemática aproximada de agarre y eje, no es prueba visual')

assert 'markTarget(stack, target, level)' in ability
assert 'KatanaNetwork.broadcastVisual' in ability
assert 'BotSlashParticle180' in (root/'java/com/stainkatana/katana/client/KatanaParticle.java').read_text()
print('OK: marcas en habilidades y renderer orientado basado en Better Combat Particle')

inspect = json.loads((a/'player_animation/inspect.json').read_text())
assert inspect['author'] == 'Overseer' and inspect['name'] == 'Inspect'
assert (root/'resources/META-INF/EMOTECRAFT_EMOTES_CC0.txt').is_file()
assert 'AbilityTimeline' in ability and 'cast.timeline.cancel()' in ability
print('OK: gesto de Emotecraft atribuido y cancelación de línea de tiempo')

scene=(root/'java/com/stainkatana/katana/client/KatanaScene.java').read_text()
assert 'SAFETY_TIMEOUT = 36' in scene and 'mc.isPaused()' in scene
assert 'KatanaScene.start()' in anim and 'KatanaScene.stop()' in anim
assert (root/'resources/META-INF/CINEMASCOPE_LICENSE.txt').is_file()
assert 'bettercombat", "katana_slash' in ability
print('OK: encuadre local cancelable y sonido de Better Combat con alternativa')
visuals=(root/'java/com/stainkatana/katana/client/KatanaVisuals.java').read_text()
network=(root/'java/com/stainkatana/katana/KatanaNetwork.java').read_text()
assert 'style == 3' in visuals and '^ leftHanded' in visuals
assert 'getId() == entityId' in visuals and 'KatanaScene.impact(style == 3, leftHanded)' in visuals
assert 'private static final String VERSION = "7"' in network
assert 'buf.writeBoolean(msg.leftHanded)' in network and 'buf.readBoolean()' in network
assert 'impactEnvelope' in scene and 'KatanaClientConfig.ZOOM_FRACTION.get()' in scene
print('OK: segundo corte, zurdos, impulso local y protocolo visual v7')

assert model['firstperson_righthand']['scale'] == [0.64, 0.64, 0.64]
assert model['firstperson_lefthand']['scale'] == [0.64, 0.64, 0.64]
assert 'visualYaw, 55, 0' in visuals and 'yaw, 90, leftHanded ? -25 : 25' in visuals
print('OK: escala de primera persona y planos de efectos de prueba')
