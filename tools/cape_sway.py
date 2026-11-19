#!/usr/bin/env python3
"""Profile for a seekable port of the equipped response to changing sides."""
from __future__ import annotations

import math
import re
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1] / 'src/main/java/com/capatest/client'


def profile():
    response = (CLIENT/'CapeResponse.java').read_text()
    model = (CLIENT/'CapaArmorModel.java').read_text()
    keys = ('SIDE_NEAR_RATE', 'SIDE_HEM_RATE', 'SIDE_YAW', 'SIDE_ROLL', 'SEGMENT_POWER', 'MAX_YAW', 'MAX_ROLL')
    return {**{k: float(re.search(r'\b'+k+r' = (\d+(?:\.\d+)?);', response)[1]) for k in keys},
            'LAST_SEGMENT': int(re.search(r'\bLAST_SEGMENT = (\d+);', model)[1]), 'DEMO_SECONDS': 2.0}


def angles(p, t, seg):
    """Steady periodic response of alternating one-second left/right inputs.

    The same exponential filter runs on live inputs in Java. The demo is
    analytic so jumping backwards on the timeline does not change the result.
    """
    half = p['DEMO_SECONDS'] / 2
    time = t % p['DEMO_SECONDS']
    side = 1 if time < half else -1
    edge = time % half

    def travel(rate):
        peak = math.tanh(rate * half / 2)
        return side * (1 - (1 + peak)*math.exp(-rate * edge))

    q = (seg/p['LAST_SEGMENT'])**p['SEGMENT_POWER']
    upper, hem = (travel(p[key]) for key in ('SIDE_NEAR_RATE', 'SIDE_HEM_RATE'))
    bias = upper + q * (hem - upper)
    return tuple(q * max(-p[k], min(p[k], bias*p[f'SIDE_{axis}']))
                 for k, axis in (('MAX_YAW', 'YAW'), ('MAX_ROLL', 'ROLL')))
