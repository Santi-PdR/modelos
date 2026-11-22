# v1.67.39 · Vuelo de las brasas

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/266f6d1c02a2c630d188acaa0bb960c20d5e3c00/entregables/v1.67.39/capatest-1.67.39.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a la .38](../v1.67.38/notas.md).

Las brasas se inclinan con el movimiento lateral que realmente tuvieron. La inclinación entra suavemente y desaparece antes de apagarse. Si una brasa va directa hacia la cámara, sube recta o se frena en un panel, no queda inclinada por la dirección de salida.

Es sólo un giro del sprite: se mantiene un cuadrilátero con el mismo centro, tamaño y luz propia. La vida, el color, el fundido, el atlas de 25 cuadros, el respaldo de tres sprites, los nacimientos y las colisiones siguen como en la .38. El paño y las hombreras conservan exactamente el código de la versión anterior.

## Prueba en Forge

Se midieron los cuatro vértices enviados por el cliente en [27 dibujos](inclinacion-brasas-forge.tsv): vuelo libre, vuelo hacia un panel y ascenso vertical; tres vistas y tres fases. La inclinación invierte su signo al mirar desde el otro lado, sin cambiar la trayectoria ni lo que se dibuja al repetir la vista. También se verificó que el borde no salta al pasar de un tick al siguiente.

| Muestra | De perfil | Vista alineada con el avance | Perfil opuesto |
| --- | ---: | ---: | ---: |
| Vuelo libre, inicio | -25,21° | 0,00° | +25,21° |
| Vuelo libre, avance | -20,58° | 0,00° | +20,58° |
| Panel, tras frenarse | 0,00° | 0,00° | 0,00° |
| Vuelo libre, al apagarse | 0,00° | 0,00° | 0,00° |

[Atlas y color en Forge](secuencia-brasa-forge.tsv) · [Hombreras en carrera](hombreras-en-carrera.jpg) · [Medidas de hombros](hombreras-resumen.tsv) · [Pruebas de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44993202859) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/309868f1686de59686d34875a93516d10d79e73e). El [visor offline](../../capa_v1170_visor.html) ilustra el mismo perfil de inclinación; no simula paneles ni colisiones.

## Instalar en `test-1`

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y usá [el bloque de PowerShell](instalar-test-1.txt). Comprueba los 778.637 bytes y el SHA-256 antes de retirar los JAR anteriores. No se ejecutó en tu Windows ni se modificó la descarga pública.

Para ver el efecto, corré en F5 de perfil en una zona oscura. Para volver atrás, quitá `capatest-1.67.39.jar` y usá [el instalador de la .38](../v1.67.38/instalar-test-1.txt).
