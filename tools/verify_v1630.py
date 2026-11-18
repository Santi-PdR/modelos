#!/usr/bin/env python3
"""Registered comparison with v1.62.0 + solid tears, rig and viewer checks."""
from __future__ import annotations

import argparse
import base64
import json
import re

import numpy as np
from PIL import Image

import armor_model_pipeline as G
import bbmodel_export as B
import cape_animation_pipeline as A
import cape_aura
import cape_material as C
import cape_reference as R
import cape_surface as S
import preview_cloth as P
from verify_v1590 import check_editor, check_tracks
from verify_v1600 import crop, iou, registered_metrics
from verify_v1610 import fit_check, visor_fit
from verify_v1620 import GLOW, bright, emission_projection, protection, views, visor_material

BACKUP = P.ROOT / 'docs/respaldos/v1.62.0'
GEO_BASE = BACKUP / P.ARMOR_GEO.relative_to(P.ASSETS)
TEX_BASE = BACKUP / P.ARMOR_TEX.relative_to(P.ASSETS)
GLOW_BASE = TEX_BASE.with_stem(TEX_BASE.stem + '_glowmask')
CLIPS = BACKUP / A.ANIM.relative_to(P.ASSETS)
SPARKS = [f'textures/particle/capa_spark_{i}.png' for i in range(3)]
OPENINGS = (
    ('Tajo izquierdo', (495, 360, 522, 392)),
    ('Abertura entre dos capas', (494, 400, 520, 427)),
    ('Desgarro central', (537, 414, 577, 450)),
    ('Borde del jirón derecho', (609, 380, 648, 423)),
)


def shoulder_occluders(rgb):
    """Pink motes block some reference pixels; never treat them as a hole."""
    x, y, x1, y1 = R.CROP
    yy, xx = np.mgrid[y:y1, x:x1]
    r, g, b = np.moveaxis(rgb.astype(np.int16), 2, 0)
    near = (xx < 496) & (yy > 175) & (yy < 253)
    far = (xx > 583) & (yy > 173) & (yy < 224)
    return (near | far) & (r > 85) & (r-g > 36) & (b-g > 16)


def family_map(geo):
    faces, owners = S.visible_faces(geo)
    return np.where(owners >= 0, np.array([f['family'] for f in faces])[owners], 0)


def opening_pixels(labels, family, rect):
    x, y, _, _ = R.CROP
    left, top, right, bottom = rect
    window = np.s_[top-y:bottom-y, left-x:right-x]
    goal, clear = labels[window] == 0, family[window] == 0
    return int(np.count_nonzero(goal & clear)), int(goal.sum()), float(iou(goal, clear))


def similarity(geo, atlas, emission):
    old = P.load(GEO_BASE)
    (before, after), _ = registered_metrics(old, geo, atlas, baseline_atlas=TEX_BASE)
    for k, title in (('all', 'Silueta'), ('upper', 'Cuello y hombreras'),
                     ('lower', 'Jirones'), ('seam', 'Costura en U')):
        print(f'{title}: {before[k]:.2%} → {after[k]:.2%}')
    assert after['all'] > max(.955, before['all']+.0025), after['all']
    assert after['upper'] >= before['upper']-.001 and after['seam'] >= before['seam']-.001
    assert after['lower'] > before['lower']+.003
    print(f"RGB común: {before['mae']:.2f} → {after['mae']:.2f}/255")
    assert after['mae'] < min(1.7, .45*before['mae']), after['mae']

    rgb, labels, rose = (crop(v) for v in R.reference())
    common = (labels>0) & before['match'] & after['match']
    a, b = (iou(bright(views(g, t)) & common, rose & common) for g, t in ((old, TEX_BASE), (geo, atlas)))
    print(f'Rosa de las grietas: {a:.2%} → {b:.2%} (IoU)')
    assert b > .92 and b-a > .15
    cores = bright(rgb, cores=True) & rose & common
    a, b = [(emission_projection(g, t, l) & common) for g, t, l in
            ((old, TEX_BASE, GLOW_BASE), (geo, atlas, emission))]
    print(f'Núcleos emisivos: {iou(a, cores):.2%} → {iou(b, cores):.2%} (IoU)')
    assert iou(b, cores) > .94 and np.count_nonzero(cores & b)/b.sum() > .95

    f_old, f_new = family_map(old), family_map(geo)
    pad, covered = labels == R.SHOULDER, shoulder_occluders(rgb)
    p0, p1 = f_old == R.SHOULDER, f_new == R.SHOULDER
    a, b = iou(p0, pad), iou(p1, pad)
    print(f'Hombreras (traza completa): {a:.2%} → {b:.2%} (IoU)')
    assert b > .80 and b-a > .018
    a, b = (iou(v & ~covered, pad & ~covered) for v in (p0, p1))
    print(f'Hombreras (fuera de las motas): {a:.2%} → {b:.2%} (IoU)')
    assert b > a+.02 and p1[p0 & covered].mean() >= .995, 'una mota no es un hueco en la placa'
    for (title, rect), least in zip(OPENINGS, (.50, .73, .83, .83), strict=True):
        a, total, base = opening_pixels(labels, f_old, rect)
        b, _, current = opening_pixels(labels, f_new, rect)
        print(f'{title}: {a} → {b}/{total} píxeles de abertura; IoU {base:.2%} → {current:.2%}')
        assert current > max(least, base), title

    # Hidden sides cannot be registered to the source. Guard against adding
    # a facade that loses the thickness or the shape of the reverse.
    bg = (2, 211, 224)
    for yaw in (-38, 85, 180):
        masks = [(np.asarray(P.render(g, t, P.effective_hidden(g), yaw=yaw, pitch=8,
                                     size=320, frame=(0,15,9), bg=bg)) != bg).any(2)
                 for g, t in ((old, TEX_BASE), (geo, atlas))]
        assert iou(*masks) > .90, yaw
    print('Perfil, oblicua opuesta y forro conservan volumen (sin referencia para esas vistas).', flush=True)


def visor_embers():
    html = (P.ROOT/'docs/capa_v1170_visor.html').read_text()
    assert json.loads(re.search(r'^const INLINE_AURA = (.+);$', html, re.M)[1]) == cape_aura.profile()
    images = json.loads(re.search(r'^const INLINE_IMAGES = (.+);$', html, re.M)[1])
    for name in SPARKS:
        assert base64.b64decode(images[name.split('/')[-1]].split(',',1)[1]) == (P.ASSETS/name).read_bytes()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--look-only', action='store_true')
    cli.add_argument('--quick', action='store_true')
    args = cli.parse_args()
    geo = G.build_base()['minecraft:geometry'][0]
    atlas, glow, layout = C.map_material(geo, paint=True)
    assert layout['cards'] >= 270 and layout['density'][R.CLOTH] >= 16
    assert layout['emissive'] > 1500
    print(f"{layout['cards']} cartas · {layout['density'][R.CLOTH]:.2f} texels/u nominales de paño", flush=True)
    similarity(geo, atlas, glow)
    if args.look_only:
        return
    runtime = A.build(geo)
    protection(geo, atlas, glow, runtime, False, backup=BACKUP, changed=SPARKS)
    assert P.load(P.ARMOR_GEO) == geo and json.loads(A.ANIM.read_text()) == runtime
    for path, expected in ((P.ARMOR_TEX, atlas), (GLOW, glow)):
        with Image.open(path) as current:
            assert np.array_equal(np.asarray(current.convert('RGBA')), np.asarray(expected)), path
    bb = json.loads(B.DOC.read_text())
    check_editor(json.loads((BACKUP/'CAPA_v1.62.0.bbmodel').read_text()), bb, geo, atlas, runtime)
    check_tracks(runtime, json.loads(CLIPS.read_text()), bb)
    fit_check(geo, runtime['animations'], args.quick, pads=True)
    visor_fit(geo, runtime)
    visor_material(geo, atlas, glow)
    visor_embers()


if __name__ == '__main__':
    main()
