#!/usr/bin/env python3
"""Retarget MIT Serious Player Animations / Improved Animations to Better Combat.

Uses only torso and arm rotations from the included PlayerAnimator clips. World
position, head and leg channels are deliberately omitted: they are authored for
other renderers. Contact keyframes are rescaled to tick 12 of a 24-tick attack;
Better Combat still controls attack cooldown, hitbox and damage. This is an
experimental retarget and must be reviewed in the actual client, both hands.
"""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana'
clips = [('stain_serious_1', 'sword_attack', .375, False),
         ('stain_serious_2', 'sword_attack2', .375, False),
         ('stain_improved_3', 'stain_c_overhead', .4375, False),
         ('stain_improved_4', 'stain_c_overhead', .4375, True)]
for name, source, contact, mirrored in clips:
    original = json.loads((root / 'player_animation' / (source + '.json')).read_text())['animations'][source]
    moves = []
    for bone in ('rightArm', 'leftArm', 'torso'):
        track = original['bones'].get(bone, {}).get('rotation', {})
        for time, frame in track.items():
            # BC evaluates positions in integer ticks, collision pairs are
            # deliberately coalesced by using a consistent time scale.
            tick = round(float(time) * 12 / contact)
            if tick > 24:
                continue
            pitch, yaw, roll = frame['vector']
            if mirrored:
                yaw, roll = -yaw, -roll
            values = dict(zip(('pitch', 'yaw', 'roll'),
                              [round(math.radians(v), 6) for v in (pitch, yaw, roll)]))
            moves.append({'tick': tick, 'easing': 'LINEAR', 'turn': 0, bone: values})
    moves.sort(key=lambda m: (m['tick'], next(k for k in m if k in ('rightArm', 'leftArm', 'torso'))))
    clip = {'name': name, 'author': 'Adapted from ' + ('Serious Player Animations' if source.startswith('sword') else 'Improved Animations'),
            'description': 'Experimental rotation-only retarget; check grip and timing in game.',
            'emote': {'isLoop': 'false', 'returnTick': 2, 'beginTick': 3, 'endTick': 24,
                      'stopTick': 30, 'degrees': False, 'moves': moves}}
    (root / 'attack_animations' / (name + '.json')).write_text(json.dumps(clip, indent=2) + '\n')
    print('Generated', name, 'from', source)
