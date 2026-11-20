"""Folded yoke and sleeve armor for the equipped cape.

Apply after packing the legacy layout. The silhouette of the new mount does
not get to reallocate the skirt's UVs or its baked glow.
"""
from __future__ import annotations

from math import asin, atan2, degrees, hypot

import armor_model_pipeline as G

FRAME = 'cape_fixed_yoke'
PADS = ('v18_pad_0', 'v18_pad_1')
ARMS = ('rightArm', 'leftArm')
LININGS = ('v20_mount_backing_left', 'v20_mount_backing_right')
FACING = 'v20_mount_facing'


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
    # A shallow facing hugs the upper shirt so the lower join does not read
    # as a cape hung halfway down the back. It only adds 0.09u to a jacket;
    # the solid folds below it keep the turned head free of raised trim.
    facing = [box((-3.76,18.29,1.80),(7.52,3.28,.53), down='edge')]
    neckline = ((-3.80,22.48,2.06),(-1.89,21.73,2.06),(1.89,21.73,2.06),(3.80,22.48,2.06))
    facing.extend(tube(a,b,1.40,.53,up='lip') for a,b in zip(neckline,neckline[1:]))
    by[FACING] = G.bone(FACING, FRAME, (0,24,0), (0,0,0), facing)
    geo['bones'].append(by[FACING])

    # A drape lining, not a second top mount. The inner edge stays in the
    # shirt while the outer fold follows the hinge of the free cloth.
    by[G.GUSSET_BONE].update(pivot=[0, 17.61, 1.94], cubes=[
        box((-3.48,16.97,1.43), (6.96,1.28,2.01), down='edge'),
        box((-3.38,17.08,3.23), (6.76,1.06,2.19), down='edge', up='lip'),
    ])
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
    for side in (-1, 1):
        by[G.COLLAR_RETURN]['cubes'].append(rails((side*3.57,18.76,-2.57),
                                                (side*3.90,18.88,2.78), 1.22, .89, down='edge'))
        by[G.UNDER_YOKE_BONE]['cubes'].append(rails((side*4.03,18.95,2.43),
                                                  (side*3.13,18.31,4.20), 1.26, .92))
        by[G.SHOULDERS_BONE]['cubes'].append(tube((side*3.18,18.60,-2.18), (side*4.63,18.85,-2.28),
                                                .84, .91, down='edge', up='lip'))
    for i, (a, b) in enumerate(zip(rows[1], rows[1][1:])):
        by[f'v18_chain_{i}']['cubes'] = [tube((a[0],a[1]-.39,a[2]+.76), (b[0],b[1]-.39,b[2]+.76),
                                            .24,.44,'seam',north='iron',down='edge')]

    # Steel lies outboard of the head box, directly on the sleeve rather
    # than cantilevering from the back fold. The slope, crown and front lip
    # are independent relief, not a painted suggestion on a flat panel.
    for name, arm, lining, side in zip(PADS, ARMS, LININGS, (-1, 1), strict=True):
        p = [side*6.73, 23.99, -.64]
        by[name].update(parent=arm, pivot=p, rotation=[-3., side*5., side*14.5])
        x, y, z = p
        by[name]['cubes'] = [
            box((x-1.05,y-.91,z-1.64),(2.10,1.00,3.28),'steel_side',up='steel'),
            box((x-.92,y+.01,z-1.30),(1.84,.40,2.74),'steel_side',up='steel'),
            box((x+side*.88-.22,y-.24,z-1.49),(.44,.58,3.20),'steel_side',up='steel_rim',north='steel_rim'),
            box((x-.96,y-1.36,z-1.91),(1.92,1.43,.86),'steel_side',north='steel',up='steel'),
        ]
        # A folded panel along the sleeve, with the front below the plate
        # and the rear caught underneath the hem of the yoke.
        by[lining].update(parent=arm, cubes=[
            tube((side*4.17,18.59,-2.28), (side*6.41,22.86,-2.36), 1.02,.93, down='edge', up='lip'),
            rails((side*6.37,23.28,-1.99), (side*6.40,23.47,2.26), 1.72,.92, down='edge', up='lip'),
            rails((side*6.39,23.18,2.23), (side*5.19,18.71,2.64), 1.74,.83, down='edge', up='lip'),
            tube((side*3.81,21.62,2.02), (side*6.11,22.54,2.00), 1.24,.55, up='lip'),
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
    gather_upper_fold(geo)
    return geo


# Pleat only the crown, in the rest frame of the upper cloth hinge. Neither
# the hinge/pivots nor the animation keys are relocated: underlayers below
# this band keep identical geometry and motion, including the long tips.
FOLD_LINE = 16.2
FOLD_RATIO = .14


def gather_upper_fold(geo):
    """Tuck the ends of the cloth under the yoke, away from the rear of the head."""
    import numpy as np
    from preview_cloth import cube_points, rotmat

    mirror = np.array([-1., 1., 1.])
    for b in geo['bones']:
        if b.get('parent') != 'cape_top' or not b['name'].startswith(('v17_ribbon_', 'v17_vein_', G.SADDLE_BONE)):
            continue
        mat = rotmat(b.get('rotation', (0,0,0)))
        p = mirror * b['pivot']
        mat[:3,3] = p - mat[:3,:3] @ p
        inv = np.linalg.inv(mat)
        for c in b['cubes']:
            v = cube_points(c, mat, inflate=False)
            excess = np.maximum(0, v[:,1] - FOLD_LINE)
            if not excess.any():
                continue
            v[:,1] -= (1 - FOLD_RATIO) * excess
            # Preserve the grain orientation and UVs. GEO needs an oriented
            # box, so re-fit it around the gathered corners of this fold.
            x, y, _ = v[[1,3,4]] - v[0]
            y /= np.linalg.norm(y)
            z = np.cross(x,y)
            z /= np.linalg.norm(z)
            basis = np.stack((np.cross(y,z),y,z), axis=1)
            lo, hi = (v @ basis).min(0), (v @ basis).max(0)
            size = hi - lo
            center = mirror * (inv[:3,:3] @ basis @ ((hi + lo)/2) + inv[:3,3])
            r = inv[:3,:3] @ basis
            # Inverse of the mirrored Z/Y/X order used by GeckoLib.
            rotation = [degrees(-atan2(r[2,1], r[2,2])), degrees(asin(np.clip(r[2,0],-1,1))),
                        degrees(atan2(r[1,0], r[0,0]))]
            c.update(origin=(center-size/2).round(4).tolist(), size=size.round(4).tolist(),
                     pivot=center.round(4).tolist(), rotation=np.round(rotation,4).tolist())
