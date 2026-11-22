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
# Original wrist motion for the katana: the axe reference does not animate the
# held item. Tilt the blade through the downstroke, then settle it back; the
# player model arm remains the parent, so both follow the same hand transform.
# These angles are authored for this mod, not copied from Better Combat.
bones['rightItem'] = {'rotation': {
    '0.0000': {'vector': [0, 0, 0], 'easing': 'linear'},
    '0.1750': {'vector': [20, 0, 0], 'easing': 'linear'},
    '0.3500': {'vector': [-35, 0, 0], 'easing': 'linear'},
    '0.4375': {'vector': [-45, 0, 0], 'easing': 'linear'},
    '0.6125': {'vector': [-20, 0, 0], 'easing': 'linear'},
    '0.8750': {'vector': [0, 0, 0], 'easing': 'linear'},
}}
out = root/'forge/resources/assets/stainkatana/player_animation/stain_c_overhead.json'
out.write_text(json.dumps({'format_version':'1.8.0','animations':{'stain_c_overhead':{'animation_length':.875,'bones':bones}}},indent=2)+'\n')
print('Adapted', out)
