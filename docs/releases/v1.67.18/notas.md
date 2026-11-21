# v1.67.18 · Cuello y hombreras asentados

**Prueba descartada:** las capturas en `test-1` mostraron que todavía sobresalían el borde del cuello y la salida de la tela. La prueba vigente es [v1.67.19](../v1.67.19/notas.md). Los resultados que siguen son históricos.

[JAR de prueba](https://github.com/Santi-PdR/modelos/raw/945bc2d7d7f65765f766a7b59f9746fecc9b07fa/entregables/v1.67.18/capatest-1.67.18.jar) · [SHA-256](JAR.sha256) · [Capturas de Forge](../../capa_v16718_colocacion_forge.jpg) · [Blockbench](https://github.com/Santi-PdR/modelos/raw/5200616227cd6baa57869567833b3d8f015fbd06/docs/CAPA_v1.67.18.bbmodel).

En [v1.67.17](../../capa_v16717_colocacion_forge.jpg), el cuello había quedado bajo y retrasado, separado de las hombreras. El ajuste nuevo recupera el apoyo en la espalda alta. Los retornos llegan a las dos placas originales y las placas se asientan sobre las mangas. El encastre sigue al torso, no a la cabeza ni a la cámara. Con élitros se conserva el ajuste corto para las alas. No se editan cubos, UV, texturas, clips, brillo ni icono.

## Verificación

- **Encastre:** comprobado con los cubos dibujados y las mangas vanilla de Steve y Alex, en ambas formas de equipar. El solape mínimo en la espalda alta fue 0,690 unidades del modelo; entre retorno y placa, 0,543. No alcanza con que las piezas se superpongan en pantalla. El mismo control geométrico aplicado a los ajustes de v1.67.17 los rechaza.
- **Silueta en Forge:** espalda, frente, tres cuartos, perfil y cenital. De frente, la placa compacta y la ancha cubren el 65% y el 71% del ancho de sus mangas en Steve; el 71% y el 73% en Alex. La medida compara la misma toma con y sin las placas.
- **Órbita, mirada y salto:** siete cámaras independientes con cabeza quieta y 49 poses de mirada con cámara quieta por combinación. La montura rígida se mantiene en las coordenadas del torso (máximo 0,000019 unidades de diferencia), también en el salto de 1,25 bloques. No es una garantía de que no haya oclusiones con poses extremas, cascos o modelos de terceros.
- **Movimiento y efectos:** 911 fotogramas de marcha y transiciones de pecho/Curios, sin reinicios de fase. Pasaron hotbar, recarga, luz, oclusión, paso lateral, élitros, planeo y nado. El visor offline también conserva el encastre al cambiar la mirada en un fotograma pausado.
- **Arte y JAR:** 18 recursos de arte idénticos al JAR v1.67.14. El proyecto Blockbench sólo cambia de nombre de versión. El archivo distribuido es reproducible y no lleva las sondas de prueba.

[Compilación y Forge](https://github.com/Santi-PdR/modelos/actions/runs/44833876875) · [Copia exacta de los artefactos](https://github.com/Santi-PdR/modelos/actions/runs/44834837336). Código probado: `fa6be8f`. Entorno: Minecraft Java 1.20.1, Forge 47.3.0, GeckoLib 4.8.1, Curios 5.14.1 opcional.

El JAR histórico pesa 742 539 bytes. Las instrucciones viejas para `test-1` se retiraron. No se cambió el instalador público.
