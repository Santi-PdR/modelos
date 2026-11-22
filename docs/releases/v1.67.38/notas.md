# v1.67.38 · Hombreras, giro del paño y brasas

**[JAR de prueba](https://raw.githubusercontent.com/Santi-PdR/modelos/7e1e20752281197140e9f1cfc290b084ee572691/entregables/v1.67.38/capatest-1.67.38.jar)** · [PowerShell para `test-1`](instalar-test-1.txt) · [SHA-256](JAR.sha256) · [Volver a v1.67.37](../v1.67.37/notas.md).

- **Hombreras:** una bisagra corta sobre cada manga eleva el canto al balancear el brazo. No cambia la forma de la placa ni su colocación en reposo. El sólido y la emisión usan el mismo encastre; cuello y montura siguen sujetos al torso. Se conserva el ajuste anterior con élitros y en el asiento.
- **Paño:** los jirones sueltos terminan de acompañar el giro después del torso. El retardo crece hacia las puntas y se amortigua en el agua. Las raíces cosidas y los ocho clips existentes quedan intactos.
- **Brasas:** al encenderse tiran a rosa cálido y pasan gradualmente a violeta. Se conservan la opacidad, los sprites, el tamaño, el vuelo, la frecuencia de emisión y el halo del manto.

## Pruebas de Forge

Alex en pecho y Curios: 24 cuadros de carrera por ranura, con el encastre fijo de la .37 proyectado sobre **la misma manga y postura** como control. No son dos capturas comparadas píxel a píxel. La profundidad, en píxeles de modelo (1/16 de bloque), se mide en las caras de la placa y el bisel. El borde conserva el contacto con la tela, sin cambiar las dimensiones de sus cubos ni añadir cruces apreciables con la cabeza en la muestra. No se supone que estas poses cubran todos los mods de animación o de piel.

| Ranura | Lado del jugador | Hundimiento medio, .37 → .38 (u) | Contacto mínimo de costura (u) |
| --- | --- | ---: | ---: |
| Pecho | Derecha | 0,086 → 0,072 | 1,090 |
| Pecho | Izquierda | 0,137 → 0,073 | 0,350 |
| Curios | Derecha | 0,086 → 0,073 | 1,090 |
| Curios | Izquierda | 0,138 → 0,075 | 0,351 |

[Capturas de carrera](hombreras-en-carrera.jpg) · [Medidas por cuadro](hombreras-movimiento.tsv) · [Resumen](hombreras-resumen.tsv).

En la [maniobra de giro y frenada agachada](maniobra/maniobra-forge.tsv) también se comprobaron las costuras y la holgura de las dos placas con la cabeza y el pelo. El recorrido de cada placa se abre hacia afuera en vez de levantar el borde interior hacia la cara.

[El giro](remate-giro-forge.tsv), medido con Steve y Alex en ambas ranuras, activó 0,442–0,445° de corrección de punta antes del límite; al volver a recto la media residual fue ≤0,0001°. En [las brasas](secuencia-brasa-forge.tsv) se contrastaron los colores de 20 cuadriláteros reales del atlas, incluidos los cuadros intermedios y el respaldo de tres sprites. Siguen pasando [saltos](saltos-forge.tsv), [escalera](escalera-forge.tsv), [nado](nado-forge.tsv), [bote](bote-resumen.tsv), [nuca](maniobra/retorno/retorno.tsv) y [nacimientos con Shift](nacimiento-agachado-resumen.tsv).

[Compilación comprobada en Forge](https://github.com/Santi-PdR/modelos/actions/runs/44990011121) · [Fuentes](https://github.com/Santi-PdR/modelos/tree/be17e48759423aed188393bd87323a770a97121d).

## Probar en `test-1` y volver a la .37

**Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1 · Curios 5.14.1 opcional.** Cerrá Minecraft y usá el [bloque de PowerShell](instalar-test-1.txt). Comprueba los 777.620 bytes y el SHA-256 antes de retirar los JAR anteriores de `capatest`. No se ejecutó en tu Windows ni se modificó la descarga pública.

En F5, caminá, pasá a carrera y girá en diagonal. Mirá las hombreras de perfil para ver cómo acompañan las mangas y frená para ver el remate del paño. Mirá las brasas de noche. Si querés volver atrás, quitá `capatest-1.67.38.jar` y usá el [instalador de la .37](../v1.67.37/instalar-test-1.txt).
