#!/usr/bin/env python3
"""Localizar piezas del manto dentro de la cabeza en las tomas de Forge.

Las profundidades de cajas son un diagnóstico, no píxeles atravesados. Se
conservan la toma y los cubos medidos de la misma pasada para poder analizar
la corona sin atribuirle automáticamente un cruce de otra pieza.
"""
import argparse
from collections import Counter
from pathlib import Path

import numpy as np

from verify_forge_combined import SLOTS, timeline
from verify_forge_gaits import crop, table
from verify_forge_postures import read_boxes
from verify_forge_walk import read
from verify_v1660 import contacts


def is_collar(name):
    return name.startswith(('v17_cowl_', 'v19_cuellito_'))


def measure(root, out):
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    for slot in SLOTS:
        stem = f'maniobra-{slot}'
        data = read(root/f'{stem}.tsv')
        timeline(data, slot)
        meshpath = root/f'{stem}-cubos.tsv'
        mesh = read_boxes(meshpath)
        assert sorted(mesh) == list(data['time'][data['fit'] == 1].astype(int)), slot
        view = data[data['image'] != '-']
        photos = {int(r['time']): str(r['image']) for r in view if 62 <= r['time'] < 80}
        assert len(photos) == 2, slot
        ids = sorted(set(photos) | {t for t in (49, 52, 58, 67, 70, 73, 82, 86, 93, 103) if t in mesh})
        lines = []
        for t, groups in mesh.items():
            r = data[(data['time'].astype(int) == t) & (data['fit'] == 1)][0]
            head = np.array([groups['head'][0], groups['hat'][0]])
            np.testing.assert_allclose(np.linalg.norm(head[:, [1, 3, 4]]-head[:, :1], axis=2), [[8]*3, [9]*3], atol=.004)
            pieces = [(n, i, box) for n, group in groups.items() if n not in ('head','hat','body','jacket',
                      'left_sleeve','right_sleeve','left_arm','right_arm','left_leg','right_leg')
                      for i, box in enumerate(group)]
            hits = np.maximum(0., -contacts(np.array([[box for _, _, box in pieces]]), head[None])[0].T)
            if t in photos:
                assert r['crouching'] == 1 and r['sneak'] > .99 and r['yaw'] > 23 and r['pitch'] < -14, (slot, r)
                crown = [tuple(row) for row, (name, _, _) in zip(hits, pieces, strict=True) if is_collar(name)]
                rank = sorted(((p[0], p[1], n, i) for (n, i, _), p in zip(pieces, hits, strict=True)), reverse=True)
                print(f'{slot}: t={r["time"]:.2f}, yaw {r["yaw"]:.2f}°, pitch {r["pitch"]:.2f}°; '
                      f'cuello/cabeza {max(p[0] for p in crown):.3f}u. Mayores cruces: '
                      + ', '.join(f'{n}[{i}] {a:.3f}/{b:.3f}u' for a,b,n,i in rank[:5]), flush=True)
                # Upper-body detail from the actual unaltered color pass.
                crop(root/photos[t], 330, 230, .10, .55).save(out/f'{slot}-{t}-detalle.png', optimize=True)
                for a,b,n,i in rank:
                    if b > .05:
                        summary.append((slot,t,f'{r["time"]:.5f}',photos[t],f'{r["pitch"]:.4f}',f'{r["yaw"]:.4f}',n,i,f'{a:.6f}',f'{b:.6f}'))
            if t in ids:
                important = ('head', 'hat', 'body', 'v20_mount_seat', 'v20_mount_saddle', 'v20_mount_shoulders', 'v18_pad_0', 'v18_pad_1')
                lines.extend((t,n) for n in groups if (is_collar(n) or n in important or n.startswith('v18_chain_')
                                                      or n.startswith('v17_ribbon_') and n.endswith('_seg0')))
        keep = set(lines)
        raw = [line for line in meshpath.read_text().splitlines() if (int(line.split('\t',2)[0]), line.split('\t',2)[1]) in keep]
        assert set(Counter(int(line.split('\t',1)[0]) for line in raw)) == set(ids)
        (out/f'{slot}-cubos.tsv').write_text('\n'.join(raw)+'\n')
    table(out/'cruces.tsv', 'ranura tick tiempo cuadro pitch yaw pieza cubo cabeza_u capa_exterior_u', summary)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('capturas', type=Path)
    cli.add_argument('salida', type=Path)
    args = cli.parse_args()
    measure(args.capturas, args.salida)
