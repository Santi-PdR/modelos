# Guía de referencia — modelado, animación, GeckoLib y texturas

_Estudio estructurado hecho antes de la mejora v1.54.0. Se RECUERDA antes
de cada actualización del modelo. Distillado de la documentación oficial
de Blockbench, el spec del formato `.bbmodel`, las skills de modelado/
animación y la documentación de GeckoLib._

## 1. Modelado (Blockbench / .bbmodel)

- **Jerarquía de huesos ANTES de la geometría.** Los groups (huesos)
  definen el pivote; la geometría (cubos/elementos) se parenta al hueso
  que la debe mover. Los huesos decorativos se parentan al body/head.
- **Pivotes en las articulaciones reales** (hombro, cadera, cuello) para
  que la rotación gire sobre el punto correcto.
- **UUID estables: NO crear/borrar huesos que tengan animación.** Si se
  borra y recrea un hueso, su UUID cambia y los animators quedan huérfanos.
  Preferir EDITAR la posición/rotación del hueso existente.
- **Densidad de polígonos acorde al tamaño visible y la deformación.**
  No añadir cubos para arreglar textura stretching: arreglar las UV.
- **Siluetas y proporciones ANTES del detalle.** Bloquear la silueta y las
  proporciones antes de UV, textura y detalle superficial.
- **Cubos para estilo Minecraft; mesh para formas orgánicas.** Cubos son
  más simples y apropiados para estilo voxel.
- **Orden de transformación:** trasladar al origen → rotar → trasladar
  de vuelta. El orden de rotación es siempre XYZ.

## 2. Animación

- **Hierarquía de huesos limpia antes de keyframes.** En GeckoLib/Bedrock
  TODO cubos animado debe vivir bajo un hueso.
- **Interpolación:** `catmullrom`/`bezier` para movimiento orgánico y
  suave; `linear` para movimiento mecánico/snappy; `step` para cambios
  instantáneos. **No usar lineal para movimiento natural** (vértices
  angulosos, speed constante = artificial).
- **Primer y último keyframe deben coincidir en pose** para bucles
  (loop). Para movimiento de vaivén repetitivo, usar seno
  (`Math.sin(anim_time * 180) * amp`).
- **Animar un lado y reflejar** para rigs simétricos (save de trabajo y
  consistencia). El offset de tiempo en walk mejora el ritmo.
- **Pivotes en articulaciones** simplifican la rigging y hacen que la
  rotación sea correcta.

## 3. GeckoLib (render de huesos y glow)

- **Render de huesos es RECURSIVO:** se aplica transform en cada nivel y
  se recorren los hijos.
- **`setHidden(true)`** oculta los cubos del hueso; **`setChildrenHidden`**
  corta el recorrido de los hijos. En GeckoLib 4.8 son dos controles distintos.
  No cortar `cape_top/mid/bottom` ni el portador `cape_wearer_fit` al
  ocultar los cubos antiguos o al aplicar la visibilidad del slot.
- **Plegado:** conserva el pase `RenderType.eyes` con su `glowmask.png`
  de 128². No usar `AutoGlowingTexture` en la capa equipada: trasladaría
  píxeles al glow y los quitaría del albedo, abriendo agujeros.
- **Equipado:** el alpha global del re-render queda en **1,0**. Se pulsa
  el color; el alpha de cada texel del atlas emisivo marca sólo su cobertura.

## 4. Texturas, atlas y UV

- **Densidad de texel consistente**: no estirar el mismo swatch del atlas
  sobre caras de distinto tamaño. Alinear UV y densidad de texel.
- **Cartas UV:** cada cara lleva guarda de color. Al asignar espacio,
  dar prioridad a las caras expuestas sin bajar a cero la densidad de
  los cantos. Mantener el muestreo nearest en albedo y emisión.
- **Capa equipada:** albedo opaco y emisión RGBA de 512². El pase
  emisivo usa la misma geometría y profundidad que el opaco, sin el offset
  de armadura vanilla. Desde v1.67, lee también un mapa RGB de halo en el
  **mismo pase**: núcleo nearest y halo interpolado, sin mipmaps.
  `tools/cape_bloom.py` deriva ambos radios del núcleo de cada carta, en
  unidades del modelo. No difuminar globalmente el atlas: la guarda evita
  que se cuelen colores a UV vecinas, y el forro y el acero quedan mates.
  El halo suma RGB, sin cambiar la cobertura del núcleo ni el alfa del paño.
  Desde v1.67.3 la luz de bloque y el cielo, ponderado por la hora y el clima,
  controlan sólo la intensidad del halo. Se filtra por portador y se envían
  dos ganancias por vértice en `UV2` del pase propio (borde e interior).
  No usar un uniforme por portador: varios pueden compartir un lote. El
  núcleo estándar conserva sus coordenadas de luz fullbright.

## 5. Restricciones VIGENTES de este proyecto (no revivir)

- El paño visible va en **+Z (espalda)**, sin atravesar el torso.
  La montura interior se embute en la espalda; no atraviesa la cara frontal.
- **Motion espacial PROHIBIDO** (fuerza/dirección del viento, oscilación
  en Z, cresta en Z): solo **rotación** o **cosmético**.
- **Alpha del glow FIJO 1.0**; brillo en COLOR.
- **NO ocultar los huesos padre** (cape_top/mid/bottom) → rompe el render
  de hijos en F5.
- **8 RMS distintos** por clip (validación). Cualquier edit debe
  preservarlos.
- **Icono 2D:** `tools/cape_icon.py` usa la referencia elegida en v1.67.7,
  retira el damero y conserva la silueta y el alfa en todos los cuadros.
  `item/generated` sigue siendo el modelo; anima el atlas con `.png.mcmeta`,
  no uses overrides ni BEWLR. El icono preferido histórico (SHA `c90670ba…`)
  se conserva en su respaldo. La v1.67.6 tiene una copia de su primer cuadro.

## 6. Comparar y validar el ajuste equipado desde v1.61.0

1. `python3 tools/build_deliverables.py` reconstruye GEO, atlas, clips,
   `.bbmodel`, comparación y visor. Editar primero las fuentes en `tools/`.
2. `python3 tools/verify_v1630.py` coteja la entrega, no sólo el modelo en
   memoria. Para la referencia se fija la cámara y se ignoran pelo, ropa y
   partículas libres; el registro mide contorno sólido y RGB común.
3. `cape_wearer_fit` está entre `chestplate` y el conjunto equipado. No
   tiene cubos ni keyframes. El renderer aplica la holgura de cabeza,
   el fuelle y el contragiro del paño en ambos pases, según cabeza y torso
   de `HumanoidModel`. No aplicar un segundo ajuste en Curios ni hornear
   la corrección al proyecto de Blockbench.
4. En juego, comprobar en F5 primero el pecho sin Curios, luego `back`
   con el pecho vacío, y finalmente ambos slots (una sola capa y glow).
   Probar agacharse mirando arriba y girando, caminar, esprintar, caer,
   planear y nadar. Probar de día y noche: el glow debe coincidir con los
   cortes. El barrido de cajas no reemplaza estas comprobaciones.
5. En **Ajuste al portador → Zancada simulada**, pausar el clip y alternar
   **Holgura del paño** con la misma amplitud y postura. El visor reproduce
   la guía rotacional de Java, no el cambio de estados ni toda la pose
   vanilla. `tools/verify_v1660.py` compara brazos, piernas y costuras con
   y sin la guía. No usar una zancada sintética para certificar cascos,
   armaduras ni las poses de vuelo/nado del cliente.
6. En el visor, pausar con **Luz de grietas** encendida y alternar
   **Halo suave (A/B)**. Comparar **Cueva**, **Antorcha** y **Día** sin
   mover la cámara. El visor aplica la luz elegida de inmediato; en juego
   se adapta gradualmente. Probar dorso y frente. **Chispas**
   se puede activar aparte. «Referencia» desactiva los FX para comparar
   el PNG original a la misma pose, escala y cámara. `tools/verify_v1670.py`
   contrasta la oclusión, la opacidad, el halo regenerado y el visor offline.
7. Probar en Minecraft el halo junto a una pared y con el maniquí real en F5.
   No debe aparecer delante de una pared, en la cara interior ni en el pelo.
   Si un shader pack altera el pase, relanzar con `-Dcapa.sinHalo=true`
   conserva el núcleo estándar. Confirmar también el enfriamiento de las
   brasas y la prioridad de pecho. El visor no ejecuta los shaders del juego.

## 7. Verificación de los FX en Forge desde v1.67.1

- **Atlas:** 512×512 o un múltiplo entero cuadrado con las mismas UV. La
  máscara de núcleo necesita alfa; sin ella se omite la emisión, no el paño.
  Un halo corrupto o incompatible no debe dibujar el damero de textura
  ausente. Al quitar el pack y pulsar `F3+T`, vuelve la luz sin reiniciar.
- **Prueba automática (desarrollo):** `gradle -PcapeFxSmoke runClient`
  incluye Curios 5.14.1 solo en esa ejecución, usa un mundo de prueba en
  `build/fx-smoke-run/` y cierra el cliente al terminar. Para repetir desde
  cero usa un directorio de build limpio. La opción `probar_halo` de Actions
  (o el marcador `[probar-halo]` en el commit) ejecuta la misma prueba en
  pantalla virtual y adjunta las capturas si termina correctamente.
- **Qué comprueba:** elección de pase con PNG corrupto, tamaño incorrecto,
  shader inválido, núcleo corrupto y opción sin halo; recuperación y pila de
  poses ante un fallo inyectado; nacimiento y movimiento de brasas ante un
  panel; visibilidad de Curios y un único render en pecho, ambos slots con
  el pecho encantado y espalda con élitros. Desde v1.67.2 también arranca un
  planeo con Curios `back`, entra en el agua de pie, nada y vuelve a erguirse.
  Mide la diferencia entre el marco de emisión y la transformación del
  renderer, y comprueba que el cliente recibe brasas en esas posturas.
  En v1.67.3 también comprueba el shader y la subida real de vértices en
  Forge: dos ganancias distintas en un mismo lote, fondo mate, profundidad
  y alfa. Toma F5 de día, de noche y de noche junto a una linterna,
  comprobando la luz del portador y el valor que el pase envía al shader.
- **Dobladillo:** `CapeSettleTest` mide el retardo con entradas de frenada
  y aterrizaje controladas. `tools/verify_cape_settle.py` aplica esas
  muestras a mezclas de los clips del JAR: contrasta las raíces, el solape
  de cada costura y el contacto con brazos y piernas al aplicar la holgura.
  Con `--plate docs/capa_v1673_nocturna.png` regenera la comparativa usando
  el TSV de `CapeSettleTest --samples`.
- **Paso lateral (v1.67.4):** proyectar la trayectoria sobre el eje lateral
  del torso, no el de la cámara. El arrastre empieza después del segmento 0,
  sólo en Y/Z y dentro de las cotas previas. Las puntas tardan más en invertir
  el giro que el primer tramo libre. Las pruebas usan `CapeSwayTest --samples`
  y `tools/verify_cape_sway.py TSV --plate docs/capa_v1674_arrastre.png` para
  contrastar el visor, el giro en el espacio del portador y el solape de las
  costuras. El cliente de prueba da pasos en ambas direcciones de noche y
  toma capturas F5; el A/B pausado del visor no es una captura del juego.
- **Élitros (v1.67.5):** Curios `back` lee los ángulos ya interpolados del
  ala vanilla en el pecho. Usa una corrección X en `cape_top` y toma su
  máximo con la holgura de zancada. No traslada el paño ni vuelve a animar
  el ala. Verificar los ángulos de Java y los volúmenes grises del visor con
  `tools/verify_cape_wings.py TSV --plate docs/capa_v1675_elitros.png`, usando
  `CapeWingFitTest --samples`. La prueba F5 lee `cape_top` del modelo equipado
  y toma una captura con las alas ya plegadas.
- **Unión lateral (v1.67.7):** asiento profundo más dos remates sobre las
  mangas, cosidos a las hombreras. El forro inferior cubre la unión entre
  cada remate y el torso. `CapeFit.shoulderReach` recoge los remates para
  despejar cabeza y alas; `CapeFit.yokeShape` estrecha el forro antes de
  bajarlo al fuelle cuando un brazo va hacia atrás. El visor aplica ambos
  ajustes, sin cambiar el paño libre; el .bbmodel está extendido para
  edición. `verify_cape_mount.py` mide el solape, la holgura y el
  alojamiento del forro con élitros. Forge compara una vista a 89° recta
  y otra a 86° con 43° de giro de cabeza, con y sin manto en pecho y
  `back`. `verify_forge_mount.py` busca suelo en el interior de ambas
  uniones y mide el icono animado contra la misma ranura vacía.
- **Respaldo alto (v1.67.8):** dos piezas de tres paneles en `chestplate`.
  El apoyo toca el torso por encima del forro inferior y el bisel se solapa
  con el cuello. `CapeBacking` limita la altura de cada mitad según el margen
  real de la cabeza; con élitros se repliega dentro del torso. No altera la
  animación del paño. `verify_cape_backing.py` comprueba el contacto en el
  plano de la camiseta, las costuras y la holgura. En F5 se proyecta esa
  franja desde el modelo en vista oblicua y de perfil, con el respaldo
  habilitado en ambos slots y deshabilitado como control.
- **Pulso del icono (v1.67.8):** 32 fotogramas a un tick por cuadro, mismo
  contorno y duración de 1,6 s. Se comprueba el recorrido de la cresta de
  luz en la hotbar vanilla; se conservan el dibujo y el reposo de v1.67.7.
- **Lectura del diagnóstico:** la lámina de brasas compara los puntos de
  salida con los clips del JAR, no con todos los huesos animados en vivo.
  El servidor no ve el paño de cada cliente. El ajuste de élitros reduce el
  cruce del paño libre; conserva la montura y sus contactos con el ala.
  No certifica holgura para todas las alas o skins.
- **Prueba manual pendiente para packs concretos:** repetir con shaders
  de terceros y gráficos Fabulosos; agacharse, planear y nadar junto a
  losas y paredes. Cambiar el ojo de `back` y probar un cosmético encima.
  Las brasas emitidas antes de ocultarlo se apagan con su vida normal.
