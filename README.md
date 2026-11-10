# Capa Deteriorer Test — v1.3.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade la *Capa Deteriorer Evil Saiyan*: geometría propia de 72 huesos, cuatro
animaciones, textura de 128×128 con glowmask pulsante, **modelo 3D plegado en
el inventario**, **aura de brasas propia y serena** y compatibilidad opcional
con el slot **`back` de Curios API 5.14.1+1.20.1**.

## Descarga directa del `.jar`

**https://github.com/Santi-PdR/modelos/releases/download/v1.3.0/capatest-1.3.0.jar**

El CI publica el mod como **Release asset `.jar` crudo**, no como ZIP de
`actions/upload-artifact`. El repositorio es privado: hay que iniciar sesión en
GitHub con la cuenta `Santi-PdR` para descargarlo. Cada push a la rama
actualiza el mismo asset con `--clobber`; el tag `v1.3.0` queda fijo.

> PR #1 sigue abierta: https://github.com/Santi-PdR/modelos/pull/1

## Novedades de v1.3.0

**Modelo 3D de inventario / hotbar / mano, rediseñado por completo**
- La antigua placa morada de 2 cubos se sustituye por un geo de **8 huesos**:
  dorso, **cinco pliegues** a distinta altura y profundidad, yugo rígido y
  broche. `tools/item_model_pipeline.py` lo genera de forma determinista.
- Cada pliegue muestrea una franja vertical distinta del atlas
  `cape_folded.png` de **128×128**, así que las cinco caras reconstruyen una
  sola ilustración de capa continua. Se acabó el cuadrado repetido.
- `models/item/capa_deteriorer_evilsaiyan.json` ajusta `display` para GUI,
  mano, suelo, marco y tercera persona. `CapaItemRenderer` usa iluminación de
  entidad en GUI y un bamboleo de ±0.02 rad en los pliegues: relieve legible
  sin movimiento mareante.
- El modelo de armadura **puesto** no se toca: 72 huesos / 126 cubos, UV del
  68.6 %, `idle` y `moving` byte-idénticos a los originales aprobados.

**Texturas mucho más ricas, sin romper UV, alfa ni glowmask**
- `tools/texture_pipeline.py` v1.3.0 deriva una máscara de uso UV desde la
  geometría y repinta **sólo los canales RGB de texeles ya opacos**: tejido
  multiescala, luz de pliegues, bloom violeta, rim light y vetas calientes.
- El **alfa base es byte-idéntico** al original y el glowmask mantiene sus
  **1636 texeles emisivos** (GeckoLib 4.8 usa únicamente su alfa). No se
  perfora la silueta ni se amplía el brillo.
- Icono de 64×64 y atlas folded de 128×128 comparten la misma ilustración de
  capa con yugo, costuras, dobladillo de puntas y broche de diamante.
- Sprites de partícula regenerados a 64px y reducidos con Lanczos a 16×16:
  núcleo cálido, destello frío y halo que se apaga, con antialiasing real.

**Partículas: más calidad, mucho menos ruido**
- Se eliminan `PORTAL`, `CRIMSON_SPORE` y `SOUL_FIRE_FLAME`: eran las motas
  repartidas por todo el cielo en las capturas. Queda **sólo**
  `capatest:capa_ember`.
- Emisión: **1 brasa cada 10 ticks** (2 por segundo; 2 sólo al correr),
  pegada a la espalda, con dispersión 0.07/0.10/0.07 y velocidad 0.001.
- `CapaEmberParticle` sobreescribe la velocidad aleatoria que inyecta
  `Particle`, usa gravedad negativa casi nula, `hasPhysics=false`, alpha
  máximo **0.52**, tamaño reducido, fade-in/fade-out y escala decreciente.
- `spawnAura` lleva un sello por tick en `getPersistentData()` para no
  duplicar el efecto cuando `inventoryTick` y `curioTick` coinciden con Curios.

**Entrega y CI**
- `permissions: contents: write` + `gh release create/upload` publican
  `capatest-1.3.0.jar` como descarga directa. Ya **no** se sube el mod como
  artifact ZIP de Actions; sólo el log de fallo sigue usando artifact.
- La validación de CI ahora comprueba el atlas folded 128×128, los 8 huesos,
  que todas las UV caben en 128×128, las animaciones del item plegado y que
  el Java no reintroduce partículas vanilla ruidosas.

## BASE v1.2.0 (resumen)

- `parent: builtin/entity` + `GeoItemRenderer` para el ítem 3D.
- `SimpleParticleType capatest:capa_ember` con
  `RegisterParticleProvidersEvent#registerSpriteSet` y 3 sprites.
- Curios **opcional**: `data/curios/tags/items/back.json` y
  `data/capatest/curios/entities/player.json` conceden el slot `back`;
  `CuriosCompat` se carga por reflexión y `CapaCurioRenderer` reutiliza el
  `GeoArmorRenderer`. **Se conserva `5.14.1+1.20.1` exactamente**.
- Sin Curios la capa sigue funcionando en el slot de pecho.

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
tools/originals/                                   Texturas prístinas para regenerar
tools/texture_pipeline.py                          Atlas de armadura, icono, atlas folded y sprites (Pillow + numpy)
tools/item_model_pipeline.py                       Geo plegado de 8 huesos y UV continuas
tools/animation_pipeline.py                        Deriva sprint/air desde moving
.github/workflows/build.yml                        CI: validación, build, verificación del jar y Release .jar directo
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.3.0.jar
```

Para regenerar los assets (no hace falta para compilar, ya están commiteados):

```bash
python -m pip install Pillow numpy
python tools/texture_pipeline.py
python tools/item_model_pipeline.py
python tools/animation_pipeline.py
```

## GitHub Actions

`push` y `workflow_dispatch` sobre `ubuntu-latest`: `actions/checkout@v4`,
`actions/setup-java@v4` (17/temurin), `gradle/actions/setup-gradle@v4` (8.8),
validación de JSON/PNG + UV + tag/entidad Curios, `gradle build --no-daemon`,
verificación de las entradas del jar (clases, geo 3D, 3 sprites, datos) y
publicación del **`.jar` directo** en el Release `v1.3.0`. Si falla, los
errores de `javac` se publican como anotaciones y se sube el log completo.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y **`capatest-1.3.0.jar`** en `mods/`.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: capa plegada con relieve en hotbar/mano, `idle` (3.6 s),
   `moving`, `sprint`, `air`, brillo pulsante/rojo al perder vida y unas pocas
   brasas discretas detrás del jugador (también visibles para otros
   jugadores), sin motas por el cielo.
