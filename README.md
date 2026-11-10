# Capa Deteriorer Test — v1.7.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade la *Capa Deteriorer Evil Saiyan*: geometría propia, cuatro animaciones,
textura de 128×128 con glowmask pulsante, **modelo 3D plegado en el
inventario**, **aura de brasas propia y serena** y compatibilidad opcional
con el slot **`back` de Curios API 5.14.1+1.20.1**.

## Descarga directa del `.jar`

**https://github.com/Santi-PdR/modelos/releases/download/v1.7.0/capatest-1.7.0.jar**

El CI publica el mod como **Release asset `.jar` crudo**, no como ZIP de
`actions/upload-artifact`. El repositorio es privado: hay que iniciar sesión en
GitHub con la cuenta `Santi-PdR` para descargarlo. Cada push a la rama
actualiza el mismo asset de `v1.7.0` con `--clobber`; el tag queda fijo.
Las entregas anteriores siguen disponibles en `v1.6.1`, `v1.6.0`, `v1.5.1`,
`v1.4.0` y `v1.3.0`. **Usar v1.7.0**: v1.6.0 crashea al cargar el geo plegado
y v1.5.0 tiene el crash de rotación.

> PR #1 sigue abierta: https://github.com/Santi-PdR/modelos/pull/1

## v1.7.0 — pliegues anchos y material con relieve

**Objetivo: apariencia y calidad de la capa.** El defecto de v1.6.x era sutil
pero se notaba: el canvas pintaba **9 senos estrechos** de sombreado mientras
el relieve 3D era una **parábola** independiente. Sombreado y geometría
contaban historias distintas, así que la capa se leía como una tabla rayada y
no como paño.

- **Una sola onda para 2D y 3D.** `tools/cloth_spec.py` define `FOLDS = 3` y
  `fold_wave(u) = cos(2π·3·u)`. `texture_pipeline.py` la usa para luz y
  crease; `armor_model_pipeline.py::panel_z()` la muestrea en el centro de
  cada columna para el relieve en Z. Resultado: **3 pliegues anchos** (3
  columnas cada uno), cada valle oscuro coincide con una crease geométrica y
  cada cresta iluminada con un panel adelantado. La amplitud del relieve
  (0.055) es menor que el grosor del panel (0.10) para que nunca se abra un
  hueco entre columnas vistas de lado.
- **9 creases 3D** (3 por sección, en las columnas 1/4/7 = los valles), en
  lugar de las 6 arbitrarias entre columnas. Tono alterno oscuro/claro.
- **Festón real** en el dobladillo: las 9 lengüetas cuelgan con longitudes
  curvas (más largas al centro) y una inclinación suave de 2–4°, así la
  silueta inferior deja de ser una línea recta. Cada una sigue tomando sólo
  su porción del chevron del canvas.
- **Material con más calidad**: medallón con tercer anillo y cuatro engarces,
  pespuntes en el yugo, desgaste/rozaduras discretas concentrado en bordes y
  tercio inferior, tejido en sarga y grano. **Sin líneas de costura** entre
  paneles. Broche reducido a una gema pequeña.
- **Movimiento por pliegue, no por tira**: el retardo de fase por columna bajó
  de 0.045 a 0.030 rad (y el ripple de 0.62 a 0.42) para que cada pliegue
  ancho ondee como un bloque en vez de descomponerse en tiras independientes.

**Geometría**: **126 huesos / 180 cubos** (27 paneles 9×3, 9 creases, 6
ribetes laterales, 9 lengüetas, 2 alas de cuello, 1 broche). Se mantienen el
canvas 96×48 compartido por icono, item 3D plegado y capa equipada; los 61
huesos boxy ocultos en runtime; alfa base byte-idéntico; **1636 texels
emisivos**; **324 caras UV nuevas** en zonas ya opacas; radianes, caché de
huesos, fail-safes, ausencia de `JsonNull` y de mixins; Curios `back`
opcional y aura serena.

Los previews son render software: **no sustituyen una prueba in-game**, que
ahora mismo está bloqueada por el conflicto de mixins descrito más abajo.

## v1.6.1 — corrección del crash `Error loading model file`

Reportado in-game: *«El juego se cerró inesperadamente mientras Rendering
overlay»* con

```
software.bernie.geckolib.GeckoLibException:
capatest:geo/item/cape_folded.geo.json: Error loading model file
```

**Éste sí era nuestro mod.** Causa exacta, confirmada contra GeckoLib 4.8.4:

- `tools/item_model_pipeline.py` generaba el hueso raíz `cape` con
  `"parent": null`.
- `Bone.deserializer()` de GeckoLib lee ese campo con
  `GsonHelper.getAsString(obj, "parent", null)`. Como la clave **sí existe**,
  `JsonObject.has()` devuelve `true` y Gson obtiene un `JsonNull`; al llamar a
  `JsonNull.getAsString()` lanza `UnsupportedOperationException`. Eso ocurre
  en `GeckoLibCache.loadModels()` durante el reload de recursos, que envuelve
  cualquier excepción en `GeckoLibException(resource, "Error loading model
  file", ex)`. El fallo se manifiesta al renderizar el overlay porque es cuando
  se pide el modelo al caché.
- El geo **original aprobado** nunca tuvo ese problema: sus 8 huesos raíz
  simplemente **omiten** la clave `parent`. `GeometryTree.fromModel()` ya
  interpreta `parent == null` como raíz, así que no hace falta escribirla.

**Corrección**: `bone()` omite `parent` cuando es `None`; el geo plegado queda
con 33 huesos y la misma geometría, sin un solo valor `null` en todo el pack
de recursos. No cambia ni un píxel del aspecto de v1.6.0.

**Defensas añadidas**:

- El pipeline falla si el geo contiene cualquier `null`, si un `parent`
  declarado no existe o si la raíz lleva `parent`.
- El CI escanea **todos** los JSON de `src/main/resources` (incluido
  `pack.mcmeta`) buscando `JsonNull`, verifica que la raíz del geo plegado no
  declare `parent` y que todo padre sea un nombre existente, y comprueba que
  el pipeline conserva el guardia `if parent is not None`.

Era un **defecto latente desde v1.4.0**: el arranque anterior se caía antes por
el conflicto de mixins descrito más abajo, así que el juego nunca llegaba a
cargar los recursos del mod y no se pudo detectar en las entregas previas.

## v1.6.0 — una sola pieza de tela

Prioridad de esta versión: **apariencia y calidad de la capa**.

**El defecto corregido.** v1.5.1 calculaba los límites de cada sección por
separado y repartía 13 columnas sobre cada una, mientras que el canvas UV se
dividía en 16 filas y `96/13` texels por franja. El resultado era una
ilustración estirada de forma distinta arriba, en el centro y abajo, con el
medallón partido y tres bloques que se leían como cajas apiladas. Además
seguían visibles 61 huesos originales con cubos (placas, dedos, jirones,
faldones, hombreras, tiras) tapando la tela nueva.

- **Un único rectángulo global.** `tools/armor_model_pipeline.py` toma los
  límites combinados de `cape_top/mid/bottom` y los divide en un mosaico
  **9 × 3** (27 paneles) con la misma escala en las 27 caras. El canvas de
  `tools/cloth_spec.py` (96×48) se reparte en `SECTION_V` de 16 filas y
  franjas de `96/9` texels: sin distorsión por sección y sin costuras.
- **Sin líneas de costura pintadas.** Se eliminaron las rayas horizontales y
  de columna del canvas; los pliegues ahora son sombreado (`fold_light`,
  `crease`, twill, luz cenital) y un relieve suave en Z que aumenta hacia el
  dobladillo. `tools/preview_cloth.py --uv-test` pinta franjas de colores y
  marcas asimétricas para comprobar el orden UV y la alineación de las filas.
- **Menos cajas, más paño.** `CapaArmorModel.HIDDEN_DETAILS` oculta en runtime
  los **61 huesos originales con cubos** que no pertenecen a la cadena
  `chestplate → cape_top/mid/bottom`. El geo prístino sigue byte-idéntico y
  sus animaciones siguen accionando a los huesos padres. El CI verifica que
  **ningún** hueso `v15_*` cuelga de un hueso oculto.
- **Geometría más ligera y más orgánica:** **123 huesos / 177 cubos** frente a
  168 / 235 de v1.5.1. 27 paneles, 6 creases, 6 ribetes laterales, 9 lengüetas
  de dobladillo, 2 alas de cuello con la misma tela del canvas y 1 broche en
  diamante girado 45°. Vuelo de campana del 1% (el 6% se descartó: producía
  escalones en los ribetes), caída progresiva hacia atrás y rotación por fila
  común, sin giros Y por columna que abran huecos en el mosaico.
- **Mismo diseño en todas partes.** El icono de 64×64 y el item 3D plegado
  (33 huesos, 7 pliegues) muestrean ahora el **mismo canvas** que la capa
  equipada, vía `cloth_canvas_rgba()`. Antes usaban una ilustración aparte con
  dos medallones y venas neón que no existían en la tela equipada. El material
  se aclaró ligeramente para que el medallón y la filigrana se lean en la
  espalda con la luz del juego.
- **306 caras UV nuevas** en rectángulos ya opacos, alfa base byte-idéntico,
  **1636 texels emisivos** con la misma cobertura, glowmask 128×128 intacto.

**Estabilidad heredada de v1.5.1 (no se reintrodujo el crash)**

- GeckoLib guarda las rotaciones en **radianes**; todo ángulo pasa por
  `Math.toRadians` antes de `setRot*`, con límites de 12°/8°/6°.
- Sin `getBakedModel()` en el hot path: los huesos se resuelven **una sola vez**
  desde el `AnimationProcessor` activo, con caché y guardia de identidad.
- Fail-safe cosmético en `setCustomAnimations`, el pass emisivo y el render de
  Curios: registran el fallo una vez y dejan la capa estática en vez de tumbar
  el juego. Estado de movimiento por instancia (`ConcurrentHashMap`).
- Onda con retardo de fase de hombros a dobladillo, viento, giro, salto, agua,
  sigilo y sprint; `idle`/`moving`/`sprint`/`air` intactos.

**Sin cambios**: aura serena (1 brasa cada 10 ticks, sin `PORTAL` /
`CRIMSON_SPORE` / `SOUL_FIRE_FLAME`), `Rarity.EPIC`, `fireResistant`, glint,
lore en_us/es_es, Curios **opcional** `5.14.1+1.20.1`, tag `curios:back` y
concesión del slot al `player`.

### Previews de validación

`tools/preview_cloth.py` es una herramienta versionada de render software
(frente, 3/4 con onda, espalda, tela sola, detalle original visible y canvas):

```bash
PYTHONPATH=tools/_deps python3 tools/preview_cloth.py --out /tmp/capa_preview --uv-test
```

`--uv-test` genera además `uv_test_atlas.png` y `uv_test_front.png`: nueve
franjas de colores con marcas asimétricas en `u=0`/`u=95` y líneas en las
tres divisiones de fila. Si las franjas aparecen en orden, alineadas y sin
inversión, el mosaico es correcto. **Los previews no sustituyen una prueba
in-game.**

Resultados versionados de **v1.7.0**:
[`docs/capa_v170_preview.png`](docs/capa_v170_preview.png) (item plegado,
frente, 3/4 con onda y espalda) y
[`docs/capa_v170_uv_test.png`](docs/capa_v170_uv_test.png) (franjas UV).

## Diagnóstico de crashes: dos fallos distintos

Hubo **dos crashes diferentes** y conviene no confundirlos:

| Crash | Origen | Estado |
|---|---|---|
| `GeckoLibException: capatest:geo/item/cape_folded.geo.json: Error loading model file` | **Sí era `capatest`** (`"parent": null`) | **Corregido en v1.6.1** |
| `MixinTransformerError ... player_animation_library.mixins.json:firstPerson.ItemInHandRendererMixin` | Conflicto entre otros mods del pack | Ajeno al mod; ver solución abajo |

### Qué significa exactamente el `MixinTransformerError`

La primera línea del `Caused by` lo dice todo:

```
org.spongepowered.asm.mixin.injection.throwables.InjectionError:
Critical injection failure: Callback method cancelItemRender(...) in
player_animation_library.mixins.json:firstPerson.ItemInHandRendererMixin
failed injection check, (0/1) succeeded. Scanned 1 target(s).
Using refmap player_animation_library.refmap.json
```

Leyéndolo por partes:

- **`player_animation_library.mixins.json`** es el fichero de configuración de
  mixins del mod **Player Animation Library** (`PlayerAnimationLibForge-1.2.8+1.20.1-all.jar`),
  no de `capatest`. Un *mixin* es un parche que modifica el bytecode de una
  clase de Minecraft al arrancar.
- **`firstPerson.ItemInHandRendererMixin`** parchea
  `net.minecraft.client.renderer.ItemInHandRenderer`, la clase que dibuja el
  item que llevas en la mano en primera persona.
  ([código del mixin](https://github.com/KosmX/minecraftPlayerAnimator/blob/HEAD/minecraft/common/src/main/java/dev/kosmx/playerAnim/mixin/firstPerson/ItemInHandRendererMixin.java)).
- **`cancelItemRender`** es un `@Inject` con `cancellable = true` sobre
  `ItemInHandRenderer#renderItem`, en el punto `INVOKE` de
  `ItemRenderer.renderStatic(LivingEntity, ItemStack, ItemDisplayContext,
  boolean, PoseStack, MultiBufferSource, Level, int, int, int)`. Su trabajo es
  cancelar el dibujado del item cuando una animación está mostrando el modelo
  en tercera persona. La firma de 8 parámetros del error es la del método
  `renderItem` que él intercepta, no la del objetivo.
- **`(0/1) succeeded. Scanned 1 target(s)`** es la clave: Mixin **sí encontró
  el método** `renderItem` (1 target), pero **no encontró ni una** llamada a
  `renderStatic` con esa firma exacta dentro de él (0 inyecciones aplicadas).
  Pasa cuando otro mixin ya reescribió `renderItem`, cuando `ItemRenderer`
  cambió la firma de `renderStatic`, o cuando el `refmap` (que traduce los
  nombres a los mappings SRG de Forge) no coincide con la versión instalada.
  No es un error de memoria, de GPU ni de un asset: es un **parche que no
  encuentra dónde engancharse**.
- **`Description: Initializing game`** porque la transformación de clases
  ocurre al arrancar: `Main.main` → `Minecraft.<init>` →
  `EntityRenderDispatcher.<init>` fuerza la carga de `ItemInHandRenderer` y
  ahí salta el mixin. Es antes de crear un mundo y, por tanto, **antes de que
  exista una capa equipada** o se cargue un solo recurso de `capatest`.

En todo el stack no aparece ni una clase `com.capatest.*`: este mod **no
registra mixins** (el CI lo verifica) y sólo usa GeckoLib y la API pública de
Forge. **Quitar `capatest` no arregla este arranque.** Tampoco lo arregla
cambiar de versión del mod: el `GeckoLibException` del geo sí era nuestro y
quedó corregido en v1.6.1, pero éste es otro fallo, de otro mod.

### Cómo desatascarlo (nombres reales de tu pack)

1. **Quita `ImmediatelyFast-Forge-1.5.5+1.20.4.jar`**. Es una build de
   **Minecraft 1.20.4 corriendo en 1.20.1** y modifica justo el render de
   items. Sustitúyela por la build 1.20.1 de ImmediatelyFast o déjala fuera.
   Es el candidato número uno.
2. **Quita los snapshots** `TRansition-1.0.21-1.20.1-forge-SNAPSHOT.jar` y
   `TRender-1.0.15-1.20.1-forge-SNAPSHOT.jar`: transforman el render de
   primera persona y pueden reescribir `renderItem` antes que PAL.
3. **Actualiza `PlayerAnimationLibForge-1.2.8+1.20.1-all.jar`** a una build
   1.20.1 compatible, o quítalo **junto con los mods que lo requieren**
   (`fiskheroes`, `TRender`/`TRansition`). Quitar PAL solo puede provocar
   `ClassNotFoundException` en sus dependientes.
4. **Aísla por grupos**: arranca primero con Forge + GeckoLib + Curios +
   `capatest-1.7.0.jar`. Si arranca, ve añadiendo el resto de 5 en 5 hasta que
   reaparezca el `MixinTransformerError`: el culpable está en ese grupo.

`skinlayers3d`, `embeddium`, `photon`, `flywheel`, `create` y los demás salen
en el stack sólo porque también aplican mixins a `Minecraft` o
`EntityRenderDispatcher`; no son la excepción. `Flywheel Backend: flywheel:off`
es un dato informativo. El `Código de salida: 4294967295 (0xFFFFFFFF)` es
simplemente `-1` como unsigned: el launcher indica "se cerró con error", no
aporta más causa.

Mientras este conflicto siga activo **no puedes ver ninguna mejora de la
capa**: el juego se cae antes de renderizar nada. Por eso conviene resolverlo
primero.

## v1.5.1 — corrección preventiva de rotación (histórico)

v1.5.0 sumaba grados (`bend` hasta 12 ≈ 687°) a `GeoBone#setRotX/Y/Z`, que
esperan radianes, y consultaba `getBakedModel()` por frame (puede reiniciar
los `BoneSnapshot` a mitad de frame). v1.5.1 convirtió los ángulos, cacheó los
huesos y añadió los fail-safes. Era un **bug real del código** y sigue
corregido, pero el crash de arranque compartido después por el usuario era el
conflicto de mixins descrito arriba, no este. **v1.5.0 sigue marcada como
rota.**

## BASE v1.4.0 / v1.3.0 / v1.2.0 / v1.1.0 (resumen)

- v1.4.0: capa equipada con relieve (98 huesos / 152 cubos), item 3D plegado
  rehecho con 33 huesos y 7 pliegues en abanico, entrega directa del `.jar`.
- v1.3.0: modelo 3D plegado de 8 huesos, aura serena y entrega directa del
  `.jar` desde GitHub Releases; fuera el ZIP de Actions como entrega.
- v1.2.0: modelo 3D en inventario, partículas propias con sprites animados y
  compatibilidad opcional con el slot `back` de Curios API.
- v1.1.0: atlas mejorado respetando UV/alfa, icono 64×64, `sprint` (0.72 s) y
  `air` (1.35 s) derivados de `moving`, `CapaGlowLayer` con latido de 3.2 s.

### Referencias usadas

- **GitHub / física y geometría**: [tr7zw/WaveyCapes](https://github.com/tr7zw/WaveyCapes)
  (pieza flexible, vaivén, límites de ángulo, anti-clipping),
  [ismaildzf/finery](https://github.com/ismaildzf/finery)
  (simulación de cuerda de 16 puntos y estado por portador),
  [GlowberryClient #102](https://github.com/ChimeraAnt-DEV/GlowberryClient/pull/102)
  (cadena segmentada, curva de amplitud y retardo de fase) y
  [#106](https://github.com/ChimeraAnt-DEV/GlowberryClient/pull/106)
  (mallas Blockbench frente a box-stacking),
  [FabricExtras/ArmorModelAPI](https://github.com/FabricExtras/ArmorModelAPI)
  (passes base/glow/trim), [GeoArmor](https://github.com/i3667563-dot/GeoArmor)
  y [M1nut1/GeoAnim](https://github.com/M1nut1/GeoAnim) (config/display/UV/pivots;
  sus versiones modernas no son portables tal cual a Forge 1.20.1).
- **GeckoLib**: [repositorio oficial](https://github.com/bernie-g/geckolib) y
  su rama `1.20.1` para `setCustomAnimations`, `GeoBone`, `BakedModelFactory`,
  `GeoQuad` (inversión de U con `mirror=false`), `AutoGlowingGeoLayer` y el
  orden de caras/UV.
- **Vídeos / Blockbench**: tutorial de capa de alta resolución
  [bDoOqqyvL3o](https://www.youtube.com/watch?v=bDoOqqyvL3o), capa 4D con
  capas delgadas [TmMt-6F5ZuU](https://www.youtube.com/watch?v=TmMt-6F5ZuU),
  textura de skin/capa [mje8iTV5uTw](https://www.youtube.com/watch?v=mje8iTV5uTw)
  y accesorios modelados [6KPFVyU_GO0](https://www.youtube.com/watch?v=6KPFVyU_GO0) /
  [Xtii4cKgZjY](https://www.youtube.com/watch?v=Xtii4cKgZjY). Se consultaron
  descripciones y metadatos (sin transcripción completa de cada vídeo); la
  implementación se validó con previews software, no con capturas in-game.

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1, Curios 5.14.1 (compileOnly)
src/main/java/com/capatest/                         Mod, material, item, renderers, CapaArmorModel, glow layer, partículas, compat Curios
src/main/resources/META-INF/mods.toml               Metadatos: Forge + GeckoLib obligatorios, Curios opcional
src/main/resources/assets/capatest/                 geo/animaciones 3D, texturas, sprites, lang, modelo builtin/entity
src/main/resources/data/                           tag curios:back + concesión del slot al player
tools/originals/                                   PNG prístinos + geo de armadura prístino
tools/cloth_spec.py                                 Canvas 96×48, 9 columnas, FOLDS=3/fold_wave, SECTION_V, UV opacas y zonas reservadas
tools/fold_spec.py                                 7 franjas UV y pose de los pliegues del item
tools/texture_pipeline.py                          Atlas de armadura, canvas compartido, icono, atlas folded y sprites (Pillow + numpy)
tools/armor_model_pipeline.py                      Rectángulo global 9×3 + relieve con fold_wave, creases en valles, festón y clasp
tools/item_model_pipeline.py                       Geo plegado de 33 huesos + animación del item
tools/animation_pipeline.py                        Deriva sprint/air desde moving
tools/preview_cloth.py                             Previews software de frente/3-4/espalda/tela/canvas y --uv-test
docs/capa_v170_preview.png                         Preview versionado de las cuatro vistas de la capa
docs/capa_v170_uv_test.png                         Test visual del orden UV del mosaico 9×3
.github/workflows/build.yml                        CI: validación, build, verificación del jar y Release .jar directo
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.7.0.jar
```

Para regenerar los assets (no hace falta para compilar, ya están commiteados):

```bash
python -m pip install Pillow numpy
python tools/armor_model_pipeline.py   # primero: la textura lee sus UV nuevas
python tools/texture_pipeline.py
python tools/item_model_pipeline.py
python tools/animation_pipeline.py
```

## GitHub Actions

`push` y `workflow_dispatch` sobre `ubuntu-latest`: `actions/checkout@v4`,
`actions/setup-java@v4` (17/temurin), `gradle/actions/setup-gradle@v4` (8.8),
validación de JSON/PNG + **ningún `JsonNull` en todos los recursos** + raíz del
geo plegado sin `parent` + 7 pliegues + **126 huesos / 180 cubos** + 27
paneles 9×3 + 9 creases en los valles de `FOLDS=3` + onda compartida entre el
canvas 2D y `panel_z()` + 61 huesos boxy ocultos sin descendientes `v15_*` +
UV nuevas en zonas opacas + hashes prístinos + regresión de radianes/sin
`getBakedModel()` +
**ausencia de mixins** + tag/entidad Curios, `gradle build --no-daemon`, verificación de las entradas
del jar y publicación del **`.jar` directo** en el Release `v1.7.0`. Si falla,
los errores de `javac` se publican como anotaciones y se sube el log completo
como artifact aparte (que **no** es la entrega).

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y **`capatest-1.7.0.jar`** en `mods/`.
   Si el juego crashea **al arrancar** con `MixinTransformerError`, ver la
   sección «Diagnóstico de crashes»: es un conflicto entre otros mods.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: capa plegada con 7 pliegues y broche en hotbar/mano; capa
   equipada con **una sola ilustración continua** (medallón único, sin cortes
   entre las tres secciones), pliegues que ondean al caminar/correr,
   `idle` (3.6 s), `moving`, `sprint`, `air`, brillo pulsante/rojo al perder
   vida y unas pocas brasas discretas detrás del jugador, sin motas por el
   cielo.
