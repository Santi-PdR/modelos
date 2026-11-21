# v1.67.21 · Continuidad y ajuste equipado

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/4f96e5a8458b5cc1a534bd47a8b3758e24304c5a/entregables/v1.67.21/capatest-1.67.21.jar)** · [SHA-256](JAR.sha256) · [Comparación en Alex](comparacion-alex-forge.jpg) · [Steve y Alex en Forge](../../capa_v16721_colocacion_forge.jpg).

- La fase de las piernas se conserva al pasar de caminar a correr y al volver a caminar. La apertura del paño interpola entre ticks y deja de reaccionar de golpe al pico de cada pie. Frenar deja un breve arrastre en lugar de cerrar las bisagras de golpe.
- Las placas suben alrededor de **0,6u** en sus pivotes y el tejido existente sobre los hombros avanza **0,44u** para que el manto se lea un poco más de frente. Se conservan las piezas y su grosor.
- Sólo el borde alto de la capucha respira y acompaña el paso y el giro. La montura, los retornos, la costura y las raíces no siguen a la cabeza. No se mueve el paño hacia atrás para esconder los cruces.

## Comprobado en Forge 1.20.1

[Cliente de prueba y compilación reproducible](https://github.com/Santi-PdR/modelos/actions/runs/44860549521) · Fuentes `c05b981`. La compilación y los controles del cliente pasaron; la copia inicial a la rama falló y se recuperó el mismo JAR por SHA-256. Pecho y Curios se probaron con las pieles y mangas vanilla de Alex y Steve, con muestras dentro de los ticks y en sus límites. Las mismas matrices de colocación se comprobaron en sólido y emisión. No se cambian atlas, modelo original, animaciones base, hotbar, chispas ni el ajuste geométrico con élitros.

| Alex | Peor pico de la bisagra alta | Mayor velocidad de la punta | Píxeles de placa visibles sobre mangas |
| --- | ---: | ---: | ---: |
| Pecho | 14.38 → 8.93°/tick | 5.73 → 3.71u/tick | 757 → 899 px |
| Curios | 15.28 → 8.93°/tick | 6.24 → 4.08u/tick | 756 → 901 px |

Las dos primeras columnas comparan la mayor pendiente entre fotogramas en arranque, giro, comienzo de carrera y frenado. La última mide las placas renderizadas sobre las mangas en capturas con y sin placas. No mide el área de tela: el ajuste de la tela se aprecia en la comparación frontal. `u` = píxel de modelo (1/16 de bloque). [Marcha por transición](continuidad-forge.tsv) · [Lectura frontal](lectura-frontal-forge.tsv).

En las **152 posturas muestreadas de Alex** se mantuvo el solape mínimo de **0.173u** en la unión de las raíces y de **0.054u** entre paño y espalda. La capucha recorrió hasta **0.337u** respecto de su pose de reposo durante carrera. La placa compacta dejó de invadir la cabeza sólida en la vista cenital de pie y agachado. [Lámina de posturas](revision-alex-forge.jpg) · [Medidas](revision-alex-forge.tsv).

Sigue habiendo cruces con la cabeza al mirar muy arriba y con el brazo en algunas fases de carrera. Este ajuste conserva las proporciones de v1.67.20 y no es una solución de colisión para todas las poses o capas de piel. No se modifica el instalador público.
