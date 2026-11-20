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
LININGS = ('v20_mount_backing_left', 'v20_mount_backing_right')


def sew(geo, swatches):
    """Author the fixed attachment, keeping the existing bone/piece IDs."""
    from cape_surface import spec

    uv = {role: spec(slot) for role, slot in swatches.items()}
    # The reserved 128² section already carries the steel artwork. Pull
    # just those tiles; no pixels, mip boundaries or emissive masks change.
    uv.update(steel=spec((97, 1, 13, 13)), steel_side=spec((97, 65, 13, 13)),
              steel_rim=spec((113, 65, 13, 13)))
    by = {b['name']: b for b in geo['bones']}
    by[FRAME] = G.bone(FRAME, 'chestplate', (0, 24, 0), (0, 0, 0), [])
    geo['bones'].append(by[FRAME])
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

    # The inner stay sits in the shirt. The bevel and outer fold extend out
    # from the rear face without putting the tall seam across the neck pivot.
    by[G.SEAT_BONE]['cubes'] = [
        box((-3.64, 16.96, 1.65), (7.28, 2.40, 1.25), 'red', down='edge'),
        box((-3.45, 17.76, 2.44), (6.90, 1.45, 1.40), 'red', down='edge', up='lip'),
        box((-3.29, 17.92, 3.41), (6.58, 1.08, 1.22), 'red', down='edge'),
    ]
    # A drape lining, not a second top mount. Keep its inside edge below
    # the throat and flare its rear edge with the independent fit of the skirt.
    by[G.GUSSET_BONE]['cubes'] = [
        rails((0., 18.16, 1.80), (0., 19.38, 4.73), 6.96, 1.64, down='edge'),
        rails((0., 19.38, 4.60), (0., 21.83, 4.98), 6.76, 1.04, down='edge'),
    ]
    # Sew all ribbon roots into the same free cloth. This seam moves WITH
    # cape_top (including its wing guide), but passes over the pocket at
    # that hinge's pivot instead of pulling the outer collar with it.
    path = ((-6.2, 21.26, 4.83), (-4.2, 21.81, 4.81),
            (-2.2, 21.44, 5.01), (0., 21.32, 4.86),
            (2.24, 21.75, 5.05), (4.24, 21.83, 4.49), (4.73, 21.26, 4.47))
    by[G.SADDLE_BONE].update(parent='cape_top', cubes=[
        tube(a, b, 1.43, 1.57, down='edge', up='red') for a, b in zip(path, path[1:])
    ])
    rows = (
        ((-5.67,18.82,2.68), (-4.01,18.84,3.04), (-2.74,18.54,4.08), (-1.11,18.52,4.62),
         (1.11,18.52,4.62), (2.74,18.54,4.08), (4.01,18.84,3.04), (5.67,18.82,2.68)),
        ((-5.68,18.63,2.96), (-4.04,18.68,3.65), (-2.75,18.50,5.07), (-1.13,18.48,5.58),
         (1.13,18.48,5.58), (2.75,18.50,5.07), (4.04,18.68,3.65), (5.68,18.63,2.96)),
    )
    for k, (prefix, row) in enumerate(zip(('v17_cowl_front_', 'v17_cowl_tooth_'), rows, strict=True)):
        for i, (a, b) in enumerate(zip(row, row[1:])):
            by[prefix+str(i)]['cubes'] = [tube(a, b, .92 if k == 0 else .88, 1.46,
                                                down='edge', up='red')]
    for i, (a, b) in enumerate(zip(rows[1][1:-1], rows[1][2:-1])):
        a=[a[0], a[1]-.38, a[2]+.38]; b=[b[0], b[1]-.36, b[2]+.40]
        by['v17_cowl_back_'+str(i)]['cubes'] = [tube(a, b, 1.25, 1.18, down='edge')]

    # A continuous return tucks around each torso edge. Its upper surface
    # slopes away from the neck; the front tabs sit below the chin sweep.
    for j, side in enumerate((-1, 1)):
        by[G.COLLAR_RETURN]['cubes'].append(rails((side*3.57,18.76,-2.57),
                                                (side*3.90,18.88,2.78), 1.22, .89, down='edge'))
        by[G.UNDER_YOKE_BONE]['cubes'].append(rails((side*4.03,18.95,2.43),
                                                  (side*3.13,18.31,4.20), 1.26, .92))
        by[G.SHOULDERS_BONE]['cubes'].append(box((side*3.49-.52,16.94,-2.65),
                                                 (1.04,2.29,1.44), 'red', down='edge'))
        by[f'v19_cuellito_{j}']['cubes'] = [box((side*3.43-.31,17.47,-2.78), (.62,.52,.42), 'seam')]
    for i, (a, b) in enumerate(zip(rows[1], rows[1][1:])):
        by[f'v18_chain_{i}']['cubes'] = [tube((a[0],a[1]-.39,a[2]+.76), (b[0],b[1]-.39,b[2]+.76),
                                            .24,.44,'seam',north='iron',down='edge')]

    # Steel lies outboard of the head box, directly on the sleeve rather
    # than cantilevering from the back fold. The slope, crown and front lip
    # are independent relief, not a painted suggestion on a flat panel.
    for name, arm, lining, side in zip(PADS, ARMS, LININGS, (-1, 1), strict=True):
        p = [side*6.31, 24.03, .04]
        by[name].update(parent=arm, pivot=p, rotation=[-1., side*5., side*13.])
        x, y, z = p
        by[name]['cubes'] = [
            box((x-1.09,y-.95,z-2.38),(2.18,1.06,4.76),'steel_side',up='steel'),
            box((x-.98,y+.035,z-1.78),(1.96,.44,3.80),'steel_side',up='steel'),
            box((x+side*.90-.22,y-.25,z-2.13),(.44,.62,4.46),'steel_side',up='steel_rim',north='steel_rim'),
            box((x-1.04,y-1.48,z-2.71),(2.08,1.52,.92),'steel_side',north='steel',up='steel'),
        ]
        # This fabric tongue sits on the inside/back of the sleeve. The
        # steel is sewn to it, and its lower end tucks under the yoke in
        # the neutral pose. Both follow the sleeve even when the elbow swings.
        by[lining].update(parent=arm, cubes=[
            rails((side*6.23,23.58,1.77), (side*5.47,18.71,2.45), 1.33,.67, down='edge'),
        ])
    # Snap authoring results for stable diffs and for Blockbench's precision.
    names = {FRAME, *PADS, *LININGS, G.GUSSET_BONE, G.SADDLE_BONE}
    for name, b in by.items():
        if name not in names and b.get('parent') != FRAME:
            continue
        for cube in b['cubes']:
            for field in ('origin', 'size', 'rotation', 'pivot'):
                if field in cube:
                    cube[field] = [round(v, 4) for v in cube[field]]
    return geo
