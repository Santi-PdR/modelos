#!/usr/bin/env python3
"""Keep the Java pose, Python mesh checks and live/offline visor in sync."""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from cape_chain import pose, profile

ROOT = Path(__file__).resolve().parents[1]


def verify(samples):
    p = profile()
    rows = np.loadtxt(samples, ndmin=2)
    assert rows.shape == (3690, 6)
    inline = re.search(r'^const INLINE_FIT = (.*);$', (ROOT/'docs/capa_v1170_visor.html').read_text(), re.M)
    assert inline and json.loads(inline[1])['chainMotion'] == p, 'regenerate the offline fit profile'
    np.testing.assert_allclose([pose(p,*r[:4]) for r in rows], rows[:,4:], rtol=0, atol=1e-12)
    source = (ROOT/'preview/app.js').read_text()
    functions = source[source.index('function smooth('):source.index('function haloDusk(')]
    js = functions + '''
const [profile,rows] = JSON.parse(require('node:fs').readFileSync(0,'utf8'));
for (const [phase,pace,support,brake,dy,dz] of rows) {
  const [y,z]=chainPose(profile,phase,pace,support,brake);
  if (!(Math.abs(y-dy)<1e-12 && Math.abs(z-dz)<1e-12)) throw new Error(`Chain JS differs at ${phase}/${pace}/${support}/${brake}`);
}
'''
    subprocess.run(['node','-e',js],input=json.dumps([p,rows.tolist()]),text=True,check=True)
    print(f'Cadena: {len(rows)} muestras iguales en Java, Python y el visor.',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples',type=Path)
    verify(parser.parse_args().samples)
