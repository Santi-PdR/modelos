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
| GeckoLib | **4.8.1** compilado (`geckolib-forge-1.20.1-4.8.1`, Modrinth `bVtfWE8S`); el `mods.toml` acepta `[4.8.1,)`, así que 4.8.4 también vale |
| Curios API | **5.14.1+1.20.1** (última build para Forge 1.20.1) |
| modid | `holocore` |

GeckoLib y Curios son **dependencias obligatorias**: el ítem implementa
`ICurioItem` y el render usa `ICurioRenderer` + `GeoObjectRenderer`. Sin Curios
el ítem no tendría slot y sin GeckoLib no hay modelo.

## Compilar

```bash
cd relic-hologram
./gradlew build          # o: gradle build
# -> build/libs/holocore-<mod_version>.jar  (la versión sale de gradle.properties)
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
  (`python3 tools/gen_relic_constants.py --check`);
* el tono del aura sobre nieve, piedra y cueva se comprueba con números
  (`tools/check_aura_math.py`), no a ojo;
* el JSON del shader propio es coherente (blend aditivo, `count` de cada uniform,
  atributos dentro de `NEW_ENTITY`) y todas las claves de la config están
  documentadas en la tabla de abajo;
* el shader **compila de verdad**: el arranque del cliente tiene que dejar
  `Shader del aura compilado` en el log, o el build falla.

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
| Ver valores actuales | `/relic info` (tres líneas: placement, estado en vivo y brillo) |
| Probar una animación | `/relic anim <nombre>` · `/relic anim list` |
| Ajustar cualquier clave | `/relic set` (lista) · `/relic set <clave> <valor>` |
| Guardar los ajustes | `/relic save` |
| Volver a los valores de fábrica | `/relic reset` · `/relic reset <clave>` (una sola) |
| Ver la reliquia de cerca | `/relic preview` · `/relic preview <0.5–6>` (bloques) |
| Medir el coste | `/relic stats` · `/relic stats reset` |

Los comandos de ajuste son de **cliente** y cambian la config en memoria al
instante (no la guardan): cuando el núcleo quede donde quieres, copia los
números de `/relic info` a `config/holocore-client.toml`. La segunda línea de
`info` dice lo que no se puede adivinar mirando: estado del bucle (`charged`,
`alert`…), destello actual, por qué el pase GLSL está apagado si lo está
(`shaderGlow=false`, shaderpack activo o no compiló) y las intensidades que están
mandando ahora mismo.

`/relic anim` reproduce cualquiera de las 20 animaciones por su nombre corto
(`/relic anim layer_shake`, `/relic anim release`, `/relic anim idle_calm`…), así
que se pueden revisar todas sin depender de que un mob te pegue o de esperar a que
salga una variación de reposo. Las de bucle se reproducen una vez.

`/relic stats` mide lo que no se ve. Dice cuántos **pases por dibujo** se están
emitiendo (1 si solo queda el pase base, 4 con base, emisivo, halo y GLSL),
cuántos dibujos por segundo y cuántos **milisegundos** cuesta una reliquia por
dibujo, separando modelo y aura. Es la forma de comprobar en tu máquina lo de
1.0.16 (una evaluación de animación por frame en vez de cuatro) —comparar con
1.0.15 en el mismo sitio es la prueba— y de decidir si hace falta `quality=lite`,
`glowHalo=false` o bajar `maxRenderDistance`: mira el número, cambia la palanca,
vuelve a mirar. `/relic stats reset` reinicia la media.

`/relic set` ajusta **cualquiera** de las claves de la tabla de configuración en
caliente, sin cerrar el juego: `/relic set` sin argumentos lista las 22 claves con
su valor actual, `/relic set auraIntensity 0.55` la cambia y te dice el
valor nuevo (vale el nombre completo o el corto, siempre que no sea ambiguo). Todo es **en memoria** mientras
pruebas, igual que con `/relic offset`: cuando el número te guste, **`/relic save`**
lo escribe en `config/holocore-client.toml`. Mientras haya valores sin guardar,
`/relic info` añade una línea amarilla diciendo cuántos son, para que no se
queden en el aire al cerrar el juego. Las dos únicas claves sin pasar por
`set` son `placement.shoulder` y `visuals.quality`, que tienen su propio comando
(`/relic side`, `/relic quality`) porque además validan el texto — y también
cuentan como cambios sin guardar.

`/relic reset` devuelve las **24** claves a lo que trae la config de fábrica, también
en memoria: si el resultado te gusta, `/relic save`; si no, cierra sin guardar y el
archivo sigue como estaba. Solo cuenta —y solo marca como sin guardar— las claves que
de verdad estaban en otro valor; si ya estaba todo de fábrica, lo dice y no toca nada.
Con una clave delante (`/relic reset auraIntensity`) vuelve solo esa, que es el deshacer
de un experimento suelto sin perder los demás ajustes.

`/relic set` sin argumentos lista las 22 claves con su valor actual y marca con `*` las
que no están guardadas todavía, así se ve de un vistazo qué se pierde al cerrar.

`/relic preview` dibuja **tu** reliquia delante de la cámara, a una distancia fija
(2.5 bloques por defecto; `/relic preview 1.5` la acerca), con los mismos cuatro
pases y el mismo aura. Es para mirar el brillo siempre igual y sobre cualquier
fondo —nieve, arena, cueva— sin depender de dónde caiga el hombro ni de ponerse en
tercera persona: el estado sigue siendo el real (si te pegan, se pone cargada), y
la vista previa se apaga sola al salir del mundo.

`pulse`, `release` y
`toggle` sí viajan al servidor, para que el resto de jugadores vea lo mismo. El
estado se replica solo a quien puede verlo (misma dimensión, ≤64 bloques; quien
se acerque después lo recibe al empezar a trackear), y el servidor ignora más de
una acción cada 4 ticks por jugador, así que un cliente modificado no puede
inundar la red.

## Brillo y shaders

Los pases normal y emisivo usan `entityTranslucentEmissive` con el lightmap a
tope (`FULL_BRIGHT`), que es justo lo que los shaderpacks (Iris/Oculus/OptiFine +
Complementary, BSL…) usan para detectar emisivos y aplicar su bloom. Encima hay
un tercer pase con **blend aditivo**: suma luz en vez de mezclarla, así que el
núcleo brilla también sin shaderpack.

Los dos pases emisivos llevan `LightTexture.FULL_BRIGHT`, así que el núcleo **se ve
igual de noche, en cuevas, bajo el agua y con la antorcha apagada**, con y sin
shaderpack. Si el coste molesta: `glowLayer=false` deja solo el pase base (que ya
es fullbright), `glowHalo=false` quita el halo y `shaderGlow=false` el GLSL.

La **aura** son tres billboards (quads que miran a cámara) con la textura
`relic_aura.png`, girando a distinta velocidad, sumados con el mismo blend
aditivo. Eso da el resplandor alrededor del núcleo sin tocar la pantalla y sin
depender del pack; la textura se genera con `tools/make_aura.py`.

Desde 1.0.11 el aura está **pegada al núcleo**: 0.62 / 0.85 / 1.10 bloques de
diámetro (antes 1.05 / 1.55 / 2.10, o sea cuatro veces el tamaño del modelo),
pesos 0.30 / 0.17 / 0.09 y alpha de quad 0.55. El motivo está explicado en
[BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md) §3.B: con blend aditivo, sumar
mucho sobre un fondo claro satura los tres canales y el aura se ve **blanca**
aunque el tinte sea azul. Es lo que pasaba sobre nieve hasta 1.0.10.

Desde 1.0.12 el aura son **dos pases** de los mismos tres quads: uno de **tinte**
(mezcla normal con el color del estado) y encima el **aditivo** del brillo. El aditivo
solo puede aclarar, así que sobre nieve siempre acaba en blanco; el pase de tinte
es el que conserva el color del estado. Se apaga con `auraTint=false` si prefieres
solo el brillo.

El **anillo de estado** (`relic_ring.png`, generado con `tools/make_ring.py`) es
un cuarto billboard que solo aparece cuando la reliquia tiene algo que contar
(1.15 bloques: apenas por fuera del aura, para que se lea como anillo y no como
un borde más), y tanto el anillo como el aura cambian de color con el estado:

| Estado | Color | Aura | Anillo |
|---|---|---|---|
| `idle` | azul frío | 1.0 | tenue, giro lento |
| `idle_calm` | azul apagado | 0.7 | no sale |
| `idle_charged` | ámbar | 1.15 | marcado, giro rápido |
| `idle_alert` | rojo | 1.05 | late como un aviso, gira al revés |
| `idle_dormant` | gris azulado | 0.35 | no sale |

Los cambios **no saltan**: `RelicGlowState` interpola color (≈0.30 s) y
fuerza/giro (≈0.22 s) por portador y con el tiempo real entre frames, así que se
ve igual a 30 que a 240 FPS. El giro del anillo pasa por cero al cambiar de
sentido en vez de invertirse de golpe, y el anillo se desvanece al entrar en
calma o dormido. Ese mismo factor multiplica el halo y el pase GLSL del modelo,
así que dormida se atenúa **todo** el brillo a la vez y cargada se intensifica,
en vez de quedar el aura apagada y el modelo a tope.

El **shader propio** (`visuals.shaderGlow`) añade un cuarto pase con dos bordes
de silueta (uno suave y otro pegado al canto, este último con un desvío al
violeta), una banda que sube por la reliquia entera, rejilla fina de holograma que
respira y un grano mínimo, en GLSL de verdad
(`assets/minecraft/shaders/core/holocore_relic_glow.{json,vsh,fsh}`). Se compila
en cada recarga de recursos y **se desactiva solo si hay shaderpack activo**
(Iris/Oculus/OptiFine): esos packs sustituyen el programa y la reliquia podría
quedar invisible. Con pack puesto sigues teniendo halo + aura + el bloom del
propio pack.

Dos detalles que hacen que el borde se vea siempre:

* el borde se calcula con la **posición** del vértice (la reliquia está centrada
  en el origen del modelo), no solo con la normal, así que no depende de que el
  modelo traiga normales correctas;
* el borde entra también en la **alpha**, así que la silueta brilla aunque la
  textura emisiva sea transparente justo ahí.

El tono del halo, del borde y del pase GLSL es un **cuarto** del color del estado
(tres cuartos de azul frío de núcleo), así que cargada tira a ámbar y alerta a rojo
sin dejar de leerse como holograma.

El **destello de evento** (`visuals.flashIntensity`) es lo que hace que la
reliquia *conteste*: cuando llega un pulso, una liberación, un golpe recibido o
una subida de nivel, el anillo se enciende (aunque el estado no lo tuviera) y el
brillo sube un poco; todo se apaga solo en ~0,4 s. Desde 1.0.11 el destello es
**discreto a propósito**: afecta sobre todo al anillo (una línea) y apenas al
aura y al halo, y ya **no** se dispara al despertar, dormir ni cambiar de estado
— eso era lo que producía un fogonazo blanco justo al entrar al mundo.

Lo que **no** hace: post-proceso de pantalla (caro y se pelea con los packs). El
razonamiento completo, la matriz de compatibilidad y los detalles de la API de
shaders de 1.20.1 están en [BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md).

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
| `visuals.haloIntensity` | `0.25` | Fuerza del halo aditivo (0–1). Por encima de 0.4 se ve mancha blanca sobre nieve. |
| `visuals.glowAura` | `true` | Aura: tres billboards aditivos alrededor del núcleo. |
| `visuals.auraIntensity` | `0.32` | Fuerza del aura (0–1). Es aditiva: sobre fondo claro suma hacia blanco. |
| `visuals.auraTint` | `true` | Pase de tinte (mezcla normal) del aura: es lo que da color sobre nieve/arena. |
| `visuals.glowRing` | `true` | Anillo de estado (gira y se tiñe según la reliquia). |
| `visuals.ringIntensity` | `0.60` | Fuerza del anillo (0–1). |
| `visuals.flashIntensity` | `1.0` | Destello al ocurrir algo (pulso, liberación, golpe, nivel, despertar). `0` lo apaga. |
| `visuals.shaderGlow` | `true` | Pase GLSL propio (dos bordes de silueta + banda de barrido + rejilla). Se apaga solo con shaderpack activo. |
| `visuals.shaderIntensity` | `0.35` | Fuerza del pase GLSL, independiente del halo. |
| `visuals.reducedEffects` | `false` | Reposo sin rayos/cometas/ondas (`idle_calm`). |
| `visuals.maxRenderDistance` | `32` | Distancia para dibujar la reliquia de otros jugadores (se apaga en los últimos 8 bloques). |
| `visuals.idleVariations` | `true` | Variaciones propias en reposo (temblor, glitch, pulso). `false` = solo glitch. |
| `visuals.glitchMinSeconds` / `glitchMaxSeconds` | `20` / `60` | Intervalo entre variaciones de reposo. |
| `visuals.alertRadius` | `12` | Radio en el que un monstruo activa `idle_alert`. |
| `visuals.combatHoldTicks` | `80` | Ticks en estado cargado tras el último golpe. |

Desde 1.0.20 todas estas claves (menos `placement.shoulder` y `visuals.quality`,
que tienen `/relic side` y `/relic quality`) se pueden probar en caliente con
`/relic set <clave> <valor>`; el archivo no se modifica hasta que lanzas
`/relic save`, que escribe en él lo que haya en memoria (1.0.21). El CI comprueba que la tabla de `/relic set` y esta tabla
tienen las mismas claves y los mismos rangos que `RelicConfig`.

Los offsets se aplican en el espacio del hueso `body` del jugador (origen en el
torso/cuello, Y+ abajo, Z+ espalda), no en el origen de los pies. Por eso el
`.geo.json` centrado es el correcto: el anclaje al hombro lo pone el código y no
hay que sumar la traslación que traía `relic_hologram.geo.json`.

## Qué hace exactamente

* **Equipar** → `activation` → `idle` (bucle). Al cambiar de calidad, o al volver
  a ver a **otro** portador tras 2 s fuera de pantalla, vuelve a empezar.
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
* **Variaciones de reposo** (`visuals.idleVariations`): estando quieta y despierta,
  la reliquia hace cosas sola cada 20–60 s, elegidas por peso — `layer_shake`
  (35%), `glitch` (30%), `layer_bump` (20%), `energy_pulse` (12%) y `release`
  (3%). Con `idleVariations=false` vuelve a hacer solo el glitch. El intervalo se
  ajusta con `glitchMinSeconds` / `glitchMaxSeconds`.
* Transiciones de 6 ticks (el manifiesto recomienda 4–8) y dos
  `AnimationController` simultáneos: `state` (bucles + acciones) y `layer`
  (solo `layer_*`), para que las capas no pisen los giros.
* **Se actualiza aunque no se dibuje** (1.0.19). En primera persona Curios no
  llama al renderer, así que la máquina de estados se movía solo en tercera: sin
  alerta, sin variaciones de reposo, `/relic info` sin estado y el visual podado
  a los 40 ticks — al volver, la reliquia arrancaba de cero con su `activation`.
  Ahora el cliente actualiza la reliquia del jugador local en cada tick. El
  estado queda vivo y las animaciones que habrían tocado **no se encolan**
  mientras no se ve, para no reproducirlas de golpe al girarse.

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
* El modelo es de 977 cubos (751 en lite) y se dibuja en **hasta cuatro pases**
  (base, emisivo, halo y GLSL): 5 866 quads por pase en calidad full, ~23 000
  quads por reliquia y frame con todo encendido; en lite, 4 506 por pase.
  `maxRenderDistance` (32 bloques), `quality=lite`, `glowHalo` y `shaderGlow` son
  las palancas. Lo que **no** se paga cuatro veces es la animación: desde 1.0.16
  solo el pase base la evalúa y los otros tres reutilizan la pose, y desde 1.0.17
  el aura, el anillo y el estado no reservan memoria por frame. El escaneo de
  alerta va cada 10 ticks y las variaciones de reposo son un contador, no un
  cálculo por frame.

## Checklist de pruebas

- [ ] `./gradlew build` produce `holocore-<versión>.jar` y `/relic info` responde.
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
- [ ] En primera persona `/relic info` muestra el estado (y cambia a `alert` con
      un mob cerca); pasar a tercera **no** reinicia la `activation`.
- [ ] `/relic stats` responde con los pases por dibujo (4 con base, emisivo, halo y
      GLSL) y los ms por dibujo; `/relic stats reset` los reinicia.
- [ ] `/relic set` lista las 22 claves; `/relic set auraIntensity 0.55` cambia el
      aura al instante y avisa de que es en memoria; un valor fuera de rango se
      rechaza sin tocar nada.
- [ ] Tras un `set`, `/relic info` avisa de los cambios sin guardar; `/relic save`
      los escribe en `config/holocore-client.toml` (comprobar reabriendo el juego).
- [ ] `/relic preview` pone la reliquia delante de la cámara con su aura, un poco
      a la derecha y por debajo del centro (la mirilla se ve libre);
      `/relic preview 1.5` la acerca y `/relic preview` la quita.
- [ ] `/relic reset` deja de nuevo las 24 claves en su defecto (comparar con
      `/relic set`) y avisa de los cambios sin guardar; repetido, dice que ya
      estaba todo de fábrica.
- [ ] `/relic reset scale` vuelve solo esa clave y `/relic set` deja de marcarla
      con `*`.
- [ ] Con la vista previa encendida, `/relic info` lo dice y a qué distancia; al
      pasar a espectador se apaga sola.
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
