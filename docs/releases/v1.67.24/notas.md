# v1.67.24 · El paño acompaña la transición de nado

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/1303d5cad7d7a29dae985908c27b82de8c84b8d9/entregables/v1.67.24/capatest-1.67.24.jar)** · [SHA-256](JAR.sha256) · [Capturas de nado en Forge](comparacion-nado-forge.jpg) · [Steve y Alex, pecho y Curios](../../capa_v16724_colocacion_forge.jpg).

En v1.67.23 bastaba estar en el agua para que el manto reprodujera el clip horizontal, incluso al vadear o al volver a ponerse de pie. Ahora ese clip se mezcla con la postura vertical usando la interpolación de nado de Minecraft. Al vadear, el paño vuelve a reposo o marcha; cuando el avatar nada en horizontal, conserva el clip completo. La inmersión sigue amortiguando el paño y no cambia el color ni las brasas.

El peso se actualiza con el mismo reloj de render en pecho y Curios, sin reiniciar la fase del clip. En el límite entre agua y tierra se acota el cambio a 0.10 de peso por tick para que el paño no salte de pose. Esa orilla se probó con entradas deterministas; el recorrido de Forge de abajo entra y sale **del nado sin salir de la piscina**.

## Reproducción y verificación en Forge

| Versión y ranura | Cuadros F5 | Peso del nado al vadear | En horizontal | De nuevo de pie |
| --- | ---: | ---: | ---: | ---: |
| v1.67.23 · Pecho | 147 | 100 % | 100 % | 100 % |
| v1.67.24 · Pecho | 158 | 0 % | 100 % | 0 % |
| v1.67.24 · Curios | 155 | 0 % | 100 % | 0 % |

Los pesos de v1.67.24 coincidieron con los del avatar en las fracciones de entrada y salida, con un error máximo de `5e-8` en la escala 0–1. Al quedar erguido, la bisagra superior pasó de una media de **13.88° a 4.17° en pecho**; Curios quedó en **3.97°** en la candidata. Son recorridos independientes, no fotogramas emparejados. La comparación con v1.67.23 es sólo de pecho; la toma inicial de pecho sigue al ensayo de planeo, a diferencia de la de Curios. [Resumen de medidas](nado-forge.tsv) · [Referencia de pecho](nado-ciclo-pecho-v16723.tsv) · [Pecho v1.67.24](nado-ciclo-pecho-v16724.tsv) · [Curios v1.67.24](nado-ciclo-curios-v16724.tsv).

También pasaron la marcha de Steve y Alex sin reinicios de fase, el ajuste de capucha al mirar arriba, el encastre de hombros, la holgura del paño en carrera, los élitros plegados y en planeo y el icono en la hotbar. En la auditoría de Alex, los solapes mínimos de costura, raíz y apoyo dorsal fueron **0.078 / 0.173 / 0.054 u** (`u` = 1/16 de bloque). Son mediciones sobre las posturas de ensayo, no una garantía de ausencia de cruces en todas las poses. [Marcha](continuidad-forge.tsv) · [Posturas de Alex](revision-alex-forge.tsv) · [Control pareado de brazos](holgura-brazos-forge.tsv).

## Compilación e instalación

[Compilación reproducible con Java 17 y prueba real en Forge](https://github.com/Santi-PdR/modelos/actions/runs/44900871606) · [commit de fuentes](compilacion.txt). Los 18 recursos de arte, incluidos el modelo, los ocho clips, el atlas y el icono, son los mismos; la transición se aplica al equipar el manto, no se hornea en Blockbench.

Para Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1** y Curios **5.14.1** opcional. Con Minecraft cerrado, sustituye el JAR anterior de `capatest` en `test-1/mods`; no dejes las dos versiones juntas. Esta prueba no modifica el instalador ni la descarga pública.
