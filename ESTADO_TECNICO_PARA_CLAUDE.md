# Estado técnico del proyecto (para Claude)

Snapshot del repo `Santi-PdR/modelos`, rama `arena/1ea42902-modelos`,
HEAD `c3c7803` (v1.15.0). La versión **v1.15.0 está publicada pero fue
rechazada visualmente**; el usuario pide rehacer la skin con otro agente.

## 1. Lo que el usuario dijo, textualmente

- v1.13.0: aceptó el icono `blight`.
- v1.14.0: «el icono quedo muy god, compila el mod... y compila» → aprobó el
  icono **Rosé** y autorizó publicar.
- Después, al ver el resultado: «Que es esto amigo, no se parece en nada a lo
  que te pedí, además faltan las animaciones-».
- v1.15.0 (corrección): «Esta muy mal hecho hermano, la skin de la capa, la
  haces muy mal por alguna razon. dame un zip con el proyecto y un prompt,
  lo hare con claude. ... el icono esta bien».

⇒ **El icono está bien. El problema es la skin / textura de la capa equipada.**
No hay autorización para seguir rediseñando ni para publicar sin aprobación
visual previa.

## 2. Mapa del repo

```
build.gradle, settings.gradle, gradle.properties   Forge 1.20.1 / 47.3.0 / Java 17 / Gradle 8.8
.github/workflows/build.yml                       valida recursos, compila, publica .jar + assets
src/main/java/com/capatest/                      mod, renderers, Curios, partículas
src/main/resources/assets/capatest/
  geo/item/armor/capa_deteriorer_evilsaiyan.geo.json   ← GEOMETRÍA EQUIPADA (lo que se ve en el juego)
  geo/item/cape_folded.geo.json                        item 3D plegado (inventario)
  animations/item/...                                  animaciones GeckoLib del item
  textures/item/armor/capa_deteriorer_evilsaiyan.png   ← ATLAS 128×128 DE LA CAPA
  textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png
  textures/item/capa_deteriorer_evilsaiyan.png         ← ICONO 64×64 APROBADO (NO TOCAR)
  textures/item/cape_folded.png + _glowmask.png        item plegado
  textures/particle/*.png                              sprites de partículas
src/main/resources/data/capatest/curios/...           slot back
src/main/resources/META-INF/mods.toml, pack.mcmeta

tools/originals/            copias PRÍSTINAS aprobadas (geo 72 huesos, atlas, glowmask, icono)
tools/armor_model_pipeline.py   genera el .geo.json equipado desde tools/originals
tools/cloth_spec.py             OPAQUE_RECTS, UV, chunk(), assert_opaque()
tools/texture_pipeline.py       genera atlas, glowmask, item plegado, ICONO y canvas 96×48
tools/bbmodel_export.py         exporta .bbmodel (bedrock, 1 textura, UUID canónicos, 4 animaciones)
tools/preview_cloth.py          render software de 6 vistas + --uv-test
tools/build_standalone_preview.py   empaqueta preview/ en un único HTML sin fetch
tools/item_model_pipeline.py, animation_pipeline.py, fold_spec.py   item plegado
preview/                        visor web (index.html, app.js, assets/) — IGNORADO por git, sí incluido en el ZIP
docs/                           previews PNG, .bbmodel, visor HTML autocontenido
README.md                       historial largo de versiones
```

Cadena de generación (ejecutar en este orden, con `PYTHONPATH=tools/_deps`):

```
armor_model_pipeline.py ──► geo equipado
texture_pipeline.py     ──► atlas + glowmask + item + ICONO (¡regenera el icono!)
bbmodel_export.py       ──► docs/*.bbmodel + preview/assets/*.bbmodel
preview_cloth.py        ──► PNGs de las 6 vistas
build_standalone_preview.py ──► docs/*_visor.html
```

Dependencias: `python3 -m pip install --target tools/_deps Pillow numpy PyYAML`.
No hay `gradle`, `java` ni `javac` en el sandbox; el build Java lo hace
GitHub Actions (`Gradle 8.8 / JDK 17`) al hacer push.

## 3. Invariantes que el CI comprueba

Bloque `Validate resources` de `.github/workflows/build.yml`. Resumen:

- Forge 1.20.1-47.3.0, Java 17, GeckoLib 4.8.x, Curios `5.14.1+1.20.1`.
- `mod_id=capatest`, ID de item/geo `capa_deteriorer_evilsaiyan`, slot
  `curios:back` + `player/back`, `animation.item` presente, sin mixins.
- Geo equipado: los **72 primeros huesos byte-idénticos** a
  `tools/originals/capa_deteriorer_evilsaiyan.geo.json`; raíz sin `parent`;
  **0 `JsonNull`**, **0 `"parent": null`**; `visible_bounds_width=6.0`,
  `height=5.6`, `offset=[0,0.5,0]`.
- Todas las UV nuevas dentro de `OPAQUE_RECTS` (atlas 128×128, UV ≤ 128),
  alfa prístino, **1636 texels emisivos** intactos en el glowmask.
- `inflate` en (0.01, 0.03, 0.05) y espesor de tela 0.25–0.50; rotaciones en
  **radianes** en `CapaArmorModel.java` con fail-safes; `DETERIORO_NAMES`
  debe coincidir con los `v16_*` reales.
- `.bbmodel`: `meta.format_version="5.0"`, `model_format="bedrock"`,
  `box_uv=false`, **1 sola textura** (`single_texture: true`), UUID canónicos
  8-4-4-4-12, al menos una animación con keyframes cuyos animadores apunten a
  UUID de grupos existentes.
- Visor standalone: 0 `fetch`, 0 referencias `assets/`, `INLINE_GEO`, y un
  enlace con `download=` para el `.bbmodel`.
- El `.jar` se publica **crudo** como Release asset (nunca un ZIP de
  `actions/upload-artifact`), junto con `.bbmodel`, visor HTML y preview PNG.

## 4. Estado actual de los archivos (v1.15.0, RECHAZADA)

- Geometría: **290 huesos / 377 cubos**. 27 paneles `v15_cloth_*` gruesos,
  11 cintas `v16_tatter_*` de 3 tramos, 18 `v16_hem_*`,
  `v16_collar_*` 32 segmentos (2 anillos de 16), 24 `v16_fray_*`,
  5 `v16_yoke_*`, 10 `v16_shred_*`, 12 `v16_vein_*`, 56 `v16_mote_*`,
  8 `v16_ash_*`, 9 `v15_hem_*`, 4 `v15_orbit_*`, 2 `v15_rear_pad_*`.
- Canvas 96×48 (`build_armor_cloth_canvas`): carmesí/morado/ceniza con 4
  grietas. Aun así el usuario dice que la skin está muy mal hecha.
- `.bbmodel`: 383 cubos, 291 grupos, **4 animaciones** (`idle_respiracion`,
  `caminar`, `correr_saltar`, `deterioro_particulas`), **5008 keyframes** sobre
  212 huesos, maniquí Steve/Alex con cara y túnica, textura 128×144.
- Release `v1.15.0` (latest, publicada 2026-11-11T14:31:07Z), CI
  `43038672713` ✅. Release `v1.14.0` anterior, también rechazada.
- PR #1 abierto.

## 5. Errores ya cometidos (no repetir)

1. **v1.14.0**: 78 tiras finas magenta del mismo ancho → una jaula; cubo
   blanco por cabeza; `.bbmodel` con `animations: []`. Franjas rosa regulares
   en la zona `yoke` del atlas: los 32 segmentos del collar muestreaban las
   mismas dos líneas y formaban una reja.
2. **UUID md5 de 32 caracteres**: `Animation.extend()` de Blockbench exige
   `isUUID()` de 36 caracteres con guiones; si no, crea un uuid aleatorio y
   los keyframes quedan huérfanos. Ya corregido con `uid()` en
   `tools/bbmodel_export.py`.
3. **2 texturas en un `.bbmodel` `bedrock`**: inválido, ese formato tiene
   `single_texture: true`. Solución: una imagen 128×144 (atlas + parche del
   maniquí).
4. **Relieve/parábolas y grietas continuas**: `RELIEF=0.52` y puentes en Z
   dieron tablones; 9 senos de sombreado sin relación con la onda 3D dieron
   una tabla rayada.
5. **E2B 403**: la URL cruda `https://8000-*.e2b.app` fuera del Live Preview
   da `MISSING TRAFFIC ACCESS TOKEN` (`allowPublicTraffic=false`). Por eso
   existe el visor HTML autocontenido y los assets se suben a la Release de
   GitHub; no sirve un link directo al sandbox.
6. Entorno: `tools/_deps` se pierde entre sesiones → reinstalar con pip;
   `gh release view --json isLatest` no existe; `upload-artifact@v4` siempre
   comprime en ZIP (rechazado por el usuario).
7. Proceso: **se publicó dos veces antes de aprobación visual**. No repetir.

## 6. La referencia

`referencias/01_OBJETIVO_blockbench.png` es la captura de Blockbench que el
usuario dio como guía de volumen. Ver `referencias/README.md` para el detalle
de cada imagen. Las capturas in-game (`04_*`) son de versiones anteriores y
sirven para entender la escala sobre el jugador, **no** como objetivo de
diseño.
