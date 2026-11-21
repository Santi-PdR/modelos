# Historial de cambios

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
