#!/usr/bin/env python3
"""Export the arms-only fourth cut for Better Combat 1.20.1 (experimental).

The body/torso/head have no keyed transforms, so the stroke never asks the
animation library to translate or pitch the player. Hit timing remains BC's.
"""
import json
import math
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = json.loads((root/'forge/resources/assets/stainkatana/player_animation/combo_heavy.json').read_text())
source = source['animations']['combo_heavy']['bones']
moves = []
for bone in ('rightArm', 'leftArm'):
    samples = list(source[bone]['rotation'].values())
    for tick, sample in zip((6, 9, 17, 25), samples):
        pitch, yaw, roll = [round(math.radians(n), 6) for n in sample['vector']]
        moves.append({'tick': tick, 'easing': 'EASEINOUTSINE', 'turn': 0,
                      bone: {'pitch': pitch, 'yaw': yaw, 'roll': roll}})
clip = {'name':'stain_fourth_cut', 'author':'Stain Katana',
        'description':'Fourth katana cut; arms only, no body tilt.',
        'emote':{'isLoop':'false', 'returnTick':2, 'beginTick':6,
                 'endTick':25, 'stopTick':30, 'degrees':False, 'moves':moves}}
out = root/'forge/resources/assets/stainkatana/attack_animations/stain_fourth_cut.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(clip, indent=2)+'\n')
print('Created', out)
