#!/usr/bin/env python3
"""Bake two scales of additive spill from the existing cloth crack cores.

Light is measured on each face in model units, not atlas pixels. Padding,
lining, hardware and unrelated UV islands never receive the convolution.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

import preview_cloth as P

CORE = P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem + '_glowmask')
HALO = P.ARMOR_TEX.with_stem(P.ARMOR_TEX.stem + '_halo')


def blur(signal, sigma_xy):
    for axis, sigma in enumerate(reversed(sigma_xy)):
        radius = int(np.ceil(3 * sigma))
        x = np.arange(-radius, radius + 1)
        kernel = np.exp(-0.5 * (x / sigma)**2)
        kernel /= kernel.sum()
        signal = np.apply_along_axis(lambda row: np.convolve(np.pad(row, radius), kernel, 'valid'), axis, signal)
    return signal


def faces(geo):
    """Return texel rectangles and face metadata of the already mapped GEO."""
    for b in geo['bones']:
        for cube in b.get('cubes', []):
            for side, spec in cube['uv'].items():
                uv = P.face_uv(spec)
                x0, y0 = np.floor(uv.min(axis=0)).astype(int)
                x1, y1 = np.floor(uv.max(axis=0)).astype(int) + 1
                yield b['name'], cube, side, uv, np.s_[max(y0, 0):y1, max(x0, 0):x1]


def build(geo, core):
    light = np.asarray(core.convert('RGBA'))
    assert light.shape == (512, 512, 4)
    halo = np.zeros(light.shape[:2] + (3,), np.uint8)
    written = np.zeros(light.shape[:2], bool)
    for bone, cube, side, uv, rect in faces(geo):
        src = light[rect]
        if not src[..., 3].any():
            continue
        assert bone.startswith('v17_ribbon_') and side != 'north', (bone, side)
        assert np.all(uv % 1 == .5) and not written[rect].any(), (bone, side, uv)
        written[rect] = True
        points = P.cube_points(cube, np.eye(4))[P.FACE_ORDER[side]]
        axes = np.linalg.norm(points[[0, 2]] - points[1], axis=1)
        density = (np.array(src.shape[:2][::-1]) - 1) / axes
        signal = (src[..., 0].astype(float) / 255) * (src[..., 3] / 255)
        # Hot pink on the lip of a cut, violet in the wider skirt.
        near = blur(signal, np.maximum(.65, density * .095))
        far = blur(signal, np.maximum(1., density * .235))
        spill = near[..., None] * (180, 56, 114) + far[..., None] * (93, 38, 137)
        halo[rect] = np.rint(np.minimum(spill, (114, 42, 111))).astype(np.uint8)
    assert not light[~written, 3].any()
    # Even wind-exposed lining/metal tiles stay black. This includes texels
    # touched by linear filtering (the core itself is nearest-sampled).
    for bone, _, side, uv, rect in faces(geo):
        if light[rect][..., 3].any():
            continue
        u, v = np.floor(uv.min(axis=0) - .5).astype(int)
        w, h = np.ceil(uv.max(axis=0) - .5).astype(int) + 1
        assert not halo[max(0, v):h, max(0, u):w].any(), (bone, side)
    return Image.fromarray(halo)


def write():
    with Image.open(CORE) as core:
        halo = build(P.load(P.ARMOR_GEO), core)
    halo.save(HALO, optimize=True)
    print(f'halo: {halo.size}, {np.count_nonzero(np.asarray(halo)[..., 0])} texels de luz de proximidad')


if __name__ == '__main__':
    write()
