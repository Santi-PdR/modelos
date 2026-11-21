# v1.67.31 · Tira de la nuca en la frenada agachada

**[Descargar JAR de prueba](https://github.com/Santi-PdR/modelos/raw/7adc4d285ac0e8468219aa062822518f6893352b/entregables/v1.67.31/capatest-1.67.31.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.30](../v1.67.30/notas.md).

La [prueba con la .30 original y las pasadas sin cada grupo](../v1.67.30/maniobra/diagnostico-nuca/README.md) separó la tira cosida (`v18_chain_*`) del borde de la capucha. La tira formaba la mayor parte de la raya al frenar. La .31 recoge esa tira y los cinco tramos del borde que aportaban a la marca. Es una traslación suave al levantar y girar la cabeza agachado en suelo seco: no oculta cubos ni cambia su escala. La montura, las placas, las raíces del paño, el GEO, las texturas y los clips conservan los datos de la .30.

## Prueba en Forge

[Antes/después de la nuca](maniobra/maniobra-nuca.jpg) · [Maniobra completa](maniobra/maniobra-forge.jpg) · [Mediciones de color](maniobra/maniobra-nuca.tsv) · [Malla en el giro y el retorno](maniobra/maniobra-nuca-malla.tsv) · [Control del techo del pelo](maniobra/maniobra-corona.tsv).

| Ranura y momento | Granate .30 → .31, de 5.184 muestras | Suma de secciones de malla sin → con ajuste, u² | Muestras de pelo recuperadas |
| --- | ---: | ---: | ---: |
| Pecho · paso sostenido | 1041 → 557 (46,5 % menos) | 2,71 → 0,00 | 488 |
| Pecho · frenada | 1826 → 175 (90,4 % menos) | 11,49 → 0,50 | 1662 |
| Curios · paso sostenido | 998 → 504 (49,5 % menos) | 2,70 → 0,00 | 448 |
| Curios · frenada | 1789 → 165 (90,8 % menos) | 10,94 → 0,45 | 1629 |

Se comparó el mismo interior de la cara posterior de la cabeza, registrado en cada toma real. Las muestras no son píxeles únicos. Las secciones por cubo miden intersecciones geométricas en la pose de la .31, con y sin el desplazamiento; no equivalen a superficie visible. La capa sigue cubriendo el borde inferior donde se une al cuello. Las fotos cubren la frenada en un sentido. No se certifica toda la vuelta de la cabeza ni el giro contrario con estas tomas.

La parte superior del pelo sigue limpia en el giro sostenido y la frenada. En el lateral medido durante la frenada hubo 630 → 308 muestras granate en pecho y 635 → 356 en Curios. La punta del paño conserva su frenada: **2,96 → 2,94 u/tick** en pecho y **2,97 → 2,96 u/tick** en Curios. [Costura, montura, zancada, mezcla de seis ticks y holgura de piernas](maniobra/maniobra-forge.tsv). También pasaron [marcha](continuidad-forge.tsv), [escalera](escalera-forge.tsv), [saltos](saltos-forge.tsv), [nado](nado-forge.tsv), [posturas](revision-alex-forge.tsv), élitros, halo, brasas y hotbar. [Build reproducible y pruebas Forge](https://github.com/Santi-PdR/modelos/actions/runs/44960804366) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/5a978956ab3444de525fdd277930f9d0a805417b).

## Instalación y respaldo

- Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1**; Curios **5.14.1** opcional.
- Cerrá Minecraft y pegá todo el [bloque de PowerShell](instalar-test-1.txt). Verifica **755.125 bytes** y el SHA-256 antes de retirar JAR anteriores de `capatest`. Se verificaron el script y los bytes descargables; no se ejecutó en tu Windows.
- Para volver a la .30, quitá primero `capatest-1.67.31.jar` de `test-1/mods` y usá el [PowerShell fijado de la .30](../v1.67.30/instalar-test-1.txt). No se cambiaron las descargas anteriores ni se creó una Release pública.
- [Blockbench](../../CAPA_v1.67.31.bbmodel) · [Visor offline](../../capa_v1170_visor.html). El ajuste se aplica al render equipado, no a las curvas editables.
