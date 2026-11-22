# v1.67.40 · Halo al arrancar y frenar

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/78affa5083570571c23d8692a12a09a111b54757/entregables/v1.67.40/capatest-1.67.40.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a la .39](../v1.67.39/notas.md).

En la oscuridad, el halo se aviva brevemente con los cambios de velocidad. La luz junto a las grietas responde primero y el borde violeta tarda un poco más en alcanzar su máximo. El extra se desvanece al mantener el ritmo o al quedar quieto, se atenúa en penumbra y en el agua, y es nulo con luz plena. El halo base sigue respirando como antes.

Sólo cambia la intensidad del halo existente, no el color del núcleo ni la cantidad de pases. No cambian el modelo, el shader ni los atlas. El paño, las hombreras y las brasas se mueven igual que en la .39. Sin el shader de halo, la emisión estándar sigue funcionando como antes.

## Verlo y medirlo

En el [visor offline](../../capa_v1170_visor.html), abrí **Halo al arrancar y frenar · A/B** → **Simular arranque y frenada**. Alterná **Pulso de movimiento** en pausa para comparar con la .39 a la misma luz, pose y fase. El visor simula la velocidad, no el movimiento del jugador en el mundo.

[Forge](https://github.com/Santi-PdR/modelos/actions/runs/44995225824) reprodujo un cambio de 0 a 0,16 bloques por tick y una frenada con el manto equipado. La tabla muestra el aumento de intensidad enviado por la malla con respecto al halo base de la .39, a la misma exposición y fase. No es una medición del brillo de toda la pantalla.

| Tramo en cueva | Pico interior | Pico del borde |
| --- | ---: | ---: |
| Arranque | +0,313 a 200 ms | +0,303 a 450 ms |
| Frenada | +0,313 a 200 ms | +0,299 a 450 ms |

En la [prueba del shader en GPU](pulso-halo-gpu.tsv), el rojo subió 36/255 en un texel interior y 3/255 en uno del borde, con la misma opacidad y sin cambiar los texels mates ni los tapados. [Traza de la malla equipada](pulso-halo-forge.tsv) · [Pausa de render](pausa-render-forge.tsv) · [Traspaso real pecho–Curios](traspaso-forge.tsv) · [Hombreras](hombreras-resumen.tsv) · [Brasas](inclinacion-brasas-forge.tsv).

## Instalar en `test-1`

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). Verifica los 780.716 bytes y el SHA-256 antes de retirar los JAR anteriores. No se ejecutó en tu Windows ni cambia la descarga pública.

Probalo en F5, en una cueva, arrancando y frenando con la espalda a la vista. Para volver atrás, quitá `capatest-1.67.40.jar` y usá [el instalador de la .39](../v1.67.39/instalar-test-1.txt).
