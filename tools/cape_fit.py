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
    limits = ('KEEP_AFTER', 'SOFTNESS', 'OPEN_FROM', 'OPEN_END', 'DEPTH_START', 'DEPTH_END',
              'LIP_Y', 'LIP_Z', 'LIP_HEIGHT', 'LIP_ADVANCE', 'LIP_RISE', 'LIP_SHIFT')
    turn = [float(re.search(r'\bTURN_' + k + r' = ([\d.]+);',code)[1]) for k in limits]
    seat = seat_profile()
    return dict(pivots=json.loads(pivots.replace('{','[').replace('}',']')), turn=turn,
                seatPlane=seat['plane'], seatDepth=seat['depth'])


def torso_shape(stance, pitch, yaw, depth, seat, plate, arm, effort, dry=1., elytra=False):
    """CapeTorsoFit in +look-up degrees, with authored affines in mirrored X."""
    if elytra or dry <= 0 or not all(map(math.isfinite,(stance,pitch,yaw,depth,arm,effort,dry,seat,plate))):
        return (0.,None,None,None,None,None)
    signed_turn = math.remainder(yaw,360.)
    down, turn = -pitch, abs(signed_turn)
    lean_room = 1-smooth(.05,.36,stance)
    steep_room = 1-.82*smooth(62,88,down)*smooth(24,36,turn)
    sleeve_room = 1-smooth(2.85,6,effort)
    release = smooth(44,57,turn)
    space = (1-smooth(.02,.40,depth))*lean_room*(1-release)*steep_room
    reach = space*sleeve_room
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

    def collar(reach, shift=0., scale=1.):
        return [*pivots[0],0.,-.58*tuck,shift-1.62*reach*tuck*scale,
                1+tuck*(.965-1),1+tuck*(.41-1),(1-.12*reach*tuck)*scale] if tuck > 0 else None

    crown = trim*(1+1.24*smooth(.76,.995,seat)+.46*smooth(78,87,down)*smooth(.79,.995,seat))
    stroke = .68*smooth(23,43,down)
    outer = stroke*dry*space*(1-smooth(2.85,6,arm))
    start,soft,opening,end,d0,d1,lip_y,lip_z,lift,advance_lip,rise,side = profile['turn']
    lost = max(0.,release-smooth(44,57,start))
    hold = (lost*lost/(lost+soft)*(1-smooth(opening,end,turn))*smooth(30,45,down)*(1-smooth(64,78,down))
            *(1-smooth(d0,d1,depth))*lean_room*steep_room*sleeve_room)
    scale = ((1-profile['seatDepth']*max(seat,outer+stroke*dry*hold))
             / (1-profile['seatDepth']*max(seat,outer)))
    shift = (1-scale)*(profile['seatPlane']-depth-pivots[0][2])
    settled = dry*smooth(.78,.99,plate)
    compact = rest*(1-smooth(.54,.76,seat))*(1-smooth(.10,.26,stance))
    wide = fit(2,1,1-.60*rest,1-.59*rest,1-.14*advance*rest,
               rest*(.065+.37*sweep+.48*advance-.47*upright)+.07*settled,
               rest*(-.24*advance+.52*sweep+.22*upright)-.38*settled) if rest or settled else None
    fold = collar(crown+hold*smooth(24,43,down),shift,scale)
    lip = fold
    if fold is not None and hold > 0:
        x,y,z,dx,dy,dz,sx,sy,sz = fold
        thickness = 1-.12*crown*tuck
        raise_by = lift*hold
        drift = -math.copysign(side,signed_turn)*hold*smooth(48,57,down)
        lip = [x,y,z,dx+drift,dy+raise_by*(y+dy-lip_y)+rise*hold,dz-(thickness-sz)*(lip_z-z)-advance_lip*hold,
               sx,sy*(1+raise_by),thickness]
    return (outer,fold,lip,collar(trim*.16),fit(1,compact,.94,.92,1-.17*advance,.18*advance,-.24*advance),wide)


def torso_frame(b, transform, prefix="torso_"):
    x,y,z,dx,dy,dz,sx,sy,sz = transform
    return dict(name=prefix+b['name'],parent=b.get('parent'),pivot=[-x,y,z],
                offset=[-dx,dy,dz],scale=[sx,sy,sz],cubes=[])


@lru_cache(maxsize=1)
def mount_profile():
    code = SOURCE.with_name('CapeMountPlacement.java').read_text()
    values = {name:float(n) for name,n in re.findall(r'final double (\w+) = ([.\d]+);', code)}
    values['plates'] = [list(map(float,re.search(r'\b' + name + r' = new Shift\(([^)]+)\)',code)[1].split(',')))
                        for name in ('SMALL','WIDE')]
    return values


def mount_placement(stance, pitch, yaw, effort=0., *, dry=1., enabled=True):
    """Torso-relative fit (positive pitch looks up), mirrored from Java."""
    d = depth(stance,pitch,yaw)
    if not enabled or dry <= 0:
        return d,d,pitch,0.,0.,0.,0.,1.,0.
    f = mount_profile()
    yaw = abs(math.remainder(yaw,360))
    plate = (dry * (1-smooth(.05,.45,stance)) * (1-smooth(3,21,yaw))
             * (1-smooth(19,39,-pitch)) * (1-smooth(.2,2.45,d)) * (1-smooth(4,22,effort)))
    k = dry*smooth(f['LEAVE_AT'],f['SEATED_AT'],pitch)*(1-smooth(.08,.50,stance))
    if not k:
        return d,d,pitch,0.,0.,0.,0.,1.,plate
    relief = smooth(f['RELIEF_START'],f['RELIEF_END'],pitch)
    quiet = pitch*(1-k)
    settled = depth(stance,quiet,yaw)
    room = f['REAR'] + relief*(f['EXTRA_REAR']+f['DIAGONAL']*smooth(19,43,yaw))
    d = d*(1-k)+k*(settled+k*room)
    tilt, dy = f['TILT']*k,-(f['DROP']+f['EXTRA_DROP']*relief)*k
    drape = tilt+(f['DRAPE']+f['EXTRA_DRAPE']*relief)*k
    ay = f['JOIN_Y']-f['PIN_Y']
    az = (f['JOIN_Z']-f['PIN_Z'])*(1+d/profile()['gussetDepth'])
    y,z = f['JOIN_Y']-f['PIVOT_Y'],f['PIN_Z']+az-d-f['PIVOT_Z']
    a = math.radians(tilt)
    c,s = math.cos(a),math.sin(a)
    by = f['PIVOT_Y']-f['PIN_Y']+dy+c*y-s*z
    bz = f['PIVOT_Z']-f['PIN_Z']+d+s*y+c*z
    return (d,settled,quiet,dy,tilt,drape,math.degrees(math.atan2(bz,by)-math.atan2(az,ay)),
            math.hypot(by,bz)/math.hypot(ay,az),plate)


def viewer_profile(*, placed=False):
    fit = dict(profile(),backing=B.profile(),seat=seat_profile(),plates=plate_profile(),torso=torso_profile())
    if placed:
        fit['mount'] = mount_profile()
    return fit


def wearer_pose(geo, stance, pitch, yaw, *, legacy=False, elytra=False, arm_back=0., close=True,
                plates=True, arm_effort=None, torso=True, placed=False):
    """Bake the worn frame, not keyframes. Historical checks use placed=False."""
    changes = {'chestplate': dict(rotation=[stance*profile()['bodyAngle'], 0., 0.],
                                  offset=[0., -3.2*stance, 0.])}
    shape = (0.,None,None,None,None,None)
    outer = None
    effort = arm_back if arm_effort is None else arm_effort
    d, settled, fit_pitch, dy, tilt, drape, link_pitch, link_scale, plate_shift = mount_placement(
        stance,pitch,yaw,effort,enabled=placed and not elytra and not legacy)
    mix = plate_influence(stance,fit_pitch,yaw,effort,elytra=elytra) if close and plates and not legacy else 0.
    if legacy:
        changes[G.FIT_BONE] = dict(rotation=[-fold(stance, pitch, yaw), 0., 0.])
    else:
        f = profile()
        changes.update({
            G.FIT_BONE: dict(offset=[0.,dy,d]),
            G.DRAPE_BONE: dict(rotation=[-settled*f['drapePerUnit']+drape,0.,0.]),
            G.GUSSET_BONE: dict(scale=[1.,link_scale,link_scale*(1.+d/f['gussetDepth'])]),
            G.SHOULDERS_BONE: dict(scale=shoulder_scales(stance,pitch,yaw,elytra=elytra)),
            G.UNDER_YOKE_BONE: dict(scale=yoke_scales(stance,pitch,arm_back,elytra=elytra)),
        })
        if tilt:
            frame = mount_profile()
            changes[G.FIT_BONE].update(pivot=[0.,frame['PIVOT_Y'],frame['PIVOT_Z']], rotation=[-tilt,0.,0.])
            changes[G.GUSSET_BONE]['rotation'] = [-link_pitch,0.,0.]
        q = seat_profile()
        if close and any(b['name'] == q['frame'] for b in geo['bones']):
            snug = seating(stance,fit_pitch,yaw,arm_back,elytra=elytra)
            if torso:
                shape = torso_shape(stance,fit_pitch,yaw,settled,snug,mix,arm_back,effort,elytra=elytra)
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
    _,collar,lip,facing,small,wide = shape
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
        elif name.startswith('v17_cowl_back_'):
            transform = lip
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
            root = frame
        if plate_shift and plates and name in data['names']:
            x,y,z = mount_profile()['plates'][data['names'].index(name)]
            frame = dict(name='place_'+name, parent=root['parent'], pivot=[0.,0.,0.],
                         offset=[-x*plate_shift,y*plate_shift,z*plate_shift], cubes=[])
            root['parent'] = frame['name']
            bones.append(frame)
    return dict(geo, bones=bones)
