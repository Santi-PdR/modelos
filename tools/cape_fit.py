"""Shared wearer-fit profile and HumanoidModel 1.20.1 pose math.

Java owns the compact angle table. The preview copies it at build time,
so the interactive fit probe doesn't invent another set of rotations.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache

import numpy as np

import armor_model_pipeline as G
import preview_cloth as P

SOURCE = P.ROOT / 'src/main/java/com/capatest/client/CapeFit.java'
HEAD_PIVOT = np.array([0., 24., 0.])
HEAD = P.CORNERS * 8.5 + [-4.25, -.25, -4.25]


@lru_cache(maxsize=1)
def profile():
    code = SOURCE.read_text()
    table = re.search(r'\bFOLD\s*=\s*(\{.*?\});', code, re.S)[1]
    values = json.loads(table.replace('{', '[').replace('}', ']'))
    bone = re.search(r'\bBONE\s*=\s*"([^"]+)"', code)[1]
    assert bone == G.FIT_BONE
    scalar = lambda name: float(re.search(r'\b' + name + r'\s*=\s*(\d+(?:\.\d+)?);', code)[1])
    return dict(bone=bone, pitchStep=scalar('PITCH_STEP'), yawStep=scalar('YAW_STEP'),
                bodyAngle=math.degrees(scalar('CROUCH_RADIANS')), fold=values)


def fold(stance, pitch, yaw):
    """Positive pitch looks up; stance measures vanilla body tilt (0..1)."""
    f = profile()
    table = np.asarray(f['fold'])
    st = np.clip(stance * (len(table)-1), 0, len(table)-1)
    ax = np.arange(table.shape[1]) * f['yawStep']
    px = np.arange(table.shape[2]) * f['pitchStep'] - 90.
    ya = abs(math.remainder(yaw, 360.))
    levels = [np.interp(ya, ax, [np.interp(pitch, px, row) for row in posture])
              for posture in table]
    return float(np.interp(st, np.arange(len(table)), levels))


def rotate(p, pivot, degrees):
    return (p-pivot) @ P.R('x', degrees)[:3,:3].T + pivot


def head_in_body(stance, pitch, yaw):
    # Head.y=4.2 and body.y=3.2 in crouch. Undo the chest transform in
    # model coordinates, so measurement is against cape after its hinge.
    head = HEAD @ (P.R('y', yaw) @ P.R('x', pitch))[:3,:3].T
    return rotate(head + HEAD_PIVOT - [0., stance, 0.], HEAD_PIVOT,
                  stance * profile()['bodyAngle'])


def wearer_pose(geo, stance, pitch, yaw):
    """Bake the preview transforms for one frame, not an animation track."""
    changes = {
        'chestplate': dict(rotation=[stance*profile()['bodyAngle'], 0., 0.], offset=[0., -3.2*stance, 0.]),
        G.FIT_BONE: dict(rotation=[-fold(stance, pitch, yaw), 0., 0.]),
    }
    return dict(geo, bones=[dict(b, **changes.get(b['name'], {})) for b in geo['bones']])
