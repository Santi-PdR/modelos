#!/usr/bin/env python3
"""Adapt Improved Animations' MIT axe movement into a restrained katana overhead cut."""
import json
import math
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = json.loads((root/'referencias/improved_animations/attack_axe.json').read_text())
parts = {part['name']: part['keyframes'] for part in source['parts']}
bones = {}
for name, target in [('rightArm','rightArm'), ('leftArm','leftArm'), ('body','torso')]:
    track = {}
    for frame in range(11):
        values = [round(math.degrees(v), 4) for v in parts[name][str(frame)]['rotate']]
        if name == 'leftArm': values[0] = round(values[0] - 30, 4)
        if name == 'body': values = [0, values[1], 0]
        track[f'{frame * .0875:.4f}'] = {'vector': values, 'easing':'linear'}
    bones[target] = {'rotation':track}
# Carry the sword wrist orientation from Serious Player Animations instead of
# leaving the inherited item at its idle angle. This is an experimental
# cross-mod retarget: review contact and grip, not just the parsed values.
serious = json.loads((root/'forge/resources/assets/stainkatana/player_animation/sword_attack2.json').read_text())
bones['rightItem'] = serious['animations']['sword_attack2']['bones']['rightItem']
out = root/'forge/resources/assets/stainkatana/player_animation/stain_c_overhead.json'
out.write_text(json.dumps({'format_version':'1.8.0','animations':{'stain_c_overhead':{'animation_length':.875,'bones':bones}}},indent=2)+'\n')
print('Adapted', out)
