# v1.67.26 · Apoyo en la escalera y caída al soltarse

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/0fd30c035b93414591e807be775d030a5bc87ca1/entregables/v1.67.26/capatest-1.67.26.jar)** · [SHA-256](JAR.sha256) · [Comparación F5 en Forge](comparacion-escalera-forge.jpg) · [Ajuste en Steve y Alex](../../capa_v16726_colocacion_forge.jpg).

En v1.67.25, estar fuera del suelo bastaba para mezclar el clip de caída, incluso al subir, sostenerse o bajar por una escalera. Ahora el paño reconoce el apoyo mientras Minecraft reconoce el bloque escalable. Al retroceder y soltarse, vuelve a abrirse progresivamente según el descenso y se recoge al aterrizar.

El cambio sólo afecta a la pose del paño equipado, también cuando se usan las animaciones de reserva de GeckoLib. No altera la física del jugador, la posición de la montura, los ocho clips, las texturas, el icono, el halo ni las brasas. El proyecto Blockbench lleva el nombre de la nueva versión sin cambiar su contenido artístico.

## Antes y después en Forge

Alex en F5, en pecho y `back` de Curios. El recorrido usa teclas reales: subir, sujetarse con agachado, dejarse deslizar en la escalera y retroceder hasta caer al suelo. El jugador se coloca al principio, pero no se fuerza su pose ni su velocidad durante el recorrido. Son dos recorridos independientes por ranura, no una simulación de las imágenes.

| Medida | Pecho: v1.67.25 → v1.67.26 | Curios: v1.67.25 → v1.67.26 |
| --- | ---: | ---: |
| Subida · peso medio de caída | 22.0% → 0.0% | 22.0% → 0.0% |
| Pausa en la escalera · peso medio | 22.3% → 0.0% | 22.3% → 0.0% |
| Deslizamiento con apoyo · peso medio | 40.1% → 0.0% | 40.1% → 0.0% |
| Al soltarse · peso máximo | 100.0% → 95.5% | 100.0% → 94.4% |
| Bisagra superior al deslizarse · promedio (°) | 13.09 → 6.60 | 11.82 → 6.37 |

Los porcentajes indican el peso del clip de caída (`FALL`), no cuántos cuadros estaba abierto el paño. La apertura al soltarse y el asentamiento mantienen los límites de transición de v1.67.25. Sólo se ensayó el recorrido en una escalera vanilla; no es una comprobación de cada bloque escalable de otros mods.

[Medidas de escalera](escalera-forge.tsv) · Trazas: [pecho anterior](escalera-pecho-v16725.tsv), [pecho nuevo](escalera-pecho-v16726.tsv), [Curios anterior](escalera-curios-v16725.tsv) y [Curios nuevo](escalera-curios-v16726.tsv).

También se verificaron en el cliente los [saltos y aterrizajes](saltos-forge.tsv), [costuras](costuras-saltos-forge.tsv), [marcha de Steve y Alex](continuidad-forge.tsv), [posturas de Alex](revision-alex-forge.tsv), [entrada y salida del nado](nado-forge.tsv), élitros plegados y en vuelo, Curios, la hotbar y los efectos de luz.

## Compilación e instalación

[Referencia de v1.67.25](https://github.com/Santi-PdR/modelos/actions/runs/44918559887) (JAR idéntico al de la entrega anterior) · [Build y prueba de v1.67.26](https://github.com/Santi-PdR/modelos/actions/runs/44918607814) · [commit de las fuentes](compilacion.txt).

Para Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1** y Curios **5.14.1** opcional. Con Minecraft cerrado, reemplaza el JAR anterior de `capatest` en `test-1/mods`; no dejes ambas versiones juntas. No se ha cambiado la descarga pública ni el instalador.
