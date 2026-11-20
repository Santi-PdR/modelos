#!/usr/bin/env python3
"""Summarise metadata and method references; do not copy mod assets/code."""
import collections, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path
path = Path(sys.argv[1]); data = path.read_bytes()
lines = ['Ultimate Battle 1.1.1 / Minecraft 1.20.1, CurseForge file 9385647.',
         'SHA256: '+hashlib.sha256(data).hexdigest(),
         'Static reference analysis only; no source, textures or effects copied.', '']
with zipfile.ZipFile(path) as z:
    names = z.namelist()
    if 'fabric.mod.json' in names:
        meta=json.loads(z.read('fabric.mod.json'))
        lines += ['=== fabric.mod.json metadata ===']
        for key in ('id','name','version','license','environment','depends'):
            lines.append(f'{key}: {meta.get(key)}')
    lines += ['', '=== Relevant class names ===']
    classes=[n for n in names if n.endswith('.class') and re.search(r'(blade|katana|camera|cinema|cutscene|anim|battlecombo)',n,re.I)]
    lines += classes
    lines += ['', '=== Relevant animation/model metadata paths ===']
    lines += [n for n in names if n.endswith('.json') and re.search(r'(blade|katana|animation|cinema)',n,re.I)][:300]
    lines += ['', '=== Method signatures and call counts ===']
    chosen=[n for n in classes if re.search(r'(blade|camera|cinematic|battlecombo)',n,re.I) and not re.search(r'\$\d+\.class$',n)]
    for name in chosen[:45]:
        cls=name[:-6].replace('/','.')
        result=subprocess.run(['javap','-classpath',str(path),'-p','-c',cls],capture_output=True,text=True)
        if result.returncode != 0:
            lines.append(f'=== {cls}: unavailable ===');continue
        lines.append('=== '+cls+' ===')
        current=None
        for line in result.stdout.splitlines():
            if re.match(r'^  (public|private|protected|static)',line) and line.strip().endswith(';') and '(' in line:
                if current: lines.append('  calls: '+', '.join(f'{n} x{v}' for n,v in current.most_common(15)))
                lines.append(line.strip());current=collections.Counter()
            elif current is not None and '// Method ' in line:
                current[line.split('// Method ',1)[1].split(':',1)[0]] += 1
        if current is not None: lines.append('  calls: '+', '.join(f'{n} x{v}' for n,v in current.most_common(15)))
Path('katana_stain/referencias/ultimate_battle_auditoria.txt').write_text('\n'.join(lines)+'\n')
