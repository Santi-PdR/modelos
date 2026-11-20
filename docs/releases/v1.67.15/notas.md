# v1.67.15 · Prueba del anclaje equipado

[Descargar el JAR verificado](https://github.com/Santi-PdR/modelos/raw/8b794488ab4a4e32a685307bb0751bafc7261329/entregables/v1.67.15/capatest-1.67.15.jar) · [SHA-256](JAR.sha256) · [Capturas reales en F5](../../capa_v16715_anclaje_forge.jpg) · [Proyecto Blockbench](https://github.com/Santi-PdR/modelos/blob/e9691b1ac525d5af4d8eabe00a85521d465f5ddf/docs/CAPA_v1.67.15.bbmodel) · [Visor de este ensayo](https://github.com/Santi-PdR/modelos/blob/e9691b1ac525d5af4d8eabe00a85521d465f5ddf/docs/capa_v1170_visor.html)

La parte alta de la capa queda cosida a la camiseta. El forro delantero y lateral conecta la montura con las hombreras de cuatro piezas; mirar arriba no empuja el anclaje hacia atrás. El pliegue superior y el fuelle acompañan al paño sin arrastrar el cuello. Se conservaron los ocho clips, los pivotes del paño, las piezas bajas, las texturas de albedo, emisión y halo, el icono y las brasas.

## Comprobado con este mismo JAR

- [Forge 1.20.1, ejecución 44799635475](https://github.com/Santi-PdR/modelos/actions/runs/44799635475): Steve y Alex, en pecho y Curios. Comparativas con y sin placas, incluyendo frente y cenital; miradas de −89° a +89°, giros de hasta ±73° y salto de 1,25 bloques. En 197 muestras, el desplazamiento máximo del anclaje respecto al torso o a la manga correspondiente fue de 0,000020 unidades de modelo.
- 904 cuadros de marcha en pecho y Curios, sin reinicios de fase ni vaivén medible del asiento. Pasaron también luz, oclusión, hotbar, élitros, planeo, nado y recarga de recursos.
- La comprobación geométrica de la mirada recta hacia arriba cubre reposo, caída y aterrizaje; se midieron por separado los solapes de la camiseta, el fuelle y las 12 raíces. El visor se abrió por HTTP y desde disco sin conexión, con el mismo proyecto exportado.

La prueba no certifica todas las combinaciones de giro extremo y agachado ni armaduras o cascos de otros mods. La simulación de zancada de amplitud máxima todavía registra cruces del paño con los brazos; la marcha y la carrera ensayadas en el cliente real pasaron.

**Entorno:** Minecraft Java 1.20.1, Forge 47.3.0, GeckoLib 4.8.1 y Curios opcional. Es un JAR de prueba separado; no se modificó el instalador ni se publicó una Release.
