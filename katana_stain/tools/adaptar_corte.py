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
        # Preserve the imported timing/shape, but raise the sword and amplify its
        # arc for a readable katana wind-up instead of a small idle-arm gesture.
        if source == 'rightArm':
            values = [round(-45 + values[0] * 1.15, 4), round(values[1] * 1.2, 4), round(values[2] * 1.2, 4)]
        elif source == 'leftArm':
            values[0] = round(values[0] - 35, 4)
        # Rotate torso only around Y: no crouch/translation or whole-body deformation.
        elif source == 'body': values = [0, values[1], 0]
        track[f'{frame * .0875:.4f}'] = {'vector': values, 'easing': 'linear'}
    bones[target] = {'rotation': track}
clip = {'format_version': '1.8.0', 'animations': {'stain_x_cut': {'animation_length': .875, 'bones': bones}}}
out.write_text(json.dumps(clip, indent=2) + '\n')
print('Adapted', src, 'to', out)
