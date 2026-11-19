"""Viewer and fit-probe counterpart of the render-only Java stride guide."""
from __future__ import annotations

import math
import re
from functools import lru_cache

import cape_fit as F
import preview_cloth as P

SOURCE = P.ROOT / 'src/main/java/com/capatest/client/CapeStride.java'


@lru_cache(maxsize=1)
def profile():
    scalars = {k: float(v) for k, v in re.findall(r'\bdouble ([A-Z_]+) = ([0-9.]+);', SOURCE.read_text())}
    assert set(scalars) == {'ARM_GAIN', 'ARM_INSET', 'ARM_FIT', 'LEG_GAIN', 'LEG_INSET', 'LEG_FIT',
                            'LEG_SHARE', 'TOP_LIMIT', 'MID_TARGET_LIMIT', 'SOFT_EDGE'}
    return scalars


def back_degrees(pitch, yaw):
    """Radian angles of a ModelPart, projected on the backward axis."""
    return math.degrees(math.asin(max(0., min(1., math.sin(pitch) * math.cos(yaw)))))


def lifts(top, mid, arm, leg, stance, depth):
    s = profile()
    lean = max(0., min(1., stance)) * F.profile()['bodyAngle']
    arm = max(0., s['ARM_GAIN'] * arm - s['ARM_INSET'] - lean - s['ARM_FIT'] * depth)
    leg = max(0., min(s['MID_TARGET_LIMIT'], s['LEG_GAIN'] * leg - s['LEG_INSET'] - lean - s['LEG_FIT'] * depth))
    want = min(s['TOP_LIMIT'], max(arm, s['LEG_SHARE'] * leg))

    def raise_pitch(gap):
        if gap <= 0:
            return 0.
        t = min(1., gap / s['SOFT_EDGE'])
        return gap * t * (2 - t)

    upper = raise_pitch(want - top) if want > 0 else 0.
    return upper, raise_pitch(leg - top - upper - mid) if leg > 0 else 0.


def adjust(geo, arm, leg, aim):
    by = {b['name']: b for b in geo['bones']}
    top, mid = ('cape_top', 'cape_mid')
    extra = dict(zip((top, mid), lifts(by[top]['rotation'][0], by[mid]['rotation'][0], arm, leg,
                                      aim[0], F.depth(*aim))))
    return dict(geo, bones=[dict(b, rotation=[b['rotation'][0] + extra[b['name']], *b['rotation'][1:]])
                            if extra.get(b['name'], 0) else b for b in geo['bones']])


def gait(phase, amplitude):
    """Synthetic opposed swing for the visor, with separate arm and leg pivots."""
    swing = math.degrees(amplitude * math.cos(2 * math.pi * phase))
    return (swing, -swing), (-1.4*swing, 1.4*swing)


def demand(stance, arms, legs):
    def back(poses, crouch=0.):
        return max(back_degrees(math.radians(p) + crouch, 0.) for p in poses)
    return back(arms, .4*stance), back(legs)
