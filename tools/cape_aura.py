#!/usr/bin/env python3
"""Export the worn ember layout from the server code to the offline viewer."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEM = ROOT/'src/main/java/com/capatest/item'
JAVA = ITEM/'CapeState.java'


def profile():
    source = JAVA.read_text()
    table = lambda name: json.loads(re.sub(r'(?<!\d)\.(\d)', r'0.\1',
        re.search(r'\b'+name+r'\s*=\s*(\{.*?\});', source, re.S)[1]).replace('{','[').replace('}',']'))
    origins,spread = table('SPARK_ORIGINS'),table('SPARK_JITTER')
    assert len(origins) == len(spread) == 4 and all(len(pair)==2 for pair in origins)
    for pair,radii in zip(origins,spread,strict=True):
        for k,pos in enumerate(pair):
            assert len(pos)==len(radii)==3 and all(r>0 for r in radii)
            assert (pos[0]<0) == (k==0) and pos[1]>radii[1] and pos[2]-radii[2]>.30
    modes = {'animation.'+clip: json.loads('['+values+']') for clip, values in
             re.findall(r'\("([a-z]+)",\s*new Aura\(([^)]+)\)\)', source)}
    runtime = (ITEM/'CapaDeteriorerItem.java').read_text()
    def constant(name):
        return int(re.search(rf'\b{name}\s*=\s*(\d+)\s*;', runtime)[1])
    cap = constant('MAX_SPARKS_PER_TICK')
    assert len(modes) == 8 and all(len(values)==4 and 0<values[0]<=cap for values in modes.values())
    return dict(origins=origins, spread=spread, modes=modes,
                pulseTicks=constant('SPARK_INTERVAL_TICKS'))
