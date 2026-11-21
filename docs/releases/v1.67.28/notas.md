# v1.67.28 · Transiciones y caída del paño

**[Descargar el JAR de prueba](https://github.com/Santi-PdR/modelos/raw/5adcba808cff1cbdc59dda6b0c31fc6f76594188/entregables/v1.67.28/capatest-1.67.28.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.27](../v1.67.27/notas.md).

- **Arranque y frenada:** el paño abre y se asienta con menos tirón. En suelo seco, las bisagras abren y cierran de forma más gradual, sin cambiar el reloj de los pasos. El cambio entre caminar y correr pasa de seis a ocho ticks (de 0,30 s a 0,40 s). Los ciclos estables de v1.67.27 se conservan.
- **Reposo y agachado:** en reposo la flexión nace pequeña arriba y llega a las puntas con retardo, sin mover la montura. Al agacharse la sección baja cae un poco más y oscila menos. Sólo cambian las rotaciones de estos dos clips; no se agregaron traslaciones ni escalas.
- **Hombrera izquierda del portador:** se baja y orienta un poco el borde interior para dejar margen cuando gira la cabeza. Sigue recogida de frente (a la derecha en la vista frontal). La pieza mantiene su forma; la otra hombrera y la montura independiente de élitros se conservan.

## Comparaciones en el cliente Forge

- **F5, de carrera a reposo:** [pecho](comparacion-freno-pecho-forge.gif) · [Curios](comparacion-freno-curios-forge.gif).
- **Reposo y agachado:** [pecho](comparacion-calma-pecho-forge.gif) · [Curios](comparacion-calma-curios-forge.gif).
- **Hombrera:** [frente y giro de Alex](comparacion-giro-forge.jpg) · [montaje de Steve y Alex](../../capa_v16728_colocacion_forge.jpg).

| Alex | Arranque p90 (u/tick) | Frenada de carrera p90 (u/tick) | Arco en reposo / agachado (°) | Caja cabeza/placa en giro (u) | Canto frontal x99 (px) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pecho | 3,40 → 2,83 | 2,20 → 1,80 | 2,53 → 3,23 / 2,57 → 2,06 | 0,91 → 0,52 | 543,00 → 543,00 |
| Curios | 3,44 → 2,85 | 2,07 → 1,68 | 2,53 → 3,23 / 2,56 → 2,06 | 0,91 → 0,52 | 543,00 → 543,00 |

Valores de v1.67.27 → v1.67.28. `u` equivale a 1/16 de bloque. El p90 mide la rapidez de un punto de seguimiento al final del paño, en el marco del torso, no del movimiento de la cámara. El arco es la oscilación fundamental pico a pico de la bisagra inferior. El cruce entre cajas de malla es un proxy, no una medida de píxeles tapados ni garantía de holgura en todas las skins. `x99` es el percentil 99 horizontal de los píxeles de la placa. Los GIF son tomas reales, de dos recorridos independientes, sin interpolación artificial ni sincronización pie por pie.

[Transiciones con Steve y Alex](transiciones-forge.tsv) · [Reposo y agachado](reposo-agachado-forge.tsv) · [Ritmo de la zancada](ritmo-forge.tsv) · [Apoyos y canto frontal](hombrera-forge.tsv) · [Distintas miradas](hombrera-mirada-forge.tsv).

Trazas crudas de Alex:

| Ranura | Marcha y frenada .27 | Reposo y agachado .27 | Toma completa .28 |
| --- | --- | --- | --- |
| Pecho | [TSV](paso-pecho-marcha-v16727.tsv) | [TSV](paso-pecho-v16727.tsv) | [TSV](paso-pecho-v16728.tsv) |
| Curios | [TSV](paso-curios-marcha-v16727.tsv) | [TSV](paso-curios-v16727.tsv) | [TSV](paso-curios-v16728.tsv) |

También pasaron las pruebas en Forge de [posturas](revision-alex-forge.tsv), [escalera](escalera-forge.tsv), [saltos y aterrizaje](saltos-forge.tsv), [nado](nado-forge.tsv), élitros, halo, brasas y hotbar. Se conservan el GEO, los atlas, el icono, los efectos y la animación plegada.

Una [prueba posterior que combina carrera, giro y paso agachado](maniobra/README.md) encontró un tirón breve al iniciar el paso agachado, en ambas ranuras, con la montura fija. El diagnóstico no sustituye este JAR.

## Instalación y respaldo

- Minecraft Java **1.20.1**, Forge **47.3.0** y GeckoLib **4.8.1**. Curios **5.14.1** es opcional para `back`.
- Cerrá Minecraft y usá el [bloque PowerShell de `test-1`](instalar-test-1.txt) o reemplazá manualmente la versión anterior. El bloque valida el tamaño (**750.760 bytes**) y el SHA-256 antes de instalar y sólo retira JAR anteriores de `capatest` tras validar el nuevo. No se cambió la descarga ni el instalador público. El cliente Forge se probó en CI; el bloque no se ha ejecutado en tu Windows.
- [Proyecto de Blockbench](../../CAPA_v1.67.28.bbmodel) · [Visor offline](../../capa_v1170_visor.html). El proyecto editable guarda las curvas de base; el calce equipado y la mezcla de movimiento se aplican en el juego.
- [Respaldo de animaciones y proyecto v1.67.27](../../respaldos/v1.67.27/README.md), guardado antes de los retoques en [`fa5f2b1`](https://github.com/Santi-PdR/modelos/commit/fa5f2b1bb18d54d8a0f069773faaa342f28d4661).

[Marcha original .27](https://github.com/Santi-PdR/modelos/actions/runs/44924671178) · [Captura ampliada .27](https://github.com/Santi-PdR/modelos/actions/runs/44929858741): ambos JAR coinciden byte por byte con el entregado. [Compilación y capturas .28](https://github.com/Santi-PdR/modelos/actions/runs/44930868176) · [Comparación final aprobada y adjunto](https://github.com/Santi-PdR/modelos/actions/runs/44932083151) · [Fuentes verificadas](https://github.com/Santi-PdR/modelos/tree/fb91ca29c612c4023a3309038c58afcbb13dd33b). La comparación final se ejecutó por separado sobre las mismas capturas y el mismo JAR de la compilación .28.
