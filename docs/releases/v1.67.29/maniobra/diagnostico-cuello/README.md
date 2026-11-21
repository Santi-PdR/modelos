# De dónde salía la mancha sobre el pelo en v1.67.29

En la misma maniobra de Alex en Forge se ve un fragmento granate aislado sobre la cara superior del pelo. Los recortes son de las capturas originales del JAR entregado, en [pecho](pecho-63-detalle.png) y [Curios](curios-63-detalle.png) durante el paso agachado, y al [frenar en pecho](pecho-77-detalle.png) y [en Curios](curios-77-detalle.png).

La intersección de las cajas con la cara superior de la **cabeza base** (no la caja inflada de la segunda capa) identifica `v17_cowl_back_0`, `_1` y `_2`; el tramo `_1` es el que más corta esa cara. Los mayores solapes volumétricos de [cruces.tsv](cruces.tsv) señalan otras piezas, incluidos el forro y el frente del cuello, pero no atribuyen por sí solos esa mancha. La frente, la nuca y los costados no son la misma prueba.

[Forge original de la .29](https://github.com/Santi-PdR/modelos/actions/runs/44953657027) · [Revisión de sus cuadros y del mismo JAR byte por byte](https://github.com/Santi-PdR/modelos/actions/runs/44955071025). `pecho-cubos.tsv` y `curios-cubos.tsv` guardan las cajas del cuello, la cabeza y las piezas vecinas en muestras de esa prueba, en coordenadas del torso.
