# Accesorios para el portador de Blight Star

El manto ya hace de silueta principal por detrás. Las próximas piezas deberían darle carácter al portador de frente o de perfil: carbón raspado, costuras granate y un solo punto de luz, sin sumar otro emisor de brasas. Son propuestas, no objetos incluidos en el mod.

| Propuesta | Colocación y lectura | Qué comprobar antes de texturizar |
| --- | --- | --- |
| **Brazalete Ascua** — primero | Antebrazo izquierdo, al tercio de la muñeca. Dos segmentos de carbón, un puente granate y una grieta rosa corta en el costado exterior. Que se lea de frente y al caminar; no hace falta que cubra toda la mano. | Pivote del antebrazo; brazos Steve/Alex, manga exterior, objetos en mano, ataque y nado. Con placa de brazo, usar un ajuste propio o dejarlo bajo la manga, no agrandarlo a ciegas. |
| **Sello de la Estrella Hendida** | Broche de esternón, por debajo del cuello. Una estrella asimétrica de carbón y un centro rosa de uno o dos texeles. Añade un foco al frente sin convertir el cuello del manto en solapas. | Pechera de hierro y élitros, hombros al agacharse y cabeza mirando abajo. Probar un broche bajo y corto antes de añadir una cadena. |
| **Reliquia en reposo** | Reutilizar el núcleo de [`reliquia_holografica_v3.zip`](../reliquia_holografica_v3.zip) como objeto de cinturón, hacia delante, con un punto azul frío y la carcasa casi mate. La versión con órbitas funcionaría mejor como pieza de exhibición, separada del manto. | El original flota detrás del hombro: ahí competiría con el paño. En la cadera, comprobar codo, pierna y el borde del manto en sprint; no heredar las órbitas, el pulso grande ni el fogonazo. |

## Primer prototipo: Brazalete Ascua

**Prototipo geométrico v0:** [Blockbench](prototypes/brazalete_ascua/Brazalete_Ascua_fit_v0.bbmodel) · **estudio animado v1:** [Blockbench](prototypes/brazalete_ascua/Brazalete_Ascua_fit_v1.bbmodel) · [previsualización conceptual de efectos](prototypes/brazalete_ascua/efectos_preview.html) · [alcance y pruebas pendientes](prototypes/brazalete_ascua/README.md). Los pases v1 no están integrados en el JAR ni en Curios.

- **Volumen:** ~2,5 unidades de altura del brazo (16 unidades = 1 bloque). Envolver sólo lo necesario para leer una pieza cerrada de frente. Una bisagra oscura por dentro y la grieta por fuera; reservar el lado hacia el torso para evitar enganches al balancear el brazo.
- **Atlas:** 32×32 como punto de partida. El v1 añade una máscara blanca de estudio para la grieta y una previsualización esquemática de un halo leve; ninguno está conectado a un pase emisivo real. Reutilizar los tonos del manto, no su atlas. La estrella y el paño deben seguir dominando al ver las dos piezas juntas.
- **Movimiento:** el ajuste final debería ser rígido con el brazo, sin giro independiente. Los clips de pulso y resonancia v1 sólo son ensayos del núcleo en Blockbench; no son animación funcional en juego ni movimiento del brazo. La página de estudio permite probar dos motas ascendentes, pero no se añadió un emisor al mod; decidir si sobreviven después de revisar su legibilidad. La primera revisión visual necesita tres cuartos frontal, dorso y perfil con y sin manga exterior. La vista de primera persona sería un paso aparte: no se da por hecha con un renderer de Curios.
- **Montaje:** ensayar como modelo separado en Blockbench, no añadir cubos al GEO de la capa. Si funciona con el manto solo y con `back` + pechera, decidir el slot (`bracelet` si se usa Curios) después de aprobar el ajuste.
