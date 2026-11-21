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
out = root/'forge/resources/assets/stainkatana/player_animation/stain_c_overhead.json'
out.write_text(json.dumps({'format_version':'1.8.0','animations':{'stain_c_overhead':{'animation_length':.875,'bones':bones}}},indent=2)+'\n')
print('Adapted', out)
