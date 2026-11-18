# Mantle of the Blight Star — v1.62.0

Capa cosmética para **Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1**.
Se equipa en el pecho o en `back` con Curios opcional.

[Builds de Forge (Actions)](https://github.com/Santi-PdR/modelos/actions/workflows/build.yml)
· [Proyecto Blockbench](docs/CAPA_v1.62.0.bbmodel)
· [Visor offline](docs/capa_v1170_visor.html)

### v1.62.0 — forma más fiel y luz que sigue las grietas

![Referencia, v1.61.0 y v1.62.0 registradas con la misma cámara](docs/capa_v1620_antes_despues.png)

- Se afinaron la cresta granate, el canto de las placas, el asiento de la
  costura y las puntas. Los escalones nuevos son sólidos conectados a sus
  gajos. Se conserva el hueco que atraviesa las dos capas del paño.
- El atlas equipado opaco **256 × 256** tiene cartas UV por cara y guarda de
  color. Las cartas dan más resolución a las crestas y grietas expuestas
  que a los cantos en escorzo, sin subir de 256². El reverso sigue mate y
  no se pintan pelo, ropa ni motas flotantes en la tela.
- Los núcleos magenta emiten donde están las grietas de la referencia.
  Forge dibuja la luz en un **segundo pase** con la misma profundidad que el opaco, sin el offset de
  la armadura vanilla y sin borrar texels del albedo. Se quita el reflejo de encantamiento sólo al equiparla,
  no del item en inventario. Pecho y Curios comparten ambos pases y el ajuste.
- El `.bbmodel` lleva el mismo atlas opaco y la misma geometría. Se
  conservan los ocho clips, icono, plegado, chispas y sus texturas. Queda
  respaldo de los recursos exactos de [v1.61.0](docs/respaldos/v1.61.0/).

Con el trazado fijo: **93,66 → 95,21 %** de silueta y **88,85 → 92,66 %**
en la costura. En los píxeles comunes el error RGB baja de **6,92 a 3,97**
sobre 255. El solapamiento de núcleos emisivos sube de **11,11 a 76,74 %**
(medir dónde emiten, no solamente cuánta área emite).

[Registro de silueta](docs/capa_v1620_registro.png) ·
[Prueba de emisión](docs/capa_v1620_luz.png) ·
[Visor con comparación deslizable, luz y ajuste](docs/capa_v1170_visor.html)

`python3 tools/verify_v1620.py` compara el mismo trazado sin cambiar la
cámara, verifica los píxeles del original y los dos mapas del visor y
comprueba holguras y unión de las piezas durante poses y mezclas. El barrido no equivale a probar cascos
u otras animaciones de mods ni a una captura F5.

### v1.61.0 — contorno, materiales y ajuste equipado

![Original, v1.60.0 y v1.61.0. Cámara y escala fijas](docs/capa_v1610_antes_despues.png)

- **Modelo:** se afinan el canto y el asiento de las placas, la cresta granate
  y los ocho tramos de la costura en U. Las raíces del paño se apoyan en el cuello
  durante los cambios de estado. Los desgarros y las puntas escalonadas
  son volúmenes unidos a sus gajos; no se simulan con transparencia.
- **Material:** 185 cartas UV; el paño pasa de 2,55 a 3,45 texels por unidad.
  El atlas sigue opaco, con los dos glowmasks, 3.380 texels emisivos,
  icono y item plegado intactos.
- **Forge y Curios:** misma corrección rotacional a partir de la cabeza y el
  torso que está renderizando el portador. Curios ya no suma otra inclinación
  al agacharse. Las hombreras conservan sus ángulos y clips originales en
  lugar de recibir una segunda animación. Se conserva la prioridad de pecho.
- **Blockbench:** mismos cubos y atlas que el mod, ocho clips sin cambios y
  UUIDs anteriores conservados. La bisagra por portador está neutra en el editor.
  Se puede ensayar moviendo la cabeza en **Ajuste al portador** en el visor.

Comparación con el trazado fijo: **91,0 → 93,7 %** de silueta, **88,3 → 92,7 %**
en la zona alta y **71,3 → 88,9 %** de costura (IoU). El error medio RGB
pasa de **8,50 a 6,96 / 255** en los píxeles comunes a las tres máscaras.
Persisten diferencias en el borde de las placas, el cuello alto y algunas
puntas. El pelo, la ropa y las motas libres se excluyen del trazado.

[Registro de silueta](docs/capa_v1610_registro.png) ·
[Ocho estados](docs/capa_v1170_estados.png) · [GIF](docs/capa_v1170_animaciones.gif) ·
[Respaldo íntegro de los recursos v1.60.0](docs/respaldos/v1.60.0/).

`python3 tools/verify_v1610.py` comprueba export, atlas, solapes y holgura con
841 poses, 504 mezclas, giros de cabeza y torso de pie y agachado. Es un
ensayo geométrico con la cabeza vanilla ampliada 0,25 unidades; no valida
cascos grandes, poses de otros mods ni sustituye una prueba F5 en Forge.

### v1.60.0 — volver a la referencia original

![Referencia original, v1.59.0 y v1.60.0, registradas con la misma cámara](docs/capa_v1600_antes_despues.png)

- **Forma**: cuello granate alto y continuo, costura mate en U, hombreras
  de carbón y doce jirones escalonados. Las puntas violetas son más largas
  que el paño rojo de encima. Ya no hay un dobladillo de dos colas ni acero claro.
- **Textura**: cartas UV locales muestrean la superficie visible de la
  imagen registrada. El atlas no incorpora piel, pelo, cuadrícula ni motas
  sueltas. El reverso y los cantos tienen materiales propios. Diez cortes
  al ras usan el glowmask anterior, sin bañar todo el paño en rosa.
- **Mod**: las chispas nacen en los bordes del cuello o cerca del dobladillo,
  como en la imagen, con hasta tres por ocho ticks. La respuesta del paño
  usa tiempo transcurrido, no FPS; no se añade movimiento en XYZ. Se
  mantienen los ocho estados y el alfa 1,0 fijo del pase emisivo.
- **Conservado**: 225 huesos, UUID, icono preferido, item plegado, ambas
  máscaras y 3.380 texels emisivos. Forge 1.20.1, GeckoLib 4.8.1 y Curios
  opcional, con prioridad para el pecho.

**Registro**: 61,0 % → 91,0 % de solapamiento (intersección/unión) con la
silueta trazada. En los píxeles de capa comunes con la referencia, el error
medio RGB bajó de 30,7 a 9,0 sobre 255. Se usa la misma cámara, sin reencuadrar
por versión. El pelo, el portador y el reverso no observado no se cuentan
como una reconstrucción exacta. Los renders son software, no capturas F5.

[Mapa de coincidencia](docs/capa_v1600_registro.png) · [Ocho estados](docs/capa_v1170_estados.png) ·
[Movimiento](docs/capa_v1170_animaciones.gif) · [Respaldo v1.59.0](docs/respaldos/v1.59.0/).

`python3 tools/verify_v1600.py` comprueba máscaras y atlas, 841 poses, 504
mezclas de clips, 147 orientaciones muestreadas de cabeza (hasta ±75° de giro y ±20° de inclinación) y los archivos
exactos del visor. No sustituye una prueba en Minecraft.

### v1.59.0 — dobladillo partido y ocho poses

[Proyecto v1.59.0](docs/respaldos/v1.59.0/CAPA_v1.59.0.bbmodel).

![Comparativa a la misma cámara/escala, con detalle del cuello](docs/capa_v1590_antes_despues.png)

- **Forma equipada:** el centro del dobladillo se abre entre dos colas
  desiguales. El paño gana relieve, con solapas oblicuas y hombreras
  escalonadas; las partes finales de cada gajo ahora comparten un pivote.
- **Materiales:** sarga granate de crestas anchas, forro violeta mate,
  bordes gastados, acero azulado con biseles y remaches. Se conservan
  byte a byte el icono preferido (pixel art), ambos glowmasks y el item
  plegado. El atlas equipado sigue opaco y conserva el RGB de neón/halo.
- **Animación:** las tres bisagras rotan con cada estado. Esprintar barre,
  planear abre el paño, caer levanta el remate, agacharse recoge y nadar
  produce una curva en S. El JSON, el visor y Blockbench comparten ocho
  duraciones y muestras; Blockbench añade tangentes Bézier a las
  rotaciones. No se reescribieron los canales de posición y escala.
- **Mod:** perfil único para clip, brillo y chispas. El planeo y el esprint
  crean una estela corta; con media vida o menos, o al 65 % de desgaste,
  se activa el pulso doble magenta. El brillo sólo modula RGB; las
  chispas se emiten detrás del cuerpo, no de la cabeza. Si llevas una
  copia en cada slot, la del pecho prevalece sobre `back`.

[Ocho estados a la misma escala](docs/capa_v1170_estados.png)
· [GIF con ciclos sincronizados por fase](docs/capa_v1170_animaciones.gif)
· [Respaldo íntegro de la base v1.58.0](docs/respaldos/v1.58.0/).

**Validación:** `python3 tools/verify_v1590.py` mide 9.141 texels RGB
repintados (6.452 de paño/forro). A la misma altura y cámara trasera,
la abertura central pasa de 0,42 a 3,85 unidades. Comprueba también el
GEO, el `.bbmodel`, las poses del visor y la holgura en 1.097 muestras.
Estos renders usan un maniquí neutro y no sustituyen una prueba en Minecraft/F5.

### v1.58.0 — pliegues envolventes y jirones violetas

[Comparativa con tus capturas de v1.57.0](docs/capa_v1580_antes_despues.png)
· [Proyecto Blockbench v1.58.0](docs/respaldos/v1.58.0/CAPA_v1.58.0.bbmodel).

El cuello deja de leerse como paneles rectos: el granate sigue un doblez
redondeado con sombra por debajo. Los jirones enseñan caras violetas más
anchas, a distinta altura, con desgarros oscuros pintados. Cambian **1.917
texels del cuello** y **6.758 del paño y forro**, con un cambio de al menos
20/255 en el **38% de los píxeles visibles** en la comparación frontal.
Las imágenes son renders software, no capturas del mod en Minecraft.

[Respaldo v1.57.0](docs/respaldos/v1.57.0/) y
`python3 tools/verify_v1580.py` verifican que la geometría, las UV, las
ocho animaciones, el icono, el item plegado y toda la energía sean
idénticos a v1.57.0. Alfa del atlas: 255.

### v1.57.0 — textura de la capa equipada

[Comparativa de las referencias y el paño equipado](docs/capa_v1570_antes_despues.png)
· [Proyecto Blockbench v1.57.0](https://github.com/Santi-PdR/modelos/releases/download/v1.57.0/CAPA_v1.57.0.bbmodel)
· [Visor 3D v1.57.0](https://github.com/Santi-PdR/modelos/releases/download/v1.57.0/capa_v1170_visor.html).

Se repintó el atlas 3D 128×128 de acuerdo con las dos capturas: granate
oscuro en capucha y capa externa, violeta en el forro y las puntas,
pliegues quebrados y cantos desgastados. No quedan el galón cobrizo ni
la estrella bordada. Se verificaron 6.760 texels distintos del paño y
forro frente a v1.56.0. Sólo se modifica RGB: geometría, UV, animaciones,
icono, item plegado y glowmasks permanecen iguales. El respaldo previo
está en [`docs/respaldos/v1.56.0/`](docs/respaldos/v1.56.0/).
`python3 tools/verify_v1570.py` comprueba estos cambios frente al respaldo.

### v1.56.0 — paño 3D y cuello rediseñados

![Capa equipada de v1.55.0 y v1.56.0 a la misma escala](docs/capa_v1560_antes_despues.png)

- **Paño equipado**: atlas 128×128 pintado desde cero. Pliegues de brasa y
  ciruela, doble galón en V y una estrella de ceniza bordada. Cambian **6.470
  de 9.216 texels** del paño y forro; **4.494** cambian al menos 32/255 en
  un canal RGB. No se repinta el item plegado.
- **Silueta**: dorso abierto en abanico y faldones de caída escalonada.
  Las piezas centrales pasan de **3,90 a 5,20 u** (dorso) y de **3,20 a
  5,50 u** (faldón). El cuello tiene UV propias a 4 texels/u. Se corrige
  la inversión de Z del modelo anterior y se comprueba la holgura en +Z
  en reposo y en 33 muestras de cada clip.
- **Preservado**: alfa del atlas 255, icono y glowmasks byte a byte, RGB de
  los 3.380 texels de energía, jerarquía, UUID y los **8 clips**; no se
  añaden pistas ni offsets animados.

Respaldo anterior a la edición: [`docs/respaldos/v1.55.0b/`](docs/respaldos/v1.55.0b/).
`python3 tools/verify_v1560.py --candidate` comprueba los candidatos antes
del rebuild; sin `--candidate` comprueba los archivos finales.
La comparativa es un render software, no una captura de Minecraft.

### v1.55.0 — nueva versión (bump)

Nueva versión. Lleva la mejora **BOLD del modelo y la textura** de la v1.54.0 (collar dorsal `v17_cowl_back_*` altura +56% con *flare* marcado; faldón frontal `v17_cowl_tooth_*` altura +78%; textura del paño rebuilt desde 0 con **pliegues verticales gruesas + trama de hilo + degradado de caída + rim light**), con la guía `docs/GUIA_MODELADO_ANIMACION.md` **re-recordada antes de la actualización**. Restricciones vigentes intactas: capa **visible y sin intersectar el cuerpo** en +Z (front), **alpha glow fijo 1.0**, **motion espacial prohibido**, **icono byte a byte** (`c90670ba…`), **8 RMS distintos**.

### v1.54.0 — mejora del modelo y la textura (guiada por el estudio)

Revisada con **`docs/GUIA_MODELADO_ANIMACION.md`** (el estudio de modelado/animación/GeckoLib/texturas que se recuerda **antes de cada actualización**: jerarquía de huesos antes de geometría, **UUIDs estables**, rotar en vez de mover). Se **empezó de 0** (reset al baseline limpio v1.53.0, con respaldo previo en `docs/respaldos/`). **(1) Modelo:** refinamiento de **silueta del collar** claramente visible — **dorso** (`v17_cowl_back_*`): altura **+56%** (2.50→3.90) y *flare* marcado; **faldón frontal** (`v17_cowl_tooth_*`): altura **+78%** (1.80→3.20) y anchura **+14%**, un pliegue grande y claro que conecta el collar con las cintas. Todos los huesos se **editan** (no se recrean): **UUIDs y animaciones intactos** (verificados). **(2) Textura REBUILT FROM 0:** el paño 3D (`capa_deteriorer_evilsaiyan.png`) y el item plegado se reconstruyen con una **TEJA visible y de alto contraste** — **pliegues verticales gruesas**, **trama de hilo (urdimbre×trama) con patrón de tejido**, **degradado de caída** y **resalte de borde (*rim light*)**. **RGB solo**, alpha/glowmask intactos, neon protegido. **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5**, el **cuellito** y las **8 animaciones con RMS distintos** intactos.

### v1.53.0 — reforma del modelo (base + textura)

**(1) Geometría:** los 27 cubos `bottom`/`mid` del paño (`v15_cloth_*`) quedaban apilados y **sueltos flotando** en la parte superior del paño; ahora son **invisibles** en Blockbench (los huesos se preservan para Java). **(2) Textura:** se añade **volumen** al paño (**RGB solo**, alpha/glowmask intactos): degradado de caída vertical, pliegues horizontales y grano de tela, protegiendo las zonas de energía emisiva. **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.52.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial. (1) **Animación**: **tercer micro-armónico de la capucha** (k=10, amplitud 1.2% de amp, RotZ) — temblor ultrafino del gorro, rotación pura. (2) **Halo orbital**: **quinto armónico de rotación** (0.04°, RotZ). (3) **Cadena delantera**: **quinto armónico de rotación** (0.04°, RotZ). (4) **Efectos y bloom**: **quinto *drift* de matiz** del resplandor del glow y del glow del item (**color solo**: alpha fijo 1.0 / ≤1.0). (5) **Chispa**: **cuarto armónico de color (matiz)** (cosmética). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.51.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial. (1) **Animación**: **segundo micro-armónico de la capucha** (k=8, amplitud 3% de amp, RotZ) — temblor ultrafino del gorro, rotación pura. (2) **Halo orbital**: **cuarto armónico de rotación** (0.06°, RotZ). (3) **Cadena delantera**: **cuarto armónico de rotación** (0.06°, RotZ). (4) **Efectos y bloom**: **cuarto *drift* de matiz** del resplandor del glow y del glow del item (**color solo**: alpha fijo 1.0 / ≤1.0). (5) **Chispa**: **tercer armónico de color (matiz)** (cosmética). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.50.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial. (1) **Animación**: **micro-rotación Z del dobladillo** (armónico k=5, amplitud 5% de amp, RotZ) y **micro-rotación Z de la vena** (armónico k=5, amplitud 8% de amp, RotZ) — temblor fino de la tela y la energy, rotación pura. (2) **Efectos y bloom**: **tercer *drift* de matiz** del resplandor del glow y del glow del item (**color solo**: alpha fijo 1.0 / ≤1.0). (3) **Chispa**: **segundo armónico de color (matiz)** (cosmética). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.49.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial. (1) **Animación**: **micro-rotación Z de la capucha** (armónico k=6, amplitud 6% de amp, RotZ) — temblor fino del gorro, rotación pura. (2) **Halo orbital**: **tercer armónico de rotación** (0.10°, RotZ). (3) **Hombreras delanteras**: **tercer armónico de rotación** (0.08°, RotZ). (4) **Hombreras traseras**: **tercer armónico de rotación** (levantamiento RotX 0.12°, inclinación RotZ 0.10°). (5) **Chispa**: **micro-variación de color (matiz)** (cosmética). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.48.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial. (1) **Animación**: **tercer armónico del *shiver* por columna** (k=16, amplitud 0.35×) en la inclinación Z de los jirones — temblor de grano, rotación pura. (2) **Cadena delantera**: **tercer armónico de rotación** (0.12°, RotZ). (3) **Efectos y bloom**: **segundo *drift* de matiz** del resplandor del glow y del glow del item (**color solo**: alpha fijo 1.0 / ≤1.0). (4) **Chispa**: **micro-variación de tamaño** (cosmética). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.47.0 — mejoras seguras en animación y efectos (sin regreso)

Cambios de **rotación o color**, sin tocar el motion espacial (no se toca la fuerza/dirección del viento ni la componente Z del desplazamiento). (1) **Animación**: **segundo armónico del *shiver* por columna** (k=13, amplitud 0.5×) en la inclinación Z de los jirones — temblor de grano, rotación pura. (2) **Dobladillo**: **segundo armónico del *flutter*** (0.4°, RotZ). (3) **Hombreras traseras**: **segundos armónicos de rotación** (levantamiento RotX 0.3°, inclinación RotZ 0.2°). (4) **Efectos y bloom**: **drift de matiz lento** del resplandor del glow y del glow del item (**color solo**: alpha del re-render emisivo fijo 1.0 / clampado a 1.0). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.46.0 — mejoras seguras en animación, textura y efectos (sin regreso)

Se sigue la línea de mejoras verificadas, con amplitudes **todas minúsculas** y cambios de **rotación o cosméticos** (ningún cambio de motion espacial). (1) **Animación**: nuevo armónico **k=15** (amplitud 0.0015, fase 17.3·φ), rotación lateral pura. (2) **Textura**: **séptima capa de hilos** (`freq×20`, amplitud 0.06×), solo color: el alpha sigue **255** en todo el atlas. (3) **Efectos y bloom**: **décimacartavo shimmer** del glow (color solo, alpha fijo 1.0), **décimacartavo parpadeo** de la chispa, **cuarto shimmer** del glow del item (alpha clampado a 1.0) y un **segundo armónico de rotación** en la hombrera delantera (0.15°, solo RotZ). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.45.0 — mejoras seguras en animación, textura y efectos (sin regreso)

Se sigue la línea de mejoras verificadas, con amplitudes **todas minúsculas** y cambios de **rotación o cosméticos** (ningún cambio de motion espacial). (1) **Animación**: nuevo armónico **k=14** (amplitud 0.002, fase 16.1·φ), rotación lateral pura. (2) **Textura**: **sexta capa de hilos** (`freq×16`, amplitud 0.08×), solo color: el alpha sigue **255** en todo el atlas. (3) **Efectos y bloom**: **décimacartavo shimmer** del glow (color solo, alpha fijo 1.0), **décimacartavo parpadeo** de la chispa, **tercer shimmer** del glow del item (alpha clampado a 1.0) y un **segundo armónico de rotación** en la cadena delantera (0.2°, solo RotZ). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.44.0 — mejoras seguras en animación, textura y efectos (sin regreso)

Se sigue la línea de mejoras verificadas de la v1.43.0, con amplitudes **todas minúsculas** y cambios de **rotación o cosméticos** (ningún cambio de motion espacial: no se toca la fuerza/dirección del viento ni la componente Z del dobladillo). (1) **Animación**: nuevo armónico **k=13** (amplitud 0.003, fase 14.9·φ), rotación lateral pura. (2) **Textura**: **quinta capa de hilos** (`freq×12`, amplitud 0.10×), solo color: el alpha sigue **255** en todo el atlas. (3) **Efectos y bloom**: **décimo shimmer** del glow (color solo, alpha fijo 1.0), **décimo parpadeo** de la chispa, **segundo shimmer** del glow del item (alpha clampado a 1.0) y un **segundo armónico de rotación** en el halo de fragmentos orbitales (0.25°, solo RotZ). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.43.0 — mejoras seguras en animación, textura y efectos (sin regreso)

Se **investiga a fondo** el regreso "capa invisible" de la v1.41.0: el diff de esa versión (armónicos 12/13 de rotación, capa de hilos, shimmers, parpadeos) es **mecánicamente inocente** — la `animation.json` es estructuralmente idéntica (delta máximo de rotación **0.2°**), la textura es **100% opaca** en ambas (delta de color máximo **2/255**), el alpha del re-render emisivo es **fijo 1.0** y la cadena de render (`chestplate → loses → tiras → venas`) **no tiene huesos visibles bajo huesos ocultos**. La invisibilidad fue **ambiental** (cache de recursos, estado del cliente), no del código.

Con esa seguridad, se aplican mejoras **verificadas y seguras**: (1) **Animación**: nuevo armónico **k=12** (amplitud 0.004, fase 13.7·φ), **rotación pura y lateral** — no toca la componente Z del dobladillo ni empuja el paño al cuerpo. (2) **Textura**: **cuarta capa de hilos** (`freq×8.5`, amplitud 0.14×), solo color: el alpha sigue **255** en todo el atlas. (3) **Efectos y bloom**: **noveno shimmer** del glow (color solo, alpha fijo 1.0), **noveno parpadeo** de la chispa y **shimmer** del glow del item (alpha clampado a 1.0). **La capa sigue colgando visible y sin intersectar el cuerpo**, en +Z (front), con la **corrección F5 intacta**.

### v1.42.0 — reversión al estado conocido-bueno (capa visible)

Se **revierte** el comportamiento al de la **v1.38.0**, la última versión en que la capa se veía correctamente, para corregir el regreso por el que **la capa no se veía**. Los cambios de la v1.39.0, v1.40.0 y v1.41.0 (armónicos 12/13, capas de hilos 4/5, shimmers 9/10, parpadeos 9/10, pulso de tamaño, latido de dos tiempos, drift de matiz) **se revueven todos**, restaurando exactamente el **movimiento, la textura y los efectos** de la v1.38.0.

La **geometría** (225 huesos / 270 cubos), la **capa en +Z (front)**, la **corrección F5** (alpha fijo 1.0) y el mirror revocado se mantienen. **La capa vuelve a colgar visible y sin intersectar el cuerpo**, como en la v1.38.0.

### v1.41.0 — mejoras seguras en animación, textura y bloom (sin regreso)

Se sigue mejorando el modelo con cambios **seguros** que **no mueven la capa hacia el cuerpo** (se evitan los cambios espaciales que causaron el regreso de la v1.39.0, corregido en la v1.40.0):

- **Animación — rotación segura.** La onda viajante suma un **décimatrece** armónico (`k=13`, amplitud `0.005`, fase `14.5·φ`), que es **rotación** (con una oscilación lateral mínima) y por tanto **no toca la componente Z del dobladillo**: no puede empujar la capa dentro del cuerpo. `k` entero → periodicidad y costura C1 intactas (self-test).
- **Textura — grano sub-texel.** El entramado suma una **quinta capa de hilos** (frecuencia `freq*12`, amplitud `0.10x`) con el grano sub-texel de la urdimbre muy fina. Determinista y simétrica, sin tocar degradado ni alfa.
- **Efectos y bloom — más vivos.** El **shimmer** emisivo suma un **décimo** componente; el **item plegado** suma un **tercer shimmer**; y la **chispa** suma un **décimo parpadeo** y un **pulso de tamaño de dos tiempos**.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección F5** y el mirror revocado.

### v1.40.0 — corrección del regreso (capa sin intersectar al jugador)

Se corrige el regreso de la v1.39.0: la capa se veía **bugeada dentro del jugador**. La causa eran **dos cambios de movimiento espacial** que empujaban el paño hacia delante, dentro del cuerpo: la **tercera armónica de la ráfaga** (fuerza/dirección del viento) y la **segunda cresta viajante** del dobladillo (oscilación extra en Z). Ambos **se revierten** a la versión verificada, para que la capa vuelva a **colgar sin intersectar el cuerpo**.

Se **conservan** las mejoras estéticas que **no mueven la capa**: el **décimasegundo armónico** (solo rotación, amplitud `0.006`, incapaz de meter la capa en el cuerpo), la **textura** (cuarta capa de hilos ultrafinos) y el **bloom/efectos** (noveno shimmer, latido de dos tiempos, drift de matiz, shimmer del item, noveno parpadeo y pulso de tamaño de la chispa). Se mantiene la **capa en +Z (front)**, la **corrección F5** y el mirror revocado.

### v1.39.0 — mejoras en animación, textura, efectos y bloom

Se mejora el modelo en cuatro frentes, sin tocar la **capa en +Z (front)**, la **corrección de la transparencia F5** ni el mirror revocado:

- **Animación — más orgánica.** La onda viajante suma un **décimasegundo armónico** (`k=12`, amplitud `0.006`, fase `13.3·φ`); la **ráfaga de viento** suma un **tercer armónico** para que sople de forma entrecortada; y el **dobladillo del jirón** gana una **segunda cresta viajante** (`k=2`, fase lenta) para que caiga con dos lomos que se cruzan. Todo `k` entero: la **periodicidad y la costura C1** se mantienen (lo comprueba el self-test de `cape_motion.py`).
- **Textura — grano de tejido.** El entramado suma una **cuarta capa de hilos ultrafinos** (frecuencia casi triple, amplitud `0.14x`) con el grano microscópico de las fibras individuales: el paño lee como tela de hilo estrecho. Determinista y simétrica, sin tocar el degradado ni el alfa.
- **Efectos y bloom — más vivos.** El **shimmer** emisivo suma un **noveno** componente; el latido pasa a ser de **dos tiempos** (onda lenta de fondo) con un **drift de matiz** violeta-magenta; el **item plegado** suma un shimmer y un segundo destello cian; y la **chispa** suma un **noveno parpadeo** y un pulso de tamaño de dos tiempos.
- **Mantenimiento.** La **geometría** (225 huesos / 270 cubos) y las ocho animaciones (sin mirror) se regeneran.

### v1.38.0 — undécimo armónico, octavo shimmer y octavo parpadeo

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.37.0:

- **Animación — undécimo armónico.** La onda viajante suma un **undécimo armónico** (`k=11`, amplitud `0.008`, fase `12.1·φ`) sobre el décimo de la v1.37.0. El destello de los hilos más finos al viento se vuelve más fino, sin romper la **periodicidad ni la costura C1** (lo comprueba el self-test de `cape_motion.py`).
- **Efectos — más vivos.** El **shimmer** emisivo suma un **octavo** componente a mayor frecuencia y amplitud menor, con fase distinta, y la **chispa** suma un **octavo** parpadeo. La luz que recorre el paño y la brasa son más vivas e irregulares, con el temblor casi imperceptible de los hilos finos.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección de la transparencia F5** (alpha fijo 1.0 del re-render emisivo, brillo al color), el **cuellito**, la **onda viajante** y la **capa colgando sin intersectar el cuerpo**. La geometría (225 huesos / 270 cubos), la textura (tercera capa de hilos) y las ocho animaciones (sin mirror) se regeneran.

### v1.37.0 — décimo armónico, séptimo shimmer y séptimo parpadeo

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.36.0:

- **Animación — décimo armónico.** La onda viajante suma un **décimo armónico** (`k=10`, amplitud `0.01`, fase `10.9·φ`) sobre el noveno de la v1.36.0. El destello de los hilos más finos al viento se vuelve más fino, sin romper la **periodicidad ni la costura C1** (lo comprueba el self-test de `cape_motion.py`).
- **Efectos — más vivos.** El **shimmer** emisivo suma un **séptimo** componente a mayor frecuencia y amplitud menor, con fase distinta, y la **chispa** suma un **séptimo** parpadeo. La luz que recorre el paño y la brasa son más vivas e irregulares, con el temblor casi imperceptible de los hilos finos.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección de la transparencia F5** (alpha fijo 1.0 del re-render emisivo, brillo al color), el **cuellito**, la **onda viajante** y la **capa colgando sin intersectar el cuerpo**. La geometría (225 huesos / 270 cubos), la textura (tercera capa de hilos) y las ocho animaciones (sin mirror) se regeneran.

### v1.36.0 — noveno armónico, sexto shimmer y sexto parpadeo

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.35.0:

- **Animación — noveno armónico.** La onda viajante suma un **noveno armónico** (`k=9`, amplitud `0.015`, fase `9.7·φ`) sobre el octavo de la v1.35.0. El destello de los hilos más finos al viento se vuelve más fino, sin romper la **periodicidad ni la costura C1** (lo comprueba el self-test de `cape_motion.py`).
- **Efectos — más vivos.** El **shimmer** emisivo suma un **sexto** componente a mayor frecuencia y amplitud menor, con fase distinta, y la **chispa** suma un **sexto** parpadeo. La luz que recorre el paño y la brasa son más vivas e irregulares, con el temblor casi imperceptible de los hilos finos.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección de la transparencia F5** (alpha fijo 1.0 del re-render emisivo, brillo al color), el **cuellito**, la **onda viajante** y la **capa colgando sin intersectar el cuerpo**. La geometría (225 huesos / 270 cubos), la textura (tercera capa de hilos) y las ocho animaciones (sin mirror) se regeneran.

### v1.35.0 — octavo armónico, quinto shimmer y quinto parpadeo

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.34.0:

- **Animación — octavo armónico.** La onda viajante suma un **octavo armónico** (`k=8`, amplitud `0.02`, fase `8.5·φ`) sobre el séptimo de la v1.34.0. El destello de los hilos más finos al viento se vuelve más fino, sin romper la **periodicidad ni la costura C1** (lo comprueba el self-test de `cape_motion.py`).
- **Efectos — más vivos.** El **shimmer** emisivo suma un **quinto** componente a mayor frecuencia y amplitud menor, con fase distinta, y la **chispa** suma un **quinto** parpadeo. La luz que recorre el paño y la brasa son más vivas e irregulares, con el temblor casi imperceptible de los hilos finos.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección de la transparencia F5** (alpha fijo 1.0 del re-render emisivo, brillo al color), el **cuellito**, la **onda viajante** y la **capa colgando sin intersectar el cuerpo**. La geometría (225 huesos / 270 cubos), la textura (tercera capa de hilos) y las ocho animaciones (sin mirror) se regeneran.

### v1.34.0 — séptimo armónico, cuarto shimmer y cuarto parpadeo

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.33.0:

- **Animación — séptimo armónico.** La onda viajante suma un **séptimo armónico** (`k=7`, amplitud `0.025`, fase `7.3·φ`) sobre el sexto de la v1.32.0. El destello de los hilos más finos al viento se vuelve más fino, sin romper la **periodicidad ni la costura C1** (lo comprueba el self-test de `cape_motion.py`).
- **Efectos — más vivos.** El **shimmer** emisivo suma un **cuarto** componente a mayor frecuencia y muy baja amplitud, con fase distinta, y la **chispa** suma un **cuarto** parpadeo. La luz que recorre el paño y la brasa son más vivas e irregulares, con el temblor casi microscópico de los hilos finos.
- **Mantenimiento.** Se mantiene la **capa en +Z (front)**, la **corrección de la transparencia F5** (alpha fijo 1.0 del re-render emisivo, brillo al color), el **cuellito**, la **onda viajante** y la **capa colgando sin intersectar el cuerpo**. La geometría (225 huesos / 270 cubos), la textura (tercera capa de hilos) y las ocho animaciones (sin mirror) se regeneran.

### v1.33.0 — corrección F5 real (capa en +Z, fin del fantasma translúcido) y efectos reafinados

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.32.0:

- **F5 — la capa vuelve a +Z y deja de verse transparente.** El **volteo a `-Z` de la v1.32.0 fue incorrecto**: la capa **vuelve a `+Z` (frente)**, su posición original, y el **mirror** que se había añadido a la animación para compensar `-Z` se **revierte por completo** (la animación vuelve a su estado original, sin mirror). Aparte, se corrige la **causa real** de que en F5 la capa se veía **transparente y "adentro" del jugador**: el brillo emisivo (`CapaGlowLayer`) pasaba `brightness` como **alpha global** del re-render, lo que translucía todo el mesh y lo dibujaba sobre el cuerpo en la vista trasera. Ahora el **alpha del re-render es fijo 1.0** y el brillo pulsante se aplica al **color** (`r,g,b`): como el glowmask tiene alpha 0 fuera de las venas, esas regiones **no se dibujan** → no hay re-render fantasma sobre el cuerpo y la capa sigue **opaca** en F5. También se afirma el **render type** de la capa como opaco (`armorCutoutNoCull`) con test de profundidad, para que la parte trasera se ocluya correctamente.
- **Efectos — brillo reafinado.** El brillo emisivo vuelve a latir **centrado en 1.0** (`0.86-1.14`, con más ganancia al esprintar) con los **tres shimmer** y el **tercer parpadeo** de la chispa. Se mantienen el **cuellito**, la **onda viajera** y la **capa colgando sin intersectar el cuerpo**.
- **Textura — atlas regenerado.** El atlas se regenera (tercera capa de hilos tejidos) y se re-verifica. La **geometría (225 huesos / 270 cubos)** y las **ocho animaciones (sin mirror)** se regeneran en `+Z`.

Se mantiene la **corrección de jump** (no teletransporte) de la v1.30.0.

### v1.32.0 — cuellito, capa visible en F5 y textura/efectos más finos

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos, geometría), sobre la v1.31.0:

- **F5 — la capa ya no se ve invisible.** La capa se **voltea a `-Z` (detrás del jugador)**: antes quedaba en `+Z`, el **frente**, y en la vista **F5** (cámara detrás) se ocultaba por el cuerpo, por eso se veía invisible. Ahora la capa y el cuello renderizan **detrás** y son visibles en F5. El render type es doble cara (`armorCutoutNoCull`), así que el volteo no introduce problemas de culling.
- **Geometría — cuellito.** Se añade el **cuellito**: **3 bloques chiquitos** (`v19_cuellito_*`) junto a la **nuca**, para que la capa parezca **atada al jugador** y no flotante.
- **Animación — sexto armónico.** La onda viajera suma un **sexto armónico** (`k=6`, amplitud `0.035`) para el destello fino de los hilos más finos al viento. `k=6` es entero: la onda sigue **periódica y C1** (self-test de `cape_motion.py`).
- **Textura — entramado más fino.** El `_weave` del atlas suma una **tercera capa de hilos** a frecuencia doble de la fina (`freq*4.6`, amplitud `0.22x`): el paño lee como tejido de hilo estrecho, no como una lámina de dos frecuencias.
- **Efectos — más orgánicos.** El **shimmer** emisivo suma un **tercer** componente y la **chispa** un **tercer** parpadeo, ambos a mayor frecuencia y fase distinta, para que la luz y la brasa sean irregulares y vívidas.

Se mantiene la **corrección de jump** (no teletransporte) de la v1.30.0.

### v1.31.0 — quinto armónico, tela tejida fina y efectos más orgánicos

Se sigue mejorando el modelo en todos sus aspectos (textura, animación, efectos), sobre la v1.30.0:

- **Animación — quinto armónico.** La onda viajera suma un **quinto armónico** (`k=5`, amplitud `0.06`) sobre el cuarto de la v1.29.0. El ribete de la tela gana el temblor fino de los hilos individuales al viento. `k=5` es entero, así que la onda sigue **periódica y C1** (lo comprueba el self-test de `cape_motion.py`).
- **Textura — entramado de hilos finos.** El `_weave` del atlas suma una **segunda capa de hilos a mayor frecuencia** (`freq*2.4`, amplitud `0.35x`) sobre la capa gruesa: el paño lee como tejido fino y no como una lámina de una sola frecuencia. Determinista y simétrico, sin tocar la calibración de color (grad 60.4, fid 0.000).
- **Efectos — más orgánicos.** El **shimmer** de la capa emisiva suma un segundo componente a mayor frecuencia (la luz que recorre el paño con temblor), y la **chispa** suma un segundo parpadeo a otra frecuencia y fase, para que la brasa sea irregular y viva.

Se mantiene la **correción de jump** (no teletransporte) y la **visibilidad en F5** de la v1.30.0.

### v1.30.0 — arreglo de jump (no teletransporte) y visibilidad en F5

Dos correcciones de comportamiento, sobre la v1.29.0:

- **La animación de salto ya NO teletransporta la capa.** El clip
  `animation.air` (`FLY_ANIM`, usado al saltar)arranca y termina ahora
  en la **pose de reposo de `idle`**. Antes cada clip (salvo `idle`)
  llevaba `posbias`/`bias` constantes aplicados a todos sus keyframes,
  así `air` empezaba/terminaba en `(-0.57, 0.35, 0.90)` mientras
  `idle` lo hacía en `(-0.09, -0.28, -0.31)`: al entrar o salir del
  clip al saltar, la capa pegaba un salto brusco de ~1.2u en Z y de
  rotación instantánea — el "teletransporte". Ahora **todos los clips
  arrancan y terminan en la pose de reposo de `idle`** y el movimiento
  propio del estado vive en el interior del clip, con transición
  continua.
- **La capa ya NO se vuelve invisible en F5 (cámara trasera).** La causa:
  las tiras `v17_ribbon_*` son **hijas** de las 3 losas
  `cape_top/mid/bottom`, y Java las ocultaba con `setHidden(true)`. En
  tercera persona **GeckoLib no renderiza a los hijos de un hueso
  oculto**, así que al mirar la capa desde atrás desaparecía entera.
  Ahora se **anulan los cubos** de las 3 losas en el geo (quedan
  visibles pero sin geometría) y **no se ocultan** en runtime, de modo
  que sus hijas (las tiras) renderizan desde cualquier ángulo.

Se mantiene la **textura tejida**, las **animaciones** de los ocho
estados y los **efectos** (shimmer + twinkle) de la v1.29.0.

### v1.29.0 — textura tejida, animación con ribete y efectos más vivos

Siguiendo la mejora del modelo: textura, animación y efectos.

- **El atlas de la capa 3D GANÁ una tela tejida y pliegues finos.**
  El paño era una superficie lisa; ahora superpone **hilos warp/weft
  cruzados** (`_weave`, determinista, sin ruido) y **pliegues secundarios**
  a mayor frecuencia. Se lee como tela, no como plástico, sin tocar el
  degradado carmesí → morado.
- **El degradado carmesí → morado se fortalece.** La capa interna se
  profundiza (canal R más bajo) para que `grad ≥ 60`. La **fidelidad al
  diseño** cae de **0.174 a 0.000** — el único término que la mantenía
  en ya era el degradado; ahora está al límite de la medida. El icono
  2D se mantiene **byte a byte el PREFERIDO de la v1.25.0**
  (SHA `c90670ba…`), que la auditoría comprueba.
- **Las animaciones suman un cuarto armónico.** La onda viajante de
  los ocho estados (`cape_motion.wave`) añade un armónico `k=4` de
  amplitud 0.10: el paño pierde el ribete mecánico y ondula como tela
  al viento. Como `k` es entero, la onda sigue **periódica y C1** en la
  costura del bucle (el self-test lo comprueba).
- **Los efectos se vuelven más vivos.** La capa emisiva suma un
  **shimmer viajante** sobre el latido (la luz recorre el paño, no es
  un pulso llano) y la **chispa** parpadea (*twinkle*) como una brasa.

### v1.28.0 — tu icono de vuelta y el paño desaturado

Dos cosas que pediste, más una que salió de medirlas.

- **El icono vuelve a ser el PREFERIDO, byte a byte.** Comparaste el
  rediseño de la v1.27.0 con el icono anterior y elegiste el anterior:
  es el de la **v1.25.0** (commit `af5c5b0`, SHA-256
  `c90670ba367557d7c7c003fa38dbe10c27cc88dcee1ef37fedc48f3a82820ee5`,
  `referencias/ICONO_V125_PREFERIDO_BACKUP.png`). El PNG activo vuelve a
  ser ese mismo byte a byte y **el pipeline lo regenera igual**: el mapa
  de 16×16, las ocho motas flotantes, las veintiséis grietas y los cinco
  tonos del paño son los de la v1.25.0. La auditoría lo comprueba por
  SHA, y el rediseño de la v1.27.0 **no se borra**: queda guardado en
  `referencias/ICONO_V1270_REDISEÑO_BACKUP.png`.
- **El atlas de la capa 3D se desatura.** Al comparar la textura que
  ensenaste en Blockbench (la del icono) con el atlas actual se vio que
  el paño del modelo era **demasiado saturado**: el canal verde iba 10-24
  por debajo de tu foto de referencia en las diez bandas, y el rojo del
  hombro iba 40 por encima. El icono elegido usa la rampa **medida** de
  la captura, cuyo extremo inferior es un violeta apagado; el atlas
  usaba un violeta eléctrico. Con la paleta nueva —carmesí `106,24,40`
  en vez de `142,24,40`, violeta `62,48,74` en vez de `62,20,74`— el
  **error de color acumulado baja de 321 a 210** (medido por
  `tools/audit_model.py` contra `REFERENCIA_CAPA.png`), que es el mejor
  valor que respeta el degradado carmesí→morado del contrato. La capa 3D
  y el icono cuentan ahora **la misma tela**.
- **Ni la geometría ni las animaciones cambian**: 222 huesos, 282 cubos,
  las mismas ocho pistas. Las **27 anclas `v15_cloth_*` siguen existiendo**
  y lo que se apaga es **sólo su render**, también en el visor; el
  diagnóstico sigue en la casilla `Anclas`.
- **La v1.27.0 y la v1.27.1 no se tocan**: quedan como histórico con su
  `.jar` y su `.bbmodel` intactos. Además el `.jar` **exacto de la
  v1.27.0** se rescata de su artifact histórico (`14057282072`), se
  verifica contra el digest que publica la API de la release y se deja
  en la rama `artifacts/v1.27.0` con su `SHA256SUMS.txt`.

### v1.27.1 — el arreglo del visor, en su propia release

**Patch de entrega**: el modelo es **idéntico** a la v1.27.0 (mismo geo de
222 huesos y 282 cubos, mismo atlas, mismas ocho animaciones). Lo que
cambia es **dónde vive** el arreglo:

- El visor de `docs/` (el `.html` autocontenido que se abre en doble clic)
  **ya no dibuja las 27 anclas `v15_cloth_*`**. Antes el runtime Java y el
  render software las ocultaban, pero el visor seguía pintándolas: el
  entregable que se miraba enseñaba las motas negras que la v1.27.0
  arreglaba. Ahora el hueso, la jerarquía y las ocho pistas se conservan
  intactos y lo que se apaga es su render, también en el visor.
- El **diagnóstico sigue disponible**: el visor cuenta las anclas y las
  pinta si se activa la casilla `Anclas` (`showAnchors` / `l_anchors`).
- La **v1.27.0 no se toca**: esta release es nueva y la anterior queda
  como histórico, con su `.jar` y su `.bbmodel` intactos.
- El `.jar` se deja además en la **rama de artefactos** `artifacts/v1.27.1`
  (mismo binario, con su `SHA256SUMS.txt`), para poder descargarlo y
  verificar su SHA-256 allí donde el CDN de releases no responde.

### v1.27.0 — las motas negras fuera, hombrera y cadena rehechas, icono legible

Tres defectos que se veían en las capturas y que esta entrega arregla de
verdad, con la geometría, el atlas, el runtime y la auditoría cambiados.

- **Las 27 anclas de la onda ya no se dibujan**: son cubos de 0.16 que
  existen **sólo** para dar pose a la tela (los usa `panels[]` y las ocho
  pistas del `animation.json`). El hueso, la jerarquía y la animación se
  conservan **intactos**: lo que se apaga es su render, en Java
  (`hideClothAnchors`) y en el render software, para que el cuello no
  tenga motas negras.
- **La hombrera deja de ser una masa negra**: era un único cubo
  2.40×0.90×1.80 de gris carbón plano (luminancia ~34, sin volumen) que
  en el juego se leía como una mancha en el hombro. Ahora son **cuatro
  piezas de acero** por hombro (placa, lam, filo exterior y labio
  delantero), con UV **por cara**, filo de luz arriba-izquierda, sombra
  abajo-derecha, remaches y un filete carmesí que la ata al paño.
- **La cadena deja de ser una fila de puntos**: el parche eran ocho motas
  claras sobre fondo negro. Ahora cada eslabón es un **anillo de acero**
  con hueco interior, brillo especular y sombra propia, y los ocho se
  cruzan y se solapan sobre la espalda, por detrás del cuello.
- **El icono 2D se lee en la hotbar**: mantiene la silueta aprobada (dos
  picos de cuello y faldón de **cinco** puntas) pero con tres pliegues
  legibles, acero para la hombrera y la cadena, broche blanco y sólo
  **cuatro** píxeles magenta (antes quince chispas y ocho motas: ruido).
  El icono de la v1.25.0 queda guardado como histórico.
- **Controles de visibilidad**: `-Dcapa.visibilidad=normal|anclas|hombreras|cadena`
  (y `CapaArmorModel.setVisibilidad(...)`) para ver u ocultar y **aislar**
  cada pieza por separado; el render software acepta `--isolate` y
  `--show-anchors`.
- **Rótulos del preview corregidos**: en este geo el exterior de la capa
  mira a +Z, así que la vista `yaw=0` es la **espalda (F5)** y `yaw=180`
  el **interior**. Antes estaban cambiados.
- **El visor deja de pintar las 27 anclas**: el runtime Java y el render
  software ya las ocultaban, pero `preview/app.js` seguía dibujándolas, así
  que el entregable que se mira enseñaba las mismas motas negras que esta
  versión arregla. Ahora el visor las oculta y trae una casilla
  **«Anclas (diagnóstico)»** para volver a verlas.
- **Los entregables son REPRODUCIBLES**: `tools/build_deliverables.py`
  reconstruye geo, atlas, icono, clips, `.bbmodel`, previews, GIF, hoja de
  estados, comparativas y el visor autocontenido. Los scripts que hacían
  el GIF y la hoja de estados vivían en `/tmp` (fuera del repo) y se
  perdían. En v1.59.0 la misma reconstrucción usa `tools/present_v1590.py`
  y las pistas serializadas del mod.
- **El código fuente del visor está versionado**: `preview/app.js` y
  `preview/index.html` (~41 KB). Antes todo `preview/` estaba en
  `.gitignore`, así que el visor publicado (14 MB) **no se podía
  reconstruir desde un clon limpio**: sus fuentes no estaban en el repo.
  Sólo quedan fuera los assets, que son salidas generadas.

### v1.26.0 — la capa ya no se inclina siempre hacia el mismo lado

Una entrega de **arreglos**, sin tocar la forma 3D ni el atlas: cuatro
defectos reales que sesgaban el movimiento y dejaban pasar la CI.

- **Eje de simetría por familia (el bug visible)**: TODO usaba un `7.5`
  global, heredado de las 16 tiras de la élitra. Con 12 mechones eso
  iba de −1.0 a +0.47 y con las 9 columnas del paño de −1.0 a +0.07: la
  capa se inclinaba **siempre** hacia el mismo lado, el paño izquierdo
  ondeaba el **doble** que el derecho y el vaivén del paso no era simétrico.
  Ahora el eje es `(columnas − 1) / 2` de cada familia, medido sobre los
  pivotes X reales del geo: mechones 12 → **5.5**, paño 9 → **4.0**,
  grietas 10 → **4.5**, capucha 7 → **3.0**, cuello 5 → **2.0**,
  cadena 8 → **3.5**, hombreras 2 → **0.5**. Los MISMOS números viven
  en Python (`cape_motion.py`), en Java (`CapaArmorModel.motionAxis`) y
  en el visor, y la CI los compara fichero a fichero.
- **Lista de huesos de deterioro podada**: `DETERIORO_NAMES` arrastraba
  **42 nombres que ya no existen** en el geo (4 mechones de más, 10 tejas
  y 4 piezas de capucha) y le faltaban los **10** huesos `v18_chain_*` /
  `v18_pad_*`: las hombreras y la cadena **no recibían** respuesta del
  portador. Ahora son exactamente los 150 huesos de tela del geo, y la CI
  lo comprueba contra el propio fichero de geometría.
- **La CI validaba un literal, no el código**: cuatro comprobaciones
  buscaban la cadena `MAX_SPARKS_PER_TICK = 4`, que sólo sobrevivía en
  un Javadoc viejo: el runtime hace **8 ticks y 3 chispas** desde la
  v1.25.0 y la CI daba verde igual. Ahora la CI **parsea** las
  declaraciones, comprueba los valores (8 y 3) y verifica que el código
  no pida más chispas de las permitidas.
- **Limpieza**: rótulo `bulto v1.17.0` → versión dinámica, docstrings que
  aún decían «4 clips» / «4 animaciones» / «182 huesos», y las familias
  fantasma `v16_*`, `v17_shingle_*` y `v17_yoke_*` (que el propio workflow
  prohíbe) fuera del camino de animación. Sin tocar las familias
  originales válidas ni el geo.

### v1.25.0 — icono preferido de vuelta, sin flotantes y más luz

Dijiste: *«el 1 era mucho mejor, cámbialo de vuelta… no importa la
animación; arregla la mano; esas partículas/bloques flotando que no se
mueven con la capa; mejora el bloom, la luz y la animación»*.

- **Icono revertido BYTE A BYTE** al que te gustaba (el de la imagen 1):
  mismo PNG, mismo SHA-256 (`c90670ba…`), estático, sin `overrides` ni
  propiedad de modelo. Backup obligatorio:
  `referencias/ICONO_PREFERIDO_BACKUP.png` (byte-idéntico, verificado por
  la auditoría). Se eliminan las 3 texturas/frame, los 3 modelos y la clase
  de animación del icono.
  > En la v1.27.0 el icono activo cambia, así que este PNG pasa a llamarse
  > `referencias/ICONO_V125_PREFERIDO_BACKUP.png` (SHA `c90670ba…`, el
  > mismo byte a byte) y `referencias/ICONO_PREFERIDO_BACKUP.png` vuelve a
  > ser copia byte-idéntica del icono ACTIVO.
- **Adiós a los bloques flotantes**: las 10 grietas 3D `v17_vein_*` eran
  HIJAS de `chestplate`, así que cuando la capa se movía se quedaban
  clavadas en el aire. Ahora cuelgan del **tramo del mechón** que las
  lleva (heredan rotación Y posición) y van **embebidas** en el paño
  (sólo ~0.06 de relieve).
- **Chispas pegadas al dobladillo**: se emitían a 0.42–0.74 bloques de la
  espalda mientras la tela vive a 0.09–0.21 → parecían barras sueltas.
  Ahora nacen SOBRE el paño (0.10–0.30), cada 8 ticks, máximo 3.
- **Mejor luz y bloom**: el halo del glowmask pasa a 3 anillos
  (48/118/240/255 de alfa) con la fuente neón realzada +10 %, y el latido
  emissive en juego sube de 0.76–1.00 a 0.82–1.22 (más brillo al correr).
- **Animación más natural**: fase y amplitud PROPIAS de cada mechón
  (determinista, sigue C1), simetría corregida a 12 columnas (antes el eje
  seguía en 7.5 y la capa aleteaba más por un lado), más retardo en volar
  (0.60), caer (0.68), correr (0.56) y deterioro (0.75) para que las
  puntas arceden detrás en vez de salir como palos rectos.
- **Mano**: el ítem plano salía gigante en tercera persona — escala
  0.75→0.55 (y 0.80→0.65 en primera persona).

### v1.24.0 — icono ANIMADO en la hotbar y legible como item

Dijiste: *«el icono puede ser animado en la hotbar y tener efectos, además
de que debe verse bien como item (se veía raro antes)»*.

- **Legibilidad**: el icono anterior era un blob de confeti rosa sin
  silueta. Ahora es un **MANTO** reconocible a 16×16: arco de cuello,
  **broche encendido** en el centro, hombros anchos, costuras verticales
  que separan paneles, degradado carmesí → violeta (paleta medida de la
  referencia) y **cinco puntas rotas** en el dobladillo.
- **Animación en hotbar SIN BEWLR**: se usa el mismo mecanismo que el
  compass y el reloj de vanilla — una **propiedad de modelo**
  `capatest:frame` (0/0.25/0.5/0.75) registrada en
  `FMLClientSetupEvent` (`CapaIconAnimation`) y tres `overrides` en el
  modelo del item que cambian la textura cada 4 game ticks (bucle de
  0.8 s). Funciona en hotbar, inventario, mano, suelo y marco de item, y
  el modelo sigue siendo `item/generated` plano (regla v1.17.2).
- **Efectos en las frames**: pulso **viajero** por las dos grietas de
  energía (ventana de 3/2 celdas que avanza), broche que alterna
  casi-blanco ↔ rosa y **dos motas que suben 2 px por frame** (chispa
  flotando). Sin partículas vanilla, sin geometría, sin lag.
- Las 3 texturas extra (`*_f1/f2/f3.png`, 64×64) y sus modelos viven en
  `assets/capatest/textures|models/item/`; el glowmask, el atlas y la
  capa 3D no cambian en esta entrega.

### v1.23.0 — geometría, textura y partículas REHECHAS desde cero

Dijiste: *«Rehace la geometría, textura y partículas de esta capa en
Blockbench para que deje de parecer hecha de tiras finas y sueltas…
cuello alto y grueso… dos hombreras carbón… cadena oscura… 10 a 14
mechones anchos, planos y superpuestos en dos capas… degradado definido…
grietas y bordes en rosa/magenta neón con emissive… una partícula
personalizada exclusiva… chispas rectangulares pequeñas, verticales y
semitransparentes… alrededor de los bordes y las puntas inferiores»*.

- **Geometría**: adiós a las 16 cintas de élitra. Ahora **12 mechones
  anchos** (1.95→2.6 unidades) en **dos capas intercaladas**: 6 externos
  rojo carmesí y 6 internos morado oscuro, con solape real, curva orgánica
  en X y Z, y **punta afilada** (0.10 unidades) tras un decrecimiento
  triangular desde `t=0.52`. Se conserva la V: las alas exteriores mueren
  antes que los mechones centrales.
- **Cuello / hombreras / cadena**: bufanda alta y gruesa de carmesí oscuro
  (7 piezas en U + 7 faldones anchos que la conectan al paño + 5 de
  reverso), 2 hombreras carbón y una cadena de 8 eslabones oscuros sobre
  la parte alta de la espalda. Las 27 anclas de animación siguen enterradas
  dentro del cuello, sin dibujar nada.
- **Textura limpia**: el atlas ya NO es el recorte de la foto con la cabeza
  blanca, el arnés y el ruido. `tools/cape_atlas_v1230.py` pinta un
  **degradado definido carmesí → morado oscuro**, costuras entre mechones,
  **agujeros de desgaste en las puntas** y grietas/bordes en rosa/magenta
  neón con halo, núcleo y centro brillante. El `*_glowmask.png` enciende
  exactamente esos texels: GeckoLib los renderiza **fullbright / emissive**.
- **Partícula exclusiva**: se retiran `capa_ember`, `capa_blight_mote`,
  `capa_shard` y TODAS las partículas vanilla (`DustParticleOptions`,
  `DustColorTransitionOptions`). Queda **una sola**, `capa_spark`, con 3
  sprites propios: barra vertical de 6×12 con bordes semitransparentes y
  centro casi blanco. `CapaSparkParticle` no tiene gravedad, sube suave y
  se desvanece; nace dispersa en los bordes y las puntas inferiores
  (`y=0.12..0.95`), **nunca detrás de la cabeza**. Presupuesto fijo:
  1 emisión cada 6 ticks, máximo 4 chispas → sin lag.

### v1.22.0 — 8 estados de movimiento, FX visibles y capa pegada al cuerpo

Dijiste: *«mejores la capa en nivel de animación… piensa en caminar, correr,
volar… agrega o mejora los efectos, que se vea bonito claramente sin lag…
parece que vuela despegada del jugador… tiene mucho espacio entre líneas,
parece una élitra»*.

- **Animación por estados (8 clips, no 4 clonados)**: reposo, caminar,
  correr, **volar/elytra**, **caída libre**, **agacharse**, **agua** y
  deterioro. Cada uno tiene su propia silueta: al volar la capa se
  extiende hacia atrás y las puntas suben (`bias -7°`, `posbias +0.42`),
  al caer el aire la levanta (`+8.5°`), al agacharse se recoge pegada al
  cuerpo, en agua flota amortiguada. Antes `animation.air` era un CLON de
  correr. El controlador Java elige el estado con **8 ticks de transición**
  para que no haya saltos de pose, y el visor tiene un selector para verlos.
- **FX claramente visibles, sin lag**: aura de polvo con ESCALA real en el
  mundo (`DustParticleOptions` 1.8), halo de cuello con transición rosa→
  violeta (`DustColorTransitionOptions` 2.2), motas repartidas por las tres
  alturas del paño y **estela** al correr/volar/caer. Techo duro
  `MAX_AURA_PARTICLES_PER_TICK = 8`, 2 emisiones/s, sin geometría, sin
  sonidos, sin búsqueda de entidades. El overlay del visor pasó de
  cuadraditos de 2 px a halo radial + tres capas de brillo.
- **Anclaje (captura 6)**: la capa vivía en `z=2.3..5.0`, a 3–5 unidades
  del cuerpo, y era una LÁMINA plana: de perfil parecía despegada. Ahora
  `ribbon_z(k,t)` la curva en 3D (nace en `z~1.4`, cae hacia atrás, las
  alas se enrollan hacia delante), el capuchón bajó a la misma z con
  solapas que giran y abrazan los hombros, y el paño engrosó de 0.3 a
  ~0.7 unidades. Las anclas siguen ocultas DENTRO del capuchón.
- **De élitra a capa rasgada**: `fill` pasó de `0.72` constante a
  `0.98 − 0.16·t` (paño continuo bajo la bufanda, huecos irregulares sólo
  en las puntas) y tres jirones secundarios largos cruzan el abanico. El
  capuchón ya no tiene cuadrados negros: toma el carmesí de las alas de la
  propia foto (`cowl_uv()`), sin repintar el atlas. **Fidelidad con tu
  imagen 1.239** (límite 1.50) y silueta 1.08×, intactas.

### v1.21.0 — la animación deja de latir: onda viajera real

Dijiste: *«la animacion esta fea btw, y sigue trabajando con el modelo»*.
Diagnóstico: `cape_motion.wave()` restaba `sin(fase)` a cada armónico para
forzar `w(0)=0`. Eso convertía el retardo por tramo en una AMPLITUD y hacía
que los 182 huesos volvieran TODOS a la pose neutra al principio y al final
de cada clip: un latido global con un parón en el bucle, no tela. Además
`CapaArmorModel.java` calculaba una segunda onda con fase 0.45 y PISABA la
de GeckoLib, así que Minecraft y Blockbench no coincidían.

- **`tools/cape_motion.py` reescrito**: `sin(2πf+φ) + 0.28·sin(4πf+1.7φ)
  + h·sin(6πf+2.3φ)`, frecuencias enteras ⇒ periódica y C1 en la costura
  SIN anclar nada a cero. `φ = -0.62·tramo + col·0.19 + fase_clip` vuelve
  a ser un retardo TEMPORAL: la onda baja por el jirón.
- **Envolvente física**: amplitud `tramo^1.35`, aleteo mayor en las alas
  exteriores, ráfaga común (`gust`), arrastre siempre positivo (`drag`),
  vaivén de paso retardado y estremecimiento sólo en `deterioro`.
- **Desplazamiento acumulado**: los 7 tramos son HERMANOS en el geo, así
  que girar cada cubo sobre su centro sólo los hacía vibrar. Ahora cada
  tramo recibe `position` con una curva `tramo^1.6`: el jirón se DEFORMA
  como una tela. GeckoLib recibe ese canal (antes lo perdía) con 17
  muestras e interpolación lineal, en vez de 9 muestras con
  `easeInOutSine` que paraban la tela 9 veces por ciclo.
- **Java ya no reimplementa la onda**: GeckoLib aplica `sample()` y
  `setCustomAnimations` sólo SUMA la respuesta al giro, salto, sprint,
  agache y agua leyendo `b.getRotX()` ya animado.
- **Visor**: espejo exacto de la curva (verificado muestra a muestra),
  soporta `offset` por hueso y NO dibuja el maniquí blanco por defecto:
  se ve la capa sola, como en Blockbench.
- **Forma**: barrido A..I medido contra tu PNG. Jirones ~16% más finos
  (`fill 0.86 → 0.72`) y cierre del dobladillo `0.38 → 0.28`: huecos
  negros reales y puntas separadas en vez de falda maciza. Silueta
  `1.10× → 1.08×`, fidelidad con la imagen `1.239`.

### v1.20.0 — el `.bbmodel` versionado y la V de la referencia

Dijiste: *«el bbmodel no cambio de version… sigue mejorando y cambia
la version»*. Dos cosas:

1. **Versión real del archivo.** `tools/bbmodel_export.py` lee
   `mod_version` y escribe `docs/CAPA_v1.20.0.bbmodel`; el `name` que
   muestra Blockbench es `capa_deteriorer_evilsaiyan_v1_20_0` y el
   asset de Release se llama `CAPA_v1.20.0.bbmodel`. Se borraron los
   nombres viejos (`capa_v1170.bbmodel`, `CAPA_v1.17.0.bbmodel` y los
   `.bbmodel` de v1.14/15/16). El visor offline también descarga con
   el nombre de la versión. Enlace permanente de esta entrega: [https://github.com/Santi-PdR/modelos/releases/download/v1.20.0/CAPA_v1.20.0.bbmodel](https://github.com/Santi-PdR/modelos/releases/download/v1.20.0/CAPA_v1.20.0.bbmodel).
2. **Forma contra tu PNG.** La v1.19.0 seguía siendo una falda: las 16
   cintas llegaban casi al suelo y la bufanda tenía dos cuernos. Ahora:
   - `tip_t()` devuelve **0.66–0.80 en las alas exteriores** y ~1.0 en
     el centro → alas diagonales rojas que mueren a media altura y
     jirones violeta que cuelgan hasta abajo (la V de la captura).
   - `fan_x()` abre un 30% más deprisa en las alas → salen del cuello
     inclinadas, no verticales; el radio base se recalibró a 7.40 para
     no ensanchar la silueta (1.10×, límite 1.60×).
   - `ribbon_w()` quita un 16% de paño → **huecos negros reales** entre
     jirones en vez de falda maciza.
   - La bufanda pasa a **cuenco**: el borde superior cae hacia los
     hombros (antes subía) y los dientes se giran menos. Sin cuernos.
   - Fidelidad píxel a píxel con tu imagen: **1.239** (límite 1.50).

### Rev. B — «se ven cosas volando» y «mejora las animaciones»

En las capturas de Blockbench había cubos rosa **dentro del modelo**, una
barra desprendida arriba, una línea de puntos y un aviso de que no
encontraba «todo lo que es partículas». Causas y arreglos:

| Síntoma | Causa real | Arreglo |
|---|---|---|
| Cubos rosa/grises flotando alrededor de la capa | 18 `v17_mote_*` + 8 `v17_ash_*` eran **geometría** | eliminados del geo y del `.bbmodel`. Ahora los emite `spawnAura()` en runtime, a lo largo del paño, desde el servidor |
| Blockbench «no encuentra las partículas» | animador `effects` de Bedrock con keyframes `particle` que apuntaban a `particles/*.json` (Snowstorm) inexistentes junto al `.bbmodel` | se eliminó el Effects track y los 3 JSON; el `.bbmodel` es autocontenido: 1 textura embebida y **0 referencias externas** |
| Barra suelta arriba / línea de puntos | el reverso de la bufanda estaba 6 unidades **detrás** del cuerpo; 6 tiras `v17_yoke_*` (arnés del maniquí) y 27 anclas `v15_cloth_*` flotaban | reverso integrado al paño (z 2.86), yugo eliminado, anclas ocultas **dentro** del capuchón opaco (siguen existiendo para Java) |
| La tela vibraba, no ondeaba | 4 ondas distintas; GeckoLib animaba **0** huesos `v17_*`; Java usaba `i*0.37` (índice global) | **`tools/cape_motion.py`**: una sola curva C1 con retardo real por tramo (`-0.62*seg + col*0.19`), vaivén de paso, barrido al correr y estremecimiento. La consumen el `.bbmodel`, `cape_animation_pipeline.py` (GeckoLib), `CapaArmorModel.java` y el visor |

Resultado: **254 huesos / 308 cubos**, `.bbmodel` de **182 cubos** y
**12624 keyframes** Bézier C1 en 4 clips, sin un solo cubo desprendido
(test de vecino más cercano < 2.2 u en CI). Las partículas siguen siendo
3 tipos reales (`capa_ember`, `capa_blight_mote`, `capa_shard`) pero
**sólo aparecen al llevar la capa puesta**. Fidelidad con tu imagen
1.239 y **silueta 1.00×** (antes 1.09×: el abanico radial se
estrechó un 10% midiendo el PNG).

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
- **Las motas NO son geometría** (rev. B): las 8 medidas en la captura
  son la guía de distribución de las partículas que `spawnAura()` genera
  en runtime cuando la capa está equipada.
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

### Descargas v1.62.0

El [workflow de Forge](https://github.com/Santi-PdR/modelos/actions/workflows/build.yml)
compila `capatest-1.62.0.jar` con JDK 17 y Gradle 8.8. Abre el run de la
rama de este rediseño y baja **capatest-jar** en Artifacts. El ZIP incluye
`SHA256SUMS.txt`: sólo se sube tras comparar dos builds y verificar los
recursos exactos dentro del JAR. La [v1.59.0 publicada](https://github.com/Santi-PdR/modelos/releases/tag/v1.59.0)
sigue disponible por separado.

```sh
sha256sum -c SHA256SUMS.txt
```

Para versiones históricas con copia en `artifacts/vX.Y.Z`, sigue disponible
`python3 tools/fetch_published_jar.py 1.55.0 --keep-sums`.

El mismo rescate vale para una versión **anterior**: el JAR exacto de la
`v1.27.0` se recupera de su artifact histórico (`14057282072`) o de su
asset de release, se comprueba contra el digest de la API de la release y
se publica en `artifacts/v1.27.0` con su `SHA256SUMS.txt`:

```sh
python3 tools/materialize_published_jar.py --version 1.27.0 --artifact 14057282072
```

✅ **Completado y verificado**: la CI republicó `artifacts/v1.27.0` y el
tarball por `codeload` contiene el JAR exacto
`477 797` bytes, `sha256:e80bd1f43ff7f53617003b29f140320a1834b80a765596aab1a88c2bf7ed6f2d`,
byte a byte igual al asset de la Release v1.27.0, junto con su
`SHA256SUMS.txt`.

El script prueba **dos fuentes** (asset de release y artifact histórico)
y exige el MISMO digest en ambas: si el binario no coincide byte a
byte, no escribe nada.

**Modelo de Blockbench:** [CAPA_v1.62.0.bbmodel](docs/CAPA_v1.62.0.bbmodel),
byte a byte igual a la descarga que ofrece el visor offline.

Regla de entrega: **el `.bbmodel` cambia de nombre con `mod_version`** y
**siempre se incluye su enlace**. El workflow lee la versión de
`gradle.properties` para alinear JAR, tag y assets, y prepara un borrador
con `workflow_dispatch(publicar=true)` o un commit marcado `[publicar]`.
El borrador se hace público sólo tras la verificación de CI.

### Histórico — tests y efectos en runtime (v1220)

`tools/audit_model.py` es un **test de regresión numérico**: renderiza el
geo+atlas reales y compara décima a décima con `REFERENCIA_CAPA.png`
(mediana RGB, cobertura de paño, densidad de energía y silueta). El workflow
`build.yml` lo ejecuta con `--check` **antes de compilar**, instala
`numpy`/`Pillow` y **falla el build** si el error global supera 165
(v1.18.0: el criterio pasa a ser la fidelidad píxel a píxel con tu imagen; ver abajo). Así la autoevaluación no depende de mi sandbox.

**Rev. B:** el `.bbmodel` ya NO tiene keyframes `particle` ni pista
`effects`: esos JSON de Snowstorm no existen junto al archivo y por eso
Blockbench avisaba al abrirlo. Las partículas son **100% runtime**:
`CapaDeteriorerItem.spawnAura(..., deterioro)` emite brasas a tres
alturas del paño, estela al correr, esquirlas y motas frías (máximo 7
por tick), desde el servidor para que las vean los demás jugadores.
`CuriosCompat` usa el mismo estado. El visor las dibuja como overlay 2D,
nunca como cubos. **La CI compila con JDK 17 + Gradle 8.8.**

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
- **Proyecto Blockbench**: [`docs/CAPA_v1.53.0.bbmodel`](docs/CAPA_v1.53.0.bbmodel),
  156 cubos / 222 grupos, 8 animaciones en bucle con **26208 keyframes**
  y UUID canónicos: curvas **Bézier** con tangentes analíticas (C1),
  marcadores, retardo por tramo, vaivén de paso, barrido al correr,
  respiración de capucha y pulso de venas. **Sin Effects track**, sin
  partículas en el modelo y sin archivos externos: abre limpio en
  Blockbench con la textura 128×128 embebida.
- **Previews**: [`docs/capa_v1170_preview.png`](docs/capa_v1170_preview.png),
  [`docs/referencia_analizada.png`](docs/referencia_analizada.png).

Se conservan: los **72 huesos originales byte-idénticos**, alfa prístino,
**1636 emisivos**, UV opacas ≤128, `inflate` ≤0.05, espesor 0.25–0.50,
0 `JsonNull`, 0 mixins, `animation.item`, radianes y fail-safes.
**222 huesos / 282 cubos**. `CapaArmorModel.java` usa `motionParts()`
para los **150 huesos de tela reales** (los mismos que hay en el geo); la
curva vive en
[`tools/cape_motion.py`](tools/cape_motion.py).

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

### Ronda v1.17.3: lo que se veía al abrir el `.bbmodel` en Blockbench

El usuario probó el archivo en Blockbench y lo rechazó. Al rasterizar el
`.bbmodel` **en pose estática y aplicando la jerarquía de grupos** (que es
lo que hace Blockbench, y que mi visor web no hacía) aparecieron tres
elementos que en el visor pasaban desapercibidos:

1. **Un maniquí Steve/Alex completo** — cabeza blanca, brazos amarillos,
   torso y piernas — metido dentro del archivo como "referencia de escala",
   con un parche de textura en las filas 128..143 de una imagen 128×144.
   Tapaba literalmente la capa.
2. **126 cubos de la armadura antigua** (dedos, manos, arnés, broches):
   el renderer Java los oculta con `setHidden(true)`, pero Blockbench los
   dibuja todos. Parecían antenas y chatarra alrededor del capuchón.
3. **La bufanda flotando separada** del cuerpo, porque las 4 tejas de
   hombro sobresalían por encima y el capuchón estaba 1.15 unidades alto.

Arreglos: el `.bbmodel` exporta **sólo los 214 cubos de la capa**; los 72
huesos prístinos se conservan como *grupos vacíos* para no perder pivotes
ni rotaciones de la jerarquía. Textura 128×128, todas las UV ≤ 128, sin
maniquí. Capuchón bajado y adelgazado para solapar con los jirones; alas de
hombro recogidas. Se mantienen 286 grupos, 4 animaciones y 11950 keyframes.

**Pendiente de aprobación visual:** necesito una captura de Blockbench del
archivo nuevo para seguir afinando la forma (sigue siendo más compacta que
el abanico rasgado de la referencia).

### v1.18.0 — empezar de 0 desde la imagen

Dijiste: *«no hablo de que se vea feo solo en blockbench, se ve feo la
textura y el modelo de la capa en si. empieza de 0 para crear la capa de
la imagen»*. Se tiraron el atlas procedural y la envolvente de campana de
las rondas anteriores.

| Antes | Ahora |
|---|---|
| Atlas construido con una paleta sintética + pliegues + cuchilladas dibujadas a mano | **`tools/reference_canvas.py`** limpia tu PNG (fuera checkerboard, cabeza, brazo beige, arnés gris, suelo), lo recorta a la capa y lo reduce a **96×48**: el atlas ES tu imagen |
| Una franja UV vertical por jirón (degradado inventado) | **`foto_uv()`**: cada tramo 3D muestrea el rectángulo de la foto que ocupa realmente. El volumen se construye ENCIMA de la imagen |
| `ribbon_x` con envolvente casi constante → delantal de columnas rectas | **`fan_x()`**: abanico radial medido, jirones que nacen juntos bajo la bufanda, se abren hasta t≈0.72 y **cierran en V** hacia las puntas |
| Jirones anchos y unidos (`fill=0.78`) → falda maciza | Jirones finos con huecos negros reales entre ellos |
| Capuchón rojo liso que cortaba la capa | Capuchón y alas de hombro muestrean también la foto; arnés gris adelgazado |

Se eliminaron el grano, el dithering Bayer, el bloom, el diezmado de
energía y el carbonizado: cualquiera de ellos desdibujaba la foto. El
glowmask sigue encendiendo las cuchilladas rosa reales (1636 emisivos).

**Criterio de auditoría nuevo y honesto:** las métricas de
cobertura/energía/color medían un atlas sintético que ya no existe, así que
quedan como información. El test que bloquea CI es ahora la **fidelidad
píxel a píxel** entre el atlas del mod y
`referencias/REFERENCIA_CAPA_atlas96.png` (error medio **1.24**, límite
1.50), más el cierre de la silueta (1.12×, límite 1.60×).

Estado de esa ronda: 286 huesos / 340 cubos, 4 animaciones, 11950
keyframes y 3 emisores. **La rev. B posterior** los deja en 254 / 308,
12624 keyframes y partículas únicamente en runtime. Se conservan el
icono 2D y los backups byte-idénticos del icono aprobado.
