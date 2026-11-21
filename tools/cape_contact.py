"""Rigid collar fit, measured in torso model pixels, not screen overlap."""
from __future__ import annotations

import numpy as np

from preview_cloth import CORNERS
from verify_v1600 import sat


def lap(a, b):
    """Best intersection of two groups of oriented, possibly scaled cubes."""
    pairs = np.repeat(a, len(b), axis=0), np.tile(b, (len(a), 1, 1))
    return float(-sat(*pairs).min())


def seat_contacts(parts, label):
    """Check each half of jacket → lining → collar → return → pad → sleeve.

    An overlapping lower seat is not enough: .17 still touched the torso at
    waist height. Measure three patches per side on its *upper rear* edge.
    Likewise a plate can cover a sleeve in F5 but remain detached in depth.
    """
    def get(*prefixes):
        boxes = [v for name,v in parts.items() if name.startswith(prefixes)]
        assert boxes, (label, 'faltan cubos de', prefixes)
        v = np.concatenate(boxes)
        assert v.ndim == 3 and v.shape[1:] == (8,3) and np.isfinite(v).all(), (label,prefixes)
        return v

    jacket = get('jacket')
    lo, hi = jacket.min((0,1)), jacket.max((0,1))
    center = (lo[0]+hi[0])/2
    half = (hi[0]-lo[0])/2
    collar = get('v17_cowl_front_', 'v17_cowl_back_', 'v17_cowl_tooth_')
    saddle = get('v20_mount_saddle')
    collar_return = get('v17_cowl_return')
    shoulders = get('v20_mount_shoulders')
    lining = get('v20_mount_backing_')
    plates = get('v18_pad_')
    sleeves = get('left_sleeve','right_sleeve')
    assert len(plates) == 13 and len(shoulders) == 2 and len(sleeves) == 2, label
    values = []
    for side in (-1,1):
        def same_side(v):
            w = v[side*(v[:,:,0].mean(1)-center) > 0]
            assert len(w), (label,side,'falta una mitad del encastre')
            return w

        back, tab, turn, plate, arm = map(same_side,(lining,shoulders,collar_return,plates,sleeves))
        patch = CORNERS*[.45,1.35,.70]
        upper = min(lap(back, (patch+[center+side*half*f-.225,hi[1]-1.47,hi[2]-.25])[None])
                    for f in (.24,.45,.66))
        contacts = (upper, lap(back,saddle), lap(saddle,collar), lap(collar,turn), lap(turn,tab),
                    lap(tab,plate), lap(plate,arm))
        assert np.all(np.asarray(contacts) > [.23,.26,.20,.14,.17,.27,.38]), (
            label, side, 'encastre espalda/forro/cuello/retorno/hombrera/manga', np.round(contacts,3).tolist())
        values.append(contacts)
    return np.min(values, axis=0)


def depth_intervals(boxes, xy):
    """Intersect +Z lines with the *faces* of affine boxes, not their AABBs."""
    basis = (boxes[:, [1,3,4]] - boxes[:, :1]).transpose(0,2,1)
    inv = np.linalg.inv(basis)
    start = np.column_stack((xy, np.zeros(len(xy))))
    origin = np.einsum('kij,pkj->pki', inv, start[:,None,:] - boxes[None,:,0])
    direction = inv[:,:,2]
    parallel = abs(direction) < 1e-9
    step = 1 / np.where(parallel, 1, direction)
    near, far = -origin*step, (1-origin)*step
    enter = np.where(parallel, -np.inf, np.minimum(near,far)).max(-1)
    leave = np.where(parallel, np.inf, np.maximum(near,far)).min(-1)
    inside = (~parallel | ((origin >= -1e-6) & (origin <= 1+1e-6))).all(-1)
    for a,b,hit in zip(enter, leave, inside & (leave > enter), strict=True):
        yield sorted(zip(a[hit], b[hit], strict=True))


def upper_back_fit(parts, label):
    """Check the visible rim and support above the first ribs, not the waist pin.

    In .18 one small contact was enough for the SAT chain even though a
    broad hollow ran across the neck. Sweep the bare back face (the jacket
    may be transparent) and reject a stand-off cavity or an oversized rim.
    """
    body, = parts['body']
    lo, hi = body.min(0), body.max(0)
    np.testing.assert_allclose(hi-lo, [8,12,4], atol=.006, rtol=0, err_msg=f'{label}: vanilla torso basis')
    back, top = hi[2], hi[1]
    center, width = (lo[0]+hi[0])/2, hi[0]-lo[0]
    rim = np.concatenate([v for n,v in parts.items() if n.startswith(('v17_cowl_back_', 'v17_cowl_front_'))])
    stand_off = rim[:,:,2].max() - back
    assert stand_off < 2.75, (label, 'el borde del cuello sigue retrasado (u)', round(stand_off,3))
    lining = np.concatenate([v for n,v in parts.items() if n.startswith('v20_mount_backing_')])
    shell = np.concatenate((lining, rim, *[v for n,v in parts.items() if n.startswith(('v17_cowl_tooth_', 'v20_mount_saddle'))]))
    xy = [(center+width*f, top-drop) for f in np.linspace(-.325,.325,9) for drop in np.linspace(1.02,2.13,7)]
    max_gap, skin_lap = 0., np.inf
    for line in depth_intervals(shell, np.array(xy)):
        support = max((back-a for a,b in line if a <= back and b > back+.12), default=-np.inf)
        skin_lap = min(skin_lap, support)
        depth = back
        for a,b in line:
            if b <= depth:
                continue
            max_gap = max(max_gap, a-depth)
            depth = b
    assert skin_lap >= .055 and max_gap <= .30, (
        label, 'hueco entre piel y cuello (u)', round(skin_lap,3), round(max_gap,3))

    roots = [np.asarray(parts[f'v17_ribbon_{i}_seg0']) for i in range(12)]
    assert all(len(r) for r in roots), label
    supports = np.concatenate([v for n,v in parts.items() if n.startswith(
        ('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_', 'v20_mount_saddle'))])
    root_lap = min(lap(root, supports) for root in roots)
    assert root_lap > .025, (label, 'el paño no nace de la costura (u)', round(root_lap,3))
    return np.array([stand_off, max_gap, skin_lap, root_lap])
