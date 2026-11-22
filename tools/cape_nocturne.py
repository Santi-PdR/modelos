#!/usr/bin/env python3
"""Export the halo envelope shared by the mod and the software visor."""
from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT/'src/main/java/com/capatest/client/CapeNocturne.java'
SHADER = ROOT/'src/main/resources/assets/capatest/shaders/core'


def profile():
    java = JAVA.read_text()
    fields = ('DARK_LEVEL', 'LIGHT_LEVEL', 'DAY_GAIN', 'INNER_BASE', 'INNER_PULSE',
              'EDGE_BASE', 'EDGE_PULSE', 'EDGE_DELAY', 'PERIOD', 'SEED_SHIFT', 'GAIN_UNITS',
              'WAKE_LIMIT', 'WAKE_DEAD_ZONE', 'INNER_WAKE_SCALE', 'EDGE_WAKE_SCALE', 'WAKE_WATER_DAMPING')
    values = {key: float(re.search(r'\b'+key+r' = ([0-9.]+);', java)[1]) for key in fields}
    response = JAVA.with_name('CapeResponse.java').read_text()
    for key in ('SPEED_RATE', 'HEM_SPEED_RATE', 'RIM_SPEED_RATE'):
        values[key] = float(re.search(r'\b'+key+r' = ([0-9.]+);', response)[1])
    values.update(DEMO_START=.60, DEMO_STOP=3.20, DEMO_SECONDS=6, DEMO_SPEED=.352)
    fade = re.search(r'smoothstep\(([0-9.]+), ([0-9.]+), halo\.r\)', (SHADER/'cape_bloom.fsh').read_text())
    values['EDGE_LO'], values['EDGE_HI'] = map(float, fade.groups())
    unit = re.search(r'vec2\(UV2\) / ([0-9.]+);', (SHADER/'cape_bloom.vsh').read_text())
    assert float(unit[1]) == values['GAIN_UNITS']
    return values


def darkness(p, light):
    t = min(1, max(0, (light - p['DARK_LEVEL']) / (p['LIGHT_LEVEL'] - p['DARK_LEVEL'])))
    return 1 - t*t*(3-2*t)


def demo_wake(p, t, water=0):
    def speed(rate):
        start = math.exp(-rate * max(0, t - p['DEMO_START']))
        stop = math.exp(-rate * max(0, t - p['DEMO_STOP']))
        return p['DEMO_SPEED'] * (stop - start)

    hem = speed(p['HEM_SPEED_RATE'])
    return abs(hem - speed(p['RIM_SPEED_RATE'])), abs(speed(p['SPEED_RATE']) - hem), water


def gains(p, dusk, seconds, seed=0, wake=(0, 0, 0)):
    phase = seconds/p['PERIOD'] + seed*p['SEED_SHIFT']
    inner = p['INNER_BASE'] + p['INNER_PULSE'] * (.5+.5*math.cos(math.tau*phase))
    edge = p['EDGE_BASE'] + p['EDGE_PULSE'] * (.5+.5*math.cos(math.tau*(phase-p['EDGE_DELAY'])))
    day = p['DAY_GAIN']
    motion_edge, motion_inner, water = wake
    contrast = dusk*dusk*(1 - p['WAKE_WATER_DAMPING']*water)

    def boost(value, scale):
        strength = max(0, value - p['WAKE_DEAD_ZONE'])*scale
        return p['WAKE_LIMIT']*strength/(1 + strength)

    return (day+dusk*(edge-day)+contrast*boost(motion_edge, p['EDGE_WAKE_SCALE']),
            day+dusk*(inner-day)+contrast*boost(motion_inner, p['INNER_WAKE_SCALE']),
            p['EDGE_LO'], p['EDGE_HI'])
