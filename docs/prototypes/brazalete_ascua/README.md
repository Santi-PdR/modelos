# Brazalete Ascua — estudio animado v1

[Previsualización interactiva de efectos](efectos_preview.html) · [Proyecto Blockbench con clips](Brazalete_Ascua_fit_v1.bbmodel) · [Máscara de brillo (estudio)](brazalete_ascua_glowmask.png) · [Atlas base 32×32](brazalete_ascua.png) · [Geometría original v0](Brazalete_Ascua_fit_v0.bbmodel) · [Esquema de ajuste](esquema.svg) · [Generador](../../../tools/prototype_brazalete_ascua.py).

La forma sigue siendo el brazalete de 15 cubos: carbón mate, puente granate y una grieta exterior en cuatro placas. El v1 separa el núcleo para ensayar dos clips de Blockbench:

- `grieta_pulso_sutil`: pulso cíclico de 1,8 s, con escala máxima de ±1,8% en la grieta.
- `resonancia_corta`: eco puntual de 0,36 s, con una expansión máxima conceptual de 4,5% que vuelve a reposo.

La previsualización HTML añade un halo local muy tenue, un punto de luz y dos motas pequeñas opcionales que ascienden junto a la grieta; incluye control de pausa, disparo manual del eco y cambio rosa/violeta para ilustrar el estado Blight. Las motas son sólo una simulación visual para decidir si conviene conservarlas, no partículas emitidas por el mod. La máscara blanca sólo marca la UV de la grieta.

## Alcance y validación

Todo permanece aislado en esta carpeta; no se modificó el GEO del manto, el registro de ítems, Curios, código de render, shaders ni JAR. El clip geométrico y la página SVG/HTML son **estudios de concepto**: no forman una animación conectada al juego. La máscara no es un pase emisivo operativo y el cambio de matiz y las dos motas sólo se simulan en la página. No se agregó un sistema de partículas al mod.

El generador valida los 15 cubos, grupos, clips y PNG. Eso no sustituye abrir el modelo en Blockbench: faltan revisar la animación, las UV, orientación en Steve/Alex, mangas, objetos en mano y encastre con el manto en juego. **No se declara aprobado visualmente ni probado en Forge.** La versión pública v1.67.13 sigue intacta; no se creó una build.
