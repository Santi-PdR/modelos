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

    if len(sys.argv) > 4:
        rows = [tuple(map(float, row.split('\t'))) for row in Path(sys.argv[4]).read_text().splitlines()]
        # Stance × pitch (including the shallow end of the stroke) × yaw × wings × arm.
        assert len(rows) == 5 * 11 * 9 * 2 * 5
        q = F.seat_profile()
        js = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,check=True,text=True,capture_output=True,
                            input=json.dumps(dict(fit=F.viewer_profile(),seatSamples=[r[:5] for r in rows])))
        for (s,p,y,w,arm,*java), actual in zip(rows,json.loads(js.stdout),strict=True):
            snug = F.seating(s,p,y,arm,elytra=bool(w))
            python = [snug,1-q['depth']*snug,1-q['width']*snug,
                      F.depth(s,p,y)*profile['drapePerUnit']-q['hem']*snug]
            for tested in (java,actual):
                assert all(abs(a-b) < 1e-8 for a,b in zip(tested,python,strict=True)), (s,p,y,w,arm,tested,python)
        print(f'Ceñido del borde y remates: {len(rows)} poses coinciden en Java/Python/visor.')

    if len(sys.argv) > 5:
        import numpy as np
        rows = np.loadtxt(sys.argv[5]).tolist()
        assert len(rows) == 5 * 8 * 8 * 6 * 2
        profile = F.viewer_profile()
        names = profile['plates']['names']
        js = subprocess.run(['node','tools/check_viewer_pose.js'],cwd=P.ROOT,check=True,text=True,capture_output=True,
                            input=json.dumps(dict(fit=profile,plateSamples=[r[:5] for r in rows])))
        lip = profile['plates']['lips']
        for (s,p,y,w,arm,java,rise,reach), (amount,*mats) in zip(rows,json.loads(js.stdout),strict=True):
            k = F.plate_influence(s,p,y,arm,elytra=bool(w))
            assert abs(java-k) < 4e-8 and abs(amount-k) < 1e-8, (s,p,y,w,arm,java,k,amount)
            # The renderer passes the already rounded float influence here.
            assert abs(rise-F.smooth(*lip[:2],java)) < 4e-8, (s,p,y,w,arm,java,rise)
            assert abs(reach-F.smooth(*lip[2:],java)) < 4e-8, (s,p,y,w,arm,java,reach)
            geo = {'bones':[{'name':n,'cubes':[{},{}]} for n in names]}
            posed = P.matrices(F.wearer_pose(geo,s,p,y,elytra=bool(w),arm_effort=arm))
            expected = [posed[n].ravel() for n in names] + [posed.get('rim_'+n,posed[n]).ravel() for n in names]
            assert np.allclose(mats,expected,atol=1e-9,rtol=0), (s,p,y,w,arm)
        print(f'Placas visibles: {len(rows)} poses Java/Python/visor coinciden.')


if __name__ == '__main__':
    main()
