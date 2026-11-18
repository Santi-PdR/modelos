#!/usr/bin/env python3
"""Two aligned atlases for the worn cape: opaque cloth and independent light.

Only visible pixels of the matching material train a face's tile. The atlas
is not a decal across the model: each tile stays on its own solid when the
rig bends. Hidden backs, undersides and hard edges use authored swatches.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

import cape_reference as R
import cape_shape as shape
import cape_surface as S
import preview_cloth as P
from armor_model_pipeline import source_cube

SIZE = 256
GUARD = 1


def requests(faces, uses, factor):
    for name, (w, h) in S.SWATCHES.items():
        yield name, 2*w, 2*h
    for i, f in enumerate(faces):
        n = uses[i]
        if n <= 5 or (f['fn'] in ('north', 'down') and n < 18):
            continue
        density = S.DENSITIES[f['family']] * factor
        p = f['pts']
        # Use the actual length of each face axis so that edges and broad
        # folds have the same texel density on the model.
        w = max(2, math.ceil(np.linalg.norm(p[0] - p[1]) * density))
        h = max(2, math.ceil(np.linalg.norm(p[2] - p[1]) * density))
        yield i, w, h


def tiles(faces, owners):
    seen = owners >= 0
    uses = np.bincount(owners[seen], minlength=len(faces))
    lock = np.zeros((SIZE, SIZE), bool)
    # Retained UVs of the hidden legacy armor still have a real texture.
    lock[:128, :128] = True
    for factor in (2.2, 2.1, 2.0, 1.92, 1.85, 1.78, 1.7, 1.62, 1.55):
        req = list(requests(faces, uses, factor))
        packed = S.pack(lock, [(i, w+2*GUARD, h+2*GUARD) for i,w,h in req])
        if packed is not None:
            slots = {i: (x+GUARD,y+GUARD,w-2*GUARD,h-2*GUARD)
                     for i,(x,y,w,h) in packed.items()}
            return slots, dict(cards=len(slots)-len(S.SWATCHES), factor=factor,
                               density={i: d*factor for i,d in S.DENSITIES.items()})
    raise ValueError('las cartas del equipo no caben en el atlas')


def sample_card(face, i, owners, width, height):
    image, labels, saturated = R.reference()
    family = face['family']
    material = face['mat']
    if family == R.SHOULDER and source_cube(face['b']['name'], face['ci']) in (1,3):
        material = 'lip'
    rgb = S.swatch(material, width, height, phase=face['ci']).reshape(-1,3)
    glow = np.zeros((len(rgb),4), np.uint8)
    y, x = np.nonzero(owners == i)
    x = x + R.CROP[0]
    y = y + R.CROP[1]
    select = labels[y,x] == family
    if not select.any():
        return rgb.reshape(height,width,3), glow.reshape(height,width,4)
    x,y = x[select],y[select]
    corners = face['px']
    matrix = np.stack((corners[0]-corners[1], corners[2]-corners[1]),axis=1)
    uv = np.linalg.solve(matrix, np.stack((x,y))-corners[1,:,None])
    j = np.clip(np.floor(.5+uv[0]*(width-1)).astype(int),0,width-1)
    k = np.clip(np.floor(.5+uv[1]*(height-1)).astype(int),0,height-1)
    which = j+k*width
    sample = image[y,x].astype(float)
    valid = np.unique(which)
    for v in valid:
        group = which == v
        pixels = sample[group]
        match = np.median(pixels,axis=0)
        rgb[v] = np.clip(match/face['shade'],0,255)
        # Only the hot, in-cloth cores emit. The surrounding pink reflected
        # light is ordinary diffuse color, not another glowing rectangle.
        if family != R.CLOTH:
            continue
        r,g,b = pixels.T
        hot = saturated[y[group],x[group]] & (r>=148) & (r-g>=72) & (b-g>=42)
        amount = hot.mean()
        if amount < .48:
            continue
        red,green,blue = np.median(pixels[hot],axis=0)
        # This color is sampled *without* the albedo's diffuse shade. Soft
        # edges (coverage within the texel) fade in the texture alpha only.
        glow[v] = np.round([min(255,red*1.13),min(255,green*1.45),min(255,blue*1.25),
                            110+125*amount]).astype(np.uint8)
    # Extend the diffuse edge a few texels into the same tile for turns
    # that uncover a little more of this face. Never dilate the emitter.
    empty = np.flatnonzero(~np.isin(np.arange(len(rgb)),valid))
    if len(empty):
        diff = (empty[:,None]%width-valid[None,:]%width)**2 + (empty[:,None]//width-valid[None,:]//width)**2
        closest = np.argmin(diff,axis=1)
        amount = np.clip(1-np.sqrt(diff[np.arange(len(empty)), closest])/3.0,0.,.78)[:,None]
        rgb[empty] = (1-amount)*rgb[empty] + amount*rgb[valid[closest]]
    return rgb.reshape(height,width,3), glow.reshape(height,width,4)


def map_material(geo, *, paint=False):
    """Allocate the same UVs for GEO, Blockbench, viewer and both game passes."""
    geo['description']['texture_width'] = SIZE
    geo['description']['texture_height'] = SIZE
    for b in geo['bones']:
        if b['name'].startswith('v17_vein_'):
            # Preserve anchors/IDs, but no glued-on geometry over the splits.
            b['cubes'] = []
    faces, owners = S.visible_faces(geo)
    slots, layout = tiles(faces, owners)
    for i, f in enumerate(faces):
        mat = f['mat']
        code, name, side = f['family'], f['b']['name'], f['fn']
        if code == R.SHOULDER and source_cube(name,f['ci']) in (1,3):
            mat = 'lip'
        if i in slots:
            uv = S.spec(slots[i])
        else:
            if code == R.CLOTH and side == 'north':
                mat = 'reverse' if mat == 'violet' else 'red'
            elif code == R.CLOTH and side in ('up','down'):
                mat = 'edge'
            uv = S.spec(slots[mat])
            if code == R.CLOTH and side == 'north':
                col = int(name.split('_')[2])
                seg = int(name.rsplit('seg',1)[1]) + source_cube(name,f['ci'])
                lo,hi = shape.segment_bounds(col,seg) if seg < shape.SEGS else (shape.tip_t(col)-.027,shape.tip_t(col))
                x,y,w,h = slots[mat]
                uv = dict(uv=[x+.5,round(y+.5+(h-1)*lo,4)],
                          uv_size=[w-1.,round(max(.5,(h-1)*(hi-lo)),4)])
        f['c']['uv'][side] = uv
    if not paint:
        return layout
    base = np.full((SIZE,SIZE,4),(22,13,26,255),np.uint8)
    base[:128,:128] = np.asarray(Image.open(S.ATLAS_FILE).convert('RGBA'))
    light = np.zeros_like(base)
    for i,(x,y,w,h) in slots.items():
        if isinstance(i,str):
            rgb,em = S.swatch(i,w,h),None
        else:
            rgb,em = sample_card(faces[i],i,owners,w,h)
        g = GUARD
        base[y-g:y+h+g,x-g:x+w+g,:3] = np.pad(np.round(np.clip(rgb,0,255)).astype(np.uint8),
                                              ((g,g),(g,g),(0,0)),mode='edge')
        if em is not None:
            light[y:y+h,x:x+w] = em
    assert np.all(base[...,3] == 255)
    layout['emissive'] = int(np.count_nonzero(light[...,3]))
    return Image.fromarray(base), Image.fromarray(light), layout


def atlas():
    from armor_model_pipeline import build_base
    model = build_base()['minecraft:geometry'][0]
    base, glow, _ = map_material(model, paint=True)
    return base, glow
