#!/usr/bin/env python3
"""Comprueba, con numeros, que el aura se lee de color y no se quema.

El aura son quads con blend aditivo (suma) y, desde 1.0.12, un pase previo de
tinte (mezcla normal). Sobre un fondo claro el aditivo no puede dar color: sumar
a 0.95 lo lleva a 1.0, o sea blanco. Ese fue el fallo de 1.0.9-1.0.10, y no se
ve en el codigo, se ve en la captura.

Este script toma los numeros **del propio codigo** (diametros, pesos, alpha,
tinte, color del estado y pixel central de la textura), compone las dos pasadas
sobre tres fondos tipicos y falla si el resultado se satura o pierde el tono.
Asi el diseno queda verificado y no depende de que alguien lo mire a ojo.

Uso: python3 tools/check_aura_math.py
"""

import pathlib
import re
import struct
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
AURA_JAVA = ROOT / 'src/main/java/com/santipdr/holocore/client/RelicAura.java'
STATE_JAVA = ROOT / 'src/main/java/com/santipdr/holocore/client/RelicGlowState.java'
CONFIG_JAVA = ROOT / 'src/main/java/com/santipdr/holocore/config/RelicConfig.java'
AURA_PNG = ROOT / 'src/main/resources/assets/holocore/textures/relic/relic_aura.png'
RING_PNG = ROOT / 'src/main/resources/assets/holocore/textures/relic/relic_ring.png'

# Fondos de referencia (sRGB aproximado de lo que pinta el juego).
BACKGROUNDS = {
    'nieve': (0.93, 0.95, 0.97),
    'piedra': (0.35, 0.35, 0.36),
    'cueva': (0.02, 0.02, 0.03),
}

# Limites de aceptacion (elegidos para "se tine, no se quema ni parece sombra").
MAX_OSCURECIDO = 0.08       # sobre nieve no puede bajar la luminancia mas que esto
MIN_TONO_NIEVE = 0.10       # sobre nieve el resultado tiene que verse cian (b - r)
MIN_TONO_OSCURO = 0.15      # sobre fondo oscuro el tono tiene que ser claro
MAX_BLANCO = 0.95           # el canal mas bajo no puede acercarse a 1 (eso es blanco)


def floats(texto):
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', texto)]


def leer_constantes():
    aura = AURA_JAVA.read_text(encoding='utf-8')
    diametros = floats(re.search(r'DIAMETER = \{([^}]*)\}', aura).group(1))
    pesos = floats(re.search(r'WEIGHT = \{([^}]*)\}', aura).group(1))
    alpha = floats(re.search(r'AURA_ALPHA = ([\d.]+)F', aura).group(1))[0]
    boost = floats(re.search(r'TINT_ALPHA_BOOST = ([\d.]+)F', aura).group(1))[0]
    anillo = floats(re.search(r'RING_DIAMETER = ([\d.]+)F', aura).group(1))[0]
    darken = 1.0  # el tinte usa el color del estado tal cual

    state = STATE_JAVA.read_text(encoding='utf-8')
    # 1.0.17 movio los destinos de estado a constantes TARGET_* (antes se creaba
    # un Target por frame). Se aceptan las dos formas para que el numero salga
    # sea cual sea la que este en el codigo.
    idle = (re.search(r'TARGET_IDLE = new Target\(([^)]*)\)', state)
            or re.search(r'case IDLE -> new Target\(([^)]*)\)', state))
    assert idle is not None, 'no se encontro el color del estado IDLE en RelicGlowState'
    tinte = floats(idle.group(1))[:3]

    config = CONFIG_JAVA.read_text(encoding='utf-8')
    intensidad = floats(re.search(r'"auraIntensity", ([\d.]+)D', config).group(1))[0]

    # Eco en el suelo: su alpha maximo sale de flash=1, y el tinte va a su bola.
    # Se lee la constante del eco, no un literal suelto: `flash * 0.55F * fade`
    # tambien existe en el anillo y en la onda, y el script comprobaba otro numero.
    eco_alpha = floats(re.search(r'GROUND_ADDITIVE = ([\d.]+)F', aura).group(1))[0]
    eco_boost = floats(re.search(r'GROUND_TINT_BOOST = ([\d.]+)F', aura).group(1))[0]
    # Los otros dos pases de evento (1.0.50): la onda y el eco del anillo.
    onda = floats(re.search(r'SHOCK_ADDITIVE = ([\d.]+)F', aura).group(1))[0]
    onda_boost = floats(re.search(r'SHOCK_TINT_BOOST = ([\d.]+)F', aura).group(1))[0]
    eco_anillo = floats(re.search(r'ECHO_ADDITIVE = ([\d.]+)F', aura).group(1))[0]
    eco_anillo_boost = floats(re.search(r'ECHO_TINT_BOOST = ([\d.]+)F', aura).group(1))[0]
    # Las motas del vacio del End (1.0.52).
    mota = floats(re.search(r'MOTE_ADDITIVE = ([\d.]+)F', aura).group(1))[0]
    mota_boost = floats(re.search(r'MOTE_TINT_BOOST = ([\d.]+)F', aura).group(1))[0]
    return (diametros, pesos, alpha, boost, darken, tinte, intensidad, anillo,
            eco_alpha, eco_boost, onda, onda_boost, eco_anillo, eco_anillo_boost,
            mota, mota_boost)


def leer_pixel_central(ruta=AURA_PNG, modo='centro'):
    """Decodifica el PNG a mano (sin Pillow) y devuelve un pixel.

    ``modo='centro'`` devuelve el del centro (el aura es un degradado radial: ahi
    esta su pico). ``modo='pico'`` devuelve el pixel de mas peso, que es lo que hay
    que mirar en el anillo: su centro esta vacio, el aro esta a media textura.
    """
    data = ruta.read_bytes()
    pos, idat, ancho, alto, canal = 8, b'', 0, 0, 0
    while pos < len(data):
        largo = struct.unpack('>I', data[pos:pos + 4])[0]
        tipo = data[pos + 4:pos + 8]
        trozo = data[pos + 8:pos + 8 + largo]
        if tipo == b'IHDR':
            ancho, alto, _, canal = struct.unpack('>IIBB', trozo[:10])
        elif tipo == b'IDAT':
            idat += trozo
        pos += 12 + largo
    assert canal == 6, 'la textura del aura tiene que ser RGBA'
    crudo = zlib.decompress(idat)
    stride = ancho * 4
    previa = bytearray(stride)
    filas = []
    i = 0
    for _ in range(alto):
        filtro = crudo[i]
        i += 1
        fila = bytearray(crudo[i:i + stride])
        i += stride
        for x in range(stride):
            a = fila[x - 4] if x >= 4 else 0
            b = previa[x]
            c = previa[x - 4] if x >= 4 else 0
            if filtro == 1:
                fila[x] = (fila[x] + a) & 255
            elif filtro == 2:
                fila[x] = (fila[x] + b) & 255
            elif filtro == 3:
                fila[x] = (fila[x] + (a + b) // 2) & 255
            elif filtro == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                fila[x] = (fila[x] + pr) & 255
        filas.append(bytes(fila))
        previa = fila
    if modo == 'pico':
        mejor, elegido = -1.0, None
        for fila in filas:
            for x in range(0, stride, 4):
                a = fila[x + 3] / 255.0
                peso = a * (0.2126 * fila[x] + 0.7152 * fila[x + 1] + 0.0722 * fila[x + 2]) / 255.0
                if peso > mejor:
                    mejor, elegido = peso, tuple(c / 255.0 for c in fila[x:x + 4])
        assert elegido is not None, 'la textura del anillo esta vacia'
        return elegido
    centro = filas[alto // 2][(ancho // 2) * 4:(ancho // 2) * 4 + 4]
    return tuple(c / 255.0 for c in centro)


def luminancia(color):
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def componer(fondo, pesos, alpha, boost, darken, tinte, intensidad, tex):
    tex_rgb, tex_a = tex[:3], tex[3]

    # 1) Tinte: mezcla normal, capa por capa.
    dst = list(fondo)
    for peso in pesos:
        cobertura = min(1.0, peso * intensidad * boost * tex_a)
        for c in range(3):
            dst[c] = dst[c] * (1.0 - cobertura) + tinte[c] * darken * tex_rgb[c] * cobertura

    # 2) Aditivo encima (el shader de entidad multiplica color x textura).
    for peso in pesos:
        aporte = peso * intensidad * alpha * tex_a
        for c in range(3):
            dst[c] = min(1.0, dst[c] + tinte[c] * tex_rgb[c] * aporte)
    return tuple(dst)


def componer_eco(fondo, eco_alpha, eco_boost, tinte, tex):
    """Eco en el suelo: tinte (mezcla normal) y aditivo encima, con su textura."""
    tex_rgb, tex_a = tex[:3], tex[3]
    dst = list(fondo)
    cobertura = min(1.0, eco_alpha * eco_boost)
    for c in range(3):
        dst[c] = dst[c] * (1.0 - cobertura) + tinte[c] * tex_rgb[c] * cobertura
    for c in range(3):
        dst[c] = min(1.0, dst[c] + tinte[c] * eco_alpha * tex_rgb[c] * tex_a)
    return tuple(dst)


def main():
    (diametros, pesos, alpha, boost, darken, tinte, intensidad, anillo, eco_alpha, eco_boost,
     onda, onda_boost, eco_anillo, eco_anillo_boost, mota, mota_boost) = leer_constantes()
    tex = leer_pixel_central()
    print(f'textura centro: rgb {tuple(round(c, 2) for c in tex[:3])} alpha {tex[3]:.2f}')
    print(f'diametros {diametros}  pesos {pesos}  auraAlpha {alpha}  '
          f'tinte +{boost}x oscurecido {darken}  intensidad {intensidad}')

    fallos = []
    # El anillo es una linea: si queda dentro del aura no se lee como anillo.
    if anillo <= max(diametros):
        fallos.append(f'el anillo ({anillo} bloques) queda dentro del aura ({max(diametros)})')

    for nombre, fondo in BACKGROUNDS.items():
        salida = componer(fondo, pesos, alpha, boost, darken, tinte, intensidad, tex)
        tono = salida[2] - salida[0]
        print(f'  {nombre:7s} fondo {tuple(round(c, 2) for c in fondo)} -> '
              f'{tuple(round(c, 2) for c in salida)}  tono(b-r) {tono:+.2f}')

        if min(salida) > MAX_BLANCO:
            fallos.append(f'{nombre}: se blanquea (canal minimo {min(salida):.2f} > {MAX_BLANCO})')
        if nombre == 'nieve':
            if tono < MIN_TONO_NIEVE:
                fallos.append(f'nieve: el tono se pierde (b-r {tono:+.2f} < {MIN_TONO_NIEVE})')
            caida = luminancia(fondo) - luminancia(salida)
            if caida > MAX_OSCURECIDO:
                fallos.append(f'nieve: parece una sombra (baja {caida:.2f} > {MAX_OSCURECIDO})')
        if nombre == 'cueva':
            if tono < MIN_TONO_OSCURO:
                fallos.append(f'cueva: el tono se pierde (b-r {tono:+.2f} < {MIN_TONO_OSCURO})')
            if sum(salida) <= sum(fondo):
                fallos.append('cueva: el aura no ilumina')

    # --- Eco en el suelo (1.0.48): antes solo sumaba y sobre nieve se quedaba -----
    # blanco; ahora lleva tinte debajo. Se comprueba igual que el aura.
    eco_tex = leer_pixel_central(RING_PNG, 'pico')
    print(f'anillo pico: rgb {tuple(round(c, 2) for c in eco_tex[:3])} '
          f'alpha {eco_tex[3]:.2f}  eco {eco_alpha:.2f} x {eco_boost:.2f}')
    for nombre, fondo in BACKGROUNDS.items():
        salida = componer_eco(fondo, eco_alpha, eco_boost, tinte, eco_tex)
        tono = salida[2] - salida[0]
        print(f'  eco {nombre:5s} -> {tuple(round(c, 2) for c in salida)}  tono(b-r) {tono:+.2f}')
        if min(salida) > MAX_BLANCO:
            fallos.append(f'eco {nombre}: se blanquea (canal minimo {min(salida):.2f})')
        if nombre == 'nieve' and tono < MIN_TONO_NIEVE:
            fallos.append(f'eco nieve: el tono se pierde (b-r {tono:+.2f})')

    # --- Los otros dos pases de evento (1.0.50) --------------------------------
    # La onda de chispas y el eco del anillo eran 0.55 de aditivo: sobre nieve,
    # blanco. Se comprueban con la misma regla que el eco del suelo.
    eventos = [
        ('onda', onda, onda_boost, leer_pixel_central()),
        ('eco anillo', eco_anillo, eco_anillo_boost, eco_tex),
        ('motas', mota, mota_boost, leer_pixel_central()),
    ]
    for nombre, aditivo, tinte_boost, tex in eventos:
        print(f'{nombre}: aditivo {aditivo:.2f}  tinte x{tinte_boost:.2f}  '
              f'texto rgb {tuple(round(c, 2) for c in tex[:3])} alpha {tex[3]:.2f}')
        for fondo_nombre, fondo in BACKGROUNDS.items():
            salida = componer_eco(fondo, aditivo, tinte_boost, tinte, tex)
            tono = salida[2] - salida[0]
            print(f'  {nombre} {fondo_nombre:5s} -> {tuple(round(c, 2) for c in salida)}  '
                  f'tono(b-r) {tono:+.2f}')
            if min(salida) > MAX_BLANCO:
                fallos.append(f'{nombre} {fondo_nombre}: se blanquea '
                              f'(canal minimo {min(salida):.2f})')
            if fondo_nombre == 'nieve' and tono < MIN_TONO_NIEVE:
                fallos.append(f'{nombre} nieve: el tono se pierde (b-r {tono:+.2f})')

    if fallos:
        for fallo in fallos:
            print(f'FALLO: {fallo}')
        return 1
    print('Aura OK: se lee de color sobre los tres fondos y no satura.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
