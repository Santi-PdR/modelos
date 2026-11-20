#!/usr/bin/env python3
"""Offline structural/bytecode analysis, no reference art or code is redistributed."""
import collections, json, re, subprocess, sys, zipfile
from pathlib import Path
jar = sys.argv[1]
classes = [
 'com.eternalcraft.darkesthours.movesets.headtaker.HeadtakerServerEvents',
 'com.eternalcraft.darkesthours.movesets.headtaker.HeadtakerState',
 'com.eternalcraft.darkesthours.movesets.headtaker.client.HeadtakerClientEvents',
 'com.eternalcraft.darkesthours.skills.battle.BattleCombo',
 'com.eternalcraft.darkesthours.skills.mirage.client.CameraPose',
 'com.eternalcraft.darkesthours.item.windstorm.client.WindstormCinematics',
]
lines = ['Behavior study: Darkest Hours v1.0.0; static bytecode analysis, not a runtime trace.',
         'Names and call counts are observations; methods may be obfuscated. No artwork copied.', '']
for cls in classes:
    result = subprocess.run(['javap','-classpath',jar,'-p','-c',cls],capture_output=True,text=True,check=True).stdout
    lines += ['=== '+cls+' ===']
    current = None
    methods = []
    for line in result.splitlines():
        if re.match(r'^  (public|private|protected|static)', line) and line.strip().endswith(';') and '(' in line:
            current = [line.strip(), collections.Counter()]
            methods.append(current)
        elif current and '// Method ' in line:
            name = line.split('// Method ',1)[1].split(':',1)[0]
            current[1][name] += 1
    for signature, calls in methods:
        lines.append(signature)
        lines.append('  method calls: ' + ', '.join(f'{name} x{n}' for name,n in calls.most_common(20)))
    lines.append('')
with zipfile.ZipFile(jar) as z:
    lines.append('=== player-animation metadata ===')
    for name in z.namelist():
        if not name.startswith('assets/darkesthours/player_animation/') or not name.endswith('.json'): continue
        try:
            data=json.loads(z.read(name))
            if 'emote' in data:
                em=data['emote']; moves=em.get('moves',[])
                lines.append(f'{name}: begin={em.get("beginTick")} end={em.get("endTick")} stop={em.get("stopTick")} moves={len(moves)}')
            else:
                anim=data.get('animations',{})
                details = ', '.join(f'{key}: {val.get("animation_length")}s, {len(val.get("bones",{}))} bones' for key,val in anim.items())
                lines.append(f'{name}: {details or "other format"}')
        except (ValueError, TypeError): lines.append(name+': unsupported')
Path('katana_stain/referencias/darkesthours_comportamiento.txt').write_text('\n'.join(lines)+'\n')
