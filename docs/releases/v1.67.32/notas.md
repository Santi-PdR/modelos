# v1.67.32 · Retorno de la capucha y continuidad del halo

La prueba más reciente es [v1.67.33](../v1.67.33/notas.md). Este JAR sigue disponible para volver atrás.

**[Descargar JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/35ec91a169424ff08b86108703ccaf7b2ef7f49b/entregables/v1.67.32/capatest-1.67.32.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.31](../v1.67.31/notas.md).

- Al frenar agachado, cada sentido del giro recoge el borde que lo necesita. Cerca del centro, la capucha se mantiene recogida aunque el borde alto ya se haya relajado. La tira acompaña ese movimiento y el ajuste se libera con la mezcla de Shift al volver a ponerse de pie.
- El halo y el tinte conservan el fundido por portador: otro renderer del mismo personaje no vuelve al brillo inicial ni retrocede el reloj. Se conservan el pase de núcleo de respaldo, las brasas y el pulso del icono.
- **Sin rediseño.** El JAR conserva byte por byte el GEO, los atlas, las texturas, los shaders, los sprites y las curvas de los ocho clips de la .31. El cambio de capucha es una traslación durante el render: no estira, oculta ni elimina cubos.

## Antes y después en Forge

[Retorno en pecho](maniobra/retorno/retorno-pecho.jpg) · [Retorno en Curios](maniobra/retorno/retorno-curios.jpg) · [Color por toma](maniobra/retorno/retorno.tsv) · [Malla y velocidad del ajuste](maniobra/retorno/retorno-malla.tsv).

| Alex · ranura y sentido | Frenada t77: granate .31 → .32 | Retorno t79–83: granate .31 → .32 | Pelo recuperado t79–83 | Sección media t80–91 (u²), .31 → .32 |
| --- | ---: | ---: | ---: | ---: |
| Pecho · + | 176 → 173 | 10.803 → 324 (−97,0 %) | 10.539 | 17,573 → 0,021 |
| Pecho · − | 1.306 → 164 | 15.536 → 100 (−99,4 %) | 15.434 | 16,916 → 0,000 |
| Curios · + | 173 → 193 | 14.834 → 217 (−98,5 %) | 14.719 | 16,560 → 0,044 |
| Curios · − | 1.284 → 145 | 15.780 → 96 (−99,4 %) | 15.692 | 17,272 → 0,000 |

El color se mide en la misma zona registrada de la nuca en capturas reales de cada versión. Son muestras, no píxeles únicos; se emparejan por tick y se registra la diferencia de ángulo. Las tomas del centro agachado son de la .32. La sección compara las dos traslaciones en **la misma pose** de Forge y no equivale a superficie visible: 42/48 de esas poses dan menos de 0,001 u² y el máximo es 0,262 u². El recorrido del ajuste no supera 1,838 u/tick y la unión medida de la tira no baja de 0,334 u. No es una garantía para todas las skins, poses, mods o shaders.

[Maniobra completa](maniobra/maniobra-forge.jpg) · [Techo del pelo](maniobra/maniobra-corona.tsv) · [Frenada y costuras](maniobra/maniobra-forge.tsv): picos de punta de **2,96 / 2,96 u/tick** en pecho / Curios. Pasaron [marcha](continuidad-forge.tsv), [saltos/aterrizajes](saltos-forge.tsv), [escalera](escalera-forge.tsv), [nado](nado-forge.tsv), [posturas](revision-alex-forge.tsv), élitros, luz/recarga, brasas y hotbar.

[Continuidad del halo en Forge](halo-continuidad-forge.tsv): dos instancias de la capa de luz y un mismo portador, cambiando el entorno de claro a oscuro. El borde pasa de **0,460** a **0,623**; el segundo renderer conserva ese valor y el tinte aun si llega con una fracción de tick anterior. Dos ticks después sigue hacia **1,019**. Otra entidad no hereda el fundido. Se comprobó aparte el fallback al núcleo cuando falta el halo.

## Instalar y volver atrás

- **Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá todo el [bloque de PowerShell](instalar-test-1.txt). Verifica **757.310 bytes** y el SHA-256 antes de retirar otros `capatest` anteriores de `test-1/mods`. Se verificaron el script y los bytes descargables, no se ejecutó en tu Windows.
- Para volver a la .31, quitá primero `capatest-1.67.32.jar` y usá el [instalador fijado de la .31](../v1.67.31/instalar-test-1.txt). No se creó una Release pública.
- [Build reproducible y pruebas Forge](https://github.com/Santi-PdR/modelos/actions/runs/44966024640) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/fcc2ec7bb83119189a980b0bd81fae5118f2ddac) · [Blockbench .32](https://raw.githubusercontent.com/Santi-PdR/modelos/35ec91a169424ff08b86108703ccaf7b2ef7f49b/docs/CAPA_v1.67.32.bbmodel) · [Visor offline](../../capa_v1170_visor.html).
