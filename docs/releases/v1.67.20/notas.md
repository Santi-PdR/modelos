# v1.67.20 · Forma original, sólo colocación

**[JAR directo de prueba](https://github.com/Santi-PdR/modelos/raw/bd92d1cdc27ec247dc8fa787a3cb6e01aaeead64/entregables/v1.67.20/capatest-1.67.20.jar)** · [SHA-256](JAR.sha256) · [Comparación en Alex](../../capa_v16720_forma_original_alex.jpg) · [Steve y Alex en Forge](../../capa_v16720_colocacion_forge.jpg) · [Blockbench v1.67.20](https://github.com/Santi-PdR/modelos/raw/bd92d1cdc27ec247dc8fa787a3cb6e01aaeead64/docs/CAPA_v1.67.20.bbmodel).

[Revisión adicional en Alex](revision.md): cámara F5, agachado, giros y carrera, con el mismo JAR.

El render de v1.67.19 comprimía el cuello y modificaba las dimensiones de las placas. Esta prueba conserva el modelo de v1.67.14: mismos cubos, atlas, UV, animaciones, icono, descripción y efectos. No se escala ni deforma el paño al equiparlo. Se traslada el manto entero 2,27 unidades hacia la espalda y 0,25 hacia abajo en el marco del torso. Se colocan intactas las hombreras sobre las mangas, y el apoyo interior original se traslada 0,32 unidades para acompañar las raíces de la tela. La variante separada para élitros no cambia.

**[Prueba en el cliente Forge 1.20.1](https://github.com/Santi-PdR/modelos/actions/runs/44847310583).** La comparación usa la misma cámara con Alex en Curios: perfil, tres cuartos y cenital. También se comprobaron Steve y Alex en pecho y Curios, la marcha, el salto y las alas. En las cuatro combinaciones, el paño visible llegaba al torso en 53 de 63 muestras sin contar la chaqueta. Los 87 cubos de colocación medidos conservaron sus dimensiones; ambas placas se vieron sobre el borde superior de su manga. Los 897 cuadros de marcha y transiciones no mostraron reinicios de fase.

La montura no persigue la cabeza: al mirar muy arriba el cuello puede cruzar la nuca. El barrido geométrico aún detecta cruces con los brazos al correr y con la cabeza al agacharse; no se ha intentado ocultarlos deformando el modelo.

Archivo de 741 774 bytes. Compilación reproducible comprobada en CI. El instalador público y las Releases no cambiaron.
