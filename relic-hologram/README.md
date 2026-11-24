# Holographic Core / Núcleo Holográfico

Reliquia cosmética para **Minecraft 1.20.1 / Forge**: un núcleo holográfico de luz
azul que flota sobre un hombro del portador, con estelas orbitales, esfera
armilar, cristales y efectos intermitentes. Se equipa en el slot **`charm`** de
Curios y se anima con GeckoLib 4.

| Pieza | Versión verificada |
|---|---|
| Minecraft | 1.20.1 |
| Forge | 47.4.0 (rango `[47.4,)`) |
| Java | 17 |
| GeckoLib | **4.8.1** compilado (`geckolib-forge-1.20.1-4.8.1`, Modrinth `bVtfWE8S`); el `mods.toml` acepta `[4.8.1,)`, así que 4.8.4 también vale |
| Curios API | **5.14.1+1.20.1** (última build para Forge 1.20.1) |
| modid | `holocore` |

GeckoLib y Curios son **dependencias obligatorias**: el ítem implementa
`ICurioItem` y el render usa `ICurioRenderer` + `GeoObjectRenderer`. Sin Curios
el ítem no tendría slot y sin GeckoLib no hay modelo.

## Compilar

```bash
cd relic-hologram
./gradlew build          # o: gradle build
# -> build/libs/holocore-<mod_version>.jar  (la versión sale de gradle.properties)
```

El workflow `.github/workflows/holocore.yml` hace lo mismo en CI y, antes de
compilar, valida que:

* los seis assets (geo, geo lite, dos animaciones y dos texturas) son
  **byte a byte** los del zip `reliquia_holografica_para_mod_v19.zip`;
* todos los JSON son válidos y no contienen `null` (GeckoLib 4.8 lanza
  `UnsupportedOperationException` con un `"parent": null`);
* están las 20 animaciones, las capas solo tocan `relic_react`, y los .geo de
  calidad full/lite declaran los mismos 98 huesos;
* `RelicAnimations.java` coincide con `tools/relic_manifest.json`
  (`python3 tools/gen_relic_constants.py --check`);
* el tono del aura sobre nieve, piedra y cueva se comprueba con números
  (`tools/check_aura_math.py`), no a ojo;
* el JSON del shader propio es coherente (blend aditivo, `count` de cada uniform,
  atributos dentro de `NEW_ENTITY`) y todas las claves de la config están
  documentadas en la tabla de abajo;
* el shader **compila de verdad**: el arranque del cliente tiene que dejar
  `Shader del aura compilado` en el log, o el build falla.

Cambios por versión: [CHANGELOG.md](CHANGELOG.md).

Para publicar el jar como Release: ejecutar el workflow a mano con
`publicar = true`, o un push cuyo mensaje contenga **`[publicar-holocore]`**.

> La palabra clave es exclusiva de este mod a propósito: `.github/workflows/`
> `build.yml` (el workflow viejo de *Mantle of the Blight Star* / `capatest`)
> también publica cuando ve `[publicar]` en el mensaje, así que reutilizarla
> desde aquí re-subía la release `v1.28.0` del otro mod.

## Probar en el juego

`./gradlew runClient` arranca un cliente de desarrollo con GeckoLib y Curios.

> El CI lanza ademas `runClient` bajo xvfb (sin GPU): comprueba que el mod
> construye, que Curios registra el renderer y que el cliente no cae. Ese test
> ya encontro un fallo real (un evento del bus FORGE registrado en el bus MOD).
>
> **Nota de dev:** Curios 5.14.1 trae su refmap de Mixin con nombres SRG
> (`f_19803_` = `Entity.firstTick`); con mappings `official` y en entorno de
> desarrollo ese refmap no se remapea y el arranque falla en `AccessorEntity`.
> Por eso los runs de `build.gradle` llevan `mixin.env.disableRefMap=true`. No
> afecta al jar publicado (ahí el refmap SRG es el correcto).

En el juego:

* `/give @s holocore:holographic_core` o la pestaña creativa **Holographic Core**;
* receta: amatista arriba y abajo, dos cristales y un diamante en el centro;
* equipar en el slot **charm** del inventario de Curios (tecla por defecto: `C`).

### Teclas y comandos

| Acción | Cómo |
|---|---|
| Despertar / dormir | tecla **G** o `/relic toggle` |
| Pulso manual | tecla **P** o `/relic pulse` |
| Pasar de un estado de brillo al siguiente | tecla **M** o `/relic mood next` |
| Pulso de energía | `/relic pulse` |
| Liberación total | `/relic release` |
| Afinar posición | `/relic offset <x> <y> <z>` (píxeles de modelo) |
| Afinar escala | `/relic scale <0.1–4.0>` |
| Cambiar de hombro | `/relic side left\|right` |
| Calidad (full/lite) | `/relic quality full\|lite` |
| Ver valores actuales | `/relic info` (tres líneas: placement, estado en vivo y brillo) |
| Cambiar de "look" de golpe | `/relic preset soft\|normal\|showcase` — ajusta ritmo, aura, halo, GLSL, anillo y destello a la vez (no guarda: `/relic save`) |
| Probar un efecto | `/relic vfx shock [fuerza]` — destello a mano (0.1–1, por defecto 0.6) para ver la onda de choque sin esperar a que pase nada |
| Probar una animación | `/relic anim <nombre>` · `/relic anim list` |
| Ajustar cualquier clave | `/relic set` (lista) · `/relic set <clave> <valor>` |
| Guardar los ajustes | `/relic save` |
| Volver a los valores de fábrica | `/relic reset` · `/relic reset <clave>` (una sola) |
| Ver o forzar el estado de brillo | `/relic mood` · `/relic mood <auto\|dark\|rain\|storm\|wounded\|hunted\|resonant\|night\|submerged\|portal\|burning\|freezing\|nether\|end>` |
| Recorrer los estados o ver la lista | `/relic mood next` (ronda, igual que la tecla M) · `/relic mood list` (los trece, con el que manda marcado) |
| Forzar el suelo del eco | `/relic echo [auto\|hard\|loose\|water\|next]` (dispara un pulso para que se vea, desde 1.0.57) |
| Que los estados pasen solos | `/relic mood cycle [segundos]` (6 por defecto, 1–60) · `/relic mood cycle 0` para parar |
| Ver la reliquia de cerca | `/relic preview` · `/relic preview <0.5–6>` (bloques) |
| Medir el coste | `/relic stats` · `/relic stats reset` |

Los comandos de ajuste son de **cliente** y cambian la config en memoria al
instante (no la guardan): cuando el núcleo quede donde quieres, copia los
números de `/relic info` a `config/holocore-client.toml`. Desde 1.0.41 esa línea
de brillo termina con **el bucle y el ritmo** (`bucle idle 0.65x`): es la forma de
comprobar sin mirar qué animación está sonando y cuánto la está acelerando la
config, que era justo lo que no se podía ver cuando "iba demasiado rápido". La
segunda línea de
`info` dice lo que no se puede adivinar mirando: estado del bucle (`charged`,
`alert`…), destello actual, por qué el pase GLSL está apagado si lo está
(`shaderGlow=false`, shaderpack activo o no compiló) y las intensidades que están
mandando ahora mismo.

`/relic anim` reproduce cualquiera de las 20 animaciones por su nombre corto
(`/relic anim layer_shake`, `/relic anim release`, `/relic anim idle_calm`…), así
que se pueden revisar todas sin depender de que un mob te pegue o de esperar a que
salga una variación de reposo. Las de bucle se reproducen una vez.

`/relic stats` mide lo que no se ve. Dice cuántos **pases por dibujo** se están
emitiendo (1 si solo queda el pase base, 4 con base, emisivo, halo y GLSL),
cuántos dibujos por segundo y cuántos **milisegundos** cuesta una reliquia por
dibujo, separando modelo y aura. Es la forma de comprobar en tu máquina lo de
1.0.16 (una evaluación de animación por frame en vez de cuatro) —comparar con
1.0.15 en el mismo sitio es la prueba— y de decidir si hace falta `quality=lite`,
`glowHalo=false` o bajar `maxRenderDistance`: mira el número, cambia la palanca,
vuelve a mirar. `/relic stats reset` reinicia la media.

`/relic set` ajusta **cualquiera** de las claves de la tabla de configuración en
caliente, sin cerrar el juego: `/relic set` sin argumentos lista las 22 claves con
su valor actual, `/relic set auraIntensity 0.55` la cambia y te dice el
valor nuevo (vale el nombre completo o el corto, siempre que no sea ambiguo). Todo es **en memoria** mientras
pruebas, igual que con `/relic offset`: cuando el número te guste, **`/relic save`**
lo escribe en `config/holocore-client.toml`. Mientras haya valores sin guardar,
`/relic info` añade una línea amarilla diciendo cuántos son, para que no se
queden en el aire al cerrar el juego. Las dos únicas claves sin pasar por
`set` son `placement.shoulder` y `visuals.quality`, que tienen su propio comando
(`/relic side`, `/relic quality`) porque además validan el texto — y también
cuentan como cambios sin guardar.

`/relic reset` devuelve las **24** claves a lo que trae la config de fábrica, también
en memoria: si el resultado te gusta, `/relic save`; si no, cierra sin guardar y el
archivo sigue como estaba. Solo cuenta —y solo marca como sin guardar— las claves que
de verdad estaban en otro valor; si ya estaba todo de fábrica, lo dice y no toca nada.
Con una clave delante (`/relic reset auraIntensity`) vuelve solo esa, que es el deshacer
de un experimento suelto sin perder los demás ajustes.

`/relic set` sin argumentos lista las 22 claves con su valor actual y marca con `*` las
que no están guardadas todavía, así se ve de un vistazo qué se pierde al cerrar.

`/relic preview` dibuja **tu** reliquia delante de la cámara, a una distancia fija
(2.5 bloques por defecto; `/relic preview 1.5` la acerca), con los mismos cuatro
pases y el mismo aura. Es para mirar el brillo siempre igual y sobre cualquier
fondo —nieve, arena, cueva— sin depender de dónde caiga el hombro ni de ponerse en
tercera persona: el estado sigue siendo el real (si te pegan, se pone cargada), y
la vista previa se apaga sola al salir del mundo.

`pulse`, `release` y
`toggle` sí viajan al servidor, para que el resto de jugadores vea lo mismo. El
estado se replica solo a quien puede verlo (misma dimensión, ≤64 bloques; quien
se acerque después lo recibe al empezar a trackear), y el servidor ignora más de
una acción cada 4 ticks por jugador, así que un cliente modificado no puede
inundar la red.

## Brillo y shaders

Los pases normal y emisivo usan `entityTranslucentEmissive` con el lightmap a
tope (`FULL_BRIGHT`), que es justo lo que los shaderpacks (Iris/Oculus/OptiFine +
Complementary, BSL…) usan para detectar emisivos y aplicar su bloom. Encima hay
un tercer pase con **blend aditivo**: suma luz en vez de mezclarla, así que el
núcleo brilla también sin shaderpack.

Los dos pases emisivos llevan `LightTexture.FULL_BRIGHT`, así que el núcleo **se ve
igual de noche, en cuevas, bajo el agua y con la antorcha apagada**, con y sin
shaderpack. Si el coste molesta: `glowLayer=false` deja solo el pase base (que ya
es fullbright), `glowHalo=false` quita el halo y `shaderGlow=false` el GLSL.

La **aura** son tres billboards (quads que miran a cámara) con la textura
`relic_aura.png`, girando a distinta velocidad, sumados con el mismo blend
aditivo. Eso da el resplandor alrededor del núcleo sin tocar la pantalla y sin
depender del pack; la textura se genera con `tools/make_aura.py`.

Desde 1.0.11 el aura está **pegada al núcleo**: 0.62 / 0.85 / 1.10 bloques de
diámetro (antes 1.05 / 1.55 / 2.10, o sea cuatro veces el tamaño del modelo),
pesos 0.30 / 0.17 / 0.09 y alpha de quad 0.55. El motivo está explicado en
[BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md) §3.B: con blend aditivo, sumar
mucho sobre un fondo claro satura los tres canales y el aura se ve **blanca**
aunque el tinte sea azul. Es lo que pasaba sobre nieve hasta 1.0.10.

Desde 1.0.12 el aura son **dos pases** de los mismos tres quads: uno de **tinte**
(mezcla normal con el color del estado) y encima el **aditivo** del brillo. El aditivo
solo puede aclarar, así que sobre nieve siempre acaba en blanco; el pase de tinte
es el que conserva el color del estado. Se apaga con `auraTint=false` si prefieres
solo el brillo.

El **anillo de estado** (`relic_ring.png`, generado con `tools/make_ring.py`) es
un cuarto billboard que solo aparece cuando la reliquia tiene algo que contar
(1.15 bloques: apenas por fuera del aura, para que se lea como anillo y no como
un borde más), y tanto el anillo como el aura cambian de color con el estado:

| Estado | Color | Aura | Anillo |
|---|---|---|---|
| `idle` | azul frío | 1.0 | tenue, giro lento |
| `idle_calm` | azul apagado | 0.7 | no sale |
| `idle_charged` | ámbar | 1.15 | marcado, giro rápido |
| `idle_alert` | rojo | 1.05 | late como un aviso, gira al revés |
| `idle_dormant` | gris azulado | 0.35 | no sale |

Y por encima del ciclo de animación hay **catorce estados de brillo** que solo cambian
la luz, no la animación (`RelicAnimatable.Mood`, desde 1.0.29; los dos de dimensión son de
1.0.51 y el de peligro de 1.0.60). Se aplican cuando mandan: ardiendo > congelándose >
herido > **peligro** > tormenta > agua > portal > Nether > End > oscuridad > lluvia > noche >
resonancia.

| Estado de brillo | Cuándo | Qué hace |
|---|---|---|
| herido (`wounded`) | al portador le queda menos del 35% de vida | tira el color a rojo, sube el aura y enciende el anillo aunque esté en reposo |
| peligro (`hunted`) | **un monstruo** a menos de `alertRadius` bloques (desde 1.0.60) | magenta de alarma —el único color así en la paleta—, el anillo más marcado de todos (+0.45), vaivén 1.30, giro 1.26× y un **escáner**: un anillo que sale del núcleo cada 2 s y se apaga al abrirse (desde 1.0.61) |
| tormenta (`storm`) | truena donde está el portador | azul casi blanco, más aura y el giro más rápido | Cada 5–11 s pega un destello como el cielo (desde 1.0.42).
| resonancia (`resonant`) | otro portador a menos de 12 bloques | violeta, anillo más marcado y giro rápido: las dos reliquias se «oyen» |
| oscuridad (`dark`) | menos de luz de bloque 4 **y** menos de luz de cielo 8 (encerrado) | casi blanca y bastante más aura: en una cueva es la única luz que hay |
| lluvia (`rain`) | llueve encima del portador (sin tormenta) | azul profundo, anillo más tenue y las chispas se cambian por **gotas que caen** (desde 1.0.38) |
| noche (`night`) | hay cielo, es de noche y no llueve (desde 1.0.32) | pálido y frío, giro lento y las chispas flotan a media velocidad y con la mitad de densidad |
| agua (`submerged`) | el portador tiene los ojos dentro del agua (desde 1.0.33) | verde azulado, el anillo casi apagado, el giro más lento de todos (0.66×) y las chispas se cambian por **burbujas** que suben y se apagan |
| portal (`portal`) | un portal del Nether, del End o de salida a menos de 4 bloques (desde 1.0.35) | violeta de obsidiana, giro 1.22× y las chispas estiradas hacia arriba, como el borde del portal |
| ardiendo (`burning`) | el portador está en llamas (desde 1.0.39) | naranja de brasa —el único estado cálido—, giro 1.40× (el más rápido), el vaivén más amplio y **brasas que suben parpadeando** |
| congelándose (`freezing`) | el portador se está helando (nieve en polvo, desde 1.0.45) | hielo pálido, giro 0.78×, apenas se mueve y **copos diminutos que caen en zigzag** |
| Nether (`nether`) | el portador está **en el Nether** (desde 1.0.51) | brasa de forja —más roja y honda que ardiendo—, giro 1.14×, más vaivén y **pavesas** que salen disparadas y caen, no brasas que solo suben (VFX propio desde 1.0.53) |
| End (`end`) | el portador está **en el End** (desde 1.0.51) | hueso verdoso, el anillo casi apagado, el vaivén más corto y **motas del vacío** que giran despacio y se apagan por el camino (VFX propio desde 1.0.52) |

El conjunto además se mueve solo: **flota** con un vaivén lento de 0.022 bloques
(la amplitud sube con la tormenta y baja cuando está herido, y **+60% si corres**) y
**se asienta** en cada evento, achatándose un 4% y ensanchándose un 5%. Es lo que separa «una animación que
se reproduce» de «un objeto que está ahí». El movimiento se aplica al `PoseStack`
antes del modelo y del aura, así que los dos se mueven juntos; se rota la matriz en
el sitio para no crear un cuaternión por reliquia y frame.

En cada evento, además, el anillo del estado se tumba **en el suelo**: se dibuja con los ejes
del portador (X y Z de la pose) y baja por su Y, no por la de la pantalla, así que la onda
golpea el suelo a sus pies en vez de ser otro aro de frente. Solo se dibuja en tercera persona
—en la vista previa no hay suelo y quedaría una tarjeta en el aire— y se apaga con
`visuals.groundEcho`.
El eco **lee el suelo** desde 1.0.55: sobre piedra o metal se cierra y rebota en un segundo
anillo, sobre arena o tierra se abre y se apaga antes, y sobre agua es un rizo más ancho y más
tenue. Se decide por la dureza del bloque (`getDestroySpeed`), una vez por segundo, no por una
lista de bloques — que se quedaría vieja a la siguiente versión del juego. Y lo que cede
**también salta** (1.0.56): polvo en arena y tierra —solo tinte, el polvo no brilla— y
salpicadura en el agua; la piedra no levanta nada.

Y el eco **también cae al andar** (1.0.62): cada 0,85 bloques aparece un anillo pequeño donde
está el pie (0,45 de la fuerza de un evento, se apaga en 0,35 s), con su polvo o su salpicadura
si el suelo cede. Se apaga con `visuals.groundEcho`, como el eco de los eventos, y en el agua no
hay pisada. En calidad `LITE` el paso se queda en el anillo: el polvo son siete quads y pasa
muchas veces por minuto (el de un evento sí se mantiene, porque es un suceso y no algo continuo).

Para mirar los cuatro sin moverte: **`/relic echo hard|loose|water|next`** fuerza el suelo y
dispara un pulso para que el eco se vea en el sitio, y `/relic echo auto` vuelve al bloque de
verdad (que `/relic echo` a secas te dice cuál es, y `/relic info` lo añade con un `*` cuando
está forzado, desde 1.0.57).

Los **tres pases de evento** (eco del suelo, onda de chispas y eco del anillo) se **tiñen**
antes de sumar, como el aura y el anillo: con solo aditivo, sobre nieve sumaban a un fondo ya
casi blanco y desaparecían. Regla: tinte con cobertura 3× el aditivo, y aditivo entre 0.12 y
0.18. Los números están comprobados en `tools/check_aura_math.py`, que compone los tres pases
sobre nieve, piedra y cueva.

**Unidades**: el reloj interno de la reliquia son ticks y todo efecto nuevo pasa por
`seconds()` (`ticks / 20`). Los primeros VFX de estado se escribieron en «por segundo» sin
convertir y salían 20× rápidos — de ahí el vaivén de 5,4 Hz que hacía que la reliquia
pareciera saltar en el sitio (corregido en 1.0.43).

En cada evento (pulso, golpe, liberación, subida de nivel) el destello abre además una
**onda de choque**: ocho partículas que salen del núcleo, se abren de 0.16 a 0.62 y se
apagan mientras giran. Sale del propio destello, así que **no guarda estado ni crea
objetos** en el render, y en reposo no cuesta ni un quad. Con el portador en movimiento
las chispas dejan además una **estela** de dos quads por chispa, más apagada y pequeña.

Al cambiar de estado de brillo la reliquia da un destello corto y un **glitch** de
una sola vez (la misma animación y el mismo uniform `HoloGlitch` que el pulso), para
que se note que ha reaccionado a algo, y **cambia la velocidad del bucle** (agua 0.66×, congelándose
0.78×, herido 0.72×, noche 0.85×, resonancia 1.18×, portal 1.22×, tormenta 1.32×, ardiendo
1.40×):
no es solo color. `/relic info` lo dice en una línea
aparte, así que si el aura se pone roja no hay que adivinar por qué.

Para verlos sin montar la escena está `/relic mood <estado>`, que fuerza uno de ellos,
`/relic mood auto` para volver a la detección normal, `/relic mood next` para pasarlos
de uno en uno (lo mismo que la **tecla M**, con el aviso en la barra de acción en vez
del chat), `/relic mood cycle [segundos]` para que pasen solos (con `0` se para, y
avisa igual que la tecla, así que al mirar la grabación se sabe qué estado es cada
tramo) y `/relic mood list` para ver los catorce nombres con el activo marcado: en
oro si está forzado, en azul si lo ha elegido la escena. Es la forma de mirar la
tormenta o el herido con un solo jugador y sin comandos raros.

Cada cambio de estado **suena** desde 1.0.58, con un tono distinto por estado (trece, todos
diferentes; los graves resuenan y los agudos tintinean, siempre con ametista de vanilla). Va
bajo la misma guarda que el glitch del cambio, así que entrar y salir de una cueva no encadena
campanadas, y se apaga con `sound.events`/`sound.volume`. Desde 1.0.59 el **pulso** usa el tono
del estado una cuarta por encima, y **bajo el agua** todo suena más bajo y más grave, como el
agua se lleva la luz.

Los cambios **no saltan**: `RelicGlowState` interpola color (≈0.30 s) y
fuerza/giro (≈0.22 s) por portador y con el tiempo real entre frames, así que se
ve igual a 30 que a 240 FPS. El giro del anillo pasa por cero al cambiar de
sentido en vez de invertirse de golpe, y el anillo se desvanece al entrar en
calma o dormido. Ese mismo factor multiplica el halo y el pase GLSL del modelo,
así que dormida se atenúa **todo** el brillo a la vez y cargada se intensifica,
en vez de quedar el aura apagada y el modelo a tope.

Hay dos VFX más, los dos sin geometría nueva: **chispas en órbita** (cinco quads
aditivos que giran en el plano de la cámara, con radio y altura distintos por
chispa y heredando el sentido de giro del estado) y un **eco del anillo** en cada
evento —pulso, golpe, liberación, cambio de estado—, un anillo más grande que se
abre y se apaga con el destello. Las dos cosas suman al lote que ya está abierto, así
que no cuestan ni un cambio de estado; las chispas se saltan en `lite` y con
`reducedEffects`.

El **shader propio** (`visuals.shaderGlow`) añade un cuarto pase con dos bordes
de silueta (uno suave y otro pegado al canto, este último con un desvío al
violeta), una banda que sube por la reliquia entera, rejilla fina de holograma que
respira, un glitch por bandas con separación de canales en los eventos y un grano
mínimo, en GLSL de verdad
(`assets/minecraft/shaders/core/holocore_relic_glow.{json,vsh,fsh}`). Se compila
en cada recarga de recursos y **se desactiva solo si hay shaderpack activo**
(Iris/Oculus/OptiFine): esos packs sustituyen el programa y la reliquia podría
quedar invisible. Con pack puesto sigues teniendo halo + aura + el bloom del
propio pack.

Dos detalles que hacen que el borde se vea siempre:

* el borde se calcula con la **posición** del vértice (la reliquia está centrada
  en el origen del modelo), no solo con la normal, así que no depende de que el
  modelo traiga normales correctas;
* el borde entra también en la **alpha**, así que la silueta brilla aunque la
  textura emisiva sea transparente justo ahí.

El tono del halo, del borde y del pase GLSL es un **cuarto** del color del estado
(tres cuartos de azul frío de núcleo), así que cargada tira a ámbar y alerta a rojo
sin dejar de leerse como holograma.

El **destello de evento** (`visuals.flashIntensity`) es lo que hace que la
reliquia *conteste*: cuando llega un pulso, una liberación, un golpe recibido o
una subida de nivel, el anillo se enciende (aunque el estado no lo tuviera) y el
brillo sube un poco; todo se apaga solo en ~0,4 s. Desde 1.0.11 el destello es
**discreto a propósito**: afecta sobre todo al anillo (una línea) y apenas al
aura y al halo, y ya **no** se dispara al despertar, dormir ni cambiar de estado
— eso era lo que producía un fogonazo blanco justo al entrar al mundo.

Lo que **no** hace: post-proceso de pantalla (caro y se pelea con los packs). El
razonamiento completo, la matriz de compatibilidad y los detalles de la API de
shaders de 1.20.1 están en [BRILLO-Y-SHADERS.md](docs/BRILLO-Y-SHADERS.md).

## Presets

Tres ajustes con nombre para no tocar 27 claves a mano cuando lo que se quiere es
cambiar de look:

| Preset | Qué hace |
| --- | --- |
| `soft` | Flotado lento y discreto: `animSpeed` 0.5, aura 0.22, halo 0.18, GLSL 0.25, anillo 0.45, destello 0.8 |
| `normal` | Los valores de fábrica de la tabla de abajo |
| `showcase` | Ritmo 1.0 y todo más alto (aura 0.45, halo 0.35, GLSL 0.50, anillo 0.75, destello 1.2) para grabar |

`/relic preset <nombre>` lo aplica **en memoria** (avisa de cuántas claves cambian),
`/relic info` las marca con asterisco y `/relic save` lo escribe en el toml.

## Configuración (`config/holocore-client.toml`)

| Clave | Defecto | Qué hace |
|---|---|---|
| `placement.shoulder` | `RIGHT` | Hombro; `LEFT` espeja el eje X. |
| `placement.offsetX` | `6.0` | Lateral en px de modelo (1 px = 1/16 bloque). |
| `placement.offsetY` | `-6.0` | Vertical en px; **Y+ es abajo**, así que `-6` sube 6 px. |
| `placement.offsetZ` | `8.0` | Hacia atrás en px (Z+ = espalda). |
| `placement.scale` | `1.0` | Escala global (el modelo mide ~11 px). |
| `visuals.quality` | `FULL` | `LITE` usa el .geo de 751 cubos y `idle_calm` en reposo. |
| `visuals.glowLayer` | `true` | Segundo pase emisivo (la textura `_glowing`). |
| `visuals.glowHalo` | `true` | Tercer pase con blend **aditivo** (suma luz). Se omite en `LITE` y con `reducedEffects`. |
| `visuals.haloIntensity` | `0.25` | Fuerza del halo aditivo (0–1). Por encima de 0.4 se ve mancha blanca sobre nieve. Desde 1.0.54 el pase aditivo tiene tope en el código (0.30), así que subirlo de 0.45 no blanquea más. |
| `visuals.glowAura` | `true` | Aura: tres billboards aditivos alrededor del núcleo. |
| `visuals.auraIntensity` | `0.32` | Fuerza del aura (0–1). Es aditiva: sobre fondo claro suma hacia blanco. |
| `visuals.auraTint` | `true` | Pase de tinte (mezcla normal) del aura: es lo que da color sobre nieve/arena. |
| `visuals.glowRing` | `true` | Anillo de estado (gira y se tiñe según la reliquia). |
| `visuals.ringIntensity` | `0.60` | Fuerza del anillo (0–1). |
| `visuals.flashIntensity` | `1.0` | Destello al ocurrir algo (pulso, liberación, golpe, nivel, despertar). `0` lo apaga. |
| `visuals.shaderGlow` | `true` | Pase GLSL propio (dos bordes de silueta + línea de lectura + rejilla). Se apaga solo con shaderpack activo. |
| `visuals.shaderIntensity` | `0.35` | Fuerza del pase GLSL, independiente del halo. |
| `visuals.groundEcho` | `true` | En cada evento, un anillo **tumbado a los pies** del portador que se abre y se apaga. Solo en tercera persona. |
| `visuals.sparkSpeed` | `1.0` | Multiplicador de la órbita de chispas (0–3). `1.0` es 1,6 s por vuelta; `3.0` recupera la velocidad de hasta 1.0.45 (2,8 vueltas/s, se veía como un aro temblando); `0` las deja quietas. |
| `visuals.animSpeed` | `0.65` | Ritmo del bucle de animación (0.25–2). `1.0` = el de las animaciones tal cual están hechas (idle 48 s); `0.65` lo deja flotando. El estado de brillo lo multiplica encima. |
| `visuals.reducedEffects` | `false` | Reposo sin rayos/cometas/ondas (`idle_calm`). |
| `visuals.maxRenderDistance` | `32` | Distancia para dibujar la reliquia de otros jugadores (se apaga en los últimos 8 bloques). |
| `visuals.idleVariations` | `true` | Variaciones propias en reposo (temblor, glitch, pulso). `false` = solo glitch. |
| `visuals.glitchMinSeconds` / `glitchMaxSeconds` | `20` / `60` | Intervalo entre variaciones de reposo. |
| `visuals.alertRadius` | `12` | Radio en el que un monstruo activa `idle_alert`. |
| `visuals.combatHoldTicks` | `80` | Ticks en estado cargado tras el último golpe. |
| `sound.events` | `true` | Sonidos al despertar, dormir y pulsar, **solo de la reliquia propia**. Son de ametista de vanilla: el mod no trae audio. |
| `sound.volume` | `0.45` | Volumen de esos sonidos (0–1). `0` los apaga igual que `sound.events = false`. |

Desde 1.0.20 todas estas claves (menos `placement.shoulder` y `visuals.quality`,
que tienen `/relic side` y `/relic quality`) se pueden probar en caliente con
`/relic set <clave> <valor>`; el archivo no se modifica hasta que lanzas
`/relic save`, que escribe en él lo que haya en memoria (1.0.21). El CI comprueba que la tabla de `/relic set` y esta tabla
tienen las mismas claves y los mismos rangos que `RelicConfig`.

Los offsets se aplican en el espacio del hueso `body` del jugador (origen en el
torso/cuello, Y+ abajo, Z+ espalda), no en el origen de los pies. Por eso el
`.geo.json` centrado es el correcto: el anclaje al hombro lo pone el código y no
hay que sumar la traslación que traía `relic_hologram.geo.json`.

## Sonido

La reliquia **propia** suena al despertar, dormir y pulsar, con sonidos de **ametista
de vanilla** (el mod no trae ningún asset de audio): `amethyst_block.resonate` grave
para despertar, más grave todavía para dormir y `amethyst_block.chime` agudo para el
pulso. Suena en la cabeza del jugador y no en el hombro, porque el hombro está a medio
metro de la cámara y el paneo saltaría al girar.

Las reliquias de **otros** jugadores no suenan nunca: con cuatro portadores cerca cada
pulso sería un coro sin forma de saber de dónde viene. Se apaga con
`sound.events = false` o bajando `sound.volume` a `0` (también en caliente con
`/relic set sound.volume 0`).

## Qué hace exactamente

* **Energía de movimiento** (desde 1.0.37): correr o nadar acelera el anillo (late
  ×1.7), las chispas (barrido ×1.45) y el vaivén (+60%); nadando las burbujas suben
  ×1.5. Agacharse la deja a 0.1, así que la reliquia se queda casi quieta contigo. Se
  suaviza con **tiempo real** (τ 0,30 s) para que no se note el tick, y es un eje
  **aparte** del estado de brillo: una tormenta no quita que vayas corriendo.
* **Equipar** → `activation` → `idle` (bucle). Al cambiar de calidad, o al volver
  a ver a **otro** portador tras 2 s fuera de pantalla, vuelve a empezar.
* **Desequipar** → deja de renderizarse. La `deactivation` **no** se puede ver al
  desequipar: Curios deja de llamar al renderer en el mismo tick, así que no hay
  dónde dibujarla. Sí se ve al pasar a dormido (`deactivation`, o `sleep` si el
  cambio es reciente).
* **Combate** (recibir un golpe o atacar, deducido de `hurtTime`/`swing`, sin red)
  → `charge_up` → `idle_charged` → `charge_down`.
* **Alerta** (monstruo a menos de `alertRadius`, escaneo cada 10 ticks) →
  `alert_up` → `idle_alert` → `alert_down`.
* **Golpe** → `hit` en el controlador de estado **y** `layer_hit` en el segundo
  controlador (solo `relic_react`).
* **Subir de nivel** → `layer_bump`. **Comando** → `energy_pulse` / `release`.
* **Variaciones de reposo** (`visuals.idleVariations`): estando quieta y despierta,
  la reliquia hace cosas sola cada 20–60 s, elegidas por peso — `layer_shake`
  (35%), `glitch` (30%), `layer_bump` (20%), `energy_pulse` (12%) y `release`
  (3%). Con `idleVariations=false` vuelve a hacer solo el glitch. El intervalo se
  ajusta con `glitchMinSeconds` / `glitchMaxSeconds`.
* Transiciones de 6 ticks (el manifiesto recomienda 4–8) y dos
  `AnimationController` simultáneos: `state` (bucles + acciones) y `layer`
  (solo `layer_*`), para que las capas no pisen los giros.
* **Se actualiza aunque no se dibuje** (1.0.19). En primera persona Curios no
  llama al renderer, así que la máquina de estados se movía solo en tercera: sin
  alerta, sin variaciones de reposo, `/relic info` sin estado y el visual podado
  a los 40 ticks — al volver, la reliquia arrancaba de cero con su `activation`.
  Ahora el cliente actualiza la reliquia del jugador local en cada tick. El
  estado queda vivo y las animaciones que habrían tocado **no se encolan**
  mientras no se ve, para no reproducirlas de golpe al girarse.

## Notas sobre los assets (sin modificarlos)

* Se usan `relic_hologram_centered.geo.json`, `relic_hologram_lite_centered.geo.json`
  y `relic_hologram.animation.json` (formato 1.8.0, con `catmullrom`: GeckoLib
  4.8.1 lo soporta). `relic_hologram.animation.linear.json` se incluye en el jar
  como alternativa documentada, pero no se carga.
* `relic_hologram.geo.json` (anclado al hombro) **no** se usa en el mod, tal como
  pide el manifiesto.
* GeckoLib 4.8.1 llama a su máscara emisiva `_glowmask`, no `_glowing`, y además
  **borra del pase base** los píxeles marcados en la máscara. Con
  `relic_hologram_glowing.png` (que es casi todo el atlas) el modelo base quedaría
  vacío, así que se implementa el brillo con dos pases emisivos en vez de
  `AutoGlowingGeoLayer`. La textura entregada se usa tal cual, sin renombrar.
* El modelo es de 977 cubos (751 en lite) y se dibuja en **hasta cuatro pases**
  (base, emisivo, halo y GLSL): 5 866 quads por pase en calidad full, ~23 000
  quads por reliquia y frame con todo encendido; en lite, 4 506 por pase.
  `maxRenderDistance` (32 bloques), `quality=lite`, `glowHalo` y `shaderGlow` son
  las palancas. Lo que **no** se paga cuatro veces es la animación: desde 1.0.16
  solo el pase base la evalúa y los otros tres reutilizan la pose, y desde 1.0.17
  el aura, el anillo y el estado no reservan memoria por frame. El escaneo de
  alerta va cada 10 ticks y las variaciones de reposo son un contador, no un
  cálculo por frame.

## Checklist de pruebas

- [ ] `./gradlew build` produce `holocore-<versión>.jar` y `/relic info` responde.
- [ ] Creativo: aparece en la pestaña *Holographic Core* y en la búsqueda.
- [ ] Receta de crafteo correcta (amatista + cristales + diamante).
- [ ] Equipar en `charm` → `activation` y luego `idle` en bucle.
- [ ] Desequipar → desaparece; re-equipar → vuelve a activarse.
- [ ] Tecla G y `/relic toggle` → `deactivation`/`idle_dormant` y vuelta.
- [ ] Tecla P (`/relic pulse`) → pulso con eco del anillo, glitch del shader, el
      achatado del evento y **el chime** (una sola vez; con otros portadores cerca no
      suena la de ellos).
- [ ] `/relic set sound.volume 0` en caliente → el siguiente pulso ya no suena.
- [ ] `/relic pulse`, `/relic release`, subida de nivel (`layer_bump`).
- [ ] Recibir daño → `hit` + `layer_hit`; monstruo cerca → `idle_alert`.
- [ ] Agacharse (sneak) y girar el cuerpo: el núcleo acompaña al torso sin saltos.
- [ ] Primera persona: no tapa la vista.
- [ ] Multijugador: otro jugador lo ve, también tras su login; el estado
      despierto/dormido coincide en ambos clientes.
- [ ] Noche, cueva y agua: sigue luminoso.
- [ ] Sin shaders y con Iris/Oculus: sin errores en el log y sin desaparición.
- [ ] `quality=lite` y `glowLayer=false` no rompen las animaciones.
- [ ] En primera persona `/relic info` muestra el estado (y cambia a `alert` con
      un mob cerca); pasar a tercera **no** reinicia la `activation`.
- [ ] `/relic stats` responde con los pases por dibujo (4 con base, emisivo, halo y
      GLSL) y los ms por dibujo; `/relic stats reset` los reinicia.
- [ ] `/relic set` lista las 22 claves; `/relic set auraIntensity 0.55` cambia el
      aura al instante y avisa de que es en memoria; un valor fuera de rango se
      rechaza sin tocar nada.
- [ ] Tras un `set`, `/relic info` avisa de los cambios sin guardar; `/relic save`
      los escribe en `config/holocore-client.toml` (comprobar reabriendo el juego).
- [ ] `/relic preview` pone la reliquia delante de la cámara con su aura, un poco
      a la derecha y por debajo del centro (la mirilla se ve libre);
      `/relic preview 1.5` la acerca y `/relic preview` la quita.
- [ ] `/relic reset` deja de nuevo las 24 claves en su defecto (comparar con
      `/relic set`) y avisa de los cambios sin guardar; repetido, dice que ya
      estaba todo de fábrica.
- [ ] `/relic reset scale` vuelve solo esa clave y `/relic set` deja de marcarla
      con `*`.
- [ ] `/relic mood storm` pone el aura casi blanca con las chispas azules y el bucle
      más rápido; `/relic mood wounded` la pone roja y lenta; `/relic mood auto`
      vuelve a lo normal.
- [ ] Con la vista previa encendida, `/relic info` lo dice y a qué distancia; al
      pasar a espectador se apaga sola.
- [ ] Distancia > `maxRenderDistance`: deja de renderizarse (sin tirones).
- [ ] `/relic offset 6 -6 8`, `/relic scale 1.0`, `/relic side left|right` mueven
      el núcleo en caliente y `/relic info` muestra los valores para la config.

## Estructura

```
relic-hologram/
├── build.gradle, settings.gradle, gradle.properties, gradlew
├── tools/                      # generador de constantes, icono, manifiesto
└── src/main/
    ├── java/com/santipdr/holocore/
    │   ├── HoloCore.java                 # @Mod, GeckoLib.initialize, config, red
    │   ├── common/                       # item, registro, creativo, autoridad servidor
    │   ├── client/                       # renderer Curios, GeckoLib, estados, tecla, comandos
    │   ├── config/RelicConfig.java
    │   └── network/                      # dos paquetes: acción y estado
    └── resources/
        ├── META-INF/mods.toml, pack.mcmeta
        ├── assets/holocore/{geo,animations,textures/relic,textures/item,models,lang}
        └── data/{curios/tags/items/charm.json,holocore/recipes/holographic_core.json}
```
