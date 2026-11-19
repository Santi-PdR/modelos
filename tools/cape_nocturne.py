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
              'EDGE_BASE', 'EDGE_PULSE', 'EDGE_DELAY', 'PERIOD', 'SEED_SHIFT', 'GAIN_UNITS')
    values = {key: float(re.search(r'\b'+key+r' = ([0-9.]+);', java)[1]) for key in fields}
    fade = re.search(r'smoothstep\(([0-9.]+), ([0-9.]+), halo\.r\)', (SHADER/'cape_bloom.fsh').read_text())
    values['EDGE_LO'], values['EDGE_HI'] = map(float, fade.groups())
    unit = re.search(r'vec2\(UV2\) / ([0-9.]+);', (SHADER/'cape_bloom.vsh').read_text())
    assert float(unit[1]) == values['GAIN_UNITS']
    return values


def darkness(p, light):
    t = min(1, max(0, (light - p['DARK_LEVEL']) / (p['LIGHT_LEVEL'] - p['DARK_LEVEL'])))
    return 1 - t*t*(3-2*t)


def gains(p, dusk, seconds, seed=0):
    phase = seconds/p['PERIOD'] + seed*p['SEED_SHIFT']
    inner = p['INNER_BASE'] + p['INNER_PULSE'] * (.5+.5*math.cos(math.tau*phase))
    edge = p['EDGE_BASE'] + p['EDGE_PULSE'] * (.5+.5*math.cos(math.tau*(phase-p['EDGE_DELAY'])))
    day = p['DAY_GAIN']
    return day+dusk*(edge-day), day+dusk*(inner-day), p['EDGE_LO'], p['EDGE_HI']
