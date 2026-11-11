# Mantle of the Blight Star — v1.14.0

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade el **Mantle of the Blight Star**. Esta revisión rehace por completo la
capa equipada bajo la temática **Deterioro (Shigaraki) + Evil Saiyan Rosé**.

> ✅ **Publicada.** Compilada en CI (Gradle 8.8 / JDK 17) en el commit
> `5b7d86c`; Release `v1.14.0` es la *latest*. Los previews son render
> **software**: la prueba in-game sigue pendiente.

## Ver el modelo ANTES de compilar

- **Visor AUTOCONTENIDO (recomendado)**:
  [`docs/capa_v1140_visor.html`](docs/capa_v1140_visor.html). Es un único
  `.html` con la geometría, el atlas, los iconos, los GIFs y el `.bbmodel`
  incrustados como data URLs: se abre con doble clic, sin servidor, sin red y
  sin token. Se genera con `python3 tools/build_standalone_preview.py`.
  El sandbox tiene `allowPublicTraffic=false`, así que una URL cruda
  `https://8000-*.e2b.app` abierta fuera del *Live Preview* de Arena devuelve
  **403 MISSING TRAFFIC ACCESS TOKEN**: la plataforma sólo inyecta la cabecera
  `e2b-traffic-access-token` en su propio panel de preview. Para el visor en
  vivo, usar la pestaña **Live Preview** (puerto 8000), no el link en crudo.
- **Proyecto Blockbench**: [`docs/capa_v1140.bbmodel`](docs/capa_v1140.bbmodel)
  (jerarquía de huesos, rotación del hueso en el grupo y la del cubo en el
  elemento, UV por cara, `inflate`, atlas incrustado y un grupo
  `PLAYER · Steve/Alex (referencia)` para juzgar el ajuste del cuello).
  Se genera con `python3 tools/bbmodel_export.py`. Como el formato `bedrock`
  de Blockbench es de textura única, el atlas va en una imagen 128×144: las
  128 primeras filas son el atlas del mod (byte-idéntico) y las 16 últimas un
  parche sólido exclusivo del maniquí. También se puede descargar desde el
  visor autocontenido (enlace con `download=`), sin depender del proxy del
  sandbox ni de su token.
- **Previews**: [`docs/capa_v1140_preview.png`](docs/capa_v1140_preview.png),
  [`docs/capa_v1140_side_relief.png`](docs/capa_v1140_side_relief.png),
  [`docs/capa_v1140_icon_compare.png`](docs/capa_v1140_icon_compare.png).
  Son render software, no capturas in-game.

## Descargas directas (Release `v1.14.0`)

| Archivo | Link |
|---|---|
| **Mod compilado** (`capatest-1.14.0.jar`, 171700 B) | https://github.com/Santi-PdR/modelos/releases/download/v1.14.0/capatest-1.14.0.jar |
| **Proyecto Blockbench** (`capa_v1140.bbmodel`) | https://github.com/Santi-PdR/modelos/releases/download/v1.14.0/capa_v1140.bbmodel |
| **Visor 3D offline** (`capa_v1140_visor.html`) | https://github.com/Santi-PdR/modelos/releases/download/v1.14.0/capa_v1140_visor.html |
| Comparativa de 6 vistas | https://github.com/Santi-PdR/modelos/releases/download/v1.14.0/capa_v1140_preview.png |

Release: https://github.com/Santi-PdR/modelos/releases/tag/v1.14.0 ·
CI: https://github.com/Santi-PdR/modelos/actions/runs/43033963606 ✅ ·
`capatest-1.14.0.jar` crudo, nunca ZIP de `actions/upload-artifact`.
El repositorio es privado: hay que iniciar sesión en GitHub con la cuenta
`Santi-PdR` para descargar. Las entregas anteriores siguen en `v1.12.0`,
`v1.11.0`, `v1.10.0`, `v1.9.0`, `v1.8.0`, `v1.7.0`, `v1.6.1`, `v1.6.0`,
`v1.5.1`, `v1.4.0` y `v1.3.0`. **Usar v1.14.0**.

> PR #1 sigue abierta: https://github.com/Santi-PdR/modelos/pull/1

## v1.14.0 — Deterioro / Evil Saiyan Rosé

Petición: *«revisa y corrige a fondo el modelo (.bbmodel / JSON), rehaz su
textura y geometría para elevar masivamente su calidad visual y añade efectos
dinámicos bajo Deterioro (Shigaraki) y Evil Saiyan (Rosé). Usa la foto de
Blockbench como guía de volumen de jirones, partículas y energía»*.
El icono aprobado de v1.13.0 se **conserva en forma y estilo** y se adapta a
la nueva capa.

### 1. Integración en el jugador y collar de alta calidad

- **Collar / bufanda voluminoso**: dos anillos de **14 segmentos** cada uno
  alrededor de cuello y hombros (radio exterior 5.0×2.9, interior 4.0×2.3),
  con **solape real** entre segmentos (ancho 2.35 > paso del arco) y borde
  superior dentado por altura alterna. Nada de piezas flotantes.
- **20 flecos deshilachados** cuelgan de todo el contorno, delante y detrás.
- Un **yugo de 5 piezas** une el collar con la espalda y dos **hombreras
  envolventes** (`v15_rear_pad_*`) van de `Z=-1.35` a `Z=+3.75`, abrazando el
  hombro de delante a atrás.
- El `.bbmodel` incluye un maniquí Steve/Alex; el visor web lo activa por
  defecto para comprobar que el collar rodea el cuello y no lo atraviesa.

### 2. Geometría tridimensional de jirones complejos

| | v1.12.0 (rechazada) | **v1.14.0** |
|---|---|---|
| Superficie | lámina rectangular continua de 0.85 | **27 láminas base + 78 jirones largos** |
| Capas | 1 | **3 capas** con `inflate` `0.01 / 0.03 / 0.05` |
| Espesor de las tiras | 0.85 (bloque) | **0.25 – 0.50** |
| Borde inferior | festón regular | **puntas de longitud aleatoria** que se desmoronan |
| Huesos / cubos | 193 / 281 | **339 / 484** |

Todos los cubos nuevos llevan el campo `inflate` (estándar Bedrock, lo lee
Blockbench) **y** un desplazamiento explícito en Z de 0.01–0.05, así que no
hay Z-fighting aunque GeckoLib ignore `inflate`. Cada jirón tiene cuerpo +
punta estrecha desplazada, y 12 tiras se desprenden giradas por los costados.
`visible_bounds` → `6.0 / 5.6`.

### 3. Efectos de energía y desintegración

- **56 microvóxeles** de `1×1×1` / `2×2×2` px (`0.0625` / `0.125` unidades),
  8 fragmentos de ceniza, 18 **venas** finas y 4 núcleos orbitales. Cada
  microvóxel es un hueso con **pivote desplazado 0.6**: al girarlo en runtime
  la partícula se desplaza de verdad, sin partículas externas ni mixins.
- Se concentran **abajo, en los costados y alrededor del collar**, como en la
  referencia de Blockbench.
- Rampa de textura **rosa → magenta → violeta-negro** para las partículas y
  los bordes iluminados; venas y grietas con núcleo rosa encendido.

### 4. Textura avanzada: Rosé y oscuridad

Canvas continuo 96×48 rehecho: **carmesí muy oscuro → violeta-negro**, parches
de **morado desvaído** y **gris ceniza**, trama de sarga, agujeros rasgados y
**grietas de energía a trozos** (halo magenta, núcleo `#FF7AC8`, nodos y
ramificaciones diagonales). El glowmask mantiene **exactamente 1636 texels
emisivos**, pero se **redistribuyen** a las grietas y a la rampa de partículas:
no crece (no abre huecos) y ahora la energía brilla de verdad. Alfa base
prístino, UV ≤ 128.

### 5. Flujo dinámico

`CapaArmorModel` resuelve 225 huesos `v16_*` por nombre y les da fases
independientes: respiración del collar, ondeo de jirones con retardo por
segmento, pulso de venas y deriva de microvóxeles que responde a correr,
saltar y girar. Todo en **grados → `Math.toRadians`**, con `BoneSnapshot`,
fail-safe y restauración de la pose estática. Cero mixins.

### 6. Icono actualizado

Se conserva la silueta 16×16 y la técnica **plana/duro/`NEAREST`** que aprobaste
(sin degradados, AA ni bloom). Cambia la paleta a la capa nueva, añade grietas
de energía, dobladillo de **5 puntas** deshilachadas y **4 microvóxeles**
flotando. El CI decodifica el PNG real y comprueba la coincidencia con
`ICON_PIXEL_MAP`.

### Se conserva íntegro

ID `capatest:capa_deteriorer_evilsaiyan`, nombre/lore, tag Curios `back`,
canvas 96×48, `FOLDS=3`, los **72 huesos originales byte-idénticos**, 61
detalles boxy ocultos, 1636 emisivos, alfa base, `animation.item`, aura muda,
radianes, fail-safes, raíz sin `parent`, 0 `JsonNull`, 0 mixins y UV ≤ 128.

## v1.11.0 (histórico, rechazada) — el icono tenía su PROPIA FORMA

v1.10.0 había copiado la silueta de las dos referencias 16×16 (que en realidad
son el mismo icono recoloreado). v1.11.0 dibujó una forma nueva y simétrica:
dos picos de cuello con escote en V, hombreras salientes, cintura ceñida, tres
pliegues verticales y dobladillo de tres puntas, con broche diamante y estrella
cian. **Sólo cambió el icono**, por lo que la capa equipada siguió viéndose
plana y fue rechazada. Se conserva como histórico técnico y como base de la
regresión de silueta que hoy impide repetirla.

## v1.10.0 (histórico) — icono pixel art 2D RPG y tela reworkada

### 1. Icono: ahora SÍ es como las dos capas de referencia

El icono de v1.9.0 era una ilustración suave con degradados, hombreras
biseladas y halo: **no era el estilo que pediste**. Las dos referencias
`image-13.png` / `image-14.png` son en realidad **el mismo icono 16×16
recoloreado**: capucha redondeada, hombros, pliegues verticales, dobladillo,
5–6 colores planos, contorno duro y **cero antialiasing, degradado o bloom**.

v1.10.0 recuperó esa silueta y esa técnica (la silueta se sustituye en
v1.12.0 por la forma propia descrita arriba):

- `ICON_PIXEL_MAP`: los 16×16 píxeles de la referencia, con paleta plana de
  11 colores en violeta + oro + cian (`ICON_PALETTE`).
- broche de 5 píxeles con núcleo claro, estrella cian de 4 puntas en el
  pliegue central y vetas frías sueltas (equivalentes a las verdes de la
  referencia 2).
- **Ampliado 4× con `Image.NEAREST`** a 64×64: bloques de color definidos, sin
  blur, sin degradado, sin halo. Rim light discreto de 1 píxel en el borde
  superior/izquierdo para que se lea en el slot.
- `preview_cloth.py` también amplía el icono con `NEAREST` para no mentir en
  la comparación.

Comparativa a igual escala:
[`docs/capa_v1120_icon_compare.png`](docs/capa_v1120_icon_compare.png)
(referencia 1 · referencia 2 · icono nuevo). Icono final:
[`docs/capa_v1120_icon.png`](docs/capa_v1120_icon.png).

### 2. Textura: de líneas neón a paño tejido y bordado

Dijiste que la tela probablemente se veía fea; le di la pasada antes de que la
probaras. El problema de v1.9.0 era un **gran diamante magenta de líneas
finas** sobre fondo casi negro, con bloom rosa: parecía un wireframe, no tela.
v1.10.0:

- **sarga con más presencia**: trama, diagonal, urdimbre, grano y sombreado
  de los 3 pliegues; el paño deja de ser un plano oscuro.
- **medallón relleno** con facetas oscuras y bisel, engarce **dorado** y
  núcleo cian de Blight Star; ya no es un contorno magenta vacío.
- **bordado a puntadas** (`stitch()`) en yugo, doble ribete, constelación,
  sigilos, valles de los pliegues y dobladillo, en hilo oro/violeta en vez de
  líneas luminosas continuas.
- estrellas y pespuntes en oro apagado; esporas frías más escasas; **bloom
  reducido a menos de la mitad**; cian sólo en el núcleo y los 8 rayos.
- el bulto plegado, las hombreras y la gema del broche se retiñeron a la misma
  paleta oro/violeta/cian para que item y capa equipada combinen.

**Intacto**: alfa base byte-idéntico, **1636 texels emisivos** sin ampliar el
glowmask de armadura, UV≤128, canvas 96×48, 648 caras UV nuevas en zonas
opacas, onda 2D/3D compartida y superficie lisa.

### 3. Se conserva todo lo de v1.9.0

Relieve 3D (**193 huesos / 281 cubos**: 9 nervios, 2 cortinas, 5 pesas,
cuello trasero, tirantes y arnés delantero con hombreras/cadenas/placa),
`animation.item` en GUI/hotbar/mano, glowmask de dos tintas del item, aura de
brasas + motas cian con presupuesto fijo de 4 partículas por tick de emisión,
**sin `playSound` ni `SoundEvent` propio**, fail-safes, radianes, cero
`JsonNull`, cero mixins y Curios `back`.

Los previews de esta versión son render software; la prueba in-game queda para
tu próximo arranque (v1.8.0 ya confirmó arranque, capa equipada y bulto 3D).
Previews: [`docs/capa_v1120_preview.png`](docs/capa_v1120_preview.png)
(6 vistas), [`docs/capa_v1120_uv_test.png`](docs/capa_v1120_uv_test.png),
[`docs/capa_v1120_item_glowmask.png`](docs/capa_v1120_item_glowmask.png),
[`docs/capa_v1120_particles.png`](docs/capa_v1120_particles.png),
[`docs/capa_v1120_front_rig.png`](docs/capa_v1120_front_rig.png),
[`docs/capa_v1120_side_relief.png`](docs/capa_v1120_side_relief.png) y la
comparativa del icono.

## Opciones de nombre (todas en inglés)

Implementado: **Mantle of the Blight Star**. Si prefieres otra combinación,
dime cuál y la cambio sólo en `en_us.json` / `es_es.json` (el ID interno se
queda):

| English name | Sensación |
|---|---|
| **Mantle of the Blight Star** | Cósmico, directo; **implementado** |
| Blight Star Mantle | Más corto, tipo item de RPG |
| The Blight Star's Shroud | Más oscuro y narrativo |
| Dying Light of Blight Star | Conserva explícitamente «Dying Star» |
| Blightstar Veil | Nombre compuesto, ligero |
| Last Ember of Blight Star | Enfatiza aura y brasas |

## v1.9.0 (histórico) — Blight Star, relieve, arnés y animación del item

- Nombre **Mantle of the Blight Star** en inglés, lore traducido, ID interno
  conservado.
- Medallón de estrella marchita, 4 fragmentos orbitales 3D, esporas frías y
  segundo tipo de partículas (`capa_blight_mote`) en aura muda.
- Relieve 3D y **arnés delantero** con hombreras, cadenas y placa animadas;
  193 huesos / 281 cubos.
- Bulto plegado de 36 huesos con hombreras y **`animation.item`** (bob,
  apertura de pliegues, giro/pulso del broche).
- Icono de ilustración suave y canvas de líneas magenta: **ambos reemplazados
  en v1.10.0** por el pixel art 16×16 y el paño bordado.

## v1.8.0 (histórico) — bulto 3D, icono proporcionado y material

- El item en mano/slot dejó de ser un abanico plano: **bulto 3D de 34 huesos**
  con forro, 7 franjas con relieve, yugo, cuello, broche de diamante,
  cadenas, tiras, 3 rollos y 5 puntas de dobladillo.
- Se corrigió el **recorte**: icono 64×64 y atlas plegado 128×128 dejaron de
  estirar el canvas 96×48 a un cuadrado (`cloth_canvas_fitted`). Display
  transforms ajustados y `FULL_SKY` fuera de GUI.
- `CapaItemGlowLayer` estrenó `cape_folded_glowmask.png` con `RenderType.eyes`
  y pulso de 2.6 s, sin modificar el atlas base.
- Capa equipada: medallón completo, doble ribete, sigilos, constelación,
  filigrana, dobladillo de 4 texels y **5 estrellas 3D** emisivas.
  **131 huesos / 185 cubos**, 354 caras UV nuevas, 1636 emisivos intactos.
- Nombre neutro *Dying Star Mantle* / *Manto de la Estrella Moribunda*, que
  v1.9.0 sustituyó por la combinación con Blight Star.

## v1.7.0 (histórico) — pliegues anchos y material con relieve



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

Los previews son render software; esta versión ya tiene capturas in-game.

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

Resultados versionados de **v1.12.0**:
[`docs/capa_v1120_preview.png`](docs/capa_v1120_preview.png) (bulto plegado, frente, 3/4, espalda, relieve y hombreras 3D),
[`docs/capa_v1120_uv_test.png`](docs/capa_v1120_uv_test.png) (franjas UV),
[`docs/capa_v1120_icon.png`](docs/capa_v1120_icon.png) (icono pixel art 64×64 rediseñado) y
[`docs/capa_v1120_item_glowmask.png`](docs/capa_v1120_item_glowmask.png)
(efecto emisivo del item) y
[`docs/capa_v1120_particles.png`](docs/capa_v1120_particles.png) (brasas + motas),
[`docs/capa_v1120_front_rig.png`](docs/capa_v1120_front_rig.png),
[`docs/capa_v1120_side_relief.png`](docs/capa_v1120_side_relief.png) y
[`docs/capa_v1120_icon_compare.png`](docs/capa_v1120_icon_compare.png) y
[`docs/capa_v1120_silhouette_compare.png`](docs/capa_v1120_silhouette_compare.png).

## Diagnóstico de crashes: dos fallos distintos

Hubo **dos crashes diferentes** y conviene no confundirlos. Las capturas
in-game de v1.8.0 ya muestran el juego arrancado, así que el de mixins quedó
como diagnóstico histórico para ese pack, no como bloqueo actual:

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
   `capatest-1.12.0.jar`. Si arranca, ve añadiendo el resto de 5 en 5 hasta que
   reaparezca el `MixinTransformerError`: el culpable está en ese grupo.

`skinlayers3d`, `embeddium`, `photon`, `flywheel`, `create` y los demás salen
en el stack sólo porque también aplican mixins a `Minecraft` o
`EntityRenderDispatcher`; no son la excepción. `Flywheel Backend: flywheel:off`
es un dato informativo. El `Código de salida: 4294967295 (0xFFFFFFFF)` es
simplemente `-1` como unsigned: el launcher indica "se cerró con error", no
aporta más causa.

Ese conflicto **ya no aparece en las capturas in-game de v1.8.0**: el juego
arranca y la capa se renderiza. Si vuelve a aparecer en otro pack, resuélvelo
primero, porque entonces sí bloquearía cualquier mejora visual.

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
  implementación se validó con previews software y, desde v1.8.0, también con
  capturas in-game de la capa equipada y del item en mano/slot. Para el icono
  v1.10.0/v1.12.0 se usaron además dos referencias 16×16 aportadas por el usuario
  (capa granate con broche cálido y capa negra con ribete neón); véase
  `docs/capa_v1120_icon_compare.png`.

## Estructura

```
build.gradle / gradle.properties / settings.gradle   ForgeGradle 6, Gradle 8.8, GeckoLib 4.8.1, Curios 5.14.1 (compileOnly)
src/main/java/com/capatest/                         Mod, material, item, renderers, CapaArmorModel, glow layers, 2 clases de partículas, compat Curios
src/main/resources/META-INF/mods.toml               Metadatos: Forge + GeckoLib obligatorios, Curios opcional
src/main/resources/assets/capatest/                 geo/animaciones 3D, texturas, sprites, lang, modelo builtin/entity
src/main/resources/data/                           tag curios:back + concesión del slot al player
tools/originals/                                   PNG prístinos + geo de armadura prístino
tools/cloth_spec.py                                 Canvas 96×48, 9 columnas, FOLDS=3/fold_wave, SECTION_V, UV opacas y zonas reservadas
tools/fold_spec.py                                 Bulto plegado: 7 franjas, rollos, gem y regiones reservadas
tools/texture_pipeline.py                          Atlas, canvas bordado, icono pixel art 16x16, folded, glowmask y 2 sets de sprites
tools/armor_model_pipeline.py                      9×3 + fold_wave, nervios 3D, cortinas, pesas, arnés frontal y órbitas
tools/item_model_pipeline.py                       Bulto de 36 huesos + 5 animaciones (incluida animation.item)
tools/animation_pipeline.py                        Deriva sprint/air desde moving
tools/preview_cloth.py                             6 vistas, arnés aislado, relieve de perfil, canvas/icono/partículas y --uv-test
docs/capa_v1120_preview.png                         Preview versionado de las seis vistas de la capa
docs/capa_v1120_uv_test.png                         Test visual del orden UV del mosaico 9×3
docs/capa_v1120_icon.png                            Icono pixel art 64×64 ampliado ×4
docs/capa_v1120_item_glowmask.png                   Efecto emisivo violeta/cian del item plegado
docs/capa_v1120_particles.png                       Brasas cálidas + motas frías de Blight Star
docs/capa_v1120_front_rig.png                       Arnés delantero aislado
docs/capa_v1120_side_relief.png                     Perfil del relieve 3D
docs/capa_v1120_icon_compare.png                    Referencias 16×16 frente al icono de forma propia
docs/capa_v1120_silhouette_compare.png              Máscaras alfa: refs frente a la silueta propia
.github/workflows/build.yml                        CI: validación, build, verificación del jar y Release .jar directo
```

## Compilar

JDK 17 + Gradle 8.8 (el zip original no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.12.0.jar
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
geo plegado sin `parent` (36 huesos de bulto) + **193 huesos / 281 cubos** +
27 paneles 9×3 + 9 creases + 9 nervios + arnés delantero + 5 estrellas y 4 órbitas 3D +
onda compartida entre el canvas 2D y `panel_z()` + icono/atlas con proporción
real + glowmask del item de dos tintas + 6 sprites + 5 animaciones + aura muda + 61 huesos boxy ocultos sin descendientes `v15_*` +
UV nuevas en zonas opacas + hashes prístinos + regresión de radianes/sin
`getBakedModel()` +
**ausencia de mixins** + tag/entidad Curios, `gradle build --no-daemon`, verificación de las entradas
del jar y publicación del **`.jar` directo** en el Release `v1.12.0`. Si falla,
los errores de `javac` se publican como anotaciones y se sube el log completo
como artifact aparte (que **no** es la entrega).

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x) con Java 17.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1**:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner GeckoLib y **`capatest-1.12.0.jar`** en `mods/`.
   Si el juego crashea **al arrancar** con `MixinTransformerError`, ver la
   sección «Diagnóstico de crashes»: es un conflicto entre otros mods.
4. Mundo creativo; la capa está en **Combate** o con
   `/give @s capatest:capa_deteriorer_evilsaiyan`.
5. **Sin Curios**: equipar en el **pecho** y usar **F5**.
6. **Con Curios 5.14.1+1.20.1** (opcional, p. ej. desde
   https://modrinth.com/mod/curios): abrir el inventario de Curios y ponerla en
   el slot **`back`**; se ve y anima igual que en el pecho.
7. Comprobar: bulto plegado que **se balancea y abre pliegues** en
   hotbar/mano/slot, con estrella cian y brillo violeta/cian; icono con
   hombreras, cuello y festón; capa equipada con **relieve 3D notorio**
   (nervios, cortinas laterales, pesas), **arnés delantero** con hombreras,
   tiras, cadenas y placa, y una sola ilustración continua en la espalda.
   Al caminar/correr ondean pliegues, hombreras y cadenas; `idle` (3.6 s),
   `moving`, `sprint`, `air` y `animation.item`; brillo que vira a cian al
   perder vida o correr; brasas violeta y **motas cian mudas** en órbita
   corta, sin partículas por el cielo ni sonido.
