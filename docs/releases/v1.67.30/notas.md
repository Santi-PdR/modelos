# v1.67.30 · Borde de la capucha en el giro agachado

**[Descargar JAR de prueba](https://github.com/Santi-PdR/modelos/raw/22026f27db7c2e588804495ea16d96c98af2204d/entregables/v1.67.30/capatest-1.67.30.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.29](../v1.67.29/notas.md).

El borde posterior de la capucha se repliega al levantar y girar la cabeza en paso agachado sobre suelo seco. La causa se aisló a los tramos `v17_cowl_back_0` a `_2`, que en la .29 salían a través de la cara superior de la cabeza de Alex. El ajuste conserva la escotadura y las piezas altas; no oculta cubos, no cambia su escala ni afecta al borde delantero, las placas, la montura o la frenada. El GEO, las animaciones, las texturas y los efectos son idénticos a la .29.

## Pruebas en Forge

[Detalle antes/después](maniobra/maniobra-corona.jpg) · [Vista completa de la maniobra](maniobra/maniobra-forge.jpg) · [Medición de corona y píxeles](maniobra/maniobra-corona.tsv) · [Diagnóstico .29](../v1.67.29/maniobra/diagnostico-cuello/README.md).

| Ranura y momento | Altura de la corona sobre el tope del pelo (.29 → .30), u | Suma de cortes en esa cara, u² | Píxeles granate / muestra interior .30 |
| --- | ---: | ---: | ---: |
| Pecho · paso | 1,19 → -0,50 | 6,05 → 0,00 | 0 / 5828 |
| Pecho · freno | 0,95 → -0,48 | 3,09 → 0,00 | 0 / 3324 |
| Curios · paso | 1,14 → -0,58 | 6,03 → 0,00 | 0 / 5921 |
| Curios · freno | 0,96 → -0,44 | 3,16 → 0,00 | 0 / 3325 |

En ambas ranuras se midió la cara superior real del modelo vanilla, y su proyección en el framebuffer. `u` = 1/16 de bloque. La suma de cortes mide intersecciones por cubo, no el área visible de la mancha. Estas tomas no prueban que desaparezcan todos los cruces en la nuca, los costados o con otras pieles.

La punta del paño sigue frenando sin el tirón: **2,95 → 2,96 u/tick** en pecho y **2,97 → 2,97 u/tick** en Curios, debajo del límite original de 6. [Costuras, montura y trazas](maniobra/maniobra-forge.tsv). También pasaron [marcha](continuidad-forge.tsv), [escalera](escalera-forge.tsv), [salto](saltos-forge.tsv), [nado](nado-forge.tsv), [posturas](revision-alex-forge.tsv), élitros, halo, brasas y hotbar. [Build reproducible y prueba Forge](https://github.com/Santi-PdR/modelos/actions/runs/44956032272) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/87f0e3ff4861a63348cc3ac57ab633ca60a4dec4).

## Instalación y respaldo

- Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1**; Curios **5.14.1** opcional.
- Cerrá Minecraft y pegá todo el [bloque de PowerShell](instalar-test-1.txt). Verifica **751.904 bytes** y el SHA-256 antes de retirar JAR anteriores de `capatest`. Verificado estáticamente; no se ejecutó en tu Windows.
- Si querés volver a la .29, quitá primero `capatest-1.67.30.jar` de `test-1/mods`, y luego usá el [instalador fijado de esa versión](../v1.67.29/instalar-test-1.txt). No se cambió ese JAR, su instalador ni las publicaciones.
- [Blockbench](../../CAPA_v1.67.30.bbmodel) · [Visor offline](../../capa_v1170_visor.html). Las curvas editables no cambian; el repliegue es un ajuste de render equipado.
