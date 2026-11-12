# Mantle of the Blight Star — v1.17.2

Mod de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Capa equipada en `curios:back`, temática
**Deterioro (Shigaraki) + Evil Saiyan Rosé**.

> 📦 **Release vigente: `v1.17.2`** (JAR compilado en CI). v1.14.0, v1.15.0
> y v1.16.0 fueron rechazadas visualmente y sus previews se han borrado del
> repo. Los previews actuales son render **software**: la prueba in-game y
> la aprobación visual siguen pendientes.

## Empecé de 0 usando TU referencia

Dijiste: *«quiero que empieces de 0 … aún no te veo usando las referencias
que hice para ti … quiero que quede exactamente como en la imagen»*.
Esta vez el modelo **no se diseña a ojo**: se MIDE el PNG.

| Artefacto | Qué hace |
|---|---|
| [`referencias/REFERENCIA_CAPA.png`](referencias/REFERENCIA_CAPA.png) | Tu captura de Blockbench, guardada en el repo |
| [`tools/reference_trace.py`](tools/reference_trace.py) | Segmenta paño / energía, mide envolvente, paleta por fila y **54 grietas rosa** + motas flotantes |
| [`tools/reference_profile.json`](tools/reference_profile.json) | 31 puntos de silueta, 21 filas de paleta, marcas de energía |
| [`docs/referencia_analizada.png`](docs/referencia_analizada.png) | Prueba visual: recorte, máscara, envolvente y paleta medida |
| [`tools/cape_shape.py`](tools/cape_shape.py) | Fuente de verdad compartida: campana medida, puntas, bandas UV |
| [`tools/texture_pipeline.py`](tools/texture_pipeline.py) | **Des-abanica** el recorte limpio en el atlas 96×48: cada jirón lleva los colores que le tocan en tu captura |

La **cabeza blanca es sólo escala del maniquí**: no se modela.

### Qué había mal y qué hay ahora

v1.14/15/16 eran un **cilindro de tiras paralelas** con cantos claros y UV a
trozos → rejilla. La referencia es una **CAMPANA** medida: nace estrecha en el
cuello, se abre hasta ±10 unidades hacia t≈0.73 y vuelve a cerrarse
en un dobladillo ancho de puntas desiguales.

- **16 jirones** en **abanico en V de dos niveles**, con 6 tramos y punta real, con banda UV vertical única; se
  ensanchan al bajar y rematan en punta corta (no agujas).
- **Bufanda carmesí en U** con escote bajo la cabeza, alas inclinadas,
  9 dientes rasgados delante y 5 piezas detrás para la vista F5.
- **Color medido**: carmesí `(58,25,37)` → rojo vivo `(81,23,40)` →
  violeta `(70,29,65)` → violeta desvaído `(79,41,78)`. Agujeros negros
  y grietas rosa cortas salen del PNG, no de un generador aleatorio.
- **18 motas rosa flotantes** como vóxeles 3D separados (las 8 medidas
  en la captura + 10 con la misma distribución, más densas abajo).
- **10 tejas solapadas** que cruzan la campana por delante: rompen la
  regularidad de los rayos sin volver a la rejilla rechazada.
- **10 venas 3D emisivas** sobre las grietas reales del PNG: `v17_vein_*`
  **pulsan** en Java, en el visor y en las 4 animaciones del `.bbmodel`.
  Las cuchilladas rosa largas también viven en el glowmask (1636 emisivos).
- **Icono 64×64 INTOCABLE**: **pixel art** 16×16 ampliado con NEAREST, con
  hombreras y silueta propia (no la de las referencias viejas). SHA-256
  `c90670ba367557d7c7c003fa38dbe10c27cc88dcee1ef37fedc48f3a82820ee5`.
  El icono APROBADO anterior sigue intacto en
  [`referencias/ICONO_APROBADO_BACKUP.png`](referencias/ICONO_APROBADO_BACKUP.png)
  y `tools/originals/icono_aprobado_v1130.png` (SHA `e88ccec0…4840`);
  `python3 tools/restore_icon.py` lo restaura en un comando.

### Autoevaluación medida y acabado artesanal (v1214)

Se midió el render contra el PNG con la **misma máscara** en décimas de
altura (mediana RGB del paño, cobertura, densidad de energía y semiancho de
silueta). El error global bajó de ~326 a **189**: cobertura 138 → 85 pp,
energía 100 → 69 pp, color 265 → 107, silueta 1.74× → 1.50×.

- **Masa de tela**: dobladillo, canales, rotos y agujeros recalibrados.
  La captura tiene paño, no un esqueleto de líneas sobre fondo negro.
- **Energía**: trazos cortos en guiones y codos en L; solo las **8 motas
  medidas** en el PNG son rosa vivo, las otras 18 son rescoldo violeta.
- **Calibración en lazo cerrado**: `tools/color_calibration.py` mide y
  acumula la diferencia por altura en `tools/color_calibration.json`;
  `texture_pipeline.py` la interpola sobre las 48 filas del canvas,
  ponderada por luminancia para no teñir los huecos. Sin franjas.
- **Capucha en alas** y **una sola banda gris** de arnés (antes tres
  franjas escalonadas); costuras de hombro y pliegues cosidos a mano.
- **Animaciones**: 12 muestras de onda por hueso, respiración de capucha,
  tirón de gravedad por tramo (seg4/5/6), ráfaga lenta en Java, marcadores
  en los **4 clips** y **tres emisores** Snowstorm (`capa_embers` al correr
  y deteriorarse, `capa_embers_calm` en reposo y al caminar, `capa_shards`
  solo en deterioro), con color que
  se apaga con `variable.ParticleAge`. 11950 keyframes, tangentes C1 en
  las curvas de rotación.

### Release vigente: v1.17.2

El JAR **más reciente** se publica como Release
[`v1.17.2`](https://github.com/Santi-PdR/modelos/releases/tag/v1.17.2):
`capatest-1.17.2.jar`, compilado en CI con JDK 17 + Gradle 8.8 sobre la
**textura rehecha v1.17.2**. La Release `v1.17.0` queda como histórico
(contiene una build anterior); no se sobreescribe. El workflow publica con
`workflow_dispatch(publicar=true)` o con un commit marcado `[publicar]`, y
lee la versión de `gradle.properties` para que el nombre del JAR nunca
quede desincronizado.

### Tests en GitHub y efectos en runtime (v1220)

`tools/audit_model.py` es un **test de regresión numérico**: renderiza el
geo+atlas reales y compara décima a décima con `REFERENCIA_CAPA.png`
(mediana RGB, cobertura de paño, densidad de energía y silueta). El workflow
`build.yml` lo ejecuta con `--check` **antes de compilar**, instala
`numpy`/`Pillow` y **falla el build** si el error global supera 165
(estado actual: 100.3; la textura prioriza la lectura visual limpia sobre el número). Así la autoevaluación no depende de mi sandbox.

Además, los keyframes `particle` del `.bbmodel` no se disparan solos en
Java/GeckoLib: `CapaDeteriorerItem.spawnAura(..., deterioro)` replica los
tres emisores en runtime (rescoldo en reposo, 2 brasas + estela al correr,
3 brasas + 2 motas frías con el ítem dañado o vida baja), desde el servidor
para que lo vean los demás jugadores. `CuriosCompat` usa el mismo estado.
**La CI de GitHub compila este cambio con JDK 17 + Gradle 8.8.**

### Icono remasterizado y tercer emisor (v1225)

- **Icono**: conserva la silueta 16×16 aprobada, pero cada fila toma la
  paleta MEDIDA del PNG (carmesí arriba → violeta abajo), con relieve 3D por
  píxel, grietas cortas, costuras de jirón y 8 motas flotantes. Sigue siendo
  pixel art duro (NEAREST, sin AA ni bloom). **Backup byte-idéntico** arriba.
- **Tercer emisor**: `capatest:capa_shards` — esquirlas de deterioro con 3
  sprites propios, `CAPA_SHARD` registrado en Java, disparadas solo con el
  ítem dañado o vida baja, y alternadas con las brasas en el Effects track
  de `deterioro_particulas`. El presupuesto sigue fijo (7 partículas/tick).
- **Textura**: puntas y dobladillo aclarados, energía del canvas recortada en
  mitad y puntas. Error global de la autoevaluación **190.84 → 179.30 → 138.96**
  (cobertura 85.9→73.5, energía 57.1→32.8, color 109→98, silueta 1.54×→1.42×).
- **Visor 3D**: especular suave y rim reforzado para que los pliegues tengan
  volumen; el cambio no toca el rasterizador que mide la CI.


### Ronda v1240: forma, energía y movimiento calibrados

- **Forma**: la envolvente medida del PNG se escaló al ancho real del render
  (0.82×) y se sustituyó la campana por un **abanico radial en V de dos
  niveles**: las alas exteriores nacen inclinadas desde el cuello, mueren a
  `t≈0.72` y solo los jirones centrales cuelgan hasta el dobladillo. Las
  puntas dejaron de ser astillas negras y ahora son paño violeta.
  *(v1283 revisa este punto: las alas cortas vaciaban `t=0.8`; ahora todos
  los lóbulos llegan a `t≥0.90` y la V cierra monótona.)*
- **Energía**: `tools/energy_calibration.py` es un **segundo lazo cerrado**
  (Jacobiano medido de 10 bandas) que ajusta `ENERGY_GAIN` en
  `texture_pipeline.py`. `shape_energy_density()` adelgaza la tinta **trazo a
  trazo** (componentes 8-conectados), no píxel a píxel: sin damero, con
  guiones discontinuos como los de la captura. Error de energía
  **57.1 → 32.8 pp**.
- **Color**: tres pasadas más de `tools/color_calibration.py` cerraron el
  degradado (error 109 → 98) sin teñir los huecos.
- **Animaciones**: tercer armónico de ondeo (`flutter`) con **derivada
  analítica** en las tangentes Bézier, más vivo en las puntas que en el yugo,
  replicado en Java, en el visor y en las 4 animaciones del `.bbmodel`;
  `WAVE_SAMPLES=11` afina la continuidad C1 (11950 keyframes).
- **Tests**: los umbrales de `audit_model.py --check` bajaron de 205 a 165
  para que la CI **proteja** la mejora, y el workflow verifica el nuevo
  calibrador, la V de dos niveles, los 286 huesos / 340 cubos y los 3 emisores.

### Ronda v1283: se cierran los huecos declarados

Tras «mejora lo que falta», la autoevaluación pasó de **138.96 a 77.20**:

- **Dobladillo** (`t=0.8`): 27.9% → **41.3%** de paño frente al 48% de la
  captura. Las puntas exteriores dejaron de convertirse en agujas justo en
  esa décima (`tip_t` ≥ 0.90 + afilado retrasado al 94% del jirón) y el
  abanico medio se recogió: la silueta de `t=0.2..0.7` bajó de **1.44× a
  1.27×** el ancho del PNG.
- **Remate** (`t=0.9`): 36% → **19.3%** (objetivo 18.3%). `charred_hem()`
  carboniza franjas verticales irregulares sólo en las filas `v≥43` del
  canvas: huecos negros reales entre lóbulos, sin tocar geometría, alfa ni
  las 1636 grietas emisivas. La envolvente ahora **cierra de forma
  monotona** (7.42 → 6.34 → 5.91) en vez de reabrirse en la punta.
- **Arranque / cuello** (`t=0.0`): 27.9% → **45.8%** (objetivo 41.6%).
  Capuchón continuo más ancho, dientes de hombro largos y cuatro tejas
  exteriores convertidas en **alas diagonales** con carmesí liso del yugo;
  la U gris del arnés sigue visible (la «losa» de v1244 no vuelve).
- **Energía rosa**: el descarte binario por componente dejaba un suelo de
  ~35 pp. `shape_energy_density()` usa ahora un **dash fraccional a lo largo
  del trazo** (monótono, sin damero) y `energy_calibration.py` conserva el
  **mejor perfil** de todo el lazo. Error de energía **57.1 → 16.1 pp**;
  el pico de `t=0.2` quedó en 11.3% frente al 11.5% del PNG.
- **Color y energía acoplados**: `/tmp/joint_cal.py` alterna ambos lazos y
  restaura el mejor par (perfil + tabla de color), porque corregir el color
  mueve el umbral que clasifica la energía. Residual cromático 1.3 pp/banda.
- **Contratos**: `audit_model.py` y el workflow dejan de fijar los números
  de una ronda y verifican **propiedades** (puntas desiguales ≥0.90,
  envolvente monótona, deshilachado presente, mejor-perfil conservado).

### Ronda v1331: mirando de nuevo la referencia principal

Contrastando el PNG y el render a la misma escala, la autoevaluación pasó de
**77.20 a 69.47**:

- **Yugo sin calibrar**: capuchón y alas de hombro muestrean la región
  reservada `(57..71, 76..93)`, **fuera del canvas 96×48**. Su mediana era
  (106,37,60) frente a (58,17,29) del canvas, y eso explicaba la mitad del
  error cromático en `t=0.0/0.1`. Ahora se lleva al carmesí medido
  (75,22,32) con un **viraje a violeta** hacia el borde inferior
  (60,29,45). Error de color **94 → 74** y cobertura **29.8 → 24.9 pp**.
- **Grietas cuadradas**: cada guion conservado se extiende un texel en
  vertical cuando el siguiente texel pertenece al mismo trazo; dos de cada
  tres se alargan para mezclar cuchilladas y motas. Se recalibró la
  densidad (antes se duplicaba) y el lazo conjunto energía/color guarda el
  mejor par.
- **Costuras entre lóbulos**: cinco líneas rasgadas y negras en la mitad
  inferior del atlas des-abanicado, sin tocar alfa ni los 1636 emisivos.
- **Relleno adelantado**: la rampa de anchura empezaba en `f=0.64` y no
  alcanzaba `t=0.4..0.7`, donde la referencia tiene más paño. Ahora arranca
  en `f=0.35`; cobertura **29.8 → 24.9 pp** sin volver a la falda.
- **Contratos**: CI verifica también la calibración del yugo y que los
  guiones de energía sigan siendo trazos alargados.

## Ver el modelo

- **Visor AUTOCONTENIDO**: [`docs/capa_v1170_visor.html`](docs/capa_v1170_visor.html)
  (un solo `.html`, sin servidor, sin red, sin token).
- **Comparativa con tu referencia**:
  [`docs/capa_v1170_comparativa.png`](docs/capa_v1170_comparativa.png).
- **Proyecto Blockbench**: [`docs/capa_v1170.bbmodel`](docs/capa_v1170.bbmodel),
  4 animaciones en bucle con **11950 keyframes** y UUID canónicos:
  curvas **Bézier** con tangentes analíticas (C1), marcadores de timeline,
  parpadeo de motas, tirón por tramo, respiración de capucha y un
  **Effects track en los 4 clips** con tres emisores Snowstorm
  (`docs/particles/capa_embers.json`, `capa_embers_calm.json` y `capa_shards.json`).
- **Previews**: [`docs/capa_v1170_preview.png`](docs/capa_v1170_preview.png),
  [`docs/referencia_analizada.png`](docs/referencia_analizada.png).

Se conservan: los **72 huesos originales byte-idénticos**, alfa prístino,
**1636 emisivos**, UV opacas ≤128, `inflate` ≤0.05, espesor 0.25–0.50,
0 `JsonNull`, 0 mixins, `animation.item`, radianes y fail-safes.
**286 huesos / 340 cubos**. `CapaArmorModel.java` quedó regenerado para
los 214 huesos `v15_*` / `v17_*` reales.

> PR #1: https://github.com/Santi-PdR/modelos/pull/1


### Ronda v1.17.2: textura rehecha desde las capturas in-game

Con las capturas reales del juego se vieron tres defectos que el render
software no mostraba, y **todos eran de textura / recursos**:

| Síntoma | Causa | Arreglo |
|---|---|---|
| «sigue sin verse el nuevo icono» | el item registraba un BEWLR 3D (`builtin/entity` + `CapaItemRenderer`): el PNG 2D jamás se renderizaba | modelo `minecraft:item/generated` con `layer0` = icono 64×64; se elimina `getCustomRenderer()` del item |
| «la textura se ve muy mal», confeti magenta y manchas beige/gris | el atlas **des-abanicaba píxeles crudos** del recorte (incluía brazo, arnés y checkerboard) y añadía dithering Bayer + grano por píxel | atlas construido **sólo** desde `CS.palette_at()`: pliegues radiales, huecos entre lóbulos y sarga suave; cero píxeles crudos, cero Bayer |
| «bloques/texturas bugeadas volando» | motas / venas / ceniza muestreaban texels 1×1 de color plano y los sprites de partícula tenían alpha residual en todo el borde | sprites 3×3 con centro encendido y bordes apagados, ceniza con texel oscuro y alpha de partícula **exactamente 0** en el borde |

La energía deja de ser confeti: son **cuchilladas diagonales largas** (4–8
texeles, discontinuas, con halo de 1 texel) situadas sobre las 54 grietas
medidas del PNG y completadas por densidad por décima. El capuchón deja de
ser una losa lisa: pliegues radiales, borde rasgado y carmesí medido.
Se conservan alfa prístino, 1636 emisivos, 286 huesos / 340 cubos,
11950 keyframes y los 3 emisores de partículas.

**Limpieza:** se borraron 45 archivos obsoletos (19 MB): previews de
v1.12/v1.14/v1.15/v1.16 —versiones rechazadas—, `entrega_para_claude.zip`,
los dos Markdown del prompt viejo, el ZIP del mod original y el workflow
`publicar-entrega-claude.yml` que publicaba en la Release v1.15.0. Los tres
backups byte-idénticos del icono aprobado se mantienen intactos.
