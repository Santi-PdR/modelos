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
    pairs = dict(plane='PLANE', depth='TAKE_IN', width='RETURN_IN', hem='HEM_DEGREES', downStart='DOWN_START', downFull='DOWN_FULL',
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


@lru_cache(maxsize=1)
def plate_profile():
    code = SOURCE.with_name('CapePlateFit.java').read_text()
    numeric = r'-?(?:\d+(?:\.\d+)?|\.\d+)'
    def table(name):
        source = re.search(r'\b'+name+r' = \{(.*?)\n    \};',code,re.S)[1]
        data = [list(map(float,re.findall(numeric,row))) for row in re.findall(r'\{(.*?)\}',source)]
        assert len(data) == 2 and all(len(row) == 10 for row in data)
        return data
    def values(keys):
        return [float(re.search(r'\b'+key+r' = ('+numeric+r')[;,]',code)[1]) for key in keys]
    limits = values(('DOWN_START','DOWN_FULL','TURN_START','TURN_END','LEAN_START','LEAN_END','ARM_START','ARM_END'))
    lips = values(('LIP_RISE_START','LIP_RISE_END','LIP_REACH_START','LIP_REACH_END'))
    names = [re.search(r'\b'+key+r' = "([^"]+)"', code)[1] for key in ('SMALL','WIDE')]
    return dict(names=names,targets=table('TARGETS'),limits=limits,rims=table('RIMS'),lips=lips,
                rimCube=int(values(('RIM_CUBE',))[0]))


def plate_influence(stance,pitch,yaw,arm,*,elytra=False):
    if elytra or not all(map(math.isfinite,(stance,pitch,yaw,arm))):
        return 0.
    a,b,c,d,e,f,g,h = plate_profile()['limits']
    return (smooth(a,b,-pitch)*(1-smooth(c,d,abs(math.remainder(yaw,360))))
            *(1-smooth(e,f,stance))*(1-smooth(g,h,arm)))


def plate_frame(name, parent, target, amount):
    # Parent-space transform used for rendering only. No extra bone is
    # exported in the rig: the existing plate keeps its pivot and all UVs.
    x,y,z,sx,sy,sz,lift,advance,rx,ry = target
    return dict(name='fit_'+name,parent=parent,pivot=[-x,y,z],
                offset=[0,lift*amount,advance*amount],rotation=[-rx*amount,-ry*amount,0],
                scale=[1+(sx-1)*amount,1+(sy-1)*amount,1+(sz-1)*amount],cubes=[])


def rim_frame(name, target, amount):
    a,b,c,d = plate_profile()['lips']
    rise,reach = smooth(a,b,amount),smooth(c,d,amount)
    x,y,z,across,lift,advance,sx,sy,sz,pitch = target
    return dict(name='rim_'+name,parent=name,pivot=[-x,y,z],
                offset=[-reach*across,rise*lift,reach*advance],rotation=[-rise*pitch,0,0],
                scale=[1+reach*(sx-1),1+rise*(sy-1),1+reach*(sz-1)],cubes=[])


@lru_cache(maxsize=1)
def torso_profile():
    code = SOURCE.with_name('CapeTorsoFit.java').read_text()
    pivots = re.search(r'PIVOTS = (\{.*?\});',code,re.S)[1]
    leading_z = float(re.search(r'WIDE_LEADING_Z = ([.\d]+);',code)[1])
    return dict(pivots=json.loads(pivots.replace('{','[').replace('}',']')),wideLeadingZ=leading_z)


def torso_shape(stance, pitch, yaw, depth, seat, plate, arm, effort, dry=1., elytra=False):
    """CapeTorsoFit in +look-up degrees, with authored affines in mirrored X."""
    if elytra or dry <= 0 or not all(map(math.isfinite,(stance,pitch,yaw,depth,arm,effort,dry,seat,plate))):
        return (0.,None,None,None,None)
    down, turn = -pitch, abs(math.remainder(yaw,360.))
    space = ((1-smooth(.02,.40,depth))*(1-smooth(.05,.36,stance))
             *(1-smooth(44,57,turn))*(1-.82*smooth(62,88,down)*smooth(24,36,turn)))
    reach = space*(1-smooth(2.85,6,effort))
    tuck = (dry*(1-.48*smooth(.62,.995,seat))*(1-smooth(.09,.32,stance))
            *(1-smooth(.10,.82,depth))*(1-smooth(10,25,effort)))
    trim = reach*smooth(24,43,down)
    rest = dry*(1-smooth(.72,1,plate))*(1-smooth(.10,.50,stance))*(1-smooth(14,33,pitch))*(1-smooth(70,86,turn))
    sweep, advance = smooth(5,25,effort),reach*smooth(12,42,down)
    upright = 1-smooth(0,23,down)
    profile = torso_profile()
    pivots = profile['pivots']

    def fit(i,k,sx,sy,sz,dy,dz):
        return [*pivots[i], 0.,k*dy,k*dz,*(1+k*(v-1) for v in (sx,sy,sz))] if k > 0 else None

    def collar(r): return fit(0,tuck,.965,.41,1-.12*r,-.58,-1.62*r)
    crown = trim*(1+1.24*smooth(.76,.995,seat))
    closure = .18*dry*smooth(.76,.99,plate)
    compact = rest*(1-smooth(.54,.76,seat))*(1-smooth(.10,.26,stance))
    wide = fit(2,1,1-.60*rest,1-.59*rest,1-.14*advance*rest-closure,
               rest*(.065+.37*sweep+.48*advance-.47*upright),
               rest*(-.24*advance+.52*sweep+.22*upright)+(profile['wideLeadingZ']-pivots[2][2])*closure) if rest or closure else None
    return (.68*smooth(23,43,down)*dry*space*(1-smooth(2.85,6,arm)),
            collar(crown),collar(trim*.16),fit(1,compact,.94,.92,1-.17*advance,.18*advance,-.24*advance),wide)


def torso_frame(b, transform, prefix="torso_"):
    x,y,z,dx,dy,dz,sx,sy,sz = transform
    return dict(name=prefix+b['name'],parent=b.get('parent'),pivot=[-x,y,z],
                offset=[-dx,dy,dz],scale=[sx,sy,sz],cubes=[])


def viewer_profile():
    return dict(profile(),backing=B.profile(),seat=seat_profile(),plates=plate_profile(),torso=torso_profile())


def wearer_pose(geo, stance, pitch, yaw, *, legacy=False, elytra=False, arm_back=0., close=True,
                plates=True, arm_effort=None, torso=True):
    """Bake render transforms for a frame, not animation keyframes."""
    changes = {'chestplate': dict(rotation=[stance*profile()['bodyAngle'], 0., 0.],
                                  offset=[0., -3.2*stance, 0.])}
    shape = (0.,None,None,None,None)
    outer = None
    effort = arm_back if arm_effort is None else arm_effort
    mix = plate_influence(stance,pitch,yaw,effort,elytra=elytra) if close and plates and not legacy else 0.
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
            if torso:
                shape = torso_shape(stance,pitch,yaw,d,snug,mix,arm_back,effort,elytra=elytra)
                if shape[0] > snug:
                    outer = [0.,0.,q['plane']-d,0.,0.,0.,1.,1.,(1-q['depth']*shape[0])/(1-q['depth']*snug)]
            changes[q['frame']] = dict(scale=[1.,1.,1-q['depth']*snug])
            changes[G.SHOULDERS_BONE]['scale'][0] = 1-q['width']*snug
            changes[G.DRAPE_BONE]['rotation'][0] += q['hem']*max(snug,shape[0])
        names = B.profile()['names']
        if any(b['name'] in names for b in geo['bones']):
            a,b,z = B.solve(head_in_body(stance,pitch,yaw,outer=True),d,elytra=elytra)
            changes.update({name:dict(scale=[1.,s,z]) for name,s in zip(names,(a,b),strict=True)})
    bones = [dict(b, **changes.get(b['name'], {})) for b in geo['bones']]
    _,collar,facing,small,wide = shape
    data = plate_profile()
    for b in tuple(bones):
        name = b['name']
        root = b
        transform = None
        if name in data['names']:
            i = data['names'].index(name)
            if mix:
                frame = plate_frame(name,b.get('parent'),data['targets'][i],mix)
                b['parent'] = frame['name']
                bones.append(frame)
                # Preserve the crest cube's pivot, face UVs and alpha.
                j = data['rimCube']
                if len(b.get('cubes',[])) > j:
                    rim = rim_frame(name,data['rims'][i],mix)
                    rim['cubes'] = [b['cubes'][j]]
                    b['cubes'] = b['cubes'][:j]+b['cubes'][j+1:]
                    bones.append(rim)
                root = frame
            if plates:
                transform = (small,wide)[i]
        elif name.startswith('v17_cowl_tooth_'):
            transform = facing
        elif name != 'v17_cowl_return' and name.startswith(('v17_cowl_','v19_cuellito_','v18_chain_')):
            transform = collar
        if transform is not None:
            frame = torso_frame(b,transform)
            b['parent'] = frame['name']
            bones.append(frame)
            if not (name in data['names'] and mix):
                root = frame
        if outer is not None and (transform is not None or name in data['names'] or name == G.DRAPE_BONE
                or (name != 'v17_cowl_return' and name.startswith(('v17_cowl_','v19_cuellito_','v18_chain_')))):
            # Same order as CapaArmorRenderer: outer squeeze, plate fit,
            # compact rest shape and finally the authored/GEO cube.
            frame = torso_frame(root,outer,'seat_')
            root['parent'] = frame['name']
            bones.append(frame)
    return dict(geo, bones=bones)
