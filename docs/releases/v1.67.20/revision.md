# v1.67.20 · Revisión adicional en Alex

**[Capturas de Forge](revision-alex-forge.jpg)** · [Medidas por ranura](revision-alex-forge.tsv) · [Ejecución del cliente](https://github.com/Santi-PdR/modelos/actions/runs/44849476869).

Se revisaron **152 cuadros** de Alex (piel y mangas finas vanilla) en pecho y Curios, con Forge 47.3.0, GeckoLib 4.8.1 y Curios 5.14.1, en un mundo de prueba desechable. Espalda y cenital usan la cámara real de F5; perfil y carrera usan una órbita separada de la orientación de la cabeza para que se vea la unión. Agacharse y correr se accionaron con los controles del juego; no se sustituyeron sus posturas ni la animación de la capa.

Se verificaron los 201 cubos del modelo equipado por cuadro, sin cambios de dimensiones. Las piezas rígidas no se desplazaron respecto del torso al cambiar de postura (deriva máxima 0.000033u). El JAR vuelto a compilar coincide byte por byte con [el entregado](JAR.sha256). La prueba de render se ejecutó con sondas del cliente de desarrollo; no instala nada en `test-1`.

## Resultado visual

- **El manto se mantiene apoyado.** Se conservó el solape del paño con la espalda y el de todas las raíces con la montura en los cuadros muestreados, incluso en carrera. No se midieron cruces del paño con las piernas.
- **Cenital F5:** se ve un borde oscuro que invade la nuca. La sonda midió un cruce de la placa con la cabeza de 0.161u de pie y 0.222u al agacharse. Al reproducir los mismos ángulos y matrices fuera del cliente, la placa compacta coincide con ambos valores; la ancha queda fuera en esas dos tomas.
- **Mirar arriba, girar o agacharse:** el cuello aún invade la cabeza en algunas posturas. El resultado más acusado fue al mirar 64° arriba (3.582u en la caja de la cabeza). **Al correr**, se ve que una tira del paño cruza el brazo; el máximo medido fue 2.353u sin contar la manga exterior. El apoyo en reposo no implica que estos recortes estén resueltos.

## Contacto y cruces medidos

| Escena | Cuadros | Paño/torso mín. | Unión de raíz mín. | Cuello/cabeza | Paño/brazos |
| --- | ---: | ---: | ---: | ---: | ---: |
| Espalda F5 | 16 | +0.681u | +0.253u | 16 (0.514u) | 16 (0.786u) |
| Cenital F5 (79° abajo) | 16 | +0.676u | +0.249u | 0 | 16 (0.819u) |
| Mirada alta (64° arriba) | 16 | +0.665u | +0.251u | 16 (3.582u) | 16 (0.820u) |
| Giro (55°, mirando 35° arriba) | 16 | +0.665u | +0.268u | 16 (1.949u) | 16 (0.818u) |
| Agachado | 24 | +0.549u | +0.313u | 24 (1.571u) | 0 |
| Agachado cenital F5 | 16 | +0.565u | +0.313u | 0 | 0 |
| Carrera | 48 | +0.054u | +0.173u | 48 (0.530u) | 47 (2.353u) |

`u` son píxeles de modelo (16 por bloque). Un valor positivo de unión o contacto indica solape; un valor negativo indica separación en la comparación de las cajas orientadas. Las dos últimas columnas cuentan los cuadros con un cruce de más de 0.05u y dan su profundidad máxima. Son mediciones de la malla contra las cajas de las partes **sin** la segunda capa de piel, no un recuento de píxeles visibles. El TSV también incluye la segunda capa, las placas y las piernas. En carrera, la lámina muestra el mayor solape con un brazo entre las cinco capturas guardadas por ranura.
