# Historial de cambios

## 1.0.26 — la vista previa deja de ser invisible

* **`/relic info` avisa de que la vista previa está encendida** y a qué distancia.
  Una reliquia flotando delante de la cámara sin más contexto parece un fallo del
  mod; ahora la propia información lo explica y recuerda cómo quitarla.
* **La vista previa se apaga al pasar a espectador.** El tick del jugador local
  salía antes de comprobar nada en modo espectador, así que la vista previa seguía
  dibujándose y, como `markRendered` la mantenía viva, tampoco se podaba nunca: una
  reliquia fantasma delante de la cámara hasta salir del mundo.
* 1 clave nueva por idioma (49 en cada uno).

## 1.0.25 — deshacer un solo ajuste, y ver qué está sin guardar

* **`/relic reset <clave>`**: vuelve al defecto una sola clave. Es el deshacer de un
  experimento suelto (`/relic reset scale`) sin tirar los otros 23 ajustes, y no
  marca nada como sin guardar si esa clave ya estaba en su valor de fábrica.
* **`/relic set` sin argumentos marca con `*` las claves sin guardar** y añade una
  línea con cuántas son. Antes solo se sabía el número total, y en `/relic info`;
  ahora se ve cuáles, que es lo que hace falta para decidir si lanzar `/relic save`.
* 2 claves nuevas por idioma (48 en cada uno).

## 1.0.24 — dos fallos que salen con el juego en español

* **`/relic info` enseñaba `6,00` en vez de `6.00`.** Los cuatro números de la
  primera línea (offset x/y/z y escala) se formateaban con el locale del sistema
  y no con `Locale.ROOT` como el resto. Con el juego en español salía coma
  decimal, y esos números son justo los que se copian al `holocore-client.toml`,
  donde la coma rompe el valor.
* **`/relic reset` contaba de más.** Marcaba como «sin guardar» las 24 claves
  aunque estuvieran ya en su defecto, así que un `/relic reset` sin nada que
  deshacer dejaba 24 cambios fantasma y el `/relic save` siguiente reescribía el
  archivo para nada. Ahora solo cuenta y marca las que cambian de verdad; si ya
  estaba todo de fábrica lo dice y no toca nada.
* CI: paso nuevo `Validate number formatting and reset`, que rechaza cualquier
  `String.format` sin `Locale` explícito y comprueba los dos arreglos anteriores
  sobre el código fuente.
* 1 clave nueva por idioma (46 en cada uno).

## 1.0.23 — `/relic reset`, y que las descripciones no mientan

* **Nuevo `/relic reset`**: devuelve las **24** claves a los valores de fábrica en
  memoria (después, `/relic save` si quieres quedártelos). Se apoya en la misma
  tabla que `/relic set`, así que lo que restaura es exactamente lo que trae
  `RelicConfig`.
* **La descripción del mod en la lista de mods estaba congelada en 1.0.x**:
  enumeraba `/relic offset|scale|side|quality|toggle|pulse|release|info` y no
  mencionaba `anim`, ni `stats`, ni `set`, ni `save`, ni `preview`. Ahora está al
  día y el CI compara los dos sitios donde se documentan los comandos (README y
  `mods.toml`).
* **Fuga pequeña pero real**: `ClientRelicStates` guardaba una entrada por cada
  jugador del que se hubiera recibido estado y no borraba ninguna al irse. Ahora
  se poda cada ~10 s contra la lista de jugadores del mundo (al volver a verlos,
  el servidor reenvía su estado).
* La vista previa se apaga sola si te quitas la reliquia: antes podía seguir
  dibujando un visual a punto de podarse durante un par de segundos.
* El chequeo `Validate config tweaks` comprueba ahora también el **valor por
  defecto** de las 22 claves: la tabla del comando, `RelicConfig` y el README
  quedan atados entre sí.
* 1 clave nueva por idioma (45 en cada uno).

## 1.0.22 — `/relic preview`: mirar la reliquia de cerca y siempre igual

* **Nuevo `/relic preview`**: dibuja la reliquia del jugador delante de la cámara
  a una distancia fija (2.5 bloques; `/relic preview 1.5` la acerca, rango 0.5–6)
  con los mismos cuatro pases y el mismo aura. El estado es el real —si te pegan,
  se pone cargada— y se apaga sola al salir del mundo.
* El motivo es el que faltaba para afinar el brillo: hasta ahora solo se podía
  mirar la reliquia colgada del hombro, que cambia de tamaño con la perspectiva y
  depende de dónde esté la cámara. Con la vista previa el aura queda siempre a la
  misma distancia y sobre el fondo que elijas (nieve, arena, cueva), que es lo que
  hace comparables dos `auraIntensity` distintos.
* Se dibuja en `RenderLevelStageEvent` (`AFTER_ENTITIES`) y vuelca su lote con
  `endBatch()` al terminar: no toca el render normal, es un dibujo extra mientras
  el comando esté activo.
* 2 claves nuevas en `en_us` y `es_es` (44 en cada uno). El chequeo de CI
  `Validate local relic tick` comprueba además que el hook de render sigue
  existiendo, que dibuja y que vuelca el lote.

## 1.0.21 — `/relic save`: los ajustes ya no se quedan en el aire

* **Nuevo `/relic save`**: escribe en `config/holocore-client.toml` lo que haya en
  memoria (`RelicConfig.SPEC.save()`). Hasta 1.0.20 todo lo que se ajustaba con
  `/relic set`, `/relic offset`, `/relic scale`, `/relic side` o `/relic quality`
  se perdía al cerrar el juego: había que copiar los números a mano.
* Mientras haya valores sin guardar, **`/relic info` añade una cuarta línea
  amarilla** con cuántos son, así que el aviso sale justo donde se miran los
  valores. `/relic save` sin cambios contesta «nada que guardar» y no toca el
  archivo; si la escritura falla, lo dice en vez de fingir que guardó.
* **Nuevo chequeo de CI** (`Validate documented defaults`): la columna «Defecto»
  de la tabla del README tiene que coincidir clave a clave con los valores por
  defecto de `RelicConfig`, incluida la fila compartida de `glitchMinSeconds` /
  `glitchMaxSeconds`. Esa columna era de fiar solo por costumbre.
* 4 claves nuevas en `en_us` y `es_es` (42 en cada uno).

## 1.0.20 — `/relic set`: la configuración, en caliente

* **Nuevo `/relic set`**: `/relic set` sin argumentos lista las **22 claves**
  ajustables con su valor actual; `/relic set <clave> <valor>` la cambia al
  instante (`auraIntensity`, `haloIntensity`, `auraTint`, `maxRenderDistance`…).
  Nada se guarda en el `.toml`, igual que `/relic offset`: sirve para probar sobre
  la marcha (nieve, arena, cueva) y copiar después el valor que te guste.
  `placement.shoulder` y `visuals.quality` no pasan por aquí porque ya tienen
  `/relic side` y `/relic quality`.
* Un valor fuera de rango o que no es un número se rechaza **sin tocar nada**, y
  se dice el valor que hay ahora mismo.
* **Nuevo chequeo de CI** (`Validate config tweaks`): la tabla del comando y
  `RelicConfig` tienen que coincidir en las claves (ninguna clave nueva se puede
  quedar sin poder ajustarse), en el tipo (número, entero o booleano) y en el
  **rango** de `defineInRange`. Si alguien ensancha un rango en la config y no en
  el comando, el build falla.
* 5 claves nuevas en `en_us` y `es_es` (38 en cada uno).

## 1.0.19 — la reliquia ya no se congela en primera persona

* **Bug de verdad, no cosmético**: la máquina de estados se actualizaba dentro
  del renderer de Curios, y **en primera persona el jugador local no se dibuja**.
  Mientras mirabas de frente: el escaneo de alerta no corría (así que no había
  anillo rojo al acercarse un mob), las variaciones de reposo no salían, el
  destello no decaía, `/relic info` contestaba `-` y —lo peor— el visual se
  podaba a los 40 ticks sin dibujarse: al volver a tercera persona la reliquia
  arrancaba de cero con su `activation`, perdiendo en qué estado estaba.
* **Arreglo**: el cliente actualiza la reliquia del jugador local en cada tick
  (`RelicClientEvents.tickLocalRelic`), esté o no en pantalla, preguntando a
  Curios si la lleva puesta. El estado y el brillo interpolado quedan siempre al
  día; las animaciones que habrían tocado **no se encolan** mientras el portador
  no se ve (`RelicAnimatable.update(..., visible)`), para no reproducir de golpe
  lo que pasó mientras mirabas a otro lado. `/relic anim` sí encola siempre: es
  un pedido explícito.
* El prune de `RelicVisuals` ahora mide **ticks sin actualizarse** y no ticks sin
  dibujarse, que es lo que de verdad significa «este portador ya no está».
* **Nuevo chequeo de CI** (`Validate local relic tick`): el camino de tick y el
  `markRendered` del renderer tienen que seguir existiendo y estar conectados; si
  alguien vuelve a dejar la actualización solo en el renderer, CI lo dice.
* `README`: aclarado que el reinicio por 2 s fuera de pantalla es cosa de **otros**
  portadores, y dos puntos nuevos en el checklist (estado en primera persona y
  que pasar a tercera no reinicie la activación).

## 1.0.18 — `/relic stats`: el ahorro, en números

* **Nuevo `/relic stats`** (y `/relic stats reset`): dice cuántos **pases por
  dibujo** se están emitiendo (1 si solo queda el pase base, 4 con base, emisivo,
  halo y GLSL), cuántos dibujos por segundo y cuántos **milisegundos** cuesta una
  reliquia, con modelo y aura por separado. Es la única forma de ver lo de 1.0.16
  y 1.0.17, que por diseño no cambian ni un píxel: comparar en el mismo sitio con
  1.0.15 es una medida y no una impresión. También sirve para decidir si hace
  falta `quality=lite`, `glowHalo=false` o bajar `maxRenderDistance`.
* Se mide **por dibujo** (una reliquia visible en un frame), no por frame del
  juego: dos `System.nanoTime()` y un `long` sumado, decenas de nanosegundos
  frente a los cientos de microsegundos que se miden. Todo en el hilo del
  cliente, sin hilos ni volátiles: los comandos corren en el mismo hilo que
  renderiza.
* **Nuevo chequeo de CI** (`Validate documented commands`): cada literal de
  primer nivel del árbol `/relic` tiene que aparecer en el README con `/relic`
  delante. Un comando sin documentar es un comando que nadie encuentra.
* 3 claves nuevas en `en_us` y `es_es` (33 en cada uno).

## 1.0.17 — el camino de render ya no reserva memoria (y el README deja de repetirse)

* **Cero asignaciones por frame y portador** en el aura, el anillo y el estado
  interpolado. `RelicAura` creaba un `record Frame` por frame y cuatro `Vector3f`
  por billboard para girar los ejes; con tint + aditivo + anillo eran **35
  objetos por portador y frame** (a 240 FPS con diez reliquias, ~88 000 objetos
  por segundo). Ahora `Frame` es una instancia reutilizada y el giro son seis
  multiplicaciones en `float`. `RelicGlowState.targetFor` devuelve constantes
  `static final` en vez de crear un `Target`, y `getRenderColor` reutiliza el
  `Color` mientras el tinte no cambie (el pase base va siempre en blanco).
  Ningún píxel cambia: son las mismas cuentas con menos objetos.
* **Dos chequeos nuevos de CI**: `Validate render path allocations` prohíbe `new`
  en `RelicAura` y `RelicGlowState` salvo en constantes de clase, y
  `Validate single animation evaluation` fija lo de 1.0.16 (un `defaultRender`,
  ningún `actuallyRender`, tres `renderExtra`). Las dos mejoras de rendimiento
  ya no pueden perderse en silencio.
* **README sin secciones duplicadas.** Había dos «Brillo y shaders»: la segunda
  era la de antes de 1.0.12 («El modelo se dibuja dos veces», «~11 700 quads por
  reliquia y frame»). Se queda una sola, con el recuento real (cuatro pases,
  ~23 000 quads con todo encendido) y el tinte del halo corregido a un cuarto
  del color del estado, que es lo que hace el código desde 1.0.12. El CI ahora
  falla si un `##` se repite en el README.
* `docs/BRILLO-Y-SHADERS.md` §A.1c: lo que sí cuesta por frame (geometría) y lo
  que se dejó de asignar.

## 1.0.16 — una animación por frame, no cuatro

* **Los cuatro pases ya no evalúan la animación cuatro veces.** Estudiado en el
  código de GeckoLib 4.8: `defaultRender` → `actuallyRender(isReRender=false)` es
  donde vive `model.handleAnimations(...)` (posar los 98 huesos), y `reRender`
  pasa `isReRender=true` y se salta ese trabajo a propósito (es para «alternate
  RenderType layers»). Ahora el pase base usa `defaultRender` y los otros tres
  usan `reRender` sobre la misma pose: **1 evaluación por portador y frame en vez
  de 4**.
* Efecto secundario que también se arregla solo: los pases comparten
  exactamente la misma pose. Antes cada uno recalculaba con
  `RenderUtils.getCurrentTick()` (reloj de `Blaze3D`, fraccionario), así que
  había microsegundos de diferencia entre base, emisivo, halo y GLSL — en un
  contorno aditivo eso se puede ver como flecos de color en los bordes.
* Si el fade por distancia llega a cero, la reliquia no se procesa ni se dibuja
  ese frame.

## 1.0.15 — que los nombres no vuelvan a mentir

* **Nuevo chequeo de CI**: las constantes de `RelicAnimations` tienen que ser
  exactamente las claves de `relic_hologram.animation.json`. Antes solo se
  comparaban contra el manifiesto, así que un nombre mal escrito pasaba el build y
  se quedaba en silencio hasta que GeckoLib no encontraba la animación — es la
  clase de bug que dejó las capas muertas hasta 1.0.11.
* `tools/check_aura_math.py` comprueba además que el **anillo quede por fuera del
  aura**: es una línea, y dentro del resplandor no se lee como anillo.

## 1.0.14 — banco de pruebas en el chat

* **`/relic anim <nombre>`** reproduce cualquiera de las 20 animaciones por su
  nombre corto, con sugerencias al tabular y **`/relic anim list`** para verlas
  todas (dos líneas de diez). Sirve para revisar `layer_shake`, `layer_bump` y
  `layer_hit` —las que estuvieron rotas hasta 1.0.11— sin esperar a que un mob te
  pegue. Las de bucle se reproducen una vez.
* **`/relic info` añade una tercera línea** con las intensidades que están
  mandando ahora (`aura`, `halo`, `glsl`, `anillo`) y si el tinte está activo, para
  afinar sin abrir el `.toml`.
* 6 claves nuevas en `en_us` y `es_es`, y el CI comprueba que los dos idiomas
  tengan exactamente las mismas claves.

## 1.0.13 — las constantes del aura, medidas

* Las constantes del pase de tinte ya no son a ojo: `tools/check_aura_math.py`
  lee del propio código los pesos, el alpha, el tinte, el color del estado y el
  **píxel central del PNG**, compone las dos pasadas sobre nieve, piedra y cueva y
  falla si el aura se blanquea, si baja la luminancia como una sombra o si pierde
  el tono. Corre en el CI.
* Resultado de medir: el tinte va con el color del estado **tal cual** (antes lo
  oscurecía ×0.55, que además apagaba el azul) y con cobertura ×1.6 (antes ×2.2).
  Sobre nieve el halo queda en (0.80, 0.94, 1.00) frente al fondo (0.93, 0.95,
  0.97): **tono cian +0.20 y luminancia −0.03**, o sea que tiñe sin parecer una
  mancha gris.
* El anillo usa el mismo criterio: también se tiñe, porque sobre nieve el aditivo
  lo dejaba en blanco.

## 1.0.12 — color de verdad sobre fondos claros

* **El aura pasa a tener dos pases**: uno de **tinte** (mezcla alfa normal con el
  color del estado) y encima el **aditivo** de siempre. El aditivo solo puede
  aclarar, así que sobre nieve o arena estaba condenado a verse blanco por mucho
  que se bajara la intensidad; mezclando, el halo se ve cian. Sobre cueva el que
  manda sigue siendo el aditivo.
* Nueva clave `visuals.auraTint` (por defecto `true`) para volver al
  comportamiento de 1.0.11 (solo brillo).
* **Fade por distancia**: la reliquia de otros jugadores se apaga suavemente en
  los 8 bloques antes de `maxRenderDistance`, en vez de desaparecer de un frame al
  otro. La tuya nunca se atenúa.
* El anillo pasa a 1.35 bloques para separarse del aura (1.10) y leerse como
  anillo y no como el borde del resplandor.

## 1.0.11 — el brillo vuelve a ser brillo

Arregla lo que se vio mal en juego: el aura se veía como una **nube blanca** más
grande que el jugador, y la reliquia no hacía nada sola en standby.

**El aura, otra vez pegada al núcleo** (esto es la vuelta atrás que pediste):

* diámetros 0.62 / 0.85 / 1.10 bloques (eran 1.05 / 1.55 / 2.10, hasta cuatro
  veces el tamaño del núcleo), aportes 0.30 / 0.17 / 0.09 (eran 0.55 / 0.32 /
  0.18) y alpha de quad 0.55.
* la textura ya **no tiene blanco en el centro**: el núcleo es cian (132, 219,
  255) y el degradado es más corto, así que suma color en vez de quemar el fondo.
* el anillo pasa a 1.15 bloques, apenas por fuera del aura, y por defecto es un
  poco más fuerte: es el que tiene que leerse.

**Por qué se veía blanco** (está contado con números en `BRILLO-Y-SHADERS.md`
§3.B): con blend aditivo el resultado es `fondo + aporte`, y sobre nieve el fondo
ya está a ~0.95, así que un aporte de más de ~0.05 por canal satura a 1.0. El
tinte era azul; el resultado no podía serlo. Antes sumaban tres capas grandes con
el centro en blanco puro **y** un destello que multiplicaba por 1.9.

**Destello mucho más discreto**: picos 0.80 / 0.60 / 0.40 / 0.30 (eran 1.00 / 0.85
/ 0.55 / 0.45), el peso está en el anillo (línea) y no en el aura (mancha), y ya
**no** se dispara al despertar, dormir ni cambiar de estado — eso era lo que
producía el fogonazo al entrar al mundo.

**Arreglo de verdad: las capas nunca se reprodujeron.** `triggerLayer("layer_hit")`
y `triggerLayer("layer_bump")` pasaban un nombre que no existe en el JSON (las
claves son `animation.relic.layer_hit`, etc.), así que GeckoLib no encontraba la
animación y el segundo controlador no hacía nada desde 1.0.0. Ahora usa
`RelicAnimations.LAYER_*` y el CI prohíbe los nombres literales.

**La reliquia hace cosas sola** (`visuals.idleVariations`): en reposo, cada
20–60 s elige por peso entre `layer_shake` (35%), `glitch` (30%), `layer_bump`
(20%), `energy_pulse` (12%) y `release` (3%). Antes solo había glitch.

**Defaults más bajos** (`auraIntensity` 0.32, `haloIntensity` 0.25,
`shaderIntensity` 0.35, `ringIntensity` 0.60). Si ya tienes el
`holocore-client.toml`, tus números guardados mandan: pon esos valores a mano o
borra el archivo para que se regeneren.

## 1.0.10 — red contenida y `/relic info` que informa

* **El estado ya no se manda a todo el servidor**: solo a la misma dimensión y a
  64 bloques del portador. Antes cada golpe, pulso o subida de nivel de cada
  jugador generaba un paquete para todos los jugadores conectados, aunque la
  reliquia ni se dibujara en su pantalla. Quien se acerque después lo recibe al
  empezar a trackear al portador, que ya estaba implementado.
* **Anti-spam de acciones**: el servidor ignora `toggle`/`pulse`/`release` con
  menos de 4 ticks de diferencia por jugador. Sin esto, un cliente modificado
  podía pedir pulsos en bucle y cada uno acababa en un broadcast. El límite es
  invisible para una persona (4 ticks = 0,2 s).
* **`/relic info` añade una segunda línea** con lo que no se puede adivinar
  mirando: estado del bucle (`idle`/`calm`/`charged`/`alert`/`dormant`), el
  destello actual en porcentaje y, cuando el pase GLSL está apagado, **por qué**
  (`shaderGlow=false`, shaderpack activo o no compiló). Sale del visual ya
  montado: si no lo hay, no se crea uno para contestar.

## 1.0.9 — la reliquia contesta

* **Destello de evento** (`visuals.flashIntensity`): la reliquia ya no solo cambia
  de estado, también reacciona. Un pulso, una liberación, un golpe recibido, una
  subida de nivel o el despertar/dormir suben de golpe el brillo del modelo, el
  aura y el anillo, y todo se apaga solo en ~0,4 s con decaimiento exponencial.
* El anillo se **enciende aunque el estado no lo tuviera**: un golpe en calma o
  con la reliquia dormida también deja ver el pulso, que es justo cuando el
  jugador quiere saber que pasó algo.
* Aura y anillo se **abren** durante el destello (22% y 30% de diámetro), lo que
  da la sensación de expansión sin mover ni un vértice nuevo: siguen siendo cuatro
  quads.
* El pico no se baja entre eventos (`max`), así que dos golpes seguidos en combate
  se ven como un parpadeo continuo y no como dos destellos recortados.
* Arreglados dos comentarios de la config que mentían: `shaderGlow` decía «usa
  haloIntensity» (usa `shaderIntensity`) y describía el pase con el look de 1.0.3.

## 1.0.8 — shader más limpio y tres arreglos

* **El borde ya no depende de las normales del modelo.** El fresnel se calcula con
  la posición del vértice (la reliquia está centrada en el origen del modelo), y
  la normal solo aporta un 25%. Si el modelo trae `Normal` constante, antes el
  «fresnel» se degradaba a un tinte plano sin que se notara en el log; ahora la
  silueta brilla siempre.
* **El rim entra en la alpha**, así que el contorno se ve aunque la textura
  emisiva sea transparente en ese texel: deja de ser un brillo pegado solo a las
  caras opacas.
* Halo y pase GLSL se **tiñen con el color del estado** (mezcla al 50% con el azul
  frío): cargada tira a ámbar, alerta a rojo, dormida a grisazulado. Antes el aura
  cambiaba de color y el modelo se quedaba azul.
* Segundo barrido en diagonal, líneas finas de holograma y un grano mínimo que
  rompe el banding del blend aditivo.
* **Arreglo**: el `ShaderInstance` anterior ya no se cierra en el acto al recargar
  recursos (podía quedar un lote de vértices sin volcar apuntando a un programa
  liberado); ahora se jubila y se cierra en el primer pase del frame siguiente.
* **Arreglo**: el apéndice de `docs/BRILLO-Y-SHADERS.md` vuelve a ser copia exacta
  de los ficheros GLSL. El CI lo comprueba (el JSON del apéndice llevaba desde
  1.0.3 sin el atributo `UV1`) y `tools/sync_shader_doc.py` lo regenera sin
  copiar y pegar.

## 1.0.7 — brillo coherente

* El factor de brillo del estado multiplica también el **halo aditivo y el pase
  GLSL del modelo**, no solo el aura. Antes, dormida (`DORMANT`) dejaba el aura
  al 35% pero el modelo seguía a tope, y cargada subía el aura sin tocar el
  modelo: ahora todo el brillo sube y baja a la vez.
* Es el mismo `RelicGlowState` interpolado de 1.0.6, así que la atenuación al
  dormir también es una transición y no un corte.

## 1.0.6 — transiciones

* El aura y el anillo **ya no saltan de color**: `RelicGlowState` interpola por
  portador el color (≈0.30 s), la fuerza y el giro (≈0.22 s) con el tiempo real
  entre frames, así que el resultado es el mismo a cualquier tasa de refresco.
* Consecuencias que se notan: el anillo se desvanece al entrar en calma o dormido
  en vez de desaparecer, y al pasar de alerta a reposo el giro del anillo pasa
  por cero y se invierte suave.
* El primer frame de un portador entra directo al estado (sin transición desde el
  azul por defecto), y un tirón del juego no provoca un salto: el delta está
  topado a 0.25 s.

## 1.0.5 — anillo de estado

* **Anillo de estado** (`visuals.glowRing`, `visuals.ringIntensity`): cuarto
  billboard aditivo que solo aparece cuando la reliquia tiene algo que contar, con
  textura nueva `relic_ring.png` (anillo con tres cortes y un arco más brillante,
  para que el giro se note) generada con `tools/make_ring.py`.
* **El aura y el anillo cambian de color con el estado**, reutilizando
  `RelicAnimatable.loopState()`: azul frío en reposo, azul apagado en calma,
  **ámbar** cargada (combate), **rojo** en alerta (monstruo cerca, y entonces el
  anillo gira al revés y late) y gris azulado dormida. Sin lógica nueva de
  estados: es solo presentación de lo que ya decidía la máquina de animaciones.
* El CI valida también el tamaño de `relic_ring.png` y sigue exigiendo que todas
  las claves de la config estén documentadas (ahora 21).

## 1.0.4 — repaso de calidad

Sin cambios visibles por defecto: es la pasada de «que esté bien hecho».

* `visuals.shaderIntensity`: el pase GLSL tiene su propia intensidad, separada de
  `haloIntensity`, para poder bajar el fresnel sin apagar el brillo.
* Si una recompilación del shader falla (pack de recursos roto, GLSL tocado), se
  **conserva el programa anterior** en vez de dejarlo nulo: antes una recarga
  fallida podía tumbar el render en el siguiente frame.
* El CI comprueba ahora que **cada clave de la config está documentada** en la
  tabla del README (19 claves), que la textura del aura es 64×64 RGBA y que el
  JSON del shader sigue siendo coherente.
* Las notas de cada release se generan de la entrada correspondiente del
  CHANGELOG, no de un texto fijo, así que la release cuenta lo que trae su jar.
* Documentación: nueva sección «Cómo probarlo» en `docs/BRILLO-Y-SHADERS.md` y
  corregido el apéndice (donde decía que `RenderType.create` no era accesible).

## 1.0.3 — shader propio

* **Cuarto pase con GLSL propio** (`visuals.shaderGlow`): fresnel en el borde y
  línea de barrido, sumados con blend aditivo sobre la textura emisiva. El pase
  normal, el halo y el aura no cambian, así que si el shader no está disponible
  la reliquia se ve exactamente igual que en 1.0.2.
* El shader se compila en cada recarga de recursos
  (`RegisterClientReloadListenersEvent`), no al cargar el mod, para que se rehaga
  al cambiar de pack de recursos.
* **Se desactiva solo con shaderpack activo** (Iris/Oculus/OptiFine): el pack
  sustituye el programa y el resultado sería el fallback del pack o nada. Si la
  API de Iris está disponible se le pregunta si hay pack en uso.
* Ficheros en `assets/minecraft/shaders/core/holocore_relic_glow.*`, que es donde
  los busca `ShaderInstance` (la ruta se arma como `shaders/core/<nombre>.json` y
  el nombre no admite namespace).
* El CI valida el JSON del programa y exige en el smoke test que el shader
  compile, así que un GLSL inválido rompe el build en vez de llegar al jugador.

## 1.0.2 — aura

* **Aura de tres billboards aditivos** alrededor del núcleo
  (`visuals.glowAura`, `visuals.auraIntensity`): textura radial con tres arcos,
  capas que giran a distinta velocidad y en distinto sentido, con latido lento.
  Es el resplandor tipo bloom sin post-proceso y funciona igual con o sin
  shaderpack.
* Textura nueva `textures/relic/relic_aura.png` (64×64), generada con
  `tools/make_aura.py` para que sea reproducible y no un binario a mano.
* Documentado el diseño y las alternativas descartadas (GLSL propio, post-proceso)
  en `docs/BRILLO-Y-SHADERS.md`, incluido el shader que se usaría si algún día se
  conecta (con las rutas y restricciones reales de `ShaderInstance` en 1.20.1).

## 1.0.1 — halo aditivo

* **Tercer pase de render con blend aditivo**: el núcleo suma luz en vez de
  mezclarla, así que se ve brillo acumulado también sin shaderpack. Se controla
  con `visuals.glowHalo` (por defecto `true`) y `visuals.haloIntensity`
  (`0.35`), y se omite en `LITE` y con `reducedEffects` por rendimiento.
* La intensidad se aplica por color de vértice, no con
  `RenderSystem.setShaderColor`, para no teñir el resto de la escena.
* Estudio de las alternativas (aura en billboard, `fsh` propio, post-proceso,
  integración con Iris/Oculus/OptiFine) en
  [docs/BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md).
* Los pases normal y emisivo siguen con `entityTranslucentEmissive` + lightmap a
  tope, que es lo que los shaderpacks usan para su bloom.

## 1.0.0 — primera versión publicada

Reliquia cosmética **Holographic Core** para Minecraft 1.20.1 / Forge 47.4.0,
con GeckoLib 4.8.1 y Curios API 5.14.1.

### Contenido

* Modelo y animaciones **v19 sin modificar** (977 cubos; variante `lite` de 751
  para equipos lentos), texturas 64x96 y brillo fullbright con textura emisiva,
  sin depender de shaders.
* Ítem `holocore:holographic_core` con receta propia, etiqueta `curios:charm`
  y pestaña creativa **Holographic Core**.
* Render sobre el hombro mediante `ICurioRenderer` (offset x −6, y +6, z +6,
  sin `scale(1/16)`), con una única instancia por portador.
* 20 animaciones y máquina de estados en el cliente:
  * reposo `idle` / `idle_calm` (calma si la calidad es `lite` o el portador
    tiene los efectos reducidos), `idle_charged` en combate (80 ticks de
    retención) y `idle_alert` con un monstruo a menos de 12 bloques;
  * `idle_dormant` cuando la reliquia está apagada, con `wake` / `sleep` solo si
    el interruptor se tocó hace menos de 400 ticks;
  * `activation`, `deactivation`, `charge_up/down`, `alert_up/down` con
    transiciones de 4–8 ticks; los saltos ALERT ↔ CHARGED encadenan el `*_down`
    y el `*_up` en vez de cortar la animación;
  * `hit`, `energy_pulse`, `release` y `glitch` solo si el sello del servidor
    tiene 40 ticks o menos, más las capas `layer_hit`, `layer_bump` y
    `layer_shake` sobre el hueso `relic_react`.

### Interfaz

* Tecla **G**: despertar / dormir la reliquia.
* `/relic offset <x> <y> <z>`, `/relic scale <factor>`, `/relic side left|right`,
  `/relic quality full|lite`.
* `/relic pulse` y `/relic release` lanzan las animaciones de una sola vez.
* Configuración en `config/holocore-client.toml` (estado inicial, efectos
  reducidos, calidad, lado del hombro, halo).

### Verificación de esta entrega

* `gradle build` con Gradle 8.8 / JDK 17 en CI: **verde**.
* `runClient` bajo xvfb sin GPU: **verde**; el mod registra su arranque y no
  aparece ningún *crash* en el log.
* El smoke test encontró y permitió corregir un fallo real: un evento del bus
  **FORGE** (`RegisterClientCommandsEvent`) estaba suscrito desde la clase del
  bus **MOD**, lo que abortaba la carga del mod.
* Los seis assets se comparan por SHA-256 con el zip v19 original en cada
  compilación, así que no pueden alterarse sin que el CI lo detecte.

### Notas de desarrollo

* Curios 5.14.1 publica su refmap de Mixin con nombres SRG; con mappings
  `official` y en entorno de desarrollo ese refmap no se remapea y el cliente
  falla en `AccessorEntity`. Los runs de `build.gradle` llevan
  `mixin.env.disableRefMap=true`; el jar publicado no lo necesita.
