# Capa Deteriorer Test — v1.5.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade la *Capa Deteriorer Evil Saiyan*: geometría propia, cuatro animaciones,
textura de 128×128 con glowmask pulsante, **modelo 3D plegado en el
inventario**, **aura de brasas propia y serena** y compatibilidad opcional
con el slot **`back` de Curios API 5.14.1+1.20.1**.

## Descarga directa del `.jar`

**https://github.com/Santi-PdR/modelos/releases/download/v1.5.0/capatest-1.5.0.jar**

El CI publica el mod como **Release asset `.jar` crudo**, no como ZIP de
`actions/upload-artifact`. El repositorio es privado: hay que iniciar sesión en
GitHub con la cuenta `Santi-PdR` para descargarlo. Cada push a la rama
actualiza el mismo asset de `v1.5.0` con `--clobber`; el tag queda fijo.
La entrega anterior sigue en
`https://github.com/Santi-PdR/modelos/releases/download/v1.4.0/capatest-1.4.0.jar`.

> PR #1 sigue abierta: https://github.com/Santi-PdR/modelos/pull/1

## Novedades de v1.5.0 — apariencia y calidad de la tela

**Capa EQUIPADA: una superficie continua, no un mosaico de cubos**

- El geo pasa de **72 huesos / 126 cubos** prístinos a **168 huesos / 235
  cubos**. `tools/armor_model_pipeline.py` conserva los 72 huesos aprobados
  byte-idénticos en JSON y añade 96 huesos `v15_*`: **39 paneles de tela**
  (13 columnas × 3 secciones), 36 creases con sombra/rim light, 6 ribetes
  laterales, 13 puntas de dobladillo y 2 alas de hombro.
- `tools/cloth_spec.py` define un **canvas continuo de 96×48 texels** dentro
  del atlas de 128×128. Cada panel toma una franja de ~7.38 texels; los tres
  niveles comparten la misma ilustración, con pliegues anchos, tejido,
  medallón, filigrana, ribetes y chevrones. Es el doble de resolución
  horizontal que el canvas cuadrado inicial.
- `CapaArmorModel.java` oculta **en runtime** los 15 cubos planos de
  `cape_top/mid/bottom` y los detalles de «cajas apiladas» (manos, dedos,
  espinas, cristales sueltos y esquirlas), pero deja vivos todos sus hijos:
  los paneles nuevos siguen parentados a las secciones originales y heredan
  `idle`/`moving`/`sprint`/`air`. El JSON y la animación aprobada no se tocan.
- **Caída con física ligera**: una curva de amplitud por sección/columna,
  retardo de fase de hombros a dobladillo, viento, giro del cuerpo acotado,
  salto/caída, sprint, agua y sigilo. Límites duros para evitar ángulos
  bruscos y clipping, en la línea de WaveyCapes / Finery / GlowberryClient.
- **Integridad del atlas**: alfa base byte-idéntico, **1636 texels emisivos**
  con la misma cobertura, y las 654 caras UV nuevas caen en rectángulos que ya
  eran 100% opacos. No hay agujeros ni glow inventado. El glowmask original
  apenas tiñe la nueva tela; el brillo lo aportan ribetes, medallón y pass
  emisivo existente.

**Ítem 3D plegado: mismo modelo, mejor material**

- Se conservan **33 huesos / 33 cubos**, 7 pliegues en abanico, nervios,
  yugo, cuello, alas, broche, cadenas, costuras y puntas.
- `tools/texture_pipeline.py` añade bordado de alta resolución, pespuntes a lo
  largo del contorno, medallón con halo, chevrones inferiores, twill diagonal
  y **sombreado por pliegue** con centro iluminado y bordes en sombra. Las
  siete franjas UV siguen reconstruyendo una sola capa.
- Icono de 64×64 y 3 sprites de partícula de 16×16 se regeneran desde la
  misma suite procedural.

**Sin cambios**: aura serena (1 brasa cada 10 ticks, sin `PORTAL` /
`CRIMSON_SPORE` / `SOUL_FIRE_FLAME`), `Rarity.EPIC`, `fireResistant`, glint,
lore en_us/es_es, `idle`/`moving` originales, `sprint`/`air` derivados,
Curios **opcional** `5.14.1+1.20.1`, tag `curios:back` y concesión del slot
al `player`.

### Referencias usadas

- **GitHub / física y geometría**: [tr7zw/WaveyCapes](https://github.com/tr7zw/WaveyCapes)
  (pieza flexible, vaivén, límites de ángulo), [ismaildzf/finery](https://github.com/ismaildzf/finery)
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
  su rama `1.20.1` para `setCustomAnimations`, `GeoBone`, `BakedGeoModel`,
  `AutoGlowingGeoLayer` y el orden de caras/UV.
- **Vídeos / Blockbench**: tutorial de capa de alta resolución
  [bDoOqqyvL3o](https://www.youtube.com/watch?v=bDoOqqyvL3o), capa 4D con
  capas delgadas [TmMt-6F5ZuU](https://www.youtube.com/watch?v=TmMt-6F5ZuU),
  textura de skin/capa [mje8iTV5uTw](https://www.youtube.com/watch?v=mje8iTV5uTw)
  y accesorios modelados [6KPFVyU_GO0](https://www.youtube.com/watch?v=6KPFVyU_GO0) /
  [Xtii4cKgZjY](https://www.youtube.com/watch?v=Xtii4cKgZjY). Se consultaron
  descripciones y metadatos (sin transcripción completa de cada vídeo); la
  implementación se validó con previews software, no con capturas in-game.

## BASE v1.4.0 (resumen)

- Capa equipada con relieve: 98 huesos / 152 cubos, 15 nervios, alas,
  costuras luminosas y puntas; item 3D plegado rehecho con 33 huesos y 7
  pliegues en abanico.
- Los 72 huesos y las animaciones originales ya quedaban intactos; alfa y
  cobertura glowmask sin cambios. Entrega directa del `.jar` vía Release.

## BASE v1.3.0 / v1.2.0 / v1.1.0 (resumen)

- v1.3.0: modelo 3D plegado de 8 huesos, aura serena y entrega directa del
  `.jar` desde GitHub Releases; fuera el ZIP de Actions como entrega.
- v1.2.0: modelo 3D en inventario, partículas propias con sprites animados y
  compatibilidad opcional con el slot `back` de Curios API.
- v1.1.0: atlas mejorado respetando UV/alfa, icono 64×64, `sprint` (0.72 s) y
  `air` (1.35 s) derivados de `moving`, `CapaGlowLayer` con latido de 3.2 s y
  correcciones de renderizado/armor material.

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1, Curios 5.14.1 (compileOnly)
src/main/java/com/capatest/                         Mod, material, item, renderers, CapaArmorModel, glow layer, partículas, compat Curios
src/main/resources/META-INF/mods.toml               Metadatos: Forge + GeckoLib obligatorios, Curios opcional
src/main/resources/assets/capatest/                 geo/animaciones 3D, texturas, sprites, lang, modelo builtin/entity
src/main/resources/data/                           tag curios:back + concesión del slot al player
tools/originals/                                   PNG prístinos + geo de armadura prístino
tools/cloth_spec.py                                 Canvas 96×48, 13 columnas, UV opacas y zonas reservadas
tools/fold_spec.py                                 7 franjas UV y pose de los pliegues del item
tools/texture_pipeline.py                          Atlas de armadura, canvas de tela, icono, atlas folded y sprites (Pillow + numpy)
tools/armor_model_pipeline.py                      39 paneles curvados + creases/ribetes/hem sobre el geo original intacto
tools/item_model_pipeline.py                       Geo plegado de 33 huesos + animación del item
tools/animation_pipeline.py                        Deriva sprint/air desde moving
.github/workflows/build.yml                        CI: validación, build, verificación del jar y Release .jar directo
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.5.0.jar
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
validación de JSON/PNG + 7 pliegues + **168 huesos / 235 cubos** + 39 paneles
de tela + UV nuevas en zonas opacas + hashes prístinos + `CapaArmorModel` +
tag/entidad Curios, `gradle build --no-daemon`, verificación de las entradas
del jar y publicación del **`.jar` directo** en el Release `v1.5.0`. Si falla,
los errores de `javac` se publican como anotaciones y se sube el log completo.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y **`capatest-1.5.0.jar`** en `mods/`.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: capa plegada con 7 pliegues y broche en hotbar/mano; capa
   equipada con ilustración continua, pliegues que ondean al caminar/correr,
   `idle` (3.6 s), `moving`, `sprint`, `air`, brillo pulsante/rojo al perder
   vida y unas pocas brasas discretas detrás del jugador, sin motas por el
   cielo.
