# v1.67.23 · Holgura al mirar arriba y al esprintar

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/33e7b9a0dc127e08338875f80bda286319323e83/entregables/v1.67.23/capatest-1.67.23.jar)** · [SHA-256](JAR.sha256) · [Posturas de Alex frente a v1.67.22](comparacion-gestos-forge.jpg) · [Steve y Alex, pecho y Curios](../../capa_v16723_colocacion_forge.jpg).

Al mirar muy arriba, sólo cede el borde alto de la capucha; sus movimientos de respiración y de marcha siguen activos. En carrera, los tramos libres exteriores se recogen hacia atrás y hacia el centro. El ajuste entra y sale con la transición de carrera, sin mover las bisagras ni las raíces cosidas. Se conservan las placas, el ribete de los hombros, la caída en reposo y el forro de v1.67.22. El arte, los clips, el icono y el ajuste con élitros no cambiaron.

## Ensayo en Forge

[Forge 1.20.1 con GeckoLib y Curios](https://github.com/Santi-PdR/modelos/actions/runs/44876271487) · fuentes `f7b883b` · compilación reproducible. Los cruces se miden entre cubos, no en píxeles visibles. `u` = 1/16 de bloque.

| Alex | Cuello/cabeza a 64° arriba, v1.67.22 → v1.67.23 | Paño completo/brazos, pico sin y con ajuste | Paño libre/brazos, pico | Paño libre/brazos, promedio |
| --- | ---: | ---: | ---: | ---: |
| Pecho | 3.485 → 2.194u | 2.339 → 1.843u | 2.339 → 1.778u | 0.725 → 0.365u |
| Curios | 3.479 → 2.194u | 1.981 → 1.496u | 1.981 → 1.476u | 0.640 → 0.345u |

La comparación de brazos usa **las mismas 24 poses de carrera por ranura**: el control reconstruye los tramos desde sus huesos en Forge sin el desplazamiento nuevo. Las fotos son capturas del juego, no un control fotograma a fotograma de la carrera. Todavía hay cruces residuales en posturas extremas y en las raíces. [Medidas A/B](holgura-brazos-forge.tsv) · [Todas las posturas](revision-alex-forge.tsv).

En las cuatro cenitales de Alex se conservó más del **99.7%** de los píxeles de pelo de la .22 en la zona medida, sin píxeles oscuros nuevos dentro del pelo. Se verificaron ambas uniones de tela a placa, la costura mínima de **0.078u**, el contacto mínimo de raíz de **0.173u** y el apoyo del paño contra la espalda de **0.054u**. Deriva rígida inferior a 0.0001u. Sin cruces nuevos con piernas en la muestra. La marcha de Steve y Alex pasó en ambas ranuras, sin reinicios de fase. [Nuca](nuca-forge.tsv) · [Hombros](comparacion-alex-forge.jpg) · [Marcha](continuidad-forge.tsv).

Prueba para Minecraft Java 1.20.1 con Forge 47.3.0, GeckoLib 4.8.1 y Curios 5.14.1 opcional. No sustituye la descarga pública ni cambia el instalador.
