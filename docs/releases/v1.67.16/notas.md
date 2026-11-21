# v1.67.16 · Capa original, ajuste al equiparla

Esta prueba todavía ajusta el manto con la mirada. La prueba vigente es [v1.67.20](../v1.67.20/notas.md).

[Descargar JAR de prueba](https://github.com/Santi-PdR/modelos/raw/082c38eacc81906e9698d89196a7e797735663d0/entregables/v1.67.16/capatest-1.67.16.jar) · [SHA-256](JAR.sha256) · [Capturas F5](../../capa_v16716_colocacion_forge.jpg) · [PowerShell para `test-1`](instalar-directo-test-1.txt) · [Blockbench](https://github.com/Santi-PdR/modelos/blob/abcbb0158ddeaf00eb6758ea55836ad6b3e019a8/docs/CAPA_v1.67.16.bbmodel) · [Visor offline](https://github.com/Santi-PdR/modelos/blob/abcbb0158ddeaf00eb6758ea55836ad6b3e019a8/docs/capa_v1170_visor.html)

Se descarta el rediseño de v1.67.15. La referencia es v1.67.14: sus 18 recursos de arte (geometría, texturas, animaciones, partículas y shaders) coinciden byte por byte con los del JAR nuevo. El proyecto de Blockbench sólo cambia de nombre de versión.

El ajuste se aplica al render equipado: la capa baja y se inclina al levantar mucho la mirada, en vez de apartarse tanto de la espalda. El pie de la unión se queda en el torso y las hombreras originales se trasladan enteras, un poco más arriba en reposo. No se retocan las piezas ni los clips.

## Comprobaciones

- **Forge en F5:** 296 muestras entre Steve y Alex, pecho y Curios, con barridos de mirada, giros y salto. En las cuatro combinaciones se ven ambas hombreras en las tomas de espalda, frente y cenital. Al mirar hacia arriba, el asiento se mantuvo en el mismo punto del torso (desplazamiento máximo medido de aproximadamente 0,000007 unidades de modelo).
- **Marcha y otros estados:** 900 cuadros de marcha y transiciones en las dos ranuras, sin reinicios de fase ni vaivén medible del asiento en paso estable. También pasaron la hotbar, recarga, emisión, oclusión, élitros, planeo y nado.
- **Perfil y empaquetado:** pasaron la paridad Java/Python/visor, el barrido geométrico de 1.680 poses y la reconstrucción reproducible del JAR. El paquete contiene el arte original y no incluye las sondas del ensayo. El visor se comprobó por HTTP y desde un archivo local.

[Compilación y capturas originales](https://github.com/Santi-PdR/modelos/actions/runs/44808610373) · [Revalidación y copia del JAR exacto](https://github.com/Santi-PdR/modelos/actions/runs/44810308117). En la primera ejecución los controles de marcha pasaron, pero su paso pidió al final una captura de referencia v1.67.10 que no pertenece a esta escena. La revalidación comprobó la marcha, las placas y la hotbar con las trazas y tomas de esa misma ejecución, sin cambiar el código del mod.

La comprobación cubre esas poses y modelos de jugador; no certifica todos los cascos, skins, shaders ni otros mods. **Entorno:** Minecraft Java 1.20.1, Forge 47.3.0, GeckoLib 4.8.1; Curios 5.14.1 opcional. Es una prueba separada: no se cambió el instalador público ni se publicó una Release.
