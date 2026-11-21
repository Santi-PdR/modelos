# v1.67.29 · Frenada al entrar en paso agachado

**[Descargar JAR de prueba](https://github.com/Santi-PdR/modelos/raw/309543f8f06f6e2d00c3722d980e8815ed111e31/entregables/v1.67.29/capatest-1.67.29.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.28](../v1.67.28/notas.md).

Al salir de carrera y pulsar `Shift` con `W` todavía apretada, el paño conserva parte de la apertura de la zancada y se cierra de forma gradual. La retención de holgura se desvanece en hasta **12 ticks**; la mezcla de clips sigue durando seis. No se cambiaron las animaciones, las hombreras, el GEO, el atlas, el plegado ni los efectos. El ajuste es para la bisagra, no para el cruce visual de la tela sobre la cabeza al sostener ese giro.

## Prueba en Forge

[La misma maniobra de Alex en ambas ranuras](maniobra/maniobra-forge.jpg) · [Comparación numérica](maniobra/maniobra-comparacion.tsv) · [Detalle del encastre y la malla](maniobra/maniobra-forge.tsv) · Trazas [pecho](maniobra/maniobra-pecho.tsv) y [Curios](maniobra/maniobra-curios.tsv).

| Ranura | Pico de velocidad de la punta .28 → .29 (u/tick) | Reducción del pico | Poses de malla .29 |
| --- | ---: | ---: | ---: |
| Pecho | 8,19 → **2,95** | 64 % | 86 |
| Curios | 11,64 → **2,97** | 74 % | 86 |

`u` equivale a 1/16 de bloque. Los picos se miden respecto al torso, sin contar la cámara, en recorridos independientes con la misma secuencia de teclas. Ambas ranuras quedaron bajo **6 u/tick**, con la montura fija, las costuras unidas y sin cruces significativos del paño con las piernas en las poses de la muestra. [Diagnóstico del JAR .28](../v1.67.28/maniobra/README.md).

También pasaron [marcha](continuidad-forge.tsv), [escalera](escalera-forge.tsv), [salto](saltos-forge.tsv), [nado](nado-forge.tsv), [posturas](revision-alex-forge.tsv), élitros, halo, brasas y hotbar. [Build reproducible y pruebas Forge](https://github.com/Santi-PdR/modelos/actions/runs/44953657027) · [Fuentes del JAR](https://github.com/Santi-PdR/modelos/tree/8aa309267b2727516e78d908d06638d7b6734183).

## Instalación y respaldo

- Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1**; Curios **5.14.1** opcional.
- Cerrá Minecraft y pegá el [bloque PowerShell de `test-1`](instalar-test-1.txt). Verifica **751.338 bytes** y el SHA-256 del JAR antes de retirar versiones anteriores de `capatest`. Se comprobó el bloque estáticamente; no se ejecutó en tu Windows. No se cambió la descarga ni el instalador públicos.
- [Blockbench](../../CAPA_v1.67.29.bbmodel) · [Visor offline](../../capa_v1170_visor.html) · [Respaldo exacto de v1.67.28](../../respaldos/v1.67.28/README.md). Las curvas editables son las mismas; la retención sólo actúa al equipar en Forge. Para volver a la .28, retirá primero el JAR .29 de `test-1/mods`.
