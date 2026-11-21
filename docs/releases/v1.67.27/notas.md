# v1.67.27 · Hombrera izquierda y animaciones de marcha

**[Descargar el JAR de prueba](https://github.com/Santi-PdR/modelos/raw/0b060c0219027453bb497e3a74b3c5286666edfa/entregables/v1.67.27/capatest-1.67.27.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.26](../v1.67.26/notas.md).

La **hombrera izquierda del personaje** (a la derecha de Alex al verlo de frente) queda un poco más cerca de la manga. Es la misma pieza: se gira sobre el hombro y se recoge su extremo exterior sin estrecharla ni mover la otra hombrera. El ajuste específico de élitros queda intacto.

**Al caminar**, el paño recibe dos rebotes suaves por zancada. La flexión llega más tarde al dobladillo y alterna de un lado al otro. **Al correr**, mantiene la caída hacia atrás y conserva el pulso de los pasos en el borde sin el vaivén amplio de antes. No se cambiaron el reloj de zancada ni la mezcla al arrancar, al cambiar de marcha o al frenar. Sigue habiendo ocho clips: sólo se rehicieron caminar y correr. El montaje y las raíces cosidas no adquieren pistas nuevas; no se cambiaron el icono, las texturas, los efectos ni la animación del ítem plegado.

## Antes y después en Forge

[Hombrera: frente y perfil](comparacion-hombrera-forge.jpg) · Marcha en F5: [pecho](comparacion-marcha-pecho-forge.gif) / [Curios](comparacion-marcha-curios-forge.gif) · [Montaje de Steve y Alex](../../capa_v16727_colocacion_forge.jpg).

| Alex | Saliente respecto de la manga (u) | Canto frontal x99 (px) | Alternancia al caminar (°) | Vaivén común al correr (°) |
| --- | ---: | ---: | ---: | ---: |
| Pecho | 2,08 → 1,54 | 549,0 → 543,0 | 1,77 → 3,48 | 2,07 → 0,38 |
| Curios | 2,08 → 1,53 | 549,0 → 543,0 | 1,77 → 3,48 | 2,08 → 0,38 |

Las cifras comparan v1.67.26 → v1.67.27. Una unidad de modelo (`u`) es 1/16 de bloque; `x99` es el percentil 99 horizontal de los píxeles de placa aislados con una toma sin placas. Los ángulos son amplitudes de dos tramos finales de tela medidas con la fase de zancada del jugador: alternancia es la diferencia entre lados una vez por zancada; vaivén común es el componente de esa misma frecuencia en el promedio de ambos tramos. El rebote de dos pulsos se distingue más al caminar y sigue presente al correr. Cada GIF une tomas F5 de dos recorridos reales por ranura; no hay cuadros interpolados ni es una comparación sincronizada pie por pie. Las capturas completas quedan en el artefacto `capatest-fx-en-mundo` del build.

En marcha estable no se detectaron reinicios de fase ni deriva del asiento a la precisión del registro. La rapidez del extremo (p95, en el marco del torso) cambió de 1,387 a 1,257 u/tick en pecho y de 1,380 a 1,335 en Curios. Los cambios de marcha y la frenada quedaron dentro de sus límites; no todos los picos bajaron.

[Apoyo en manga y tela](hombrera-forge.tsv) · [Prueba de mirada](hombrera-mirada-forge.tsv) · [Ritmo del dobladillo](ritmo-forge.tsv) · [Arranque, cambio de marcha y frenada](continuidad-forge.tsv) · Trazas: [pecho .26](paso-pecho-v16726.tsv), [pecho .27](paso-pecho-v16727.tsv), [Curios .26](paso-curios-v16726.tsv), [Curios .27](paso-curios-v16727.tsv).

También pasaron las pruebas en Forge de [escalera](escalera-forge.tsv), [salto, caída y aterrizaje](saltos-forge.tsv), [nado](nado-forge.tsv), [posturas de Alex](revision-alex-forge.tsv), élitros, halo, brasas y hotbar. Los cruces entre cajas de malla son un diagnóstico: no equivalen a píxeles visibles recortados y no cubren todas las skins ni todos los ángulos posibles.

## Archivos e instalación

- Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1**. Curios **5.14.1** es opcional para equipar en `back`.
- Cerrá Minecraft y reemplazá el `capatest` anterior en `test-1/mods`. El [bloque de PowerShell](instalar-test-1.txt) descarga a TEMP, verifica tamaño y SHA-256 antes de colocar el JAR, y sólo retira versiones anteriores de `capatest` después de verificar la instalada. JAR: **749,905 bytes**. No cambia el instalador público.
- [Proyecto Blockbench v1.67.27](../../respaldos/v1.67.27/CAPA_v1.67.27.bbmodel) y [visor offline](../../capa_v1170_visor.html). Blockbench guarda las curvas de base; el calce equipado sobre el jugador se ve en el visor o en Forge.
- [Respaldo exacto de las animaciones y el proyecto .26](../../respaldos/v1.67.26/README.md), guardado en Git en [`4814167`](https://github.com/Santi-PdR/modelos/commit/48141672ca1e35046aaf3290098321aaf8101450).

[Captura de referencia .26](https://github.com/Santi-PdR/modelos/actions/runs/44922651110), con JAR idéntico al entregado · [Build y pruebas de v1.67.27](https://github.com/Santi-PdR/modelos/actions/runs/44924671178) · [Fuentes verificadas](https://github.com/Santi-PdR/modelos/tree/185c952a81b2abc5d1cbae778108d0b141d3d870).
