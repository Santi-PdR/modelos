"""Rigid collar fit, measured in torso model pixels, not screen overlap."""
from __future__ import annotations

import numpy as np

from verify_v1600 import sat


def lap(a, b):
    """Best intersection of two groups of oriented, possibly scaled cubes."""
    pairs = np.repeat(a, len(b), axis=0), np.tile(b, (len(a), 1, 1))
    return float(-sat(*pairs).min())


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


def original_dimensions(parts, source, label):
    """An affine fit can keep the asset hashes but still warp the visible model."""
    edges = np.triu_indices(8, 1)

    def distances(boxes):
        v = np.asarray(boxes)
        return np.sort(np.linalg.norm(v[:, edges[0]]-v[:, edges[1]], axis=2), axis=1)

    count = 0
    for name, boxes in parts.items():
        if name not in source:
            continue  # vanilla player boxes
        target = source[name]
        assert len(boxes) == len(target), (label, name, 'cambió el número de cubos')
        np.testing.assert_allclose(distances(boxes), distances(target), atol=.004, rtol=0,
                                   err_msg=f'{label}: cambió la forma de {name}')
        count += len(boxes)
    assert count >= 60, (label, 'faltan piezas visibles de la capa', count)
    return count


def shoulder_seams(parts, label):
    """Each visible strip must still meet its own plate and collar return."""
    strips = np.asarray(parts['v20_mount_shoulders'])
    returns = np.asarray(parts['v17_cowl_return'])
    assert len(strips) == 2, (label, 'faltan piezas de tela sobre los hombros')
    seams = []
    for n in ('v18_pad_0','v18_pad_1'):
        pad = np.asarray(parts[n])
        sign = np.sign(pad[:,:,0].mean())
        fabric = strips[strips[:,:,0].mean(1)*sign>0]
        back = returns[returns[:,:,0].mean(1)*sign>0]
        assert len(fabric) == 1 and len(back), (label,n)
        seam = [lap(fabric,back),lap(fabric,pad)]
        assert seam[0] > .15 and seam[1] > .28, (label,n,'se separó la tela del hombro',seam)
        seams.append(seam)
    return np.asarray(seams)


def back_and_sleeves(parts, label):
    """Check visible cloth against bare skin, not a hidden gusset against a jacket."""
    body = np.asarray(parts['body'])
    lo, hi = body[0].min(0), body[0].max(0)
    np.testing.assert_allclose(hi-lo, [8,12,4], atol=.006, rtol=0, err_msg=f'{label}: vanilla torso basis')
    center = (lo[0]+hi[0])/2
    back, top = hi[2], hi[1]
    roots = [np.asarray(parts[f'v17_ribbon_{i}_seg0']) for i in range(12)]
    assert all(len(r) for r in roots), label
    cloth = np.concatenate(roots)
    # The lower seam of the tall original collar sits on the upper back.
    # The raised crown above the neck must not be flattened into this plane.
    samples = [(x, top-drop) for drop in np.linspace(2.55, 4.20, 7)
               for x in center + np.linspace(-2.50, 2.50, 9)]
    coverage = np.asarray([any(a <= back+.065 and b > back+.125 for a,b in line)
                           for line in depth_intervals(cloth, np.asarray(samples))]).reshape(7,9)
    count = int(coverage.sum())
    contact = lap(cloth, body)
    assert contact > .15 and count >= 42 and min(coverage[:, :4].sum(),coverage[:, -4:].sum()) >= 15, (
        label, 'el paño visible no toca la espalda a ambos lados', round(contact,3), coverage.sum(1).tolist())
    support = np.concatenate([v for n,v in parts.items() if n.startswith(
        ('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_', 'v20_mount_saddle'))])
    joins = min(lap(r, support) for r in roots)
    assert joins > .025, (label, 'la raíz no se une al cuello', round(joins,3))
    pads = [np.asarray(parts[n]) for n in ('v18_pad_0','v18_pad_1')]
    sleeves = [np.asarray(parts[n]) for n in ('left_sleeve','right_sleeve')]
    lap_sleeves = np.asarray([[lap(p,s) for s in sleeves] for p in pads])
    assert sorted(lap_sleeves.argmax(1)) == [0,1] and lap_sleeves.max(1).min() > .35, (label, lap_sleeves)
    returns = np.asarray(parts['v17_cowl_return'])
    for p in pads:
        side = np.sign(p[:,:,0].mean()-center)
        assert lap(p,returns[(returns[:,:,0].mean(1)-center)*side > 0]) > .13, (label, 'placa sin retorno')
    return contact, count, joins, lap_sleeves.max(1)
