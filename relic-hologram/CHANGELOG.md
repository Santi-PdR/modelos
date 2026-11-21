# Historial de cambios

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
