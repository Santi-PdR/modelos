"""Folded yoke and sleeve armor for the equipped cape.

Apply after packing the legacy layout. The silhouette of the new mount does
not get to reallocate the skirt's UVs or its baked glow.
"""
from __future__ import annotations

from math import atan2, degrees, hypot

import armor_model_pipeline as G

FRAME = 'cape_fixed_yoke'
PADS = ('v18_pad_0', 'v18_pad_1')
ARMS = ('rightArm', 'leftArm')


def sew(geo, swatches):
    """Author the fixed attachment, keeping the existing bone/piece IDs."""
    from cape_surface import spec

    uv = {role: spec(slot) for role, slot in swatches.items()}
    # The reserved 128² section already carries the steel artwork. Pull
    # just those tiles; no pixels, mip boundaries or emissive masks change.
    uv.update(steel=spec((97, 1, 13, 13)), steel_side=spec((97, 65, 13, 13)),
              steel_rim=spec((113, 65, 13, 13)))
    by = {b['name']: b for b in geo['bones']}
    geo['bones'].append(G.bone(FRAME, 'chestplate', (0, 24, 0), (0, 0, 0), []))
    trim = ('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_', 'v20_mount_')
    for name,b in by.items():
        if name.startswith(trim) and name not in (G.GUSSET_BONE, G.SADDLE_BONE):
            b.update(cubes=[], parent=FRAME, rotation=[0, 0, 0])
    # Back contact doesn't depend on the position of the drape or the helmet.
    def box(o,s,base='red',**fx):
        return {'origin':o,'size':s,'inflate':.01,'uv':{n:uv[fx.get(n,base)] for n in ('north','south','east','west','up','down')}}
    def angle(c,p,r):
        return dict(c, pivot=p, rotation=r)
    def tube(a,b,y,z,base='red', ends=.16, **fx):
        dx,dy,dz=(b[i]-a[i] for i in range(3)); L=hypot(dx,dy,dz); cx,cy,cz=[(a[i]+b[i])/2 for i in range(3)];
        return angle(box((cx-L/2-ends,cy-y/2,cz-z/2),(L+ends*2,y,z),base,**fx),
                     (cx,cy,cz),(0.,-degrees(atan2(dz,hypot(dx,dy))),-degrees(atan2(dy,dx))))
    def rails(a,b,w,h,base='red',**fx):
        x,y,z=a; dx,dy,dz=(b[i]-a[i] for i in range(3))
        return angle(box((x-w/2,y-h/2,z-.14),(w,h,hypot(dx,dy,dz)+.28),base,**fx),a,
                     (degrees(atan2(dy,hypot(dx,dz))),degrees(atan2(dx,dz)),0.))

    # A folded yoke with a shallow inner lining against the body, not Z-fighting
    # with the jacket. Wet layers stay put; only the under-fold gets stretched.
    # Lining lies *inside* the back of the vanilla torso. Keep it a solid,
    # not a strip that ends at the jacket or just crosses it in projection.
    by[G.SEAT_BONE]['cubes'] = [box((-3.38,17.2,1.72),(6.76,5.17,.94),'red',down='edge'),
        box((-2.92,19.54,2.30),(5.84,2.85,1.29),'red',down='edge',up='lip'),
        box((-3.24,17.98,2.32),(6.48,2.13,1.83),'red',down='edge')]
    # A drape lining, not a second top mount. Keep its inside edge below
    # the throat and flare its rear edge with the independent fit of the skirt.
    by[G.GUSSET_BONE]['cubes'] = [
        rails((0., 17.42, 1.88), (0., 17.86, 4.68), 5.94, .58, down='edge'),
        rails((0., 17.59, 4.64), (0., 22.44, 4.88), 4.36, .89, down='edge'),
    ]
    # Sew all ribbon roots into the same free cloth. This seam moves WITH
    # cape_top (including its wing guide), but passes over the pocket at
    # that hinge's pivot instead of pulling the outer collar with it.
    path = ((-6.2, 21.72, 4.83), (-4.2, 22.27, 4.81),
            (-2.2, 21.90, 5.01), (0., 21.78, 4.86),
            (2.24, 22.21, 5.05), (4.24, 22.29, 4.49), (4.73, 21.72, 4.47))
    by[G.SADDLE_BONE].update(parent='cape_top', cubes=[
        tube(a, b, 1.65, 1.57, down='edge', up='red') for a, b in zip(path, path[1:])
    ])
    rows=(([-5.21,23.66,2.24],[-4.08,23.14,2.85],[-2.75,21.77,4.21],[-1.10,21.02,4.94],
            [1.10,21.04,4.94],[2.75,21.80,4.24],[4.08,23.17,2.87],[5.21,23.66,2.25]),
          ([-5.21,23.20,2.76],[-4.08,22.71,3.63],[-2.71,21.05,5.19],[-1.12,20.66,5.90],
            [1.12,20.66,5.90],[2.71,21.08,5.22],[4.08,22.73,3.66],[5.21,23.20,2.77]))
    for k,(prefix,row) in enumerate(zip(('v17_cowl_front_','v17_cowl_tooth_'),rows)):
        for i,(a,b) in enumerate(zip(row,row[1:])):
            f=tube(a,b,.92 if k==0 else .88,1.46,down='edge', south='red',up='red')
            by[prefix+str(i)]['cubes']=[f]
    for i,(a,b) in enumerate(zip(rows[1][1:-1],rows[1][2:-1])):
        a=[a[0],a[1]-.43,a[2]+.41]; b=[b[0],b[1]-.44,b[2]+.43]
        by['v17_cowl_back_'+str(i)]['cubes']=[tube(a,b,1.38,1.18,'red',down='edge',south='red')]
    # Visible chest ends wrap around the rear of the sleeve, and the downturned
    # ends actually overlap the jacket underneath the armor lip.
    by[G.COLLAR_RETURN]['cubes'] = [rails((s*3.12,23.91,-2.68),(s*4.19,23.87,2.83),1.48,.66,down='edge') for s in (-1,1)]
    by[G.UNDER_YOKE_BONE]['cubes'] = [rails((s*3.87,23.46,2.47),(s*2.62,20.85,3.28),1.40,.96) for s in (-1,1)]
    by[G.SHOULDERS_BONE]['cubes'] = [box((s*3.14-.68,20.76,-2.56),(1.36,3.54,.94),'red',down='edge') for s in (-1,1)]
    by['v19_cuellito_0']['cubes'] = [box((-3.45,21.65,-2.69),(.62,.52,.41),'seam')]
    by['v19_cuellito_1']['cubes'] = [box((2.83,21.65,-2.69),(.62,.52,.41),'seam')]
    for i in range(7):
        a,b=rows[1][i:i+2]
        by[f'v18_chain_{i}']['cubes']=[tube([a[0],a[1]-.42,a[2]+.8],[b[0],b[1]-.43,b[2]+.8],.23,.42,'seam',north='iron',down='edge')]
    # Traditional plates: rolled main plate, stepped crown, outside ridge,
    # and a downturned lip visible from the front. Fitted around the true sleeve
    # top, not around a head-fit frame. Mirror the same relief on both sides.
    for name, arm, side in zip(PADS, ARMS, (-1, 1), strict=True):
        p=[side*5.86,24.41,.18]; n=by[name]; n.update(parent=arm,pivot=p,rotation=[-1.,side*7.,side*6.])
        x,y,z=p
        n['cubes']=[box((x-1.3,y-.78,z-1.94),(2.60,.85,4.40),'steel_side',up='steel'),
          box((x-1.12,y+.03,z-1.72),(2.24,.30,3.86),'steel_side',up='steel'),
          box((x+side*.97-.21,y-.21,z-2.04),(.42,.55,4.37),'steel_side',up='steel_rim',north='steel_rim'),
          box((x-1.09,y-1.18,z-2.60),(2.18,.84,.82),'steel_side',north='steel',up='steel')]
    # Snap authoring results for stable diffs and for Blockbench's precision.
    names = [FRAME, *PADS]
    names += [b['name'] for b in by.values() if b.get('parent') == FRAME]
    names += [G.GUSSET_BONE, G.SADDLE_BONE]
    for name in names:
        b = next(x for x in geo['bones'] if x['name'] == name)
        for cube in b['cubes']:
            for field in ('origin', 'size', 'rotation', 'pivot'):
                if field in cube:
                    cube[field] = [round(v, 4) for v in cube[field]]
    return geo
