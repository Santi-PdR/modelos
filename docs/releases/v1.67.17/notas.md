# v1.67.17 · Montaje fijo en F5 y hombreras de frente

**Prueba descartada:** el cuello quedó bajo y retrasado y las placas se veían separadas del manto. Para `test-1`, usá la [v1.67.19 corregida](../v1.67.19/notas.md).

[Descargar JAR de prueba](https://github.com/Santi-PdR/modelos/raw/287c3c960c8c18f59ed6935a3cba843cb5ea0909/entregables/v1.67.17/capatest-1.67.17.jar) · [SHA-256](JAR.sha256) · [Capturas en Forge](../../capa_v16717_colocacion_forge.jpg) · [PowerShell para `test-1`](instalar-directo-test-1.txt) · [Blockbench](https://github.com/Santi-PdR/modelos/blob/2cb51791c4083944d0ec774e8d0540ff02ee2d07/docs/CAPA_v1.67.17.bbmodel).

Esta versión reemplaza el ajuste de prueba v1.67.16. La cabeza y la cámara ya no controlan el retroceso, la altura, el cuello ni los costados del manto. La montura sigue al torso; la tela conserva su movimiento al caminar, saltar, nadar y usar élitros. Las dos placas originales se colocan completas sobre los hombros y la compacta se centra también sobre la manga fina. No se reemplaza el modelo, el atlas ni sus ocho clips.

## Verificación

- **Órbita y mirada por separado:** 6 vistas con la cabeza quieta y 49 poses de cabeza con una cámara quieta, en cada combinación de manga normal/fina y pecho/Curios. La diferencia máxima de las piezas rígidas y el anclaje de la tela, medida en el marco del torso, fue de 0,000017 unidades del modelo. El salto también se comprobó en las cuatro combinaciones.
- **Frente:** se compararon capturas con las dos placas visibles y ocultas, y sus píxeles con la proyección de cada manga vanilla. La placa compacta y la ancha cubren el 48% y el 62% del ancho de sus mangas en Steve y el 51% y el 51% en Alex, tanto en pecho como en Curios.
- **Movimiento:** 917 fotogramas de marcha y transiciones, sin reinicios de fase. Pasaron los controles de equipo, hotbar, recarga, halo, oclusión, carrera, élitros, planeo y nado.
- **Arte y empaquetado:** los 18 recursos de arte de v1.67.14 coinciden byte por byte. El Blockbench solo cambia de nombre de versión. Pasaron 504 poses del visor, 128 fases de costura y 7.440 poses con alas. El JAR es reproducible y no lleva las sondas de Forge. El visor se comprobó desde archivo local y por HTTP.

[Compilación y prueba en Forge](https://github.com/Santi-PdR/modelos/actions/runs/44821893803) · [Copia del JAR y las tomas de ese run](https://github.com/Santi-PdR/modelos/actions/runs/44822850733). **Entorno:** Minecraft Java 1.20.1, Forge 47.3.0, GeckoLib 4.8.1, Curios 5.14.1 opcional.

Las vistas pueden ocultar piezas por perspectiva o por la cabeza. En ángulos extremos, la comprobación de volumen sigue encontrando posibles cruces con la cabeza; no se vuelve a mover el manto para corregirlos. No se certifica compatibilidad visual con todos los cascos, shaders o modelos de terceros.

Descarga directa de 744 306 bytes. El bloque de PowerShell verifica el archivo antes de sustituir la copia de `test-1` y guarda el JAR anterior fuera de `mods`. Esta prueba no publica una Release ni cambia el instalador público.
