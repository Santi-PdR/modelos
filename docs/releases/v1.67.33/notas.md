# v1.67.33 · Salto agachado y brasas entre ticks

La prueba más reciente es [v1.67.34](../v1.67.34/notas.md). Este JAR queda disponible para volver atrás.

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/da2c83305c0fbe550a8f4c9a95561531afd9fc61/entregables/v1.67.33/capatest-1.67.33.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.32](../v1.67.32/notas.md).

- La nuca y la tira cosida siguen la postura de cabeza y torso en un salto agachado normal. Ya no pierden el ajuste por dejar de tocar el suelo. Se conservan las exclusiones para nado, escalera y élitros.
- El tamaño, el color y la opacidad de cada brasa se calculan en el mismo instante interpolado que su posición. El perfil, las tres imágenes, la trayectoria, las colisiones y el límite de emisión no cambian. El visor offline también interpola la apariencia; no simula la red ni los bloques de Minecraft.
- La geometría, el atlas, el halo, el icono y las curvas de los ocho clips siguen **byte por byte** iguales en el JAR. El [proyecto editable](https://raw.githubusercontent.com/Santi-PdR/modelos/da2c83305c0fbe550a8f4c9a95561531afd9fc61/docs/CAPA_v1.67.33.bbmodel) sólo cambia el nombre de versión.

## Pruebas en Forge

**Salto con Shift sostenido, Alex y cabeza centrada.** Puntos medidos en el marco del torso, en unidades de modelo (16 por bloque):

| Ranura | Despegue: control .32 → .33 | Aterrizaje: control .32 → .33 |
| --- | ---: | ---: |
| Pecho | 2,7584 → 0,0007 | 2,7583 → 0,0010 |
| Curios | 2,7579 → 0,0020 | 2,7590 → 0,0011 |

El control quita la traslación aérea de la .33 en **la misma pose** registrada, como hacía el corte por contacto con el suelo. No es una captura anterior ni una prueba de ausencia de cruces para todas las poses.

**Cambio real de ranura.** Con la pieza deteriorada puesta en Curios, la prueba quitó y volvió a equipar la pechera sana. En los **382** cuadros de la secuencia se dibujó un solo manto, incluido el cambio de renderer. Los vértices del halo mantuvieron el fundido y el tinte anterior en el primer cuadro del cambio; la tela siguió mezclando su pose. [Traza del salto y del equipo](traspaso-forge.tsv).

**Brasas.** Se leyeron los cuatro vértices de la partícula real en dos fracciones del mismo tick: el alfa enviado pasó de 84 a 132 (escala 0–255) y repetir la primera fracción dio su valor original. El ensayo del perfil para 22 duraciones a 60 FPS bajó el mayor salto de alfa de **0,312 a 0,110** (escala 0–1). Las fases de sprite siguen siendo discretas; la chispa conserva su impulso libre y el frenado contra un panel.

Además pasaron la [frenada y el retorno en ambos sentidos](maniobra/retorno/retorno.tsv), la [marcha](continuidad-forge.tsv), [saltos normales](saltos-forge.tsv), [escalera](escalera-forge.tsv), [posturas de Alex](revision-alex-forge.tsv), [nado](nado-forge.tsv), élitros, hotbar y recarga de recursos, incluido el respaldo al núcleo cuando falta el halo. [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44972113961) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/d704f3f78ac4e5e3f448765f4cc09fbdabcaf571).

## Instalar o volver atrás

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque completo de PowerShell](instalar-test-1.txt). Sólo retira JAR anteriores de `capatest` después de comprobar los 757.711 bytes y el SHA-256 del nuevo JAR. Se verificaron los bytes remotos; no se ejecutó en tu Windows.

Si volvés a la .32, quitá primero `capatest-1.67.33.jar` y usá el [instalador fijado de la .32](../v1.67.32/instalar-test-1.txt). No se modificó la descarga pública.
