#!/usr/bin/env python3
"""Stage the pre-branch worn cape for the optional Forge comparison, not the JAR."""
from argparse import ArgumentParser
from base64 import b64decode
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import subprocess
from zipfile import ZipFile

from fetch_published_jar import download_jar

ROOT = Path(__file__).resolve().parents[1]
FORK = '392648b3bd66f1c5fe73745ebadea925fe34499b'
RIG = 'capa_deteriorer_evilsaiyan'
REFERENCE = 'fixture_v1280'
JAR_SHA = '4608910630206fcd5c6dff1aa02e18e78989777a3f93bae22582c5dac045231f'
RENDER_CLASSES = ('CapaArmorRenderer', 'CapaArmorModel', 'CapaGlowLayer')


def source(path):
    local = subprocess.run(['git', 'show', f'{FORK}:{path}'], cwd=ROOT, capture_output=True)
    if local.returncode == 0:
        return local.stdout.decode('utf-8')
    endpoint = f'repos/Santi-PdR/modelos/contents/{path}?ref={FORK}'
    return b64decode(subprocess.check_output(['gh', 'api', endpoint, '--jq', '.content'])).decode('utf-8')


def main():
    ap = ArgumentParser(description=__doc__)
    ap.add_argument('--jar', type=Path, help='local copy of the v1.28.0 release JAR')
    ap.add_argument('--out', type=Path, default=ROOT/'build/generated/cape-history')
    args = ap.parse_args()
    data = args.jar.read_bytes() if args.jar else download_jar('1.28.0')[0]
    if sha256(data).hexdigest() != JAR_SHA:
        raise ValueError('v1.28.0 fixture digest does not match the published JAR')

    with ZipFile(BytesIO(data)) as jar:
        for family, suffix in [('geo', '.geo.json'), ('animations', '.animation.json'),
                               ('textures', '.png'), ('textures', '_glowmask.png')]:
            directory = f'assets/capatest/{family}/item/armor'
            target = args.out/'resources'/directory/f'{REFERENCE}{suffix}'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(jar.read(f'{directory}/{RIG}{suffix}'))

    directory = 'com/capatest/client'
    out = args.out/'java'/directory
    out.mkdir(parents=True, exist_ok=True)
    names = {name: name.replace('Capa', 'CapeHistorical', 1) for name in RENDER_CLASSES}
    for name, new in names.items():
        text = source(f'src/main/java/{directory}/{name}.java').replace(RIG, REFERENCE)
        if name == 'CapaArmorRenderer':
            # For the fit comparison use the historical diffuse atlas. The
            # old glow pass under the new controller can black out the cape.
            text = text.replace('addRenderLayer(new CapaGlowLayer(this));', '// Diffuse-only historical reference.')
        for old, renamed in names.items():
            text = text.replace(old, renamed)
        (out/f'{new}.java').write_text(text, encoding='utf-8')
    print(f'v1.28.0: activos verificados ({JAR_SHA[:12]}…), render de {FORK[:7]} preparado en {args.out}')


if __name__ == '__main__':
    main()
