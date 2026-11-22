# v1.67.41 · Balanceo de la cadena equipada

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/c4837d26be7d9589360a650b9dc86f3ceb0f7b32/entregables/v1.67.41/capatest-1.67.41.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a la .40](../v1.67.40/notas.md).

El centro de la cadena baja con las pisadas y sale ligeramente hacia afuera con un pequeño retardo. Al frenar, conserva un poco de movimiento y vuelve a su posición. Los dos extremos siguen sujetos al cuello. No se estiran los eslabones y no cambia la cadena del objeto plegado.

Se conservan el halo de la .40, el vuelo de las brasas, las hombreras articuladas y las animaciones del paño. El efecto usa la misma pose para el sólido y el brillo; no añade partículas ni pases de dibujo.

## Ver la diferencia

En el [visor offline](../../capa_v1170_visor.html), abrí **Balanceo de la cadena · A/B** → **Ver la cadena al frenar**. En pausa, alterná **Balanceo de los eslabones**: la cámara, el tiempo y la luz se mantienen. La trayectoria del maniquí es una simulación.

## Mediciones en Forge

En la [ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44997987596) se compararon **597 poses de malla** de Alex con los eslabones de la .40 reconstruidos en el mismo fotograma. Pecho y Curios, carrera, salto y giro en ambos sentidos. El centro se desplazó hasta **0,436 u** (16 u = un bloque); se conservaron los siete enlaces (solape mínimo 0,0084 u) y el apoyo en ambos lados (mínimo 0,179 u). No se midió ningún cruce adicional con el cuerpo ni las placas.

| Ruta | Caída durante el ciclo de paso (u) | Salida en carrera (u) | Arrastre al frenar con paso bajo (u) |
| --- | ---: | ---: | ---: |
| paso-pecho | 0,201 | 0,346 | 0,110 |
| paso-curios | 0,201 | 0,346 | 0,106 |
| paso-steve-pecho | 0,202 | 0,345 | 0,109 |
| paso-steve-curios | 0,202 | 0,344 | 0,110 |

El desplazamiento del centro volvió a cero en reposo. [Malla y apoyos](cadena-geometria-forge.tsv) · [Giros y asentamiento](cadena-maniobra-forge.tsv) · [Zancada](cadena-zancada-forge.tsv) · [Hombreras](hombreras-resumen.tsv) · [Halo](pulso-halo-forge.tsv) · [Brasas](inclinacion-brasas-forge.tsv).

## Probar en `test-1`

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). Verifica los 783.663 bytes y el SHA-256 antes de retirar los JAR anteriores. No se ejecutó en tu Windows ni se cambió la descarga pública.

En F5 con la espalda a la vista, caminá, corré y frená mirando el centro de la cadena. Para volver atrás, quitá `capatest-1.67.41.jar` y usá [el instalador de la .40](../v1.67.40/instalar-test-1.txt).
