# Capa Deteriorer Test — v1.1.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade una capa (armadura de pecho) animada: *Capa Deteriorer Evil Saiyan*, con
geometría propia de 72 huesos, animaciones `idle`/`moving` hechas a mano, textura
de 128×128 con glowmask, icono de inventario y efectos de aura.

## Qué cambió en v1.1.0

**Textura (mismo atlas UV, sin romper el modelo)**
- `tools/texture_pipeline.py` lee los originales de `tools/originals/`, calcula qué
  texeles usa realmente el `.geo.json` (68.6 %) y mejora **sólo los canales de color**
  de los píxeles ya opacos: grano de tela determinista, iluminación vertical,
  sombras frías hacia índigo, venas de energía magenta/carmesí y sangrado violeta
  alrededor del neon. El canal alfa se conserva byte a byte.
- Dato importante: el `AutoGlowingGeoLayer` de GeckoLib 4.8 **sólo usa el alfa** del
  `_glowmask.png` y **borra esos píxeles de la textura base**. Por eso el pipeline
  potencia el color de esos píxeles y **no amplía** la cobertura del glowmask
  (1636 texeles, idéntica), evitando agujeros en la capa.
- Icono de inventario nuevo: 16×16 → **64×64** con silueta, hombreras, emblema,
  borde neon y motas de energía (supersampling 4×).

**Animación (idle y moving intactos)**
- `tools/animation_pipeline.py` deriva dos estados nuevos de `animation.moving`
  sin modificar ni un byte de `animation.idle` / `animation.moving`:
  - `animation.sprint`: ciclo 0.72 s, rotaciones ×1.18 → la capa se abre más.
  - `animation.air`: ciclo 1.35 s, huesos de tela con barrido X ×1.55 → flota al
    saltar/caer/usar elytra.
- **Bug fix**: `GeoArmorRenderer` crea el `AnimationState` con `isMoving()=false` y
  `limbSwing=0`, y el código usaba `entity.xo/zo` (posición del tick anterior), lo
  que podía parpadear entre estados durante el render. Ahora se usa
  `getDeltaMovement()` + `onGround()` + `isSprinting()`, estable durante todo el tick.

**Efectos**
- `CapaGlowLayer`: reemplaza el `AutoGlowingGeoLayer` plano por un re-render
  emisivo con latido senoidal de 3.2 s, tinte violeta en los valles, mayor
  amplitud cuando el portador corre y viraje a carmesí al perder vida
  ("Deteriorer").
- Aura de partículas (`SOUL_FIRE_FLAME` / `PORTAL` / `CRIMSON_SPORE`) emitida desde
  el servidor en `inventoryTick`, detrás del jugador y más intensa al correr, para
  que también la vean otros jugadores.
- `Rarity.EPIC`, resistente al fuego, glint permanente en inventario y tooltip
  traducido (en_us / es_es).

**Corrección de render**
- `ArmorMaterial#getName()` devolvía `capatest:capa_deteriorer_evilsaiyan`; Forge
  interpreta los `:` como namespace y buscaba una textura de armadura vanilla
  inexistente. Ahora devuelve un id simple y el item sobreescribe
  `getArmorTexture()` apuntando al atlas de GeckoLib.
- Estadísticas de armadura coherentes por tipo (durabilidad del pecho 900,
  defensa 9, dureza 3.0, resistencia al empuje 0.15).

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1
src/main/java/com/capatest/                         Mod, material, item (estados + aura), renderer, glow layer
src/main/resources/META-INF/mods.toml               Metadatos y dependencias
src/main/resources/assets/capatest/                 geo, animación, texturas, lang, modelo de item
tools/originals/                                   Texturas prístinas para regenerar
tools/texture_pipeline.py                          Pipeline de textura (Pillow + numpy)
tools/animation_pipeline.py                        Deriva sprint/air desde moving
.github/workflows/build.yml                        CI: push + workflow_dispatch
```

## Compilar

JDK 17 + Gradle 8.8 (el zip no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.1.0.jar
```

Para regenerar los assets (no hace falta para compilar, ya están commiteados):

```bash
python -m pip install Pillow numpy
python tools/texture_pipeline.py
python tools/animation_pipeline.py
```

## GitHub Actions

`push` y `workflow_dispatch` sobre `ubuntu-latest`: `actions/checkout@v4`,
`actions/setup-java@v4` (17/temurin), `gradle/actions/setup-gradle@v4` (8.8),
validación de recursos, `gradle build --no-daemon`, verificación del contenido
del jar y `actions/upload-artifact@v4` con `build/libs/*.jar`
(excluyendo `*-sources.jar`). Si la compilación falla, los errores de `javac` se
publican como anotaciones del run y se sube el log completo.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y `capatest-1.1.0.jar` en `mods/`.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`. Equipar en el **pecho** y usar
   **F5** para verla en tercera persona.
5. Comprobar: `idle` (3.6 s) en reposo, `moving` al caminar, `sprint` al correr,
   `air` al saltar, brillo pulsante y estela de partículas detrás del jugador.
