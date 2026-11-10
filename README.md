# Capa Deteriorer Test — v1.4.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade la *Capa Deteriorer Evil Saiyan*: geometría propia, cuatro animaciones,
textura de 128×128 con glowmask pulsante, **modelo 3D plegado en el
inventario**, **aura de brasas propia y serena** y compatibilidad opcional
con el slot **`back` de Curios API 5.14.1+1.20.1**.

## Descarga directa del `.jar`

**https://github.com/Santi-PdR/modelos/releases/download/v1.4.0/capatest-1.4.0.jar**

El CI publica el mod como **Release asset `.jar` crudo**, no como ZIP de
`actions/upload-artifact`. El repositorio es privado: hay que iniciar sesión en
GitHub con la cuenta `Santi-PdR` para descargarlo. Cada push a la rama
actualiza el mismo asset con `--clobber`; el tag `v1.4.0` queda fijo.

> PR #1 sigue abierta: https://github.com/Santi-PdR/modelos/pull/1

## Novedades de v1.4.0 — el modelo, en serio

**Capa EQUIPADA con relieve real**
- El geo pasa de **72 huesos / 126 cubos** a **98 huesos / 152 cubos**.
  `tools/armor_model_pipeline.py` parte de una copia prístina en
  `tools/originals/capa_deteriorer_evilsaiyan.geo.json` y añade 26 huesos:
  15 nervios de tela (uno por panel de `cape_top`, `cape_mid` y
  `cape_bottom`), 2 alas de hombro, 2 costuras laterales luminosas y 7 puntas
  de dobladillo.
- Los **72 huesos originales quedan byte-idénticos en JSON**; los nuevos son
  hijos de `cape_top/mid/bottom`, así que heredan el movimiento sin tocar
  `idle`/`moving`/`sprint`/`air`. La CI verifica el SHA de la animación y de la
  geometría original.
- Todas las UV nuevas caen en zonas ya opacas del atlas: **alfa base y
  glowmask siguen intactos** (1636 texeles emisivos). No hay agujeros nuevos
  ni brillo inventado.

**Ítem 3D plegado rehecho**
- De 8 a **33 huesos / 33 cubos**. Ahora hay **7 pliegues en abanico** con
  altura, profundidad y rotación gradual; 6 nervios de ribete; yugo con alas;
  cuello levantado; broche con marco y gema; dos tramos de cadena; costuras
  laterales y 7 puntas de dobladillo.
- `tools/fold_spec.py` reparte el atlas de **128×128** en 7 franjas
  continuas. `tools/texture_pipeline.py` hornea iluminación por pliegue,
  dibuja líneas de pliegue exactamente en los límites UV y reserva columnas
  de forro oscuro y ribete neón. Las siete caras reconstruyen una sola capa,
  no un mosaico repetido.
- El balanceo de pliegues, cuello, broche y puntas vive ahora en
  `animations/item/cape_folded.animation.json` (generada por
  `tools/item_model_pipeline.py`), no en un `System.currentTimeMillis()` del
  renderer. `CapaItemRenderer` sólo conserva iluminación de entidad para GUI.
- `models/item/capa_deteriorer_evilsaiyan.json` ajusta `display` para que el
  relieve se lea mejor en GUI, mano, suelo, marco y tercera persona.

**Atlas plegado v1.4.0**
- Tejido, bloom violeta, vetas calientes, yugo y dobladillo de puntas como en
  v1.3.0, más: sombreado por pliegue, 6 creases con fino rim light, banda
  inferior con ribete y columnas `[120..123]` forro / `[124..127]` ribete.
- Icono de 64×64 y 3 sprites de partícula de 16×16 siguen generándose desde
  la misma suite procedural.

## BASE v1.3.0 (resumen)

- Modelo 3D plegado de 8 huesos con atlas continuo de 128×128, texturas
  multicapa y `display` propio.
- Aura **serena**: fuera `PORTAL` / `CRIMSON_SPORE` / `SOUL_FIRE_FLAME`;
  1 brasa propia cada 10 ticks, alpha 0.52, deriva mínima y fade suave.
- Entrega directa del `.jar` vía GitHub Releases; ya no hay artifact ZIP del
  mod.
- Curios **5.14.1+1.20.1** opcional, tag `curios:back` y slot `back`, sin
  cambios.
- `idle`/`moving` de la armadura byte-idénticos a los originales aprobados.

## BASE v1.1.0 (resumen)

- **Textura**: mejora de canales RGB respetando alfa y UV; glowmask intacto.
- **Animación**: `tools/animation_pipeline.py` deriva `sprint` (0.72 s) y
  `air` (1.35 s) desde `moving` sin tocar `idle`/`moving`. Detección con
  `getDeltaMovement()` + `onGround()` + `isSprinting()`.
- **Efectos**: `CapaGlowLayer` con latido de 3.2 s, amplitud al correr y
  viraje carmesí según la vida; aura emitida desde servidor; `Rarity.EPIC`,
  `fireResistant`, glint y tooltips en_us/es_es.
- **Corrección**: `ArmorMaterial#getName()` sin `:` y `getArmorTexture()`
  apuntando al atlas de GeckoLib; defensa 9, dureza 3.0, empuje 0.15,
  durabilidad de pecho 900.

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1, Curios 5.14.1 (compileOnly)
src/main/java/com/capatest/                         Mod, material, item, renderers, glow layer, partículas, compat Curios
src/main/resources/META-INF/mods.toml               Metadatos: Forge + GeckoLib obligatorios, Curios opcional
src/main/resources/assets/capatest/                 geo/animaciones 3D, texturas, sprites, lang, modelo builtin/entity
src/main/resources/data/                           tag curios:back + concesión del slot al player
tools/originals/                                   PNG prístinos + geo de armadura prístino
tools/fold_spec.py                                 7 franjas UV y pose de los pliegues del item
tools/texture_pipeline.py                          Atlas de armadura, icono, atlas folded y sprites (Pillow + numpy)
tools/armor_model_pipeline.py                      Añade relieve a la capa equipada sin tocar el geo original
tools/item_model_pipeline.py                       Geo plegado de 33 huesos + animación del item
tools/animation_pipeline.py                        Deriva sprint/air desde moving
.github/workflows/build.yml                        CI: validación, build, verificación del jar y Release .jar directo
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.4.0.jar
```

Para regenerar los assets (no hace falta para compilar, ya están commiteados):

```bash
python -m pip install Pillow numpy
python tools/armor_model_pipeline.py   # primero: el atlas lee sus UV nuevas
python tools/texture_pipeline.py
python tools/item_model_pipeline.py
python tools/animation_pipeline.py
```

## GitHub Actions

`push` y `workflow_dispatch` sobre `ubuntu-latest`: `actions/checkout@v4`,
`actions/setup-java@v4` (17/temurin), `gradle/actions/setup-gradle@v4` (8.8),
validación de JSON/PNG + UV de 7 pliegues + 98 huesos de armadura + hashes
prístinos + tag/entidad Curios, `gradle build --no-daemon`, verificación de
las entradas del jar y publicación del **`.jar` directo** en el Release
`v1.4.0`. Si falla, los errores de `javac` se publican como anotaciones y se
sube el log completo.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y **`capatest-1.4.0.jar`** en `mods/`.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: capa plegada con 7 pliegues y broche en hotbar/mano, capa
   equipada con nervios/costuras/puntas, `idle` (3.6 s), `moving`, `sprint`,
   `air`, brillo pulsante/rojo al perder vida y unas pocas brasas discretas
   detrás del jugador, sin motas por el cielo.
