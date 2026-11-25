#!/usr/bin/env python3
"""Experimental wrist retarget of MIT Serious Player Animations for C.

Only the item translation is changed, by phase, to test the Stain katana's
hand pivot. This approximation is not visually approved, and is separate
from the original clip so normal attacks remain unchanged.
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
