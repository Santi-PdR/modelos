#!/usr/bin/env python3
"""Original fallback katana movement, in PlayerAnimator/Bedrock degrees.

The contact pose is at tick 6 (0.3 seconds). No external animation is embedded.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
# Anticipation, peak of backswing, contact and recovery. The whole-body
# channels give the free arm and shoulders a purpose instead of only turning
# the item around an unanimated hand. Visually verify the grip before release.
poses = {
    'rightArm': [[-105, -15, -25], [-155, -25, -30], [-65, 15, 20], [-40, 0, 5]],
    'leftArm':  [[-70, 15, 20], [-130, 20, 20], [-65, -10, -15], [-30, 0, -5]],
    'torso':    [[0, 10, 0], [-8, 20, 0], [18, -15, 0], [0, 0, 0]],
    'body':     [[0, 0, 0], [0, 8, 0], [0, -8, 0], [0, 0, 0]],
    'rightItem':[[0, 0, 0], [15, 0, 0], [-45, 0, 0], [0, 0, 0]],
}
times = ('0.000', '0.150', '0.300', '0.550')
bones = {name: {'rotation': {t: {'vector': value, 'easing': 'easeInOutSine'}
                             for t, value in zip(times, values)}}
         for name, values in poses.items()}
clip = {'format_version': '1.8.0', 'animations': {'stain_c_fallback': {
    'animation_length': .65, 'bones': bones}}}
out = root / 'forge/resources/assets/stainkatana/player_animation/stain_c_fallback.json'
out.write_text(json.dumps(clip, indent=2) + '\n')
print('Created', out)
