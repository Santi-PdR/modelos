#!/usr/bin/env python3
"""Compare simulated mounting parameters with CapeFit compiled by javac."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys

import cape_backing as B
import cape_fit as F
import preview_cloth as P


def main():
    rows = [tuple(map(float, row.split('\t')))
            for row in Path(sys.argv[1]).read_text().splitlines()]
    assert len(rows) == 245
    profile = F.profile()
    result = subprocess.run(['node', 'tools/check_viewer_pose.js'], cwd=P.ROOT, check=True,
                            input=json.dumps(dict(fit=profile, fitSamples=[r[:3] for r in rows])),
                            capture_output=True, text=True)
    for row, js in zip(rows, json.loads(result.stdout), strict=True):
        stance, pitch, yaw, *java = row
        d = F.depth(stance, pitch, yaw)
        py = (d, 1+d/profile['gussetDepth'], d*profile['drapePerUnit'])
        for values in (py, js):
            assert all(math.isclose(a, b, rel_tol=0, abs_tol=1e-7)
                       for a, b in zip(java, values, strict=True)), (row, values)
    print(f'Java → Python y visor JS: {len(rows)} ajustes de montura coinciden')
    if len(sys.argv) > 2:
        tabs = [tuple(map(float, row.split('\t'))) for row in Path(sys.argv[2]).read_text().splitlines()]
        js = subprocess.run(['node', 'tools/check_viewer_pose.js'], cwd=P.ROOT, check=True,
                            input=json.dumps(dict(shoulderSamples=[r[:5] for r in tabs])),
                            capture_output=True, text=True)
        for (s,p,y,w,arm,*expected), actual in zip(tabs,json.loads(js.stdout),strict=True):
            python = F.shoulder_scales(s,p,y,elytra=w == 1)[1:] + F.yoke_scales(s,p,arm,elytra=w == 1)
            for out in (python,actual):
                assert all(math.isclose(a,b,rel_tol=0,abs_tol=4e-8)
                           for a,b in zip(out,expected,strict=True)), (out,expected)
        print(f'Remates y forro: {len(tabs)} muestras coinciden en Java/Python/visor.')

    if len(sys.argv) > 3:
        rows = [tuple(map(float, row.split('\t'))) for row in Path(sys.argv[3]).read_text().splitlines()]
        assert len(rows) == 990
        poses = [r[:4] for r in rows]
        js = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,check=True,text=True,capture_output=True,
                            input=json.dumps(dict(fit=F.viewer_profile(),backingSamples=poses)))
        for (s,p,y,w,*java), out in zip(rows,json.loads(js.stdout),strict=True):
            python = B.solve(F.head_in_body(s,p,y,outer=True),F.depth(s,p,y),elytra=bool(w))
            assert all(abs(a-b) < 9e-8 for a,b in zip(java,python,strict=True)), (s,p,y,java,python)
            assert all(abs(a-b) < 1e-8 for a,b in zip(out,python,strict=True)), (s,p,y,out,python)
        print(f'Respaldo alto: {len(rows)} poses coinciden en Java/Python/visor.')


if __name__ == '__main__':
    main()
