#!/usr/bin/env python3
"""Fail closed if the standalone build loses FX, keys or isolation."""
import json, struct
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'build-katana-input'
a=root/'resources/assets/stainkatana'
for effect, count in [('slash_arc',6),('blood_shard',6),('blood_pulse',6),('blood_ring',7)]:
 data=json.loads((a/'particles'/f'{effect}.json').read_text())
 assert len(data['textures'])==count
 for entry in data['textures']:
  ns,name=entry.split(':'); assert ns=='stainkatana'
  image=(a/'textures/particle'/f'{name}.png').read_bytes()
  assert image[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',image[16:24])==(64,64)
for lang in ('es_es','en_us'):
 d=json.loads((a/'lang'/f'{lang}.json').read_text(encoding='utf8'))
 assert all(k in d for k in ('key.stainkatana.stun','key.stainkatana.slash','key.stainkatana.ultimate','effect.stainkatana.blood_paralysis'))
java='\n'.join(p.read_text() for p in (root/'java').rglob('*.java'))
assert 'ParticleTypes.' not in java and 'DustParticleOptions' not in java
assert 'NetworkDirection.PLAY_TO_SERVER' in java and 'player.canHarmPlayer' in java
assert 'capatest' not in java
assert 'paralysis' in (a/'lang/en_us.json').read_text().lower()
print('OK: 25 fotogramas de Better Combat Particle, tres teclas, seguridad de red e independencia de capatest')
clips = ('sword_attack', 'sword_attack2', 'stain_c_grip_trial', 'stain_c_grip_trial2', 'kelvin_swing_first', 'kelvin_swing_second', 'kelvin_swing_first_sneak', 'kelvin_swing_second_sneak', 'stain_c_grip_sneak', 'stain_c_grip_sneak2')
for clip in clips:
    animation = json.loads((a/'player_animation'/f'{clip}.json').read_text())['animations'][clip]
    assert animation.get('loop', False) is False and animation['animation_length'] > 0
assert 'PLAY_TO_CLIENT' in java and 'TRACKING_ENTITY_AND_SELF' in java
assert 'playeranimator' in (root/'resources/META-INF/mods.toml').read_text()
assert (root/'resources/META-INF/SERIOUS_PLAYER_ANIMATIONS_LICENSE.txt').is_file()
assert (root/'resources/META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt').is_file()
assert (root/'resources/META-INF/SERIOUS_PLAYER_ANIMATIONS_CC0.txt').is_file()
kelvin_license = (root/'resources/META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt').read_text()
assert 'Kevin Merrill' in kelvin_license and 'sword_swing_first' in kelvin_license
print('OK: clips externos no cíclicos, mensaje de animación y licencias')

ability = (root/'java/com/stainkatana/katana/KatanaAbilities.java').read_text()
timeline = (root/'java/com/stainkatana/katana/AbilityTimeline.java').read_text()
assert 'IMPACT_TICK = {9, 7, 10}' in timeline and 'FINISH_TICK = {21, 16, 200}' in timeline
assert 'PlayerLoggedOutEvent' in ability and 'ServerStoppedEvent' in ability
assert 'player.getMainHandItem() != cast.stack' in ability
anim = (root/'java/com/stainkatana/katana/client/KatanaAnimations.java').read_text()
assert 'loadBetterCombat' not in anim and 'sword_attack2' in anim and 'stain_c_overhead' in anim
assert 'kelvin_swing_first' in anim and 'stain_c_grip_trial2' in anim and 'MAX_ANIMATION_ID' in anim
assert 'THIRD_PERSON_MODEL' in anim and 'ability == -1' in anim
print('OK: secuencia de impacto, cancelación, recurso externo opcional y primera persona configurada')

assert 'LAYER, 2500' in anim and 'MirrorModifier' in anim
assert 'followUpImpacted' in ability and 'broadcastAnimation(player, 3)' in ability
bc = json.loads((root/'resources/data/stainkatana/weapon_attributes/katana_stain.json').read_text())
assert bc['parent'] == 'bettercombat:katana'
attacks = bc['attributes']['attacks']
assert len(attacks) == 4 and len({a['animation'] for a in attacks}) == 4
assert attacks[3]['damage_multiplier'] > max(a['damage_multiplier'] for a in attacks[:3])
for attack in attacks:
    assert attack['animation'].startswith('stainkatana:stain_')
    clip = json.loads((a/'attack_animations'/ (attack['animation'].split(':')[1] + '.json')).read_text())['emote']
    assert clip['beginTick'] > 0 and clip['stopTick'] > clip['endTick']
    assert all(set(move) <= {'tick', 'turn', 'easing', 'rightArm', 'leftArm', 'torso'} for move in clip['moves'])
print('OK: preset de katana Better Combat, prioridad, zurdos y segundo golpe')

# Model transforms are syntax-checked here; hand alignment requires actual client captures.
model = json.loads((a/'models/item/katana_stain.json').read_text())['display']
for hand in ('thirdperson_righthand', 'thirdperson_lefthand', 'firstperson_righthand', 'firstperson_lefthand'):
    assert len(model[hand]['rotation']) == len(model[hand]['translation']) == len(model[hand]['scale']) == 3
print('OK: transformaciones de mano válidas; pendiente revisión visual de agarre')

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
assert 'SAFETY_TIMEOUT = 212' in scene and 'mc.isPaused()' in scene
assert 'KatanaScene.start(ability == 6)' in anim and 'KatanaScene.stop()' in anim
assert (root/'resources/META-INF/CINEMASCOPE_LICENSE.txt').is_file()
assert 'betterCombatSound("katana_slash", SoundEvents.PLAYER_ATTACK_SWEEP)' in ability
assert 'betterCombatSound("rapier_stab", SoundEvents.PLAYER_ATTACK_SWEEP)' in ability
print('OK: encuadre local cancelable y sonido de Better Combat con alternativa')
visuals=(root/'java/com/stainkatana/katana/client/KatanaVisuals.java').read_text()
network=(root/'java/com/stainkatana/katana/KatanaNetwork.java').read_text()
assert 'KatanaVisualStyle.ULTIMATE_CROSS' in visuals and '^ leftHanded' in visuals
assert 'getId() == entityId' in visuals and 'KatanaScene.impact(style == KatanaVisualStyle.ULTIMATE_CROSS, leftHanded, x, y, z, decisive)' in visuals
assert 'private static final String VERSION = "11"' in network
assert 'buf.writeBoolean(msg.leftHanded)' in network and 'buf.readBoolean()' in network
assert 'impactEnvelope' in scene and 'KatanaClientConfig.ZOOM_FRACTION.get()' in scene
# 0.23.0-test: decisive-execution feedback and view-only shake.
cfg=(root/'java/com/stainkatana/katana/KatanaClientConfig.java').read_text()
assert 'SCREEN_SHAKE' in cfg and 'FINAL_FLASH' in cfg and 'TITLE_CARD' in cfg
assert 'applyShake' in scene and 'finalFlashAge' in scene and 'titleAge' in scene
assert 'S E N T E N C E' in visuals and 'P A R A L Y S I S' in visuals
mote=(root/'resources/assets/stainkatana/particles/blood_mote.json').read_text()
assert 'blood_pulse_0' in mote and 'blood_pulse_5' in mote
assert 'ParticleTypes.' not in visuals and 'MOTE' in (root/'java/com/stainkatana/katana/KatanaParticles.java').read_text()
print('OK: segundo corte, zurdos, impulso local y protocolo visual v11')

assert model['firstperson_righthand']['scale'] == [0.56, 0.56, 0.56]
assert model['firstperson_lefthand']['scale'] == [0.56, 0.56, 0.56]
assert 'visualYaw, 55, 0' in visuals and 'yaw, 90, sign * 25' in visuals
assert 'yaw, 55, -sign * 30' in visuals
assert 'KatanaVisualStyle.BLOOD_BIND' in visuals and 'KatanaVisualStyle.ULTIMATE_FINAL' in visuals
print('OK: escala de primera persona y planos de efectos de prueba')

assert 'startBackstab(player, state, now)' in ability
assert 'chargedAttack(' not in ability
assert 'CombatTuning.backstabDamage(' in ability
assert 'target.isMultipartEntity()' in ability and 'part.hurt(' in ability
