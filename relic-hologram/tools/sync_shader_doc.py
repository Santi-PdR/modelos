"""Sincroniza el apendice A de docs/BRILLO-Y-SHADERS.md con los ficheros reales.

El CI compara los bloques del apendice con los assets del jar y falla si no son
identicos (que es lo que evita que el GLSL explicado se quede atras). En vez de
copiar y pegar a mano, esto reescribe los bloques `json` y los dos `glsl` del
apendice con el contenido de:

    assets/minecraft/shaders/core/holocore_relic_glow.json
    assets/minecraft/shaders/core/holocore_relic_glow.vsh
    assets/minecraft/shaders/core/holocore_relic_glow.fsh

Uso: python3 tools/sync_shader_doc.py     (desde relic-hologram/)
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'src/main/resources/assets/minecraft/shaders/core'
DOC = ROOT / 'docs/BRILLO-Y-SHADERS.md'
HEADING = '## Apéndice A'


def main() -> int:
    doc = DOC.read_text(encoding='utf-8')
    if HEADING not in doc:
        raise SystemExit(f'no encuentro "{HEADING}" en {DOC}')
    head, tail = doc.split(HEADING, 1)

    contenidos = {
        'json': [(ASSETS / 'holocore_relic_glow.json').read_text(encoding='utf-8').strip('\n')],
        'glsl': [(ASSETS / name).read_text(encoding='utf-8').strip('\n')
                 for name in ('holocore_relic_glow.vsh', 'holocore_relic_glow.fsh')],
    }
    usados = {'json': 0, 'glsl': 0}

    def repl(match):
        lang, cuerpo = match.group(1), match.group(2)
        lista = contenidos.get(lang)
        if lista is None or usados[lang] >= len(lista):
            return match.group(0)
        nuevo = lista[usados[lang]]
        usados[lang] += 1
        if nuevo.strip('\n') == cuerpo.strip('\n'):
            return match.group(0)
        print(f'bloque {lang} #{usados[lang]} actualizado')
        return f'```{lang}\n{nuevo}\n```'

    tail = re.sub(r'```(json|glsl)\n(.*?)```', repl, tail, flags=re.S)
    DOC.write_text(head + HEADING + tail, encoding='utf-8')
    faltan = [lang for lang, lista in contenidos.items() if usados[lang] < len(lista)]
    if faltan:
        print(f'AVISO: faltan bloques en el apendice: {faltan}')
        return 1
    print('apéndice A sincronizado con los assets del shader')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
