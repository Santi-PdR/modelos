"""Parse the Java fit profile and reproduce the 1.20.1 armor-layer basis.

GeckoLib uses -X/+Y/+Z model pixels and renders them through
T(0,24,0) · diag(-1,-1,1). HumanoidModel's pivot and ModelPart rotations
have to agree in that basis. The visor and numerical probes use those
same transforms, not a cape posed beside an unrelated static box.
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
HEAD_OUTER = P.CORNERS * 9 + [-4.5, -.5, -4.5]  # vanilla player's hat layer


@lru_cache(maxsize=1)
def profile():
    code = SOURCE.read_text()
    table = re.search(r'\bBACKSET\s*=\s*(\{.*?\});', code, re.S)[1]
    values = json.loads(table.replace('{', '[').replace('}', ']'))

    def string(name):
        return re.search(r'\b' + name + r'\s*=\s*"([^"]+)"', code)[1]

    def scalar(name):
        return float(re.search(r'\b' + name + r'\s*=\s*(\d+(?:\.\d+)?);', code)[1])

    assert string('BONE') == G.FIT_BONE and string('GUSSET_BONE') == G.GUSSET_BONE
    assert string('DRAPE_BONE') == G.DRAPE_BONE
    return dict(bone=G.FIT_BONE, drapeBone=G.DRAPE_BONE, gussetBone=G.GUSSET_BONE,
                pitchStep=scalar('PITCH_STEP'), yawStep=scalar('YAW_STEP'),
                bodyAngle=math.degrees(scalar('CROUCH_RADIANS')), backset=values,
                drapePerUnit=scalar('DRAPE_DEGREES_PER_UNIT'), gussetDepth=scalar('GUSSET_DEPTH'))


@lru_cache(maxsize=1)
def legacy_profile():
    return json.loads((P.ROOT/'docs/respaldos/v1.63.0/fit.json').read_text())


def _sample(table, fit, stance, pitch, yaw):
    def axis(v,n):
        v = max(0.,min(n-1.,v))
        i = min(math.floor(v),n-2)
        return i,v-i
    i,x = axis(stance*(len(table)-1),len(table))
    j,y = axis(abs(math.remainder(yaw,360.))/fit['yawStep'],len(table[0]))
    k,z = axis((pitch+90.)/fit['pitchStep'],len(table[0][0]))

    def lerp(a,b,t):
        return a+(b-a)*t

    def at(row):
        return lerp(lerp(row[j][k],row[j][k+1],z),lerp(row[j+1][k],row[j+1][k+1],z),y)
    return lerp(at(table[i]),at(table[i+1]),x)


def depth(stance, pitch, yaw):
    """Positive pitch looks up; depth is in model pixels, not degrees."""
    f = profile()
    return _sample(f['backset'],f,stance,pitch,yaw)


def fold(stance, pitch, yaw):
    """Historical rotational correction, for the v1.63 comparison only."""
    f = legacy_profile()
    return _sample(f['fold'],f,stance,pitch,yaw)


def rotate(p, pivot, degrees):
    return (p-pivot) @ P.R('x', degrees)[:3,:3].T + pivot


def head_in_body(stance, pitch, yaw, *, outer=False):
    # Head.y=4.2 and body.y=3.2 in crouch. Undo the chest transform in
    # model coordinates, so measurement is relative to the fitted torso.
    head = (HEAD_OUTER if outer else HEAD) @ (P.R('y', yaw) @ P.R('x', pitch))[:3,:3].T
    return rotate(head + HEAD_PIVOT - [0., stance, 0.], HEAD_PIVOT,
                  stance * profile()['bodyAngle'])


def body_transform(pitch, yaw=0., roll=0., position=(0.,0.,0.)):
    """Live ModelPart values (degrees and model pixels), in GEO space."""
    return (P.T(HEAD_PIVOT + np.asarray(position)*[-1,-1,1])
            @ P.rotmat((pitch,yaw,roll)) @ P.T(-HEAD_PIVOT))


def mannequin_pose(stance, pitch, yaw, arm_swing=(0.,0.), leg_swing=(0.,0.)):
    """Separate vanilla part pivots for presentation and collision probes."""
    def about(p, r, offset):
        return P.T(np.asarray(p)+offset) @ r @ P.T(-np.asarray(p))

    head = about(HEAD_PIVOT, P.R('y', yaw) @ P.R('x', pitch), [0.,-4.2*stance,0.])
    body = body_transform(stance*profile()['bodyAngle'], position=(0.,3.2*stance,0.))
    arms = [about((x,22,0),P.R('x',-swing-math.degrees(.4)*stance),[0.,-3.2*stance,0.])
            for x,swing in zip((-5,5),arm_swing,strict=True)]
    legs = [about((x,12,0),P.R('x',-swing),[0.,-.2*stance,4*stance])
            for x,swing in zip((-1.9,1.9),leg_swing,strict=True)]
    return [head, body, *arms, *legs]


def wearer_pose(geo, stance, pitch, yaw, *, legacy=False):
    """Bake render transforms for a frame, not animation keyframes."""
    changes = {'chestplate': dict(rotation=[stance*profile()['bodyAngle'], 0., 0.],
                                  offset=[0., -3.2*stance, 0.])}
    if legacy:
        changes[G.FIT_BONE] = dict(rotation=[-fold(stance, pitch, yaw), 0., 0.])
    else:
        d = depth(stance,pitch,yaw)
        f = profile()
        changes.update({
            G.FIT_BONE: dict(offset=[0.,0.,d]),
            G.DRAPE_BONE: dict(rotation=[-d*f['drapePerUnit'],0.,0.]),
            G.GUSSET_BONE: dict(scale=[1.,1.,1.+d/f['gussetDepth']]),
        })
    return dict(geo, bones=[dict(b, **changes.get(b['name'], {})) for b in geo['bones']])
