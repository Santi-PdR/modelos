# v1.67.42 — eco del dobladillo al aterrizar

**[Descargar JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/c5e30bcc6931fc94c884898147d4463e1b999ede/entregables/v1.67.42/capatest-1.67.42.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/45033840606) · [Proyecto Blockbench](../../CAPA_v1.67.42.bbmodel).

## Cambio

Tras un aterrizaje seco con suficiente caída, la parte inferior del paño da un cabeceo breve y el halo produce un eco de luz sólo sobre el dobladillo. La respuesta se limita a la submalla inferior: no cambia la geometría, el tinte ni la luz del resto de la capa. Pasos cortos, vuelo, agua y contactos no observados no deben inventar una respuesta de aterrizaje. El pulso se apaga en unos once ticks.

## Verificación

La [ejecución de CI](https://github.com/Santi-PdR/modelos/actions/runs/45033840606) terminó en éxito: validación de recursos, evaluación visual, pruebas de estados cosméticos, compilación Forge, comprobación de reproducibilidad y pruebas de Forge en mundo. El JAR de esta revisión se adjuntó al repositorio tras ambas pruebas.

En la toma Forge, el sistema midió 4.776 vértices del halo y localizó el eco exclusivamente en los 552 vértices del dobladillo. Para la caída de referencia (`lift = 0.84`), el cabeceo máximo muestreado fue 5,438° en el tick 3; el calor llegó a 0,9998 en el tick 4. En el caso menor (`lift = 0.36`), el cabeceo alcanzó 1,135° y el calor 0,209. La repetición del mismo tick conservó la luz UV2.

La prueba GPU confirmó el aumento esperado del interior del halo (RGB 163/68/166 → 203/83/204, alfa constante en 128), un cambio menor en el borde y ningún cambio en la muestra ocluida ni en la muestra mate. Los datos completos están en [muestreo de Forge](aterrizaje-halo-forge.tsv) y [muestras GPU](aterrizaje-eco-gpu.tsv). También se verificaron continuidad del halo, cadena, hombreras, movimiento, brasas y traspasos de equipo; los resultados tabulados permanecen en esta carpeta.

- JAR: 788.533 bytes.
- SHA-256: `4dadd92b47ee1026dbfdf56e63563c8dccbd98cb941d767b7d266930711e982a`.
- Artefacto construido desde el commit `bf5a7ba7fcbffc827ff083cc98640473ef35cc72`; el archivo y mediciones se adjuntaron en `c5e30bcc6931fc94c884898147d4463e1b999ede`.

## Probar en `test-1`

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y pegá el [bloque de PowerShell](instalar-test-1.txt). El script apunta únicamente a la carpeta configurada de `test-1`, valida tamaño y SHA-256 antes de retirar versiones anteriores y conserva intacto el JAR vigente si la descarga no coincide.

Probá un salto y una caída seca desde una altura suficiente, luego un paso corto, vuelo y agua como controles. Mirá el dobladillo y el halo en un lugar oscuro; el eco debe quedarse abajo y apagarse brevemente. Para volver a la prueba anterior, quitá `capatest-1.67.42.jar` y reinstalá la [.41](../v1.67.41/instalar-test-1.txt).

**Alcance:** build de prueba para `test-1`, no Release pública. No se ejecutó el script en tu Windows ni se modificó la versión pública v1.67.13. El test de Forge automatizado valida el runtime; falta tu confirmación visual en la instancia de juego.