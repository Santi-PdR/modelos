# v1.67.25 · El manto al saltar y aterrizar

**[JAR exacto de prueba](https://github.com/Santi-PdR/modelos/raw/0c3f8dc2b5c3337db6cfb152a99d168e02a7d855/entregables/v1.67.25/capatest-1.67.25.jar)** · [SHA-256](JAR.sha256) · [Comparación de saltos en Forge](comparacion-saltos-forge.jpg) · [Steve y Alex, pecho y Curios](../../capa_v16725_colocacion_forge.jpg).

En v1.67.24 el salto normal activaba el clip de planeo, aun sin élitros, y después pasaba al clip de caída completo. Con el ajuste el paño se levanta un poco al saltar, se abre más si aumenta la velocidad de descenso y se asienta sin perder de golpe la inercia al tocar suelo. El planeo con élitros conserva su clip.

La holgura que acompaña la zancada ya no depende de cuánto pesa el clip de caída. Esto corrige un segundo tirón que persistía al salir del borde en carrera: al abrirse del todo el paño, la bisagra volvía a seguir el balanceo instantáneo de las piernas. Se conservan la montura, las costuras y la separación del paño respecto de las piernas en las posturas ensayadas.

## Antes y después, en Forge

Alex en F5, con las mismas entradas de salto quieto, salto en carrera y caída desde un borde, en pecho y Curios. Son recorridos independientes. En los dos saltos con v1.67.24 el clip de planeo llegó al **100 %**; con v1.67.25 no intervino. Las medidas usan el espacio del torso (sin desplazamiento del avatar ni de la cámara).

| Medida | Pecho: v1.67.24 → v1.67.25 | Curios: v1.67.24 → v1.67.25 |
| --- | ---: | ---: |
| Salto desde parado · pico de la bisagra (°/tick) | 22.08 → 2.95 | 21.56 → 2.95 |
| Salto desde parado · apertura máxima de la bisagra (°) | 48.69 → 16.46 | 47.59 → 18.03 |
| Salto en carrera · pico de la bisagra (°/tick) | 40.87 → 0.00 | 40.36 → 0.00 |
| Salto en carrera · punta al aterrizar (u/tick) | 15.82 → 0.91 | 14.96 → 0.93 |
| Caída del borde · pico de la bisagra (°/tick) | 35.30 → 3.43 | 43.69 → 2.89 |
| Caída del borde · punta al aterrizar (u/tick) | 12.65 → 1.07 | 15.11 → 1.28 |

En los saltos en carrera, el límite de holgura ya existente (49.5°) sostuvo la bisagra superior durante la ventana medida. El paño no se congeló: la bisagra media y las puntas siguieron moviéndose.

`u` = 1/16 de bloque. Para la punta al aterrizar se mide el pico entre 1.5 ticks antes y 8 ticks después del primer cuadro en suelo. [Medidas completas](saltos-forge.tsv) · Trazas F5: [pecho anterior](saltos-pecho-v16724.tsv), [pecho nuevo](saltos-pecho-v16725.tsv), [Curios anterior](saltos-curios-v16724.tsv) y [Curios nuevo](saltos-curios-v16725.tsv).

En las **102 poses** de vuelo y suelo muestreadas, los solapes mínimos de costura, raíz y apoyo dorsal fueron **0.078 / 0.143 / 0.055 u**; la montura se mantuvo dentro de 0.000023 u de su posición relativa al torso. Los máximos de cruce medidos con cajas cerradas de brazos y piernas fueron 1.926 y 0.000 u. Las cajas incluyen zonas sin píxeles opacos; estas medidas no garantizan holgura para todas las poses. [Costuras y contacto](costuras-saltos-forge.tsv).

También pasaron la marcha y los cambios de ritmo de Steve y Alex, el nado (0 % de clip al vadear, 100 % al nadar en horizontal y 0 % de nuevo al erguirse, en ambas ranuras), los élitros plegados y en planeo, el equipo, la hotbar, la luz y las brasas. El modelo, los ocho clips, las texturas y el icono mantienen los mismos bytes. El cambio se aplica al llevar el manto; no se hornea en Blockbench. [Nado](nado-forge.tsv) · [Marcha](continuidad-forge.tsv) · [Posturas de Alex](revision-alex-forge.tsv) · [Control de holgura de brazos](holgura-brazos-forge.tsv).

## Compilación e instalación

[Referencia de v1.67.24 en Forge](https://github.com/Santi-PdR/modelos/actions/runs/44914820262) (JAR idéntico al ya entregado) · [Build y prueba de v1.67.25](https://github.com/Santi-PdR/modelos/actions/runs/44916624374) · [commit de fuentes](compilacion.txt).

Para Minecraft Java **1.20.1**, Forge **47.3.0**, GeckoLib **4.8.1** y Curios **5.14.1** opcional. Con Minecraft cerrado, sustituye el JAR anterior de `capatest` en `test-1/mods`; no dejes ambas versiones juntas. Esta prueba no modifica el instalador ni la versión pública.
