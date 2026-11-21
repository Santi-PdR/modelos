# Retorno de la mirada · v1.67.30 y v1.67.31

[Capturas de pecho](retorno-pecho.jpg) · [Capturas de Curios](retorno-curios.jpg) · [Mediciones y tiempos reales](retorno.tsv) · [Ejecución de Forge](https://github.com/Santi-PdR/modelos/actions/runs/44961551931).

Se reprodujeron los dos JAR de `test-1` byte por byte y se repitió la maniobra con Alex en pecho y Curios. El cliente de prueba capturó los giros de +55° y −55° con la cámara en el lado correspondiente. No se espejaron las imágenes. Se registraron 28 pares en coordenadas de la cabeza: t63, la frenada en t77 y al menos cuatro cuadros posteriores por ranura y sentido. Los pares pueden tener distinta fracción de tick. La cuadrícula de color tiene 5.184 muestras por cara, no 5.184 píxeles únicos.

| Toma | Pecho: granate .30 → .31 | Curios: granate .30 → .31 |
| --- | ---: | ---: |
| Frenada, giro +55° · t77 | 1833 → 176 | 1834 → 173 |
| Frenada, giro −55° · t77 | 1262 → 1306 | 1328 → 1284 |
| Fin del retorno, giro +55° · t83 | 3702 → 3709 | 3873 → 3989 |
| Fin del retorno, giro −55° · t83 | 3872 → 3899 | 3979 → 3970 |

La gran mejora de la frenada se repitió en el **giro positivo**, y todavía se ve en la nuca durante los primeros cuadros del retorno. En t78, aunque bajó el granate en la nuca, subió en el lateral medido (514 → 575 en pecho y 520 → 557 en Curios). En el **giro contrario** no se reprodujo la mejora de t77 y hubo tomas con más granate en la nuca, por ejemplo t79 en pecho (1741 → 1962). La diferencia de pose entre fracciones de tick impide atribuir todo ese aumento al desplazamiento por sí solo.

En **t83** sigue viéndose el cruce en las dos versiones. La .31 es una mejora parcial para la frenada, no una solución a todo el retorno ni a ambos sentidos. El seguimiento no cambia los JAR. Para un ajuste siguiente, conviene medir el borde y la tira en esos últimos cuadros y comprobar ambos giros antes de promover otra versión.
