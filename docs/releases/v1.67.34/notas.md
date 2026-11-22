# v1.67.34 · Continuidad de tela y halo tras un tirón

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/e6fde0d3db23264c105b9f88beacf404bdda1931/entregables/v1.67.34/capatest-1.67.34.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.33](../v1.67.33/notas.md).

Cuando vuelve el dibujo después de una pausa breve (hasta 0,5 s de tiempo del juego), el último giro o cambio de luz ya no se aplica retroactivamente a todo el intervalo sin cuadros. La tela mantiene su inercia y el halo continúa el fundido anterior, con hasta un tick de respuesta al dato nuevo en el cuadro de regreso. No intenta adivinar el instante del cambio ni aumentar los FPS. Se mantienen los reinicios tras ausencias largas, los cortes de posición del paño y la protección contra pasadas repetidas.

El modelo, las texturas, los shaders y las curvas de los ocho clips son **idénticos byte por byte**. El [proyecto Blockbench](https://raw.githubusercontent.com/Santi-PdR/modelos/e6fde0d3db23264c105b9f88beacf404bdda1931/docs/CAPA_v1.67.34.bbmodel) sólo cambia el nombre de versión. Se mantienen el fundido de tinte, las brasas y los ajustes de la .33.

## Comparación controlada contra el JAR anterior

Ocho ticks (0,4 s) entre cuadros: frenada e inversión del giro al entrar en sombra; luego, segunda inversión al salir a la luz. Salto absoluto entre el último cuadro antes de la pausa y el primero al volver:

| Medida | A la sombra · .33 → .34 | A la luz · .33 → .34 |
| --- | ---: | ---: |
| Respuesta de giro en el dobladillo (escala −1 a +1) | **1,627 → 0,379** (76,7 % menos) | **1,541 → 0,005** (99,7 % menos) |
| Intensidad del borde del halo (multiplicador) | **0,998 → 0,255** (74,4 % menos) | **1,041 → 0,292** (71,9 % menos) |

[Traza ejecutada con v1.67.33](pausa-v1.67.33.tsv) · [Traza ejecutada con v1.67.34](pausa-v1.67.34.tsv). Son medidas de los filtros, no grados de giro del jugador ni brillo de píxel.

## Verificación en Forge

En **15 cuadros** del renderer real, un maniquí con los mismos movimientos y luces, dibujado con y sin pausas, produjo el mismo UV2 de halo. La diferencia máxima de la punta en el marco del torso fue de **0 unidades de modelo en la traza** (16 unidades por bloque). Se midió lo que se envía al renderizador, no el brillo del píxel ni el rendimiento de un PC. Una pasada anterior del mismo tick no cambió ni la punta ni el brillo; un desplazamiento de teletransporte descartó el giro previo. [Mediciones de Forge](pausa-render-forge.tsv).

También pasaron la [frenada y el retorno al centro en ambos sentidos](maniobra/retorno/retorno.tsv), [marcha](continuidad-forge.tsv), [saltos](saltos-forge.tsv), [escalera](escalera-forge.tsv), [posturas de Alex](revision-alex-forge.tsv), [nado](nado-forge.tsv), [traspaso de pecho a Curios y vuelta](traspaso-forge.tsv), élitros, hotbar y recarga con respaldo de núcleo. [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44974313583) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/57d16ad34d24caea32b0e96e9bbcc46da3128caa).

## Instalar o volver a v1.67.33

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). Verifica el tamaño (758.172 bytes) y SHA-256 antes de retirar los JAR anteriores de `capatest` en `test-1`. Se verificó el archivo remoto; no se ejecutó el instalador en tu Windows.

Para volver atrás, quitá `capatest-1.67.34.jar` y pegá el [PowerShell de la .33](../v1.67.33/instalar-test-1.txt). La descarga pública no cambia.
