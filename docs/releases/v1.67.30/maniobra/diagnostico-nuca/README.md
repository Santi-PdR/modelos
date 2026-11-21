# Qué cruza la nuca en v1.67.30

[Capturas reales: pieza completa, sin cadena y sin borde](ablacion.jpg) · [mediciones](ablacion.tsv).

La toma original sale del [run que compiló y verificó el JAR entregado](https://github.com/Santi-PdR/modelos/actions/runs/44956032272). Al extraerla se compararon byte a byte ese JAR y las dos trazas de la maniobra. Después se repitió la secuencia en el [cliente de diagnóstico de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44959131158): la compilación sin sondas reprodujo exactamente el JAR v1.67.30. Sólo en las pasadas de control se retiraron los cubos de un grupo, restaurándolos después del render. El mod distribuido no contiene esa opción.

- **Giro sostenido:** el borde trasero aporta a la punta lateral granate. Al retirarlo se recuperaron 268 muestras de pelo en pecho y 245 en Curios. Quitar la cadena sola no borra esa punta. La sección de la malla también sitúa `v17_cowl_front_0` en esa zona.
- **Frenada:** la mayor parte de la raya superior visible en la cara posterior sale de `v18_chain_0` a `_4`. Quitar el grupo `v18_chain_*` recuperó 567 muestras de pelo en pecho y 653 en Curios; quitar `v17_cowl_back_*` recuperó 233 y 267. Son controles separados: los valores no se suman, porque unas piezas tapan a otras. El borde posterior (`_0`, `_1`) y algunos tramos del borde delantero (`_0`, `_2`, `_3`) explican parte de la marca restante.

Se registró la perspectiva de cada cuadro con las cuatro esquinas del techo de la cabeza de Alex y se comparó un mismo interior de su cara posterior: 5.184 muestras por toma. No es una resta de dos imágenes sin alinear ni un conteo de píxeles únicos. La sección de malla está en unidades de modelo al cuadrado y no equivale al área visible: una pieza puede cortar esa cara detrás de otra. El paño por debajo y las placas no se atribuyen a la raya sólo por proyectarse sobre la cabeza.

Los [recortes originales](capturas.tsv) y [los del ensayo](control/) conservan el color real de Forge y las cajas de la misma pasada. `python3 tools/verify_forge_nape.py <carpeta-del-diagnóstico> <salida>` reproduce la comparación.
