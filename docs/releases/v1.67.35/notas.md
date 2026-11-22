# v1.67.35 · Fundido de los dos cambios de las brasas

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/8039d835ccd2b620c31f69a668b594628b64d44d/entregables/v1.67.35/capatest-1.67.35.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.34](../v1.67.34/notas.md).

La brasa conserva sus tres dibujos originales. En cada cambio se muestran cuadros intermedios a lo largo de cinco ticks, con el mismo tiempo interpolado que usa su movimiento. Se añadieron 22 texturas de 16×16, sin agregar partículas, pasadas de dibujo ni shaders. La cantidad, el vuelo y el fundido de opacidad, tamaño y tinte no cambian. Tampoco se modifican la geometría, las texturas del paño, el halo ni los ocho clips.

## Medición controlada

Composición en software de las texturas reales, comparando las tres claves de la .34 con la nueva secuencia. Se mantuvieron las curvas de apariencia y se aplicó el corte de alfa de la partícula vanilla. Se muestrearon 22 vidas, cuatro fases y tres alineaciones de cuadro por cambio. Salto máximo de un canal RGB entre cuadros, sobre escala de 255:

| FPS simulados | Cambio | .34 → .35 | Reducción |
| ---: | ---: | ---: | ---: |
| 30 | 1 | 68,16 → 24,77 | 63,7 % |
| 30 | 2 | 75,54 → 26,84 | 64,5 % |
| 60 | 1 | 67,61 → 22,53 | 66,7 % |
| 60 | 2 | 70,33 → 22,55 | 67,9 % |
| 144 | 1 | 67,06 → 22,53 | 66,4 % |
| 144 | 2 | 68,51 → 21,90 | 68,0 % |

El aporte RGB sumado sobre el fondo se mantuvo entre 0,977 y 1,062 veces el de un fundido teórico entre las dos claves. No es una captura de píxeles de Minecraft ni una medida de FPS del equipo. [Resultados](saltos-rgb-brasas.tsv).

## Validación en Forge

El proveedor real seleccionó los cuadros esperados del atlas en los dos cambios. En 10 muestras de la secuencia nueva y 10 de un `SpriteSet` de control con tres cuadros, cada dibujo emitió cuatro vértices con luz máxima. Dibujar otro instante del mismo tick y volver al primero no cambió su color ni sus coordenadas de textura. También pasó la prueba de vuelo libre y colisión con panel. [Traza de Forge](secuencia-brasa-forge.tsv).

Se repitieron las pruebas de [marcha](continuidad-forge.tsv), [saltos](saltos-forge.tsv), [escalera](escalera-forge.tsv), [nado](nado-forge.tsv), [traspaso de pecho a Curios y vuelta](traspaso-forge.tsv), [retorno de la maniobra](maniobra/retorno/retorno.tsv) y [pausa de render](pausa-render-forge.tsv). [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44977262007) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/9b2d54956b1ac3c11b19a4e8113337f526d298cc).

Si un paquete de recursos incluye su propia lista de tres sprites, conserva los cambios de tres cuadros. Para adaptar la secuencia completa a dibujos personalizados, hay que sustituir también los cuadros intermedios.

## Instalar o volver a v1.67.34

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). Verifica el tamaño (773.733 bytes) y SHA-256 antes de retirar los JAR anteriores de `capatest` en `test-1`. Se verificó el archivo remoto; no se ejecutó el instalador en tu Windows.

Para comparar, mirá las brasas en F5 con un fondo oscuro y observá el paso de destello a ceniza, con el mismo límite de FPS que en la .34. Para volver atrás, quitá `capatest-1.67.35.jar` y pegá el [PowerShell de la .34](../v1.67.34/instalar-test-1.txt). La descarga pública no cambia.
