#!/usr/bin/env python3
"""Export the equipped chain controls; the authored eight rigid cubes stay unchanged."""
import math
import re
from pathlib import Path

LINKS = tuple(f'v18_chain_{i}' for i in range(8))
JAVA = Path(__file__).resolve().parents[1]/'src/main/java/com/capatest/client/CapeChain.java'


def profile():
    java = JAVA.read_text()
    p = {k: float(v) for k, v in re.findall(r'private static final double (\w+) = ([.\d]+);', java)}
    p['weights'] = [float(w) for w in re.search(r'LINK_WEIGHT = \{([^}]+)\}', java)[1].split(',')]
    return p


def smooth(low, high, value):
    t = max(0., min(1., (value-low)/(high-low)))
    return t*t*(3-2*t)


def pose(p, stride, pace, support, brake):
    gait = smooth(p['GAIT_START'], p['GAIT_FULL'], pace)
    lag = smooth(p['BRAKE_START'], p['BRAKE_FULL'], brake)
    step = 4*math.pi*(stride-p['STEP_DELAY'])
    drop = gait*(.12+.72*(.5+.5*math.cos(step)))
    away = gait*(.23+.73*(.5+.5*math.cos(step-p['AWAY_DELAY'])))
    return (p['DROP']*support*(drop+(1-drop)*p['BRAKE_DROP']*lag),
            p['AWAY']*support*(away+(1-away)*p['BRAKE_AWAY']*lag))
