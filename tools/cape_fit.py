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
import cape_backing as B
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


def smooth(lo, hi, x):
    t = max(0.,min(1.,(x-lo)/(hi-lo)))
    return t*t*(3-2*t)


def yoke_scales(stance, pitch, arm_back, *, elytra=False):
    posture = 0. if elytra else (1-smooth(0,.60,stance))*(1-smooth(42,83,pitch))
    sleeve = 1-smooth(2.9,6.1,arm_back)
    spread = posture*sleeve
    return [.51+.49*spread,.065+.935*posture*smooth(0,.44,sleeve),.62+.38*spread]


def shoulder_scales(stance, pitch, yaw, *, elytra=False):
    # Same pose envelope as CapeFit.shoulderReach; pitch here is +look up.
    yaw = abs(math.remainder(yaw,360.))
    down = smooth(34,62,-pitch)*(1-.62*smooth(44,73,yaw))*(1-.52*smooth(0,1,stance))
    ahead = .45*(1-smooth(0,3,yaw))*(1-smooth(0,42,abs(pitch)))*(1-.66*smooth(0,.70,stance))
    length = .245 if elytra else .245+.755*max(down,ahead)
    return [1.,.27+.73*length,length]


@lru_cache(maxsize=1)
def seat_profile():
    code = SOURCE.read_text()
    names = dict(frame=re.search(r'\bSEAT_FRAME = "([^"]+)";', code)[1])
    pairs = dict(plane='PLANE', depth='TAKE_IN', width='RETURN_IN', downStart='DOWN_START', downFull='DOWN_FULL',
                 turnStart='TURN_START', turnEnd='TURN_END', leanStart='LEAN_START', leanEnd='LEAN_END',
                 armStart='ARM_START', armEnd='ARM_END')
    return dict(names, **{key: float(re.search(r'\bSEAT_' + const + r' = ([\d.]+);', code)[1])
                          for key,const in pairs.items()})


def seating(stance, pitch, yaw, arm_back=0., *, elytra=False):
    if elytra or not all(map(math.isfinite,(stance,pitch,yaw,arm_back))):
        return 0.
    q = seat_profile()
    return (smooth(q['downStart'],q['downFull'],-pitch)
            * (1-smooth(q['turnStart'],q['turnEnd'],abs(math.remainder(yaw,360))))
            * (1-smooth(q['leanStart'],q['leanEnd'],stance))
            * (1-smooth(q['armStart'],q['armEnd'],arm_back)))


def viewer_profile():
    return dict(profile(),backing=B.profile(),seat=seat_profile())


def wearer_pose(geo, stance, pitch, yaw, *, legacy=False, elytra=False, arm_back=0., close=True):
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
            G.SHOULDERS_BONE: dict(scale=shoulder_scales(stance,pitch,yaw,elytra=elytra)),
            G.UNDER_YOKE_BONE: dict(scale=yoke_scales(stance,pitch,arm_back,elytra=elytra)),
        })
        q = seat_profile()
        if close and any(b['name'] == q['frame'] for b in geo['bones']):
            snug = seating(stance,pitch,yaw,arm_back,elytra=elytra)
            changes[q['frame']] = dict(scale=[1.,1.,1-q['depth']*snug])
            changes[G.SHOULDERS_BONE]['scale'][0] = 1-q['width']*snug
        names = B.profile()['names']
        if any(b['name'] in names for b in geo['bones']):
            a,b,z = B.solve(head_in_body(stance,pitch,yaw,outer=True),d,elytra=elytra)
            changes.update({name:dict(scale=[1.,s,z]) for name,s in zip(names,(a,b),strict=True)})
    return dict(geo, bones=[dict(b, **changes.get(b['name'], {})) for b in geo['bones']])
