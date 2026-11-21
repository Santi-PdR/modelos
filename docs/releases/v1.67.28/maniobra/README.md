# Carrera, giro y paso agachado · diagnóstico de v1.67.28

**La transición combinada todavía tiene un tirón.** En Forge, con Alex en suelo plano, el salto de la punta se repitió en pecho y en `Curios:back`. No se cambió el JAR entregado ni la descarga pública.

[Ver las cinco posturas de cada ranura](maniobra-forge.jpg) · [Medidas](maniobra-forge.tsv) · Trazas: [pecho](maniobra-pecho.tsv), [Curios](maniobra-curios.tsv).

| Ranura | Cuadros / poses medidas | Velocidad habitual de la punta (p90) | Pico de la punta | Cierre de la bisagra superior en el intervalo del pico |
| --- | ---: | ---: | ---: | ---: |
| Pecho | 238 / 84 | 0,63 u/tick | **8,19 u/tick** | 7,92° en 0,42 ticks |
| Curios | 313 / 86 | 0,85 u/tick | **11,64 u/tick** | 21,94° en 0,78 ticks |

Los picos quedaron sobre el umbral de diagnóstico de **6 u/tick**. Ocurrieron al entrar en paso agachado, con las teclas de carrera y `Shift` encadenadas y antes de soltar `W`. La bisagra superior se cerró con brusquedad mientras los pesos de los clips seguían mezclándose. La montura no saltó: su deriva máxima respecto al torso fue de **0,000016 u** en ambas ranuras, se mantuvo la costura y no se detectó cruce del paño con las piernas en las 170 poses de malla. En la lámina, aún se ve una parte granate del manto sobre la cabeza al mantener el giro agachado; la prueba no da por resuelto ese cruce visual.

`u` equivale a 1/16 de bloque. Las velocidades se miden respecto al torso, sin movimiento de cámara. Son dos recorridos independientes, no una medición de que Curios produzca siempre un pico mayor. Las intersecciones de cajas en el TSV son aproximaciones, no conteos de píxeles visibles.

## Cómo se probó y qué queda por ajustar

La sonda maneja `W`, `Sprint` y `Shift` en un mundo real del cliente Forge y programa la mirada relativa al torso (hasta 55° de giro y 35° hacia arriba). Prueba carrera → giro con `Shift` y `W` sostenida → frenada con `Shift` → vuelta a reposo en pie. No impone la pose de las piernas ni mueve la montura para lograr el resultado. Los primeros cuadros de carga no forman parte de la medición en suelo seco.

El siguiente retoque es amortiguar **el cierre de la bisagra superior al pasar de carrera a paso agachado**, sin acortar la zancada ni quitar holgura cuando las piernas la necesitan. Esta maniobra queda en CI como prueba optativa con `[probar-maniobra]`; su modo estricto sigue fallando si el pico excede el umbral.

[Capturas y malla originales](https://github.com/Santi-PdR/modelos/actions/runs/44949607859) · [Revisión de ambas ranuras](https://github.com/Santi-PdR/modelos/actions/runs/44950481289) · [Versión e instalación](../notas.md). Antes de las tomas se reconstruyó el JAR y se confirmó que era idéntico byte por byte al entregado. La sonda se ejecuta desde fuentes en Forge y no se incluye en el JAR de `test-1`.
