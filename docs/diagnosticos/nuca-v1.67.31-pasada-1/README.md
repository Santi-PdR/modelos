# Primera pasada de la nuca · descartada

La captura en Forge se completó, pero el [control de dimensiones](maniobra.txt) encontró que la tira cosida cambiaba de forma (`pecho`, t52, `v18_chain_5`: diferencia de hasta 0,789 u en las distancias entre vértices). El [control de la nuca](nuca.txt) tampoco pudo recuperar la forma de la .30 al deshacer sólo la traslación. Se [reprodujeron las mediciones](https://github.com/Santi-PdR/modelos/actions/runs/44960681553) sobre los cuadros del primer cliente, con el SHA del JAR comprobado. Los recortes son diagnóstico, no un antes/después de la corrección.

La rama de escalado para élitros también se ejecutaba cuando la tira pedía guardar su matriz para trasladarse. La corrección restringe esa rama a las piezas que usan el ajuste de élitros. No se cambió el desplazamiento de la nuca ni los umbrales de las pruebas. No se entregó el JAR de esta pasada.
