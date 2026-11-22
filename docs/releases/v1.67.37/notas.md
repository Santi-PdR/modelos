# v1.67.37 · El paño al viajar sentado

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/f989619869e686a09362d17dfeb6d155cc7db0b0/entregables/v1.67.37/capatest-1.67.37.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.36](../v1.67.36/notas.md).

El vehículo sostiene al portador aunque sus pies no toquen el suelo. La .36 interpretaba esa falta de suelo como caída y le daba peso al clip `FALL`. Ahora el paño conserva el reposo al ir sentado y responde al **desplazamiento del vehículo**, sin activar la zancada. Al bajar, se vuelve al comportamiento normal con los fundidos existentes. No cambia el movimiento del jugador o del bote, el encastre del manto, el brillo, las brasas ni los ocho clips.

## Bote real en Forge

Alex con la capa en pecho y en Curios, en reposo, remando con W, frenando y bajando con Shift. En esas mismas muestras se calculó el control con la selección de la .36. Las fotos son de la .37; no se compararon píxeles entre dos JAR. La corrección no simula colisiones del paño con el casco ni se probó con todos los vehículos.

| Ranura | Cuadros | Peso de `FALL` sin remar · .36 → .37 | Avance al remar (bloques/tick) | Respuesta de la punta · reposo → remo → freno |
| --- | ---: | ---: | ---: | ---: |
| Pecho | 300 | 22,3 % → 0,0 % | 0,357 | -0,009° → -0,468° → -0,270° |
| Curios | 307 | 22,3 % → 0,0 % | 0,357 | -0,021° → -0,468° → -0,264° |

La última columna es el ángulo adicional del filtro del paño, no el ángulo total de la tela. La velocidad propia del personaje es casi cero durante el remo; el manto usa el desplazamiento que efectivamente vio el cliente. No hubo una zancada, nado ni caída sostenida mientras iba sentado. Las pruebas numéricas conservan el despliegue en una caída libre después de bajarse y el gesto de deterioro en reposo.

[Capturas de Forge](bote-forge.jpg) · [Resumen](bote-resumen.tsv) · [Pecho](bote-pecho.tsv) · [Curios](bote-curios.tsv) · [Ejecución](https://github.com/Santi-PdR/modelos/actions/runs/44984751355) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/75ef1752a041984af33085abe55281500b2b706c).

También pasaron [saltos](saltos-forge.tsv), [escalera](escalera-forge.tsv), [nado](nado-forge.tsv), [traspaso de equipo](traspaso-forge.tsv), [retorno de la capucha](maniobra/retorno/retorno.tsv) y [nacimiento de brasas con Shift](nacimiento-agachado-resumen.tsv). Los dos JAR producen las mismas muestras de origen, proyección y aspecto de las brasas.

## Instalación y vuelta atrás

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell para `test-1`](instalar-test-1.txt). Comprueba tamaño (774.226 bytes) y SHA-256 antes de retirar los JAR anteriores de `capatest`. No se ejecutó en tu Windows ni se modificó la descarga pública.

En F5, sentate en el bote, quedate quieto, remá unos segundos y soltá W. Para volver a la .36, quitá `capatest-1.67.37.jar` y usá el [PowerShell anterior](../v1.67.36/instalar-test-1.txt).
