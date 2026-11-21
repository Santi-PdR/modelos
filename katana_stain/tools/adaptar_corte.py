#!/usr/bin/env python3
"""Convert Improved Animations' MIT sword-arm samples to a PlayerAnimator clip.

Source: ProjectSlenders/Improved-Animations, commit 9371f058d3b29e25bce6ef67ec1ea416dac0e4b1.
Only arm rotations and torso yaw are adapted; its renderer-specific translations,
head, legs, cape and hand bones are intentionally excluded. Test visually before release.
"""
import json
import math
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = root / 'referencias/improved_animations/attack_sword.json'
out = root / 'forge/resources/assets/stainkatana/player_animation/stain_x_cut.json'
data = json.loads(src.read_text())
parts = {part['name']: part['keyframes'] for part in data['parts']}
bones = {}
for source, target in [('rightArm', 'rightArm'), ('leftArm', 'leftArm'), ('body', 'torso')]:
    track = {}
    for frame in range(11):
        rotation = parts[source][str(frame)]['rotate']
        values = [round(math.degrees(v), 4) for v in rotation]
        # Rotate torso only around Y: no crouch/translation or whole-body deformation.
        if source == 'body': values = [0, values[1], 0]
        track[f'{frame * .0875:.4f}'] = {'vector': values, 'easing': 'linear'}
    bones[target] = {'rotation': track}
clip = {'format_version': '1.8.0', 'animations': {'stain_x_cut': {'animation_length': .875, 'bones': bones}}}
out.write_text(json.dumps(clip, indent=2) + '\n')
print('Adapted', src, 'to', out)
