#!/usr/bin/env python3
"""Experimental C-only wrist retarget of MIT Serious Player Animations.

The source's fixed three-pixel item translation is authored for another
weapon/model. Neutralize only that translation, leaving rotation, timing and
all other bones unchanged. Visually inspect every phase before accepting it.
"""
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/player_animation'
source = json.loads((base / 'sword_attack2.json').read_text())
clip = source['animations']['sword_attack2']
position = clip['bones']['rightItem']['position']
assert position == {'vector': [0, 3, 0]}, 'source wrist changed; review the retarget'
clip['bones']['rightItem']['position'] = {'vector': [0, 0, 0]}
out = {'format_version': source['format_version'], 'animations': {'stain_c_serious2': clip}}
(base / 'stain_c_serious2.json').write_text(json.dumps(out, indent=2) + '\n')
