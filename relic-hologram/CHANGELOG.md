# Historial de cambios

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
