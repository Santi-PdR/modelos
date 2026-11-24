#!/usr/bin/env python3
"""Catch completely missing first-person arms in the controlled visual fixture.

This is deliberately *not* a pose, grip, or general skin detector. The test
client uses the same cyan-sleeved skin, flat world, HUD and 854x480 viewport in
all three configurations. Different skins/scenes must not use this heuristic.
ImageMagick decodes the PNG; inspecting raw RGB keeps this independent of PIL.
"""
from pathlib import Path
import struct
import subprocess
import sys

FRAMES = (
    "38_blood_right_reach", "39_blood_right_draw", "40_blood_right_face", "41_blood_right_recovery",
    "42_blood_left_reach", "43_blood_left_draw", "44_blood_left_face", "45_blood_left_recovery",
    "86_x_first_prepare", "87_x_first_windup", "88_x_first_impact",
    "101_x_left_first_prepare", "102_x_left_first_windup", "103_x_left_first_impact",
)


def sleeve_pixels(path: Path) -> int:
    with path.open('rb') as image:
        header = image.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', header[16:24]) != (854, 480):
        raise ValueError(f'{path}: expected a fixture PNG at 854x480')
    # The crop excludes the HUD, the sky and the hotbar. The cyan sleeve in
    # this fixture is distinct from its green ground and deliberately detected
    # with a generous tolerance for lighting/antialiasing.
    raw = subprocess.check_output(['convert', str(path), '-crop', '620x180+0+250', '-depth', '8', 'rgb:-'])
    if len(raw) != 620 * 180 * 3:
        raise ValueError(f'{path}: unexpected decoded size {len(raw)}')
    return sum(1 for i in range(0, len(raw), 3)
               if (lambda r, g, b: r >= 55 and g * 10 > r * 11 and b * 10 > r * 11
                   and g * 5 > b * 4 and g * 5 < b * 6)(*raw[i:i + 3]))


def main(directory: Path) -> int:
    failed = []
    for name in FRAMES:
        path = directory / (name + '.png')
        try:
            count = sleeve_pixels(path)
            print(f'{name}: {count} sleeve-colored pixels')
            if count < 500:
                failed.append(f'{name}: too few sleeve pixels ({count})')
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failed.append(f'{name}: {error}')
    if failed:
        print('Missing or potentially offscreen first-person arms:', *failed, sep='\n  ', file=sys.stderr)
        return 1
    print('Fixture visibility check passed; visual quality still requires human review.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: verificar_encuadre_fixture.py <fixture screenshot directory>')
    sys.exit(main(Path(sys.argv[1])))
