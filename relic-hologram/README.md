# Holographic Core / Núcleo Holográfico

Reliquia cosmética para **Minecraft 1.20.1 / Forge**: un núcleo holográfico de luz
azul que flota sobre un hombro del portador, con estelas orbitales, esfera
armilar, cristales y efectos intermitentes. Se equipa en el slot **`charm`** de
Curios y se anima con GeckoLib 4.

| Pieza | Versión verificada |
|---|---|
| Minecraft | 1.20.1 |
| Forge | 47.4.0 (rango `[47.4,)`) |
| Java | 17 |
| GeckoLib | **4.8.1** (`geckolib-forge-1.20.1-4.8.1`, Modrinth `bVtfWE8S`) |
| Curios API | **5.14.1+1.20.1** (última build para Forge 1.20.1) |
| modid | `holocore` |

GeckoLib y Curios son **dependencias obligatorias**: el ítem implementa
`ICurioItem` y el render usa `ICurioRenderer` + `GeoObjectRenderer`. Sin Curios
el ítem no tendría slot y sin GeckoLib no hay modelo.

## Compilar

```bash
cd relic-hologram
./gradlew build          # o: gradle build
# -> build/libs/holocore-1.0.0.jar
```

El workflow `.github/workflows/holocore.yml` hace lo mismo en CI y, antes de
compilar, valida que:

* los seis assets (geo, geo lite, dos animaciones y dos texturas) son
  **byte a byte** los del zip `reliquia_holografica_para_mod_v19.zip`;
* todos los JSON son válidos y no contienen `null` (GeckoLib 4.8 lanza
  `UnsupportedOperationException` con un `"parent": null`);
* están las 20 animaciones, las capas solo tocan `relic_react`, y los .geo de
  calidad full/lite declaran los mismos 98 huesos;
* `RelicAnimations.java` coincide con `tools/relic_manifest.json`
  (`python3 tools/gen_relic_constants.py --check`).

Cambios por versión: [CHANGELOG.md](CHANGELOG.md).

Para publicar el jar como Release: ejecutar el workflow a mano con
`publicar = true`, o un push cuyo mensaje contenga **`[publicar-holocore]`**.

> La palabra clave es exclusiva de este mod a propósito: `.github/workflows/`
> `build.yml` (el workflow viejo de *Mantle of the Blight Star* / `capatest`)
> también publica cuando ve `[publicar]` en el mensaje, así que reutilizarla
> desde aquí re-subía la release `v1.28.0` del otro mod.

## Probar en el juego

`./gradlew runClient` arranca un cliente de desarrollo con GeckoLib y Curios.

> El CI lanza ademas `runClient` bajo xvfb (sin GPU): comprueba que el mod
> construye, que Curios registra el renderer y que el cliente no cae. Ese test
> ya encontro un fallo real (un evento del bus FORGE registrado en el bus MOD).
>
> **Nota de dev:** Curios 5.14.1 trae su refmap de Mixin con nombres SRG
> (`f_19803_` = `Entity.firstTick`); con mappings `official` y en entorno de
> desarrollo ese refmap no se remapea y el arranque falla en `AccessorEntity`.
> Por eso los runs de `build.gradle` llevan `mixin.env.disableRefMap=true`. No
> afecta al jar publicado (ahí el refmap SRG es el correcto).

En el juego:

* `/give @s holocore:holographic_core` o la pestaña creativa **Holographic Core**;
* receta: amatista arriba y abajo, dos cristales y un diamante en el centro;
* equipar en el slot **charm** del inventario de Curios (tecla por defecto: `C`).

### Teclas y comandos

| Acción | Cómo |
|---|---|
| Despertar / dormir | tecla **G** o `/relic toggle` |
| Pulso de energía | `/relic pulse` |
| Liberación total | `/relic release` |
| Afinar posición | `/relic offset <x> <y> <z>` (píxeles de modelo) |
| Afinar escala | `/relic scale <0.1–4.0>` |
| Cambiar de hombro | `/relic side left\|right` |
| Calidad (full/lite) | `/relic quality full\|lite` |
| Ver valores actuales | `/relic info` |

Los comandos de ajuste son de **cliente** y cambian la config en memoria al
instante (no la guardan): cuando el núcleo quede donde quieres, copia los
números de `/relic info` a `config/holocore-client.toml`. `pulse`, `release` y
`toggle` sí viajan al servidor, para que el resto de jugadores vea lo mismo.

## Brillo y shaders

Los pases normal y emisivo usan `entityTranslucentEmissive` con el lightmap a
tope (`FULL_BRIGHT`), que es justo lo que los shaderpacks (Iris/Oculus/OptiFine +
Complementary, BSL…) usan para detectar emisivos y aplicar su bloom. Encima hay
un tercer pase con **blend aditivo**: suma luz en vez de mezclarla, así que el
núcleo brilla también sin shaderpack.

La **aura** son tres billboards (quads que miran a cámara) con la textura
`relic_aura.png`, girando a distinta velocidad, sumados con el mismo blend
aditivo. Eso da el resplandor alrededor del núcleo sin tocar la pantalla y sin
depender del pack; la textura se genera con `tools/make_aura.py`.

Lo que **no** hace: post-proceso de pantalla (caro y se pelea con los packs) ni
un `.fsh` propio (con shaderpack acaba en el fallback del pack o invisible). El
razonamiento completo, el código del shader que sí se podría usar y su
compatibilidad están en [BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md).

## Configuración (`config/holocore-client.toml`)

| Clave | Defecto | Qué hace |
|---|---|---|
| `placement.shoulder` | `RIGHT` | Hombro; `LEFT` espeja el eje X. |
| `placement.offsetX` | `6.0` | Lateral en px de modelo (1 px = 1/16 bloque). |
| `placement.offsetY` | `-6.0` | Vertical en px; **Y+ es abajo**, así que `-6` sube 6 px. |
| `placement.offsetZ` | `8.0` | Hacia atrás en px (Z+ = espalda). |
| `placement.scale` | `1.0` | Escala global (el modelo mide ~11 px). |
| `visuals.quality` | `FULL` | `LITE` usa el .geo de 751 cubos y `idle_calm` en reposo. |
| `visuals.glowLayer` | `true` | Segundo pase emisivo (la textura `_glowing`). |
| `visuals.glowHalo` | `true` | Tercer pase con blend **aditivo** (suma luz). Se omite en `LITE` y con `reducedEffects`. |
| `visuals.haloIntensity` | `0.35` | Fuerza del halo aditivo (0–1). |
| `visuals.glowAura` | `true` | Aura: tres billboards aditivos alrededor del núcleo. |
| `visuals.auraIntensity` | `0.55` | Fuerza del aura (0–1). |
| `visuals.reducedEffects` | `false` | Reposo sin rayos/cometas/ondas (`idle_calm`). |
| `visuals.maxRenderDistance` | `32` | Distancia para dibujar la reliquia de otros jugadores. |
| `visuals.glitchMinSeconds` / `glitchMaxSeconds` | `20` / `60` | Intervalo del glitch aleatorio (solo en reposo). |
| `visuals.alertRadius` | `12` | Radio en el que un monstruo activa `idle_alert`. |
| `visuals.combatHoldTicks` | `80` | Ticks en estado cargado tras el último golpe. |

Los offsets se aplican en el espacio del hueso `body` del jugador (origen en el
torso/cuello, Y+ abajo, Z+ espalda), no en el origen de los pies. Por eso el
`.geo.json` centrado es el correcto: el anclaje al hombro lo pone el código y no
hay que sumar la traslación que traía `relic_hologram.geo.json`.

## Qué hace exactamente

* **Equipar** → `activation` → `idle` (bucle). Al cambiar de calidad o al
  re-equipar tras 2 s sin renderizarse, vuelve a empezar.
* **Desequipar** → deja de renderizarse. La `deactivation` **no** se puede ver al
  desequipar: Curios deja de llamar al renderer en el mismo tick, así que no hay
  dónde dibujarla. Sí se ve al pasar a dormido (`deactivation`, o `sleep` si el
  cambio es reciente).
* **Combate** (recibir un golpe o atacar, deducido de `hurtTime`/`swing`, sin red)
  → `charge_up` → `idle_charged` → `charge_down`.
* **Alerta** (monstruo a menos de `alertRadius`, escaneo cada 10 ticks) →
  `alert_up` → `idle_alert` → `alert_down`.
* **Golpe** → `hit` en el controlador de estado **y** `layer_hit` en el segundo
  controlador (solo `relic_react`).
* **Subir de nivel** → `layer_bump`. **Comando** → `energy_pulse` / `release`.
* **Glitch** aleatorio solo en reposo, cada 20–60 s.
* Transiciones de 6 ticks (el manifiesto recomienda 4–8) y dos
  `AnimationController` simultáneos: `state` (bucles + acciones) y `layer`
  (solo `layer_*`), para que las capas no pisen los giros.

## Brillo y shaders

El modelo se dibuja dos veces con `RenderType.entityTranslucentEmissive`:

1. textura base (`relic_hologram.png`, incluye el aura tenue);
2. textura emisiva (`relic_hologram_glowing.png`, sin el aura, para no sumarla
   dos veces).

Ese `RenderType` usa el shader emisivo de vanilla (sin término difuso por normal)
y se le pasa `LightTexture.FULL_BRIGHT`, así que **se ve igual de noche, en
cuevas, bajo el agua y con la antorcha apagada**. No hay ninguna dependencia de
shaders.

* **Iris/Oculus:** al ser `RenderType` de entidad estándar, los shaders lo tratan
  como cualquier entidad translúcida: sigue siendo fullbright, pero el paquete de
  shaders puede aplicarles bloom propio o teñirlo con su grading. No hay
  uniforms propios que puedan romperse.
* **Bloom real opcional:** si instalas un mod de post-proceso (p. ej. un shader
  con bloom), la textura emisiva ya alimenta ese bloom. No se integra ningún mod
  de bloom de forma obligatoria.
* **Sombreado:** al usar el shader emisivo, el núcleo no recibe sombra de caras;
  lo que se ve es el brillo de la textura, no el `lightmap`.
* Si en tu equipo el doble pase pesa demasiado, `glowLayer=false` deja solo el
  pase base (que ya es fullbright).

## Notas sobre los assets (sin modificarlos)

* Se usan `relic_hologram_centered.geo.json`, `relic_hologram_lite_centered.geo.json`
  y `relic_hologram.animation.json` (formato 1.8.0, con `catmullrom`: GeckoLib
  4.8.1 lo soporta). `relic_hologram.animation.linear.json` se incluye en el jar
  como alternativa documentada, pero no se carga.
* `relic_hologram.geo.json` (anclado al hombro) **no** se usa en el mod, tal como
  pide el manifiesto.
* GeckoLib 4.8.1 llama a su máscara emisiva `_glowmask`, no `_glowing`, y además
  **borra del pase base** los píxeles marcados en la máscara. Con
  `relic_hologram_glowing.png` (que es casi todo el atlas) el modelo base quedaría
  vacío, así que se implementa el brillo con dos pases emisivos en vez de
  `AutoGlowingGeoLayer`. La textura entregada se usa tal cual, sin renombrar.
* El modelo es de 977 cubos (751 en lite) y se renderiza en dos pases: ~11 700
  quads por reliquia y frame en calidad full. `maxRenderDistance` y
  `quality=lite` son las dos palancas de rendimiento; el escaneo de alerta va
  cada 10 ticks y el glitch es un contador, no un cálculo por frame.

## Checklist de pruebas

- [ ] `./gradlew build` produce `holocore-1.0.0.jar` y `/relic info` responde.
- [ ] Creativo: aparece en la pestaña *Holographic Core* y en la búsqueda.
- [ ] Receta de crafteo correcta (amatista + cristales + diamante).
- [ ] Equipar en `charm` → `activation` y luego `idle` en bucle.
- [ ] Desequipar → desaparece; re-equipar → vuelve a activarse.
- [ ] Tecla G y `/relic toggle` → `deactivation`/`idle_dormant` y vuelta.
- [ ] `/relic pulse`, `/relic release`, subida de nivel (`layer_bump`).
- [ ] Recibir daño → `hit` + `layer_hit`; monstruo cerca → `idle_alert`.
- [ ] Agacharse (sneak) y girar el cuerpo: el núcleo acompaña al torso sin saltos.
- [ ] Primera persona: no tapa la vista.
- [ ] Multijugador: otro jugador lo ve, también tras su login; el estado
      despierto/dormido coincide en ambos clientes.
- [ ] Noche, cueva y agua: sigue luminoso.
- [ ] Sin shaders y con Iris/Oculus: sin errores en el log y sin desaparición.
- [ ] `quality=lite` y `glowLayer=false` no rompen las animaciones.
- [ ] Distancia > `maxRenderDistance`: deja de renderizarse (sin tirones).
- [ ] `/relic offset 6 -6 8`, `/relic scale 1.0`, `/relic side left|right` mueven
      el núcleo en caliente y `/relic info` muestra los valores para la config.

## Estructura

```
relic-hologram/
├── build.gradle, settings.gradle, gradle.properties, gradlew
├── tools/                      # generador de constantes, icono, manifiesto
└── src/main/
    ├── java/com/santipdr/holocore/
    │   ├── HoloCore.java                 # @Mod, GeckoLib.initialize, config, red
    │   ├── common/                       # item, registro, creativo, autoridad servidor
    │   ├── client/                       # renderer Curios, GeckoLib, estados, tecla, comandos
    │   ├── config/RelicConfig.java
    │   └── network/                      # dos paquetes: acción y estado
    └── resources/
        ├── META-INF/mods.toml, pack.mcmeta
        ├── assets/holocore/{geo,animations,textures/relic,textures/item,models,lang}
        └── data/{curios/tags/items/charm.json,holocore/recipes/holographic_core.json}
```
