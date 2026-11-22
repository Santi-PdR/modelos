# v1.67.36 · Las brasas siguen al torso agachado

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/bc9b8efe70abf8fda72a554eaf207899525d7716/entregables/v1.67.36/capatest-1.67.36.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.35](../v1.67.35/notas.md).

Con Shift, la .35 reducía la altura de los puntos de nacimiento según la caja de colisión y dejaba el origen vertical. La .36 aplica la inclinación del torso y el descenso visual de Minecraft al nacimiento. La brasa ya desprendida sigue su vuelo original. Se mantienen el intervalo y límite de emisión, el filtro por bloques, los 25 sprites y sus fundidos. En reposo de pie, planeo y nado se mantienen las proyecciones anteriores. No cambian el modelo, el halo ni los ocho clips.

## Comparación en Forge

Sobre la **misma postura real de Alex** al mantener Shift en F5, se evaluaron 27 combinaciones de variación del punto por zona y cuadro. Fueron seis cuadros en pecho y seis en Curios. El control usa la proyección vertical de la .35 en esa malla; no son dos recorridos independientes. Los valores son distancias geométricas, en bloques, no píxeles ni número de brasas visibles.

| Ranura | Zona | Distancia media al paño · .35 → .36 | Percentil 90 · .35 → .36 |
| --- | --- | ---: | ---: |
| Pecho | dobladillo | 0,240 → 0,188 | 0,292 → 0,229 |
| Pecho | costado | 0,287 → 0,072 | 0,358 → 0,150 |
| Curios | dobladillo | 0,234 → 0,196 | 0,283 → 0,238 |
| Curios | costado | 0,285 → 0,073 | 0,352 → 0,150 |

En los 648 puntos bajos, el error máximo respecto al mismo punto transformado por el torso pasó de **0,5358 bloques a menos de una millonésima de bloque**. También se comprobó la alineación del origen del cuello. Se mide el nacimiento, no que cada partícula toque la malla ni que siga pegada después. Una prueba con un muro detrás bloqueó el nuevo origen cuando cruzaba el bloque y lo permitió en espacio libre.

[Resumen](nacimiento-agachado-resumen.tsv) · [Pecho](nacimiento-agachado-pecho.tsv) · [Curios](nacimiento-agachado-curios.tsv) · [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44980630274) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/16bc75709b7fba736d62a526faed123e0737f571).

Se repitieron [marcha](continuidad-forge.tsv), [saltos](saltos-forge.tsv), [nado](nado-forge.tsv), [traspaso entre pecho y Curios](traspaso-forge.tsv), [maniobra y retorno](maniobra/retorno/retorno.tsv), [pausa de render](pausa-render-forge.tsv) y la [secuencia de sprites](secuencia-brasa-forge.tsv). Los puntos de planeo y nado de los dos JAR dieron la misma traza en 216 muestras Java.

En la comprobación de la nuca, separamos el desplazamiento del cambio discreto de Shift (cota de 1,65 unidades del modelo, referencia .35 de 1,631327) de la velocidad dentro de la misma pose (cota anterior de 2,3 unidades por tick). Dividir el primero por el intervalo variable entre dos cuadros había generado falsos picos. Esta corrección es sólo del verificador; el SHA-256 del JAR coincide con el de la primera compilación .36.

## Instalar o volver a v1.67.35

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). Verifica el tamaño (774.088 bytes) y SHA-256 antes de retirar los JAR anteriores de `capatest` en `test-1`. El archivo remoto se verificó; no se ejecutó el instalador en tu Windows.

Para comparar, quedate quieto con Shift en F5 y mirá de costado el nacimiento de las brasas. Para volver atrás, quitá `capatest-1.67.36.jar` y usá el [PowerShell de la .35](../v1.67.35/instalar-test-1.txt). La descarga pública no cambia.
