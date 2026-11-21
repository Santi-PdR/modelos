# v1.67.22 · Hombros y nuca

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/061b28ba00e54d94ca79092b3c1c3844fa10143c/entregables/v1.67.22/capatest-1.67.22.jar)** · [SHA-256](JAR.sha256) · [Antes y después en Alex](comparacion-alex-forge.jpg) · [Steve y Alex en Forge](../../capa_v16722_colocacion_forge.jpg).

La placa ancha queda más nivelada y un poco menos saliente. El borde granate avanza hacia las mangas y se ve debajo de las placas, sin separar sus uniones con el cuello. La montura, las raíces del paño y la articulación independiente de la capucha conservan el ajuste de v1.67.21.

El render equipado normal deja fuera sólo las dos pestañas del forro interior que cruzaban el pelo en cenital. El resto del forro sigue dibujándose. No se recortó la capucha ni se cambió el proyecto de Blockbench salvo el nombre de versión. El modelo base, el atlas, los clips, el icono, la variante con élitros y el instalador público no cambiaron.

## Ensayo en mundo

[Prueba Forge 1.20.1 y compilación reproducible](https://github.com/Santi-PdR/modelos/actions/runs/44865764157), fuentes `c59f50b`. Capturas con Alex y Steve, en pecho y Curios, usando las pieles vanilla y las mismas cámaras que la prueba de v1.67.21. En las cuatro cenitales de Alex (de pie y agachado) ya no se ve la raya oscura grande. [Medida de la zona del pelo](nuca-forge.tsv).

| Alex | Tela aislada en el frente, izquierda / derecha | Placas sobre las mangas, compacta / ancha, v1.67.21 → v1.67.22 |
| --- | ---: | ---: |
| Pecho | 175 / 268 px | 376 / 523 → 366 / 508 px |
| Curios | 178 / 270 px | 376 / 525 → 366 / 510 px |

La tela se mide con una toma de control que oculta sólo la tela de hombros. Es una medida del ajuste nuevo, no un recuento comparativo de toda la tela de v1.67.21. Las dos placas conservan el apoyo sobre sus mangas. [Tela y costuras](tela-frontal-forge.tsv) · [Lectura de placas, incluido Steve](lectura-frontal-forge.tsv).

En 76 muestras de postura por ranura en Alex se conservaron la costura mínima de **0.078u**, el contacto de las raíces de **0.173u** y el apoyo del paño contra la espalda de **0.055u** o más. La marcha de Alex y Steve pasó en ambas ranuras, con movimiento independiente de la capucha y sin reinicios de fase en la muestra. `u` = 1/16 de bloque. [Posturas](revision-alex-forge.jpg) · [Medidas de postura](revision-alex-forge.tsv) · [Transiciones de marcha](continuidad-forge.tsv).

Todavía hay cruces del cuello al mirar muy arriba y del paño con el brazo en carrera. La mejora de nuca se comprobó con Alex vanilla, no con todas las capas exteriores o modelos de pelo.
