#!/usr/bin/env python3
"""Check the live vanilla boat seat and the carried motion of the hem."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from verify_forge_gaits import text
from verify_forge_walk import read

SLOTS = ('pecho', 'curios')
PHASES = ('quieto', 'remo', 'bajar')


def verify(root):
    rows = ['ranura\tcuadros\tfall_36_quieto\tfall_37_quieto\tfall_36_remo\tfall_37_remo\t'
            'avance_remo_b_tick\tvelocidad_propia_b_tick\tpunta_quieto_deg\tpunta_remo_deg\t'
            'punta_freno_deg\tderiva_asiento_u']
    for slot in SLOTS:
        data = read(root / f'bote-{slot}.tsv')
        t = data['tick']
        assert len(data) >= 70 and np.isfinite(t).all() and (np.diff(t) >= 0).all() and t[-1] >= 110, slot

        def window(start, end, seated):
            samples = data[(t >= start) & (t < end)]
            assert len(np.unique(samples['tick'].astype(int))) >= 5, (slot, start, len(samples))
            assert (samples['pasajero'] == seated).all(), (slot, start, samples['pasajero'])
            return samples

        quiet, rowing, coasting = (window(*bounds, True) for bounds in ((14, 24), (39, 56), (80, 89)))
        window(96, 112, False)
        for band in (quiet, rowing, coasting):
            assert (band['suelo'] == 0).all(), (slot, 'se probó con los pies en el suelo')
            assert np.isin(band['clip_36'], ['AIR', 'FALL']).all() and (band['clip_37'] == 'IDLE').all(), slot
            assert np.isin(band['fx'], ['AIR', 'FALL']).all(), (slot, 'selección del aura')
            assert np.min(band['fall_36']) >= .21, (slot, band['fall_36'])
            for n in ('fall_37', 'walk_37', 'run_37', 'swim_37'):
                assert np.max(np.abs(band[n])) < 1e-6, (slot, n, band[n])

        transit = float(rowing['paso_xz'].mean())
        own = float(rowing['vel_xz'].mean())
        still, drift, release = (float(s['respuesta_punta_deg'].mean()) for s in (quiet, rowing, coasting))
        assert transit > .19 and own < .025, (slot, transit, own)
        assert np.max(quiet['paso_xz']) < .025 and np.mean(coasting['paso_xz']) < .08, slot
        assert abs(still) < .18 and drift < still - .125 and release > drift + .08, (slot, still, drift, release)
        seat = float(np.ptp(data['asiento_z']))
        assert seat < .006, (slot, seat)
        values = [quiet['fall_36'].mean(), quiet['fall_37'].mean(), rowing['fall_36'].mean(), rowing['fall_37'].mean(),
                  transit, own, still, drift, release, seat]
        rows.append('\t'.join([slot, str(len(data)), *(f'{v:.6f}' for v in values)]))
        print(f'{slot}: FALL quieto {values[0]:.1%} → {values[1]:.1%}, remando {values[2]:.1%} → {values[3]:.1%}; '
              f'punta en reposo, remo y freno {still:+.3f}° / {drift:+.3f}° / {release:+.3f}°. Bajada real con Shift.', flush=True)
    (root / 'bote-resumen.tsv').write_text('\n'.join(rows) + '\n')


def plate(root):
    pic = Image.new('RGB', (1280, 824), '#17121d')
    pen = ImageDraw.Draw(pic)
    text(pen, (20, 14), 'El manto al viajar en bote', 29, bold=True)
    text(pen, (20, 59), 'Alex en F5 · Forge 1.20.1 · Paño en reposo, con el avance del bote y al bajar con Shift.', 18, '#edc4db')
    for iy, slot in enumerate(SLOTS):
        y = 128 + iy * 349
        for ix, (phase, title) in enumerate(zip(PHASES, ('Quieto', 'Remando', 'Al bajar'), strict=True)):
            x = 20 + 419 * ix
            text(pen, (x, y - 28), f'{slot.capitalize()} · {title}', 18, bold=True)
            with Image.open(root / f'bote-{slot}-{phase}.png') as still:
                pic.paste(ImageOps.fit(still.convert('RGB'), (402, 309), Image.Resampling.LANCZOS), (x, y))
    pic.save(root / 'bote-forge.jpg', quality=94, optimize=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('shots', type=Path)
    cli.add_argument('--report-only', action='store_true', help='recalcular la tabla cuando sólo se archivaron las trazas')
    a = cli.parse_args()
    verify(a.shots)
    if not a.report_only:
        plate(a.shots)
