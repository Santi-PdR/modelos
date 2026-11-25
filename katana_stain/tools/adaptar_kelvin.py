#!/usr/bin/env python3
"""Adapt Kelvin's Better Player Animations sword swings for C.

Source (archived, unmaintained upstream):
  repo: mrzenc/kelvins-better-anims @ b03e0e1049a307fcaf8e7a20732e88911a1ba1c6
  files: src/main/resources/assets/betteranimations/player_animation/
         sword_swing_first.json  sha256 fb7cd3c1b1541234bac2ff9696c0dc1735a7ac771c5c3f487af85c8a02fa9b5c
         sword_swing_second.json sha256 ad12245eb07ac408d019c3a3a043114f3646696b99ed555def458454c76bdd6b
License: MIT, Copyright (c) 2023 Kevin Merrill (see
         forge/resources/META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt).

The upstream clip predates PlayerAnimator's current bone naming, so bones are
renamed snake_case -> camelCase and `geckolib_format_version` is dropped
(it is an ignored leftover key). All keyframe times are rescaled so both
cuts last 0.9 s with the contact window aligned to the Serious Player
Animations clips used for C; the katana hilt compensation used for the
lateral trial is injected as a `rightItem` bone with the same phase window
(3 -> 15 model pixels between 0.25 s and 0.5625 s, back to 3 at the end).

Usage:
  python3 tools/adaptar_kelvin.py --src-dir /path/to/raw [out_dir]

The raw files are NOT redistributed; this script derives the shipped clips
only from sources the developer fetched separately.
"""
import argparse
import json
from pathlib import Path

BONE_RENAME = {
    'right_arm': 'rightArm',
    'left_arm': 'leftArm',
    'right_leg': 'rightLeg',
    'left_leg': 'leftLeg',
    'body': 'body',
    'head': 'head',
    'torso': 'torso',
}
TARGET_LENGTH = 0.9
# Phase window for the hilt compensation, in seconds (matches stain_c_grip_trial).
RAMP_START, CONTACT_START, CONTACT_END = 0.25, 0.375, 0.5625


def rescale_keys(channel, factor):
    if not isinstance(channel, dict):
        return channel
    out = {}
    for key, value in channel.items():
        try:
            t = float(key)
        except ValueError:
            out[key] = value
            continue
        out[f'{t * factor:.6g}'] = value
    return out


def convert(src_path: Path, dst_path: Path, source_name: str, output_name: str, original_length: float):
    with src_path.open() as fh:
        source = json.load(fh)
    clip = source['animations'][source_name]
    factor = TARGET_LENGTH / original_length
    bones = {}
    for bone, data in clip.get('bones', {}).items():
        renamed = BONE_RENAME.get(bone, bone)
        converted = {}
        for axis, channel in data.items():
            converted[axis] = rescale_keys(channel, factor)
        bones[renamed] = converted
    bones['rightItem'] = {
        'rotation': {'vector': [-80, 0, 0]},
        'position': {
            '0.0': {'vector': [0, 3, 0]},
            f'{RAMP_START}': {'vector': [0, 3, 0], 'easing': 'linear'},
            f'{CONTACT_START}': {'vector': [0, 15, 0], 'easing': 'linear'},
            f'{CONTACT_END}': {'vector': [0, 15, 0], 'easing': 'linear'},
            f'{TARGET_LENGTH}': {'vector': [0, 3, 0], 'easing': 'linear'},
        },
    }
    clip = {
        'animation_length': TARGET_LENGTH,
        'bones': bones,
    }
    out = {'format_version': '1.8.0', 'animations': {output_name: clip}}
    dst_path.write_text(json.dumps(out, indent=2) + '\n')
    print(f'{src_path.name} -> {dst_path.name} (x{factor:.4g}, bones {sorted(bones)})')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src-dir', required=True, type=Path,
                        help='Directory containing the raw upstream clips')
    parser.add_argument('out_dir', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/player_animation')
    args = parser.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    convert(args.src_dir / 'sword_swing_first.json', out / 'kelvin_swing_first.json',
            'sword_swing_first', 'kelvin_swing_first', 0.36)
    convert(args.src_dir / 'sword_swing_second.json', out / 'kelvin_swing_second.json',
            'sword_swing_second', 'kelvin_swing_second', 0.4)


if __name__ == '__main__':
    main()
