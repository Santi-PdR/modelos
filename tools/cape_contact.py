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
