#!/usr/bin/env python3
"""Adapt the CC0 crouched cuts from Serious Player Animations' template pack.

Source (template resource pack, published by the Serious Player Animations
author as CC0-1.0; verified 2026-11-25):
  repo:   McVader34/Serious-Player-Animations-Template-Resource-Pack
  branch: main
  files:  player_animation/sword_attack_sneak.json
          sha256 6a5ce096cb391bb33ccf444679de8d94178c0dd28dac052e03a81cf55cf8f1d9
          player_animation/sword_attack_sneak2.json
          sha256 445e27b0aaf15c098d1c269edfe1ae003682a8976c44eddbd6f523443f0690e2
          (license: Creative Commons Zero v1.0 Universal)

These are the agazapadas counterparts of sword_attack / sword_attack2 used for
stain_c_grip_trial2 / stain_c_grip_trial. Only the item translation is changed,
by phase, to test the Stain katana's hand pivot; the motion itself is the
upstream clip. Same convention as tools/adaptar_agarre_c.py:
  stain_c_grip_sneak  (0.875 s) <- sword_attack_sneak   (windows x 0.875)
  stain_c_grip_sneak2 (1.0 s)   <- sword_attack_sneak2  (absolute windows)
Not visually approved; separate from the original clips so normal attacks
remain unchanged.

Usage:
  python3 tools/adaptar_agarre_c_cc0.py --src-dir /path/to/raw [out_dir]
"""
import argparse
import json
from pathlib import Path

RAMP_START, CONTACT_START, CONTACT_END = 0.25, 0.375, 0.5625

def convert(src_path, dst_path, clip_name, original_length):
    source = json.loads(src_path.read_text())
    key = clip_name
    assert key in source['animations'], f'Clip {clip_name} not in {src_path}'
    clip = source['animations'][key]
    assert abs(clip['animation_length'] - original_length) < 1e-6, 'Source length changed; review retarget.'
    right_item = clip['bones'].get('rightItem', {})
    position = right_item.get('position', {})
    values = ([position.get('vector')] if isinstance(position, dict) and 'vector' in position
              else [v.get('vector') for v in position.values() if isinstance(v, dict)])
    assert values and all(v == [0, 3, 0] for v in values), \
        f'Source rightItem changed from static hilt offset: {position!r}. Review retarget.'
    scale = original_length
    end = f'{original_length:.6g}'
    clip['bones']['rightItem']['position'] = {
        '0.0': {'vector': [0, 3, 0]},
        f'{RAMP_START * scale:.6g}': {'vector': [0, 3, 0], 'easing': 'linear'},
        f'{CONTACT_START * scale:.6g}': {'vector': [0, 15, 0], 'easing': 'linear'},
        f'{CONTACT_END * scale:.6g}': {'vector': [0, 15, 0], 'easing': 'linear'},
        end: {'vector': [0, 3, 0], 'easing': 'linear'},
    }
    name = 'stain_c_grip_sneak' if original_length < 1.0 else 'stain_c_grip_sneak2'
    clip['loop'] = False
    out = {'format_version': source['format_version'], 'animations': {name: clip}}
    dst_path.write_text(json.dumps(out, indent=2) + '\n')
    print(f'{src_path.name} -> {dst_path.name} (rightItem window x{scale:.3g})')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src-dir', required=True, type=Path)
    parser.add_argument('out_dir', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/player_animation')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    convert(args.src_dir / 'sword_attack_sneak.json', args.out_dir / 'stain_c_grip_sneak.json',
            'sword_attack_sneak', 0.875)
    convert(args.src_dir / 'sword_attack_sneak2.json', args.out_dir / 'stain_c_grip_sneak2.json',
            'sword_attack_sneak2', 1.0)

if __name__ == '__main__':
    main()
