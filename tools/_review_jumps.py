"""One-shot diagnostics from the actual Forge artifacts."""
from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from os import environ
import sys
import traceback
import numpy as np
import verify_forge_jumps as V

slot = sys.argv[1]
root = Path(environ['RUNNER_TEMP'])
current, base = root/'jump-current', root/'jump-base'

def note(label, text):
    print(f'::notice title=Salto {slot} {label}::{text.replace("%", "%25").replace(chr(10),"%0A")}', flush=True)

def stage(label, fn):
    with redirect_stdout(StringIO()) as log:
        try:
            out = fn()
        except Exception as exc:
            out = None
            print(''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))[-3400:])
    note(label, log.getvalue() or 'OK')
    return out

old = stage('referencia', lambda: V.report(base, slot, reference=True))
now = stage('candidata', lambda: V.report(current, slot))
if now is None: sys.exit()
data, spans, rows = now

def diagnose():
    for e in spans:
        t = data['time']
        touch = t[e.land]
        drop = data['fall'][(t >= touch) & (t < touch + 2)]
        run = data['run'][(t >= touch + 8) & (t < touch + 11)]
        print(e.name, f'takeoff {t[e.start]:.2f}, yes floor {touch:.2f}, fall post-min {drop.min():.4f}, sprint after {run.max():.4f}')
    V.verdict(data, spans, rows, old[2] if old else None, slot)

stage('veredicto', diagnose)

def geometry():
    geo = V.load(V.ARMOR_GEO)
    rig = V.WornModel(V.fixed_wearer_pose(geo,0.,slim=True))
    source = defaultdict(list)
    for n, c in zip(rig.names,rig.place(V.matrices(geo)),strict=True): source[n].append(c)
    V.fit(current,slot,data,spans,rig,source)

stage('medida de las uniones', geometry)
