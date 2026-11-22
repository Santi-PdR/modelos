#!/usr/bin/env python3
"""Check the eight equipped links against their .40 projection in the same Forge draw."""
import argparse
from pathlib import Path

import numpy as np

from cape_chain import LINKS, pose, profile
from verify_forge_gaits import table
from verify_forge_nape import chain_seam
from verify_forge_postures import ACTOR, read_boxes
from verify_forge_walk import read
from verify_v1600 import sat
from verify_v1660 import contacts

SLOTS = ('pecho', 'curios')
COLS = 'escena cuadros cuadros_activos recorrido_max_u enlace_min_u soporte_lado_min_u costura_min_u cruce_adicional_max_u'


def pose_metrics(groups, base, key, config):
    assert set(base) == set(LINKS) and all(len(groups[n]) == len(base[n]) == 1 for n in LINKS), key
    live = np.concatenate([groups[n] for n in LINKS])
    fixed = np.concatenate([base[n] for n in LINKS])
    shifts = live-fixed
    shift = shifts[4].mean(0)
    # The only accepted difference from .40 is the weighted translation of
    # each cube, including a stationary pair of sewn ends. No shape changes.
    np.testing.assert_allclose(shifts, np.broadcast_to(np.asarray(config['weights'])[:,None,None]*shift,shifts.shape),
                               atol=.004, rtol=0, err_msg=f'{key}: changed dimensions or anchoring')
    assert abs(shift[0]) < .003 and -.003 <= -shift[1] <= config['DROP']+.003 and -.003 <= shift[2] <= config['AWAY']+.003, (key,shift)
    join = (-sat(live[:-1],live[1:])).min()
    anchors = np.concatenate([g for n,g in groups.items() if n.startswith(('v17_cowl_', 'v19_cuellito_', 'v20_mount_saddle'))])
    # Either of the sewn end's first two links can supply the overlap.
    # In .40's upward look the terminal block is just outside one collar
    # box; its unchanged neighbor still connects it to the collar.
    ends = (-contacts(live[None,[0,1,6,7]],anchors[None])[0]).max(axis=0)
    support = ends.reshape(2,2).max(axis=1).min()
    sewn = chain_seam(groups)
    assert join > .004 and support > .025 and sewn > .15, (key,'disconnected join or end',join,support,sewn)
    obstacles = np.concatenate([g for n,g in groups.items() if n in ACTOR or n.startswith('v18_pad_')])
    depths = lambda links: np.maximum(0,-contacts(links[None],obstacles[None])[0])
    added = max(0., (depths(live)-depths(fixed)).max())
    assert added <= .009, (key,'additional wearer or plate intersection',added)
    return np.linalg.norm(shift),join,support,sewn,added


def meshes(root, stem, config):
    live, control = (read_boxes(root/f'{stem}-{suffix}.tsv') for suffix in ('cubos','cadena-fija'))
    assert len(live) >= 35 and set(live) == set(control), (stem,'same-draw comparison missing')
    a = np.array([pose_metrics(p,control[t],(stem,t),config) for t,p in live.items()])
    moved = a[:,0] > .025
    assert moved.sum() >= 6 and a[:,0].max() > .18, (stem,'swing did not reach the mesh',a[:,0].max())
    return stem,len(a),int(moved.sum()),a[:,0].max(),*a[:,1:4].min(0),a[:,4].max()


def walks(root, config):
    rows = []
    for shape in ('','steve-'):
        for slot in SLOTS:
            stem = f'paso-{shape}{slot}'
            route = read(root/f'{stem}.tsv')
            t = route['time']
            inputs = np.column_stack([route[k] for k in ('stride','pace','apoyo_cadena','freno_lento')])
            measured = np.column_stack([route[k] for k in ('cadena_caida_u','cadena_salida_u')])
            expected = np.array([pose(config,*row) for row in inputs])
            np.testing.assert_allclose(measured,expected,rtol=0,atol=.002,err_msg=stem)
            step = (35 < t) & (t < 69)
            run = (108 < t) & (t < 129)
            brake = (130 < t) & (t < 146) & (inputs[:,1] < .10)
            tail = (t > 151) & (t < 156)
            # At the start of this route the same wearer has just equipped
            # or teleported from another active fixture. Measure rest after
            # that input settles, before the first step at tick 20.
            rest = ((14 < t) & (t < 19)) | ((247 < t) & (t < 370))
            assert step.sum() > 20 and run.sum() > 12 and brake.sum() > 3 and tail.sum() > 4 and rest.sum() > 8, stem
            walk = np.ptp(measured[step,0]); sprint = measured[run,1].max(); carry = measured[brake,1].max()
            quiet = np.abs(measured[rest]).max()
            residual = np.abs(measured[tail]).max()
            assert walk > .065 and sprint > .23 and carry > .025 and residual < .016 and quiet < .003, (
                stem,walk,sprint,carry,residual,quiet)
            rows.append((stem,len(t),walk,sprint,carry,residual,quiet))
    table(root/'cadena-zancada-forge.tsv',
          'escena cuadros caida_ciclo_u salida_carrera_u arrastre_freno_u residual_1s_u reposo_max_u',rows)
    for stem, n, walk, sprint, carry, residual, quiet in rows:
        print(f'{stem}: {n} draws; step drop {walk:.3f}u; outward run {sprint:.3f}u, brake with low pace {carry:.3f}u, '
              f'after 1s {residual:.4f}u, rest {quiet:.4f}u.',flush=True)


def run(root, combined):
    p = profile()
    routes = ('maniobra','giro-inverso') if combined else ('revision-alex','saltos')
    a = [meshes(root,f'{route}-{slot}',p) for route in routes for slot in SLOTS]
    table(root/('cadena-maniobra-forge.tsv' if combined else 'cadena-geometria-forge.tsv'), COLS, a)
    for stem, total, active, travel, join, end, seam, hit in a:
        print(f'{stem}: {active}/{total} active poses, max {travel:.3f}u; join {join:.4f}u, ends {end:.3f}u, seam {seam:.3f}u, added hit {hit:.4f}u.', flush=True)
    if not combined:
        walks(root,p)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots',type=Path)
    cli.add_argument('--combined',action='store_true')
    args = cli.parse_args()
    run(args.shots,args.combined)
