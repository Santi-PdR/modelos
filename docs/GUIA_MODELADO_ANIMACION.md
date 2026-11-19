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

## 5. Restricciones VIGENTES de este proyecto (no revivir)

- La capa **visible**, **sin intersectar el torso**, en **+Z (espalda)**.
- **Motion espacial PROHIBIDO** (fuerza/dirección del viento, oscilación
  en Z, cresta en Z): solo **rotación** o **cosmético**.
- **Alpha del glow FIJO 1.0**; brillo en COLOR.
- **NO ocultar los huesos padre** (cape_top/mid/bottom) → rompe el render
  de hijos en F5.
- **8 RMS distintos** por clip (validación). Cualquier edit debe
  preservarlos.
- **Icono 2D byte a byte** el PREFERIDO (SHA `c90670ba…`).

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
   **Halo suave (A/B)**. Probar luz baja y alta, dorso y frente. **Chispas**
   se puede activar aparte. «Referencia» desactiva los FX para comparar
   el PNG original a la misma pose, escala y cámara. `tools/verify_v1670.py`
   contrasta la oclusión, la opacidad, el halo regenerado y el visor offline.
7. Probar en Minecraft el halo junto a una pared y con el maniquí real en F5.
   No debe aparecer delante de una pared, en la cara interior ni en el pelo.
   Si un shader pack altera el pase, relanzar con `-Dcapa.sinHalo=true`
   conserva el núcleo estándar. Confirmar también el enfriamiento de las
   brasas y la prioridad de pecho. El visor no ejecuta los shaders del juego.
