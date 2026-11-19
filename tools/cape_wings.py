"""Vanilla elytra hulls and the render-only fit profile used by the visor."""
from __future__ import annotations

from functools import lru_cache
import math
import re

import numpy as np

import preview_cloth as P

SOURCE = P.ROOT/'src/main/java/com/capatest/client/CapeWingFit.java'


@lru_cache(maxsize=1)
def profile():
    scalars = {k: float(v) for k, v in re.findall(r'final double ([A-Z_]+) = (\d+(?:\.\d+)?);', SOURCE.read_text())}
    # ElytraModel.createLayer: 10×20×2, inflated by one model pixel.
    # ElytraLayer adds 0.125 blocks to Z. Shapes are hulls, not player capes or UVs.
    return dict(scalars, origin=[-11, -1, -1], size=[12, 22, 4], pivot=[5, 0, 2],
                folded=[15, 0, 15, 0], crouched=[40, 5, 45, 3], open=[20, 0, 90, 0])


def goal(pitch, roll, lean, depth):
    if not all(math.isfinite(x) for x in (pitch, roll, lean, depth)):
        return 0.
    p = profile()
    cut = clamp((p['CLEAR_SPAN'] - abs(roll)) / (p['CLEAR_SPAN'] - p['FOLDED']), 1)
    target = p['PITCH_BIAS'] + p['PITCH_GAIN']*clamp(pitch, 45) - p['BODY_GAIN']*clamp(lean, 30) - p['DEPTH_GAIN']*max(0, depth)
    return cut*cut*(3-2*cut)*clamp(target, p['GOAL_LIMIT'])


def lift(top, wanted):
    if wanted <= 0 or not math.isfinite(wanted) or not math.isfinite(top):
        return 0.
    p = profile()
    gap = max(0, wanted-top)
    t = clamp(gap/p['SOFT_EDGE'], 1)
    return clamp(p['CARRY']*gap*t*(2-t), p['LIFT_LIMIT'])


def clamp(value, limit):
    return max(0, min(value, limit))


def geometry(pitch, yaw, roll, down):
    """Boxes and matrices in the same wearer coordinates as the cape GEO."""
    p = profile()
    convert = P.T([0,24,0]) @ np.diag([-1.,-1.,1.,1.])
    mirror = np.diag([-1.,1.,1.,1.])
    left = P.R('z', -roll) @ P.R('y', yaw) @ P.R('x', pitch)
    x, y, z = p['pivot']
    return [convert @ P.T([x,y+down,z]) @ left, convert @ P.T([-x,y+down,z]) @ mirror @ left]


def hulls(*pose):
    p = profile()
    vertices = np.array(p['origin']) + P.CORNERS*p['size']
    return np.array([vertices @ m[:3,:3].T + m[:3,3] for m in geometry(*pose)])
