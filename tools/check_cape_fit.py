#!/usr/bin/env python3
"""Compare simulated mounting parameters with CapeFit compiled by javac."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys

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


if __name__ == '__main__':
    main()
