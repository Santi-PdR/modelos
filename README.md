# Capa Deteriorer Test — v1.2.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade la *Capa Deteriorer Evil Saiyan*: geometría propia de 72 huesos, cuatro
animaciones, textura de 128×128 con glowmask pulsante, **modelo 3D en el
inventario**, **partículas propias** y compatibilidad opcional con el slot
**`back` de Curios API**.

## Novedades de v1.2.0

**Modelo 3D del ítem (adiós icono 2D)**
- `assets/capatest/models/item/capa_deteriorer_evilsaiyan.json` usa
  `parent: builtin/entity` y `CapaDeteriorerItem#initializeClient` devuelve un
  `GeoItemRenderer` propio (`CapaItemRenderer`).
- Geo, animación y atlas independientes (`cape_folded.*`), generados por
  `tools/texture_pipeline.py`: la capa aparece plegada y con leve balanceo en
  GUI, mano, suelo y marco; la armadura puesta sigue usando el modelo grande
  de 126 cubos sin cambios.

**Partículas propias del mod**
- `SimpleParticleType` `capatest:capa_ember` registrado en
  `ForgeRegistries.PARTICLE_TYPES`, con
  `assets/capatest/particles/capa_ember.json` y tres PNG de 16×16 en
  `assets/capatest/textures/particle/`.
- `CapaEmberParticle` + `RegisterParticleProvidersEvent#registerSpriteSet`
  (bus MOD, sólo cliente): sprites animados, tinte magenta/violeta y fundido.
- `ServerLevel#sendParticles` emite las brasas detrás del jugador; las partículas
  vanilla (`SOUL_FIRE_FLAME` / `PORTAL` / `CRIMSON_SPORE`) quedan como refuerzo.

**Slot `back` de Curios (dependencia blanda)**
- `data/curios/tags/items/back.json` mete la capa en el tag `curios:back` y
  `data/capatest/curios/entities/player.json` concede el slot `back` al jugador
  (los slots predefinidos de Curios **no** se añaden por defecto).
- `CuriosCompat` se carga **por reflexión** únicamente si `ModList` detecta
  `curios`; registra un `ICurioItem` con `canEquip` restringido a `back` y
  reutiliza `spawnAura` desde `curioTick`. Sin Curios la capa sigue funcionando
  exactamente igual en el slot de pecho.
- `CapaCurioRenderer` registra un `ICurioRenderer` en `FMLClientSetupEvent` y
  delega en el mismo `GeoArmorRenderer` (`prepForRender(CHEST)` + `defaultRender`
  con el `MultiBufferSource` de Curios), conservando brillo y animaciones.
- `build.gradle` compila contra `curios-forge:5.14.1+1.20.1:api` con
  `compileOnly`: el jar de Curios **no** se empaqueta ni es obligatorio.

> Las animaciones `animation.idle` y `animation.moving` siguen siendo
> byte-idénticas a las originales aprobadas.

## BASE v1.1.0 (resumen)

- **Textura**: `tools/texture_pipeline.py` mejora sólo los canales RGB de los
  texeles ya opacos (68.6 % del atlas), conservando el alfa. El glowmask mantiene
  sus 1636 texeles, porque GeckoLib 4.8 usa únicamente su alfa.
- **Animación**: `tools/animation_pipeline.py` deriva `sprint` (0.72 s) y `air`
  (1.35 s) desde `moving` sin tocar `idle`/`moving`. Detección de movimiento con
  `getDeltaMovement()` + `onGround()` + `isSprinting()` (bug fix del parpadeo).
- **Efectos**: `CapaGlowLayer` con latido de 3.2 s, amplitud al correr y viraje
  carmesí según la vida; aura emitida desde servidor; `Rarity.EPIC`,
  `fireResistant`, glint y tooltips en_us/es_es.
- **Corrección**: `ArmorMaterial#getName()` sin `:` y `getArmorTexture()`
  apuntando al atlas de GeckoLib; defensa 9, dureza 3.0, empuje 0.15,
  durabilidad de pecho 900.

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1, Curios API (compileOnly)
src/main/java/com/capatest/                         Mod, material, item, renderers, glow layer, partículas, compat Curios
src/main/resources/META-INF/mods.toml               Metadatos: Forge + GeckoLib obligatorios, Curios opcional
src/main/resources/assets/capatest/                 geo/animaciones 3D, texturas, sprites, lang, modelo builtin/entity
src/main/resources/data/                           tag curios:back + concesión del slot al player
tools/originals/                                   Texturas prístinas para regenerar
tools/texture_pipeline.py                          Atlas de armadura, icono, atlas 3D y sprites (Pillow + numpy)
tools/animation_pipeline.py                        Deriva sprint/air desde moving
.github/workflows/build.yml                        CI: push + workflow_dispatch
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.2.0.jar
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
validación de JSON/PNG (incluye tag y entidad de Curios), `gradle build
--no-daemon`, verificación de las entradas del jar (clases, geo 3D, 3 sprites,
datos) y `actions/upload-artifact@v4` con `build/libs/*.jar` (excluyendo
`*-sources.jar`). Si falla, los errores de `javac` se publican como anotaciones
y se sube el log completo.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y `capatest-1.2.0.jar` en `mods/`.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: modelo 3D en el hotbar/mano, `idle` (3.6 s), `moving`, `sprint`,
   `air`, brillo pulsante/rojo al perder vida y brasas propias detrás del
   jugador (también visibles para otros jugadores).
