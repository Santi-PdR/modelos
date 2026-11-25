#!/usr/bin/env python3
"""Experimental wrist retargets of MIT Serious Player Animations for C.

Only the item translation is changed, by phase, to test the Stain katana's
hand pivot. This approximation is not visually approved, and is separate
from the original clip so normal attacks remain unchanged.

Emits:
  stain_c_grip_trial.json  - from sword_attack2 (1.0 s), unchanged windows
  stain_c_grip_trial2.json - from sword_attack (0.875 s), windows scaled by
                             0.875 so both compensated cuts share pacing
"""
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/player_animation'

source = json.loads((base / 'sword_attack2.json').read_text())
clip = source['animations']['sword_attack2']
assert clip['bones']['rightItem']['position'] == {'vector': [0, 3, 0]}, 'Source changed; review retarget.'
clip['bones']['rightItem']['position'] = {
    '0.0': {'vector': [0, 3, 0]},
    '0.25': {'vector': [0, 3, 0], 'easing': 'linear'},
    '0.375': {'vector': [0, 15, 0], 'easing': 'linear'},
    '0.5625': {'vector': [0, 15, 0], 'easing': 'linear'},
    '1.0': {'vector': [0, 3, 0], 'easing': 'linear'},
}
out = {'format_version': source['format_version'], 'animations': {'stain_c_grip_trial': clip}}
(base / 'stain_c_grip_trial.json').write_text(json.dumps(out, indent=2) + '\n')

source = json.loads((base / 'sword_attack.json').read_text())
clip = source['animations']['sword_attack']
SCALE = 0.875
assert clip['animation_length'] == SCALE, 'Source changed; review retarget.'
assert clip['bones']['rightItem']['position']['0.25']['vector'] == [0, 3, 0], 'Source changed; review retarget.'
clip['bones']['rightItem']['position'] = {
    '0.0': {'vector': [0, 3, 0]},
    f'{0.25 * SCALE:.6g}': {'vector': [0, 3, 0], 'easing': 'linear'},
    f'{0.375 * SCALE:.6g}': {'vector': [0, 15, 0], 'easing': 'linear'},
    f'{0.5625 * SCALE:.6g}': {'vector': [0, 15, 0], 'easing': 'linear'},
    f'{SCALE:.6g}': {'vector': [0, 3, 0], 'easing': 'linear'},
}
out = {'format_version': source['format_version'], 'animations': {'stain_c_grip_trial2': clip}}
(base / 'stain_c_grip_trial2.json').write_text(json.dumps(out, indent=2) + '\n')
