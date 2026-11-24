# Historial de cambios

## 1.0.48 — el eco del suelo deja de quemarse a blanco

El eco de 1.0.47 era **solo aditivo**: sobre nieve o arena sumaba a un fondo ya a 0.95
y el anillo salía blanco. Es el mismo fallo que tuvo el aura en 1.0.9–1.0.10, y esta vez
lo ha encontrado el comprobador de números antes que el ojo:

* **Pasa a llevar tinte debajo** (`TINT_GLOW`) y el aditivo baja de **0.42 a 0.12**, con la
  cobertura del tinte en 3× el aditivo. Resultado medido sobre los tres fondos: nieve
  `(0.86, 0.98, 1.00)` con tono +0.14, piedra +0.22 y cueva +0.22 — se lee del color del
  estado y no satura en ninguno.
* **`tools/check_aura_math.py` comprueba el eco como el aura**: decodifica también
  `relic_ring.png`, toma su píxel de más peso (el centro del anillo está vacío), compone
  tinte + aditivo sobre nieve, piedra y cueva y falla si se blanquea o pierde el tono.
  El CI ya lo ejecuta, así que el número queda atado al código.
* Los dos números salen de constantes leídas por el script (`GROUND_ADDITIVE` y
  `GROUND_TINT_BOOST`): antes buscaba un literal suelto y estaba midiendo la onda de
  choque (`flash * 0.55F * fade`), no el eco.
* 4 negativos probados en rojo: el eco de 1.0.47 (se quema), tinte flojo (pierde el tono),
  eco sin tinte y aditivo fuera de su constante.

## 1.0.47 — el eco en el suelo

* **En cada evento, el anillo se tumba en el suelo**: se dibuja con los ejes **X y Z de
  la pose** (los del portador) y baja por su **Y**, no por la de la pantalla. Un billboard
  más habría sido otro aro mirándote de frente; esto es una onda que golpea el suelo a tus
  pies y se abre de 0.32 a 1.15 bloques mientras el destello se apaga.
* **Solo en tercera persona.** En la vista previa no hay suelo debajo, así que ahí no se
  dibuja: se pasa un `onShoulder` explícito en vez de adivinar por la cámara.
* **Se apaga con `visuals.groundEcho`** (por defecto `true`). Es lo primero que hay que
  probar de este bloque: si sale como una tarjeta flotante, es un `/relic set groundEcho
  false` y te digo cómo lo arreglo con el dato.
* Cuesta **un quad** y solo mientras dura el destello: en reposo, cero.
* 29 claves de config. CI: 7 comprobaciones nuevas, con 3 negativos en rojo (eco que no se
  dibuja, eco colándose en la vista previa y eco con los ejes de la cámara).

## 1.0.46 — las chispas orbitan de verdad

La órbita de chispas iba a **0.75 rad/tick**, o sea **2,8 vueltas por segundo**: no se
veían cinco chispas, se veía un aro temblando. Era lo último que quedaba «nervioso» del
aura, y es de la misma familia que el fallo de unidades de 1.0.43 (nadie había escrito
en qué unidad estaba).

* **0.20 rad/tick**: 1,6 s por vuelta, que es lo que deja leer las cinco chispas, con su
  tamaño variable y la estela cuando te mueves.
* **`visuals.sparkSpeed`** (0–3, defecto 1.0) lo escala sin recompilar: `3` recupera
  exactamente la velocidad vieja, `0` las deja quietas en su sitio.
* La constante lleva escrito **en radianes por tick** en el comentario, con el mismo
  convenio que `SPIN`; es lo que faltaba para que no se mezclaran unidades otra vez.
* 28 claves de config. CI: 4 comprobaciones nuevas, con 3 negativos en rojo (velocidad
  vieja, órbita sin mando y rango de `sparkSpeed` cambiado).

## 1.0.45 — undécimo estado: congelándose, con copos

* **Estado nuevo `freezing`**: cuando `getTicksFrozen()` sube (nieve en polvo, agua
  helada) la reliquia pasa a **hielo pálido**, el bucle baja a **0.78×**, el vaivén se
  queda en 0.55 (el más quieto de los once) y el borde del shader baja a 0.90. El frío
  no acelera nada: lo apaga.
* **Manda sobre herido**, pero por detrás de ardiendo: las dos son daño lento, y si te
  estás quemando el fuego gana. El CI comprueba el orden de `getTicksFrozen()` contra
  el chequeo de vida.
* **Copos**: siete, diminutos, caen un cruce cada ~3,5 s con zigzag propio y se
  encienden al llegar abajo (al revés que las gotas, que se apagan). Es el único VFX
  más lento que la lluvia, y usa `seconds()` desde el primer día.
* Cuatro VFX de estado ya completos: burbujas (suben), gotas (caen rápido), brasas
  (suben parpadeando) y copos (caen en zigzag).
* 1 clave nueva por idioma (73 en cada uno). CI: 6 comprobaciones nuevas, con 3
  negativos en rojo (sin detección, copos que no se dibujan y copos en ticks).

## 1.0.44 — `/relic preset`: tres looks con nombre

El look no se puede decidir mirando números: hay 27 claves y las que mandan son seis.
* **`/relic preset soft|normal|showcase`** aplica de golpe ritmo, aura, halo, GLSL,
  anillo y destello. `soft` es flotado lento y discreto (`animSpeed` 0.5, aura 0.22),
  `normal` son los defectos y `showcase` es lo contrario: ritmo de fábrica, todo más
  alto y destello 1.2, para grabar o para ver los efectos.
* **No guarda**: se aplica en memoria, se compara y luego `/relic save`, igual que
  `/relic set`. Avisa de cuántas claves han cambiado de verdad y `/relic info` las
  marca como pendientes hasta guardarlas.
* Pasa por el mismo camino que `/relic set`, así que un valor fuera de rango se
  rechaza solo y no hay una segunda validación que se pueda quedar vieja.
* CI: los tres nombres comprobados, los 18 pares (3 × 6) tienen que ser claves reales
  de `TWEAKS`, y 3 negativos probados en rojo (clave inventada, preset que no valida y
  nombre cambiado). 72 claves de idioma.

## 1.0.43 — el fallo de unidades: es esto lo que hacía que saltara

El reloj de la reliquia son **ticks** (20 por segundo) y los efectos de 1.0.38–1.0.42
estaban escritos en «por segundo»: el número se usaba tal cual, así que todo salía
**veinte veces más rápido**. No era un tema de gusto, era un factor 20:

* **El vaivén del modelo** (1.0.31) era `sin(ticks × 1.7)`, o sea **5,4 Hz**: la
  reliquia temblaba cinco veces por segundo en el sitio. Eso es exactamente «salta en
  vez de flotar». Ahora flota con un ciclo de 3,7 s y se ladea cada 9 s.
* **Las gotas de lluvia** (1.0.38) cambiaban de sitio **22 veces por segundo**: no
  caían, parpadeaban. Ahora tardan ~0,9 s en cruzar.
* **Las brasas** (1.0.39) parpadeaban a **35 Hz** (invisible, se promediaba a gris) y
  subían en 1,5 s. Ahora parpadean a ~1,4 veces por segundo y suben en 1,5 s.
* **La onda de choque** (1.0.40) giraba a 7 rad/s; ahora a 0,35 rad/s.
* **Las burbujas** (1.0.33) subían 5,5 veces por segundo; ahora una cada 3,6 s, que es
  lo que hace una burbuja.
* Arreglado en un sitio: `seconds(ticks)` en `RelicAura`, y los efectos lo usan. CI
  comprueba el divisor y cada uso, con 4 negativos probados en rojo (vaivén, divisor,
  brasas y onda volviendo a los ticks).

Si con esto el reposo te sigue pareciendo rápido, el culpable ya no es el aura: es
`visuals.animSpeed` (o un monstruo cerca, que cambia el bucle a `idle_alert`).

## 1.0.42 — la tormenta relampaguea y `/relic vfx shock`

* **Relámpago de tormenta**: cada 5–11 s el estado `storm` pega un destello de 0.55,
  como el cielo. Es lo que separa "está lloviendo" de "hay tormenta" mirando la
  reliquia, y de paso abre la onda de choque de 1.0.40 sin que pase nada más: la
  tormenta pasa de ser un color a tener pulso. El contador se reinicia al salir del
  estado, para no heredar la espera de la tormenta anterior.
* **`/relic vfx shock [fuerza]`**: dispara el destello a mano (0.1–1, por defecto 0.6)
  y con él la onda de choque y el eco del anillo. Es la forma de ver el efecto sin
  esperar un pulso o un golpe, y de comparar una fuerza con otra.
* 1 clave nueva por idioma (69 en cada uno). CI: 7 comprobaciones nuevas, con 4
  negativos probados en rojo (tormenta sin destello, destello sin relámpago,
  contador sin reiniciar y `vfx` que no llama al destello).

## 1.0.41 — el flotado vuelve a ser lento y el shader deja de ser un aro

Dos fallos de percepción, contados con lo que se veía:

* **El reposo iba acelerado.** `idle` son 48 s de animación, pero el ritmo salía
  solo del estado de brillo y valía 1.0 para lo normal. Ahora la velocidad base la
  pone la config, `visuals.animSpeed`, por defecto **0.65**: la reliquia vuelve a
  flotar en vez de ir a saltos. El estado sigue multiplicando encima (herido 0.72,
  tormenta 1.32, ardiendo 1.40), y con `1.0` se recupera exactamente el ritmo de
  antes. Rango 0.25–2.0.
* **`/relic info` dice qué bucle suena y a qué ritmo** (`bucle idle 0.65x`). "Va muy
  rápido" no se podía comprobar: `idle` son 48 s, `idle_calm` 12 s e `idle_alert` 8 s,
  o sea que la alerta de un monstruo cercano cambia el bucle por uno seis veces más
  corto. Ahora se ve en una palabra.
* **Fuera el aro del shader.** El "barrido" era una banda de `smoothstep(0.40, 0.62)`:
  más de 20 cm de alto cruzando el modelo de lado a lado, que se leía como el anillo
  de un planeta. Ahora es una **línea de lectura** de 0.02 de ancho con un halo suave,
  y las dos se pesan por el alpha de la textura: existen sobre el cuerpo, no en el aire
  de la silueta.
* **Brillo corregido de raíz.** El rgb salía premultiplicado por alpha y el blend es
  `(srcalpha, one)`: o sea alpha², un borde débil compensado con ganancias altas, que
  es lo que hacía que brillara de más por el centro. Ahora el rgb va sin premultiplicar
  y las ganancias bajan a 0.16/0.24 y la silueta a 0.42/0.20: el borde se lee como
  contorno en vez de comerse el modelo.
* **Dither de suma.** `(hash − 0.5) * 0.03` restaba luz, y en aditivo el negativo lo
  recorta el framebuffer: no ditherizaba, solo moteaba. Ahora es `hash * 0.015`.
* **Rejilla más lenta** (60 rad/bloque y 0.010 de peso, antes 90 y 0.02): al caminar
  el patrón se corría 6 rad por tick y hervía.
* CI: 5 comprobaciones nuevas entre ritmo y shader, con 4 negativos probados en rojo
  (quitarlo del `speedFor`, devolver la banda ancha, volver a premultiplicar y volver
  al dither que resta). 27 claves de config.

## 1.0.40 — onda de choque en los eventos y estela en las chispas

* **Onda de choque**: en cada evento (pulso, golpe, liberación, subida de nivel) salen
  ocho partículas del núcleo, se abren de 0.16 a 0.62, giran mientras se abren y se
  apagan. **Sin estado propio**: el reloj es el propio destello (`t = 1 − flash`), así
  que no hay lista de partículas que mantener ni objetos que crear en el render — y en
  reposo, con el destello a cero, no cuesta ni un quad.
* **Estela de las chispas**: con el portador en movimiento (`motion > 0.35`) cada chispa
  deja una copia un poco atrás en su órbita, más apagada (42%) y más pequeña (72%).
  Parado no se dibuja: el coste aparece solo cuando hay movimiento que estelas.
* Las dos cosas son aditivas sobre el mismo lote del aura: el pase pasa de ~10 quads a
  ~18 en el peor caso (evento + corriendo + chispas), y a 0 en reposo quieto.
* El CI comprueba las tres que se pueden romper sin que se note: que la onda se dibuja,
  que su reloj es el destello (y no una variable a medias) y que la estela va detrás de
  la chispa y solo con movimiento. Probado en rojo las tres.

## 1.0.39 — décimo estado: ardiendo, con brasas

* **Estado nuevo `burning`**: si el portador está en llamas (fuego, lava, flechas de
  Fuego) la reliquia se pone **naranja de brasa** —el único estado cálido de los diez—,
  gira a **1.40×** (el más rápido), el vaivén es el más amplio después de la tormenta y
  el borde del shader sube a 1.05 (el único que pasa de 1).
* **Manda sobre todo**, herido incluido: es lo único de la lista de detección que te está
  haciendo daño mientras lo miras. El CI comprueba que `isOnFire()` va **antes** que el
  chequeo de vida, para que un refactor no lo devuelva abajo.
* **Brasas** en vez de chispas: seis que suben, se mecen poco y **parpadean** (cada una con
  su fase), encogiéndose y apagándose arriba. Sin el parpadeo suben como burbujas naranjas;
  con él, se lee fuego. Correr las aviva (×1.45). Mismo lote aditivo: cero draws nuevos.
* 1 clave nueva por idioma (68 en cada uno).

## 1.0.38 — la lluvia tiene gotas y los estados pueden pasar solos

* **VFX propio para la lluvia**: seis gotas cayendo alrededor de la reliquia, con viento
  lateral por fase, apagándose abajo. La lluvia es el estado que más tiempo se pasa
  encendido y con chispas en órbita se confundía con el reposo. Mismo lote aditivo y
  misma textura que las chispas: **cero draws nuevos**, y correr acelera la caída
  (×1.4) como si te llegara de lado.
* **`/relic mood cycle [segundos]`**: los nueve estados pasan solos cada N segundos (6 por
  defecto, 1–60) y `cycle 0` para. Avisa igual que la tecla M (barra de acción), así que
  al mirar una grabación se sabe qué estado es cada tramo. La ronda va por **ticks de
  cliente** y `/relic mood` la recuerda en una línea aparte: si no, el estado cambiaría
  solo y parecería un fallo.
* Los dos VFX de «estado» quedan simétricos: **burbujas que suben** bajo el agua y
  **gotas que caen** con lluvia, con el mismo código de base (`fract` + `billboardAt`).
* 2 claves nuevas por idioma (67 en cada uno).

## 1.0.37 — la reliquia reacciona a cómo te mueves

* **Energía de movimiento (0–1)**, un eje **aparte** de los nueve estados de brillo: el
  brillo dice *dónde* estás (tormenta, cueva, agua, portal) y esto dice *qué estás
  haciendo*. Se pueden dar a la vez, cosa que un estado nuevo no permitía: con tormenta
  y corriendo, el aura va azul **y** acelerada.
* **Qué mueve**: el anillo late ×1.7 (es lo que se ve de frente), las chispas barren
  ×1.45, el vaivén de flotado sube un 60% y nadando las burbujas suben ×1.5.
  **Agacharse** la lleva a 0.1: la reliquia se queda casi quieta contigo, que es el
  contraste que faltaba.
* **Suavizado con tiempo real** (τ 0,30 s, como el destello): correr y parar se ve como
  una transición y no como un salto por tick, y va igual a 30 que a 240 FPS.
* Se calcula en el tick del portador (`isSprinting`, `isSwimming`, `isCrouching` y la
  velocidad horizontal), no por frame, y no añade ni un draw: son multiplicadores sobre
  el aura que ya se dibujaba.

## 1.0.36 — la reliquia suena

* **Sonido propio**: al despertar, dormir y pulsar la reliquia del jugador local suena
  con **ametista de vanilla** (`amethyst_block.resonate` grave al despertar, más grave
  al dormir, `amethyst_block.chime` agudo en el pulso). El mod sigue sin traer ningún
  asset de audio.
* **Solo la reliquia propia nunca las ajenas**: cada portador vería (y oiría) su reliquia
  y las de los demás, y con cuatro jugadores cerca cada pulso sería un coro sin forma de
  saber de dónde viene. La comprobación es sobre el UUID del portador.
* **Suena en la cabeza y no en el hombro**: el hombro está a medio metro de la cámara y
  colocar ahí la fuente hace que el paneo salte al girar.
* **Dos claves nuevas**: `sound.events` (interruptor) y `sound.volume` (0–1, por defecto
  0.45). Se pueden probar en caliente con `/relic set`, como el resto. Va por
  `SoundSource.PLAYERS`, así que respeta el volumen de jugador del ajuste de sonido.
* El CI comprueba que solo suena la propia, que los sonidos son de vanilla, que se
  pueden apagar y que las tres llamadas siguen conectadas (probado en rojo cada una).

## 1.0.35 — noveno estado: portal, y las chispas se estiran

* **Estado nuevo `portal`**: con un portal del Nether, del End o de salida a menos de
  4 bloques la reliquia se pone violeta de obsidiana encantada, gira a 1.22× (el ritmo
  más nervioso de los nueve) y flota un poco más. Manda sobre la oscuridad, la lluvia
  y la noche; pierde con el agua, el herido y la tormenta.
* **El escaneo está cacheado**: mira 486 bloques **una vez por segundo** (no por tick) y
  con un `MutableBlockPos` reutilizable, porque un `BlockPos` por bloque escaneado
  serían 486 objetos por segundo y portador. El CI comprueba las dos cosas para que no
  se pierdan en un refactor.
* **Chispas estiradas**: con portal delante el recorrido gira 1.5× y el vaivén vertical
  se multiplica por 1.8, así que las chispas se alargan hacia arriba como el borde del
  portal en vez de quedarse en órbita redonda. El tinte del borde sube a 0.96.
* 1 clave nueva por idioma (65 en cada uno).

## 1.0.34 — la tecla M recorre los estados y `/relic mood list` los enseña

* **Tecla M** (`key.holocore.mood`, remapeable como la G y la P): pasa al siguiente
  estado de brillo —auto → neutral → oscuridad → lluvia → tormenta → herido →
  resonancia → noche → agua → auto— y lo dice en la **barra de acción**, no en el
  chat: con la tecla se pasan los ocho estados en unos segundos y nueve líneas de
  chat taparían justo lo que estás mirando.
* **`/relic mood next`** hace la misma ronda (comparten `cycleForcedMood`, para que no
  haya dos órdenes que se pisen) y **`/relic mood list`** saca los ocho nombres en una
  línea con el que manda marcado: en **oro** si está forzado, en **azul** si lo ha
  elegido la escena. Así se ve de un golpe si lo que miras es lo que pide el mundo.
* **Arreglo**: las sugerencias de `/relic mood` estaban escritas a mano y se habían
  quedado sin `night` ni `submerged` justo en las dos versiones que los añadieron. Ahora
  salen de `Mood.values()`, así que no se pueden quedar cortas otra vez; el CI exige
  que se generen del enum y falla si vuelven a ser una lista literal.
* 2 claves nuevas por idioma (64 en cada uno).

## 1.0.33 — octavo estado: bajo el agua, y burbujas

* **Estado nuevo `submerged`**: con los ojos dentro del agua la reliquia tira a verde
  azulado, el anillo se queda casi apagado, el bucle de animación baja a 0.66× (el más
  lento de los ocho) y el flotado a la mitad. Se detecta con
  `isEyeInFluid(FluidTags.WATER)`, que es vanilla: no hace falta estar entero dentro,
  basta con la cabeza. Manda sobre la luz y el tiempo; solo pierden con él herido y
  tormenta.
* **VFX propio: burbujas.** Primera vez que un estado cambia *qué* se dibuja y no solo
  el color: siete burbujas suben desde debajo de la reliquia, se mecen, crecen y se
  apagan al llegar arriba. Usan el mismo lote aditivo y la misma textura que las
  chispas, así que no hay pases nuevos ni draws extra; el ciclo sale de
  `fract(tiempo × 0.28 + i/7)` sin asignar nada.
* **El tinte del shader** tiene su rama (0.74): el borde se apaga porque el agua se
  lleva la luz. El comentario del `.fsh` y el apéndice del `BRILLO-Y-SHADERS.md` van
  sincronizados con `tools/sync_shader_doc.py`, como exige el CI.
* 1 clave nueva por idioma (62 en cada uno).

## 1.0.32 — séptimo estado: la noche despejada

* **Estado nuevo `night`**: con cielo encima, de noche y sin lluvia la reliquia se
  queda pálida y fría, gira a 0.85× y las chispas pasan a **flotar** a media
  velocidad, con la mitad de densidad y un tono de hielo. La detección usa
  `Level.isNight()`, que ya devuelve `false` en dimensiones con hora fija (Nether y
  End), así que allí no aparece nunca.
* **La oscuridad ahora exige estar encerrado**: antes bastaba con poca luz de bloque,
  y a cielo abierto de noche (luz de bloque 0) la reliquia se ponía en «oscuridad»
  aunque estuvieras viendo las estrellas. Ahora pide también menos de luz de cielo 8.
  Es lo que deja el hueco para `night`; en una cueva o bajo techo no cambia nada.
* **Al cambiar de estado la reliquia hace un glitch**, no solo un destello: reutiliza
  la animación y el uniform `HoloGlitch` del pulso. **Como mucho uno cada 6 s**: sin esa
  espera, caminar por el borde de una cueva o el paso de día a noche encadenaba
  animaciones de una sola vez y la reliquia parecía tiritar. No se añaden animaciones
  nuevas a propósito: los `.json` exportados están bloqueados por CI contra el zip del
  modelo (`Validate assets unchanged`), y una animación nueva se hace en Blockbench,
  no escribiendo keyframes a ciegas.
* **`/relic mood` no sobrevive a salir del mundo**: el estado forzado se suelta al
  desconectar, así que el siguiente mundo arranca en automático.
* **Dos claves de idioma que faltaban** (`neutral` y `night`): `/relic mood` con la
  reliquia en calma enseñaba `message.holocore.state.neutral` en crudo. 61 claves por
  idioma.
* **El CI exige los siete estados en cada `switch` sobre `Mood`**: un enum nuevo sin
  rama no compila (`NIGHT` se olvidó dos veces: el tinte del borde y la energía del
  flotado), y descubrirlo cuesta un build entero. La validación recorre los `.java`
  del cliente, extrae cada switch por llaves y, si no tiene `default`, exige los
  siete `case`. Probada en rojo quitando las dos ramas.

## 1.0.31 — la reliquia flota, se asienta y tiene tecla de pulso

* **Movimiento propio** (`RelicAura.applyAliveMotion`): el conjunto **flota** con un
  vaivén de 0.022 bloques, con la amplitud según el estado de brillo (tormenta 1.5×,
  resonancia 1.2×, herido 0.6×), y **se asienta** en cada evento achatándose un 4% y
  ensanchándose un 5% — eso es lo que da sensación de golpe. Se aplica al `PoseStack`
  antes del modelo y del aura, así que los dos se mueven juntos; el aura además lee
  la escala de la matriz, o sea que también se ensancha con los eventos.
* **Sin asignaciones**: el ladeo rota la matriz en el sitio
  (`poseStack.last().pose().rotateY`) en vez de `mulPose` con un eje, que crea un
  `Quaternionf` por reliquia y frame.
* **Tecla P para el pulso** (`key.holocore.pulse`, remapeable como la G): manda el
  mismo paquete que `/relic pulse`, así que se puede lanzar en mitad del combate sin
  escribir. Con lo de 1.0.29 se ve entero: eco del anillo, glitch del shader y
  achatado.
* 1 clave nueva por idioma (59 en cada uno).

## 1.0.30 — dos estados más, animación que cambia de ritmo y `/relic mood`

* **Dos estados de brillo nuevos**: `dark` (menos de luz de bloque 4: casi blanca y
  con bastante más aura, que en una cueva es la única luz que hay) y `rain` (llueve
  encima del portador sin tormenta: azul profundo y anillo más tenue). Ya son cinco,
  con prioridad herido > tormenta > oscuridad > lluvia > resonancia.
* **La animación cambia de ritmo con el estado**, no solo de color:
  `AnimationController.setAnimationSpeed` a 0.72× herido, 0.93× lluvia, 1.06×
  oscuridad, 1.18× resonancia y 1.32× tormenta. Se llama **solo al cambiar** de
  velocidad: ese método crea un lambda que captura el valor, y fijarlo cada tick
  serían 20 objetos por segundo y portador.
* **`/relic mood [estado]`**: enseña el estado de brillo que manda ahora y permite
  forzar uno (`storm`, `wounded`, `dark`, `rain`, `resonant`, `neutral`) o volver a
  automático con `auto`. Es la forma de ver la tormenta o el herido con un solo
  jugador y sin montar la escena.
* **Shader**: uniform `HoloTint`, que mueve el brillo del borde con el estado (1.08 en
  la oscuridad, 0.62 en lluvia). Antes el contorno se quedaba siempre con el mismo
  azul claro aunque el aura cambiara de color.
* **Chispas más eléctricas con tormenta**: tiran a azul en vez de heredar el blanco
  del estado, que se perdía sobre el aura.
* 5 claves nuevas por idioma (58 en cada uno).

## 1.0.29 — tres estados de brillo, chispas, eco de anillo y glitch en el shader

**Estados nuevos** (`RelicAnimatable.Mood`, aparte del ciclo de animación a
propósito: meterlos como `LoopState` obligaba a escribir transiciones para cada
pareja y una mal escrita deja el modelo en una pose que no toca). Solo cambian la
luz, y mandan en este orden: herido > tormenta > resonancia.

* **herido**: al portador le queda menos del 35% de vida. Color a rojo, aura +0.10,
  anillo +0.55 y giro más rápido.
* **tormenta**: truena donde está el portador. Azul casi blanco, aura +0.15, anillo
  +0.25.
* **resonancia**: otro portador a menos de 12 bloques. Violeta, aura +0.12, anillo
  +0.35. Se comprueba cada 20 ticks, no cada tick, y mira la reliquia del otro
  (Curios en cliente) además de si su visual está dibujado.
* Al cambiar de estado de brillo la reliquia da un destello corto, y `/relic info`
  lo dice en una línea aparte: si el aura se pone roja no hay que adivinar por qué.

**VFX nuevos**, los dos sin geometría nueva y sumando al lote aditivo que ya está
abierto:

* **Chispas en órbita**: cinco quads que giran en el plano de la cámara, con radio y
  altura distintos por chispa y heredando el sentido de giro del estado. Se saltan
  en `lite` y con `reducedEffects`, como el halo.
* **Eco del anillo**: en cada evento (pulso, golpe, liberación, cambio de estado) sale
  un anillo más grande que se abre y se apaga con el destello. Un fogonazo pasa a
  leerse como una onda.

**Shader**: uniform nuevo `HoloGlitch`, que el renderer rellena con
`min(1, flash × 1.5)`. Con glitch, la UV se parte por bandas horizontales y los
canales R y B se separan. La condición es sobre un uniform, así que sin evento se
sigue muestreando la textura una vez; con evento, tres.

CI: paso nuevo `Validate moods and vfx` (los tres estados con su texto en los dos
idiomas, la detección de cada uno, chispas, eco y el glitch cableado) y
`Validate shader resources` exige `HoloGlitch` en el JSON y la rama en el fragment.

## 1.0.28 — segunda vuelta al shader y dos pases menos donde no se ven

**Shader** (`holocore_relic_glow`), cuatro cambios, todos con motivo:

* **Dos bordes de silueta en vez de uno.** `edge²` tiñe la cara y `edge⁴` se queda
  pegado al canto, y ese canto se va al violeta (35%): la silueta tiene dos tonos
  y se lee como contorno de holograma. Los dos se calculan multiplicando, no con
  `pow`; dos `pow` por píxel para esto era gastar de más y además el corte del
  borde queda más limpio.
* **El barrido deja de repetirse por cara.** Iba sobre `UV0`, y en un modelo de 98
  huesos cada cara trae sus propias UV: en vez de una banda que recorre la
  reliquia salían cuatro por cara. Ahora el vértice pasa `viewY` (la altura en
  espacio de vista) y la banda sube por la reliquia entera, un ciclo cada 4 s.
* **La rejilla fina, igual:** anclada a `viewY`, las líneas siguen de una cara a
  otra en vez de pelearse entre caras al girar la cámara. Baja de 160 a 90 ciclos,
  que a distancia hacía muaré.
* **El borde respira** (`0.85 + 0.15·sin(t·1.6)`) y el núcleo no. El dither sigue
  sin tiempo dentro a propósito: animado deja de romper el banding y se ve hervir.

**Optimización**: en la banda de desvanecido (los últimos 8 bloques antes de
`maxRenderDistance`) el halo y el pase GLSL se saltan. Son dos recorridos más de
los 977 cubos y a esa opacidad se ven como un píxel borroso: una reliquia lejana
cuesta **2 pases en vez de 4**. Se ve en `/relic stats` como menos «pases por
dibujo».

CI: `Validate shader resources` fija las decisiones anteriores (barrido en
espacio de vista, `viewY` en el vértice, cero `pow` en el fragment, apéndice
sincronizado) y `Validate render path allocations` exige la banda de desvanecido.

## 1.0.27 — la vista previa deja de tapar la mirilla

* **`/relic preview` dibujaba la reliquia justo en el centro de la pantalla**, así
  que tapaba la mirilla y lo que estuvieras apuntando — que es justo lo que se
  quiere ver detrás para juzgar el brillo. Ahora va desplazada a la derecha y un
  poco por debajo, siguiendo los ejes de la cámara (al levantar la vista sigue
  abajo, no se queda flotando en el aire).
* El desplazamiento se da en **tangentes** (0.30 de lado, 0.17 hacia abajo, o sea
  16.7° y 9.6°), multiplicadas por la distancia: el encuadre es el mismo a 0.5
  que a 6 bloques. Con el aura de 1.10 bloques de diámetro, su borde se queda a
  ~4.6° del centro a la distancia por defecto, así que la mirilla queda libre.
* CI: `Validate local relic tick` falla si la vista previa vuelve a colocarse con
  solo el vector de mirada.

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
