# Brillos, shaders y bloom: qué se puede hacer y qué no

Nota a partir de la idea de Alex («shaders de mc, glowing, bloom propio y glsl»).
Resume lo que la reliquia ya hace, qué opciones reales hay en **Forge 1.20.1** para
subir el nivel visual, y con qué se rompe cada una.

## 1. Lo que ya hace el mod

| Ya hecho | Cómo |
|---|---|
| Brillo que no depende de la luz | El modelo se dibuja con `LightTexture.FULL_BRIGHT`: en una cueva, de noche o bajo el agua se ve igual. |
| Textura emisiva aparte | Segundo pase con `relic_hologram_glowing.png` sobre `RenderType.entityTranslucentEmissive`. |
| Efecto de luz fría | La textura emisiva es la que manda el color; la base sólo define el volumen. |
| Halo aditivo | Tercer pase con blend **aditivo** (`RelicRenderTypes.ADDITIVE_GLOW`), configurable con `glowHalo` / `haloIntensity`. Ver §3.A. |
| Aura | Tres billboards aditivos que giran, `glowAura` / `auraIntensity`. Ver §3.B. |
| Anillo de estado | Cuarto billboard que solo sale en idle/cargada/alerta, con el color del estado (`glowRing` / `ringIntensity`). |
| Shader propio | Cuarto pase con GLSL: fresnel en el borde y línea de barrido, `shaderGlow` / `shaderIntensity`. Se apaga solo con shaderpack. Ver §3.C y apéndice A. |

Es decir: el «glowing», el «bloom propio» y el «glsl» están los tres dentro, cada
uno en la versión que aguanta un shaderpack sin romperse.

## 2. Qué significa «shaders» aquí

Hay tres cosas distintas que la gente llama «shaders» y sólo dos tienen sentido
para una reliquia cosmética:

1. **Shaderpack** (Iris/Oculus, OptiFine + Complementary/BSL/Photon…). El jugador
   lo instala aparte; el mod no lo controla, pero sí puede *aprovecharse* de él.
2. **Core shader propio** (`.vsh`/`.fsh` + JSON, lo que el juego usa para dibujar
   cada `RenderType`). El mod puede traer los suyos por GLSL.
3. **Post-proceso** (`PostChain`, framebuffer + quads a pantalla completa, tipo el
   `blur` del menú de pausa). También es GLSL, pero a nivel de pantalla.

## 3. Opciones, de mejor a peor relación efecto/coste

### A. Blend aditivo (hecho) — el 80% del look, 0% de riesgo

Sumar luz en vez de mezclarla es lo que hace que un brillo parezca que «emite».
Se hace con un `RenderType` propio: blend `ONE, ONE`, sin escritura de
profundidad, shader **estándar** de entidad translúcida.

En 1.20.1 `RenderType.create(...)` no es público, así que hay que hacer lo mismo
que Forge en `ForgeRenderTypes`: una clase interna que hereda de `RenderType` y
llama a `create(...)` desde dentro. Los estados que necesitamos
(`ADDITIVE_TRANSPARENCY`, `LIGHTMAP`, `NO_CULL`, `COLOR_WRITE`) son `protected` de
`RenderStateShard`, o sea accesibles desde la subclase.

```java
private static RenderType additiveGlow(ResourceLocation texture) {
    CompositeState state = CompositeState.builder()
            .setShaderState(RENDERTYPE_ENTITY_TRANSLUCENT_SHADER)
            .setTextureState(new RenderStateShard.TextureStateShard(texture, false, false))
            .setTransparencyState(ADDITIVE_TRANSPARENCY)
            .setCullState(NO_CULL)
            .setLightmapState(LIGHTMAP)
            .setOverlayState(OVERLAY)
            .setDepthTestState(LEQUAL_DEPTH_TEST)
            .setWriteMaskState(COLOR_WRITE)
            .createCompositeState(false);
    return create("holocore_additive_glow", DefaultVertexFormat.NEW_ENTITY,
            VertexFormat.Mode.QUADS, 256, false, true, state);
}
```

La intensidad se baja con el **color de vértice** (`getRenderColor`), no con
`RenderSystem.setShaderColor`: el segundo es estado global y teñiría también al
jugador y al mundo que se dibujen después en el mismo frame.

Coste: una pasada más sobre 977 cubos. Por eso se salta en `quality=LITE` y con
`reducedEffects=true`.

### B. Aura en billboard (hecho)

Tres quads que miran a cámara con una textura radial de 64×64, sumados con el
mismo blend aditivo: es el «bloom propio» sin post-proceso. `RelicAura` los
coloca leyendo la traslación y la escala de la matriz del `PoseStack` (que en el
render de entidades está en coordenadas de mundo), así que no hay que tocar el
modelo ni sus animaciones y el aura hereda la escala de la config.

Detalles que importan:

* **Tres capas, no una**: diámetros 0.62 / 0.85 / 1.10 bloques con aportes
  0.30 / 0.17 / 0.09 y alpha de quad 0.55. Una sola capa se ve como una pegatina
  plana, pero tres capas grandes se ven como una nube (ver más abajo).
* **Giros opuestos** (0.035 / −0.022 / 0.010 rad por tick): la textura lleva tres
  arcos, así que el giro se nota como estelas orbitando. Con un degradado
  perfectamente radial girar no se vería.
* **Cara a cámara** con los ejes `left`/`up` de `Camera`, no con la orientación
  del jugador: si no, al mirar la reliquia de lado se vería como un rectángulo.
* **Escritura de vértice completa**: el RenderType usa el formato de entidades
  (`NEW_ENTITY`), así que hay que rellenar color, UV, overlay, lightmap y normal
  aunque solo se use la UV. Olvidar el lightmap deja el quad en negro.
* La textura se genera con `python3 tools/make_aura.py` (sin Pillow, PNG a mano
  con `zlib`), para que sea reproducible y revisable en diff.

**Por qué hasta 1.0.10 el aura se veía como una nube blanca** (medido, no
supuesto). Tres cosas se sumaban:

1. La textura tenía el **centro a RGB (254, 255, 255)** con alpha 254: el
   degradado radial llegaba al blanco puro antes de caer.
2. Los quads medían 1.05 / 1.55 / 2.10 bloques, o sea **hasta tres veces el
   núcleo** (0.7 bloques), y con alpha a 1.0 el aporte sumado en el centro era
   ~0.47 × tinte.
3. El destello de 1.0.9 multiplicaba eso por 1.9 y abría el aura un 22 %, y
   **también se disparaba al entrar al mundo** (transición a despierta).

Con blend aditivo el resultado es `fondo + aporte`; sobre nieve el fondo ya está
a ~0.95, así que cualquier aporte de más de ~0.05 por canal clipea a 1.0 y el
aura se ve **blanca aunque el tinte sea azul**. No es que el color estuviera mal:
es que el aditivo, sobre un fondo claro, no puede oscurecer. Arreglado en tres
frentes: textura cian sin blanco en el centro (máximo 0.52 / 0.86 / 1.0), quads
pegados al núcleo y un quinto del aporte (0.30 + 0.17 + 0.09 = 0.56 × 0.55 de
alpha), y destello que ya no toca el aura casi nada.

**Dos pases desde 1.0.12: tinte + brillo.** El aditivo tiene un techo físico: solo
puede sumar, así que sobre un fondo claro nunca puede dar color (sumar a 0.95 lo
lleva a 1.0, o sea blanco). Para conservar el color se dibujan los mismos tres
quads dos veces:

1. **Tinte** (`RelicRenderTypes.TINT_GLOW`, mezcla alfa normal) con el color del
   estado **tal cual** y una cobertura de `peso × intensidad × 1.6`. Mezclar hacia
   un cian claro quita rojo y verde sin apagar el azul, así que **tiñe sin
   oscurecer**: sobre nieve el halo queda en (0.80, 0.94, 1.00) frente al fondo
   (0.93, 0.95, 0.97), tono +0.20 y luminancia −0.03.
2. **Brillo** (`ADDITIVE_GLOW`) encima, que es el que hace el resplandor en
   oscuro.

Los dos pases comparten geometría y giro, así que no hay que duplicar nada más
que el bucle de emisión (6 quads en lugar de 3). El **anillo** hace lo mismo
(2 quads más): sobre nieve el aditivo lo dejaba blanco y se perdía.
`visuals.auraTint=false` deja solo el aditivo, que es el comportamiento de 1.0.11.

Las constantes no están a ojo: `tools/check_aura_math.py` lee los pesos, el alpha,
el tinte, el color del estado y el **píxel central del PNG**, compone las dos
pasadas sobre nieve, piedra y cueva, y falla si el resultado se blanquea, si baja
la luminancia como una sombra o si pierde el tono. Corre en el CI, así que la
próxima vez que alguien suba `auraIntensity` o el `AURA_ALPHA` se entera en el
build y no en una captura.

**Anillo de estado** (`RelicAura.drawRing`, textura `relic_ring.png` de
`tools/make_ring.py`): un solo billboard de 1.15 bloques, apenas por fuera del
aura (1.10), para que se lea como un anillo y no como el borde del resplandor;
solo se dibuja cuando el estado tiene algo que decir. El estado sale de
`RelicAnimatable.loopState()`, que ya existía para las animaciones: no hay lógica
nueva, solo color y giro.

| Estado | Color (r,g,b) | Aura | Anillo | Giro (rad/tick) |
|---|---|---|---|---|
| `IDLE` | 0.55 / 0.78 / 1.00 | 1.00 | 0.45 | 0.028 |
| `CALM` | 0.42 / 0.60 / 0.78 | 0.70 | — | — |
| `CHARGED` | 1.00 / 0.72 / 0.30 | 1.15 | 1.10 | 0.075 |
| `ALERT` | 1.00 / 0.34 / 0.28 | 1.05 | 0.85 | −0.055 (al revés, y late) |
| `DORMANT` | 0.34 / 0.44 / 0.60 | 0.35 | — | — |

El rojo y el ámbar no son arbitrarios: son los mismos tonos que usan los packs de
UI de Minecraft para «peligro» y «energía», así que se leen sin explicación. Y
como el anillo late solo en `ALERT`, se distingue de `CHARGED` incluso de reojo.

**Transiciones** (`RelicGlowState`, uno por portador): los valores no se usan en
crudo. Cada frame se acercan al objetivo con `1 - e^(-dt/tau)`, con `dt` medido en
tiempo real para ese portador — no ticks ni «un 10% por frame», que se vería
distinto a 30 y a 240 FPS. Color 0.30 s; fuerzas y giro 0.22 s. El primer frame de
un portador nuevo entra directo al estado, sin transición desde el azul por
defecto. Dos detalles que esto arregla sin código extra:

* el anillo **se desvanece** al pasar a `CALM`/`DORMANT` en lugar de desaparecer;
* al ir de `ALERT` a `IDLE` el giro pasa por cero y se invierte suave, no de golpe.

El mismo factor `aura` del estado multiplica el halo aditivo y el pase GLSL del
modelo (`RelicGeoRenderer.renderHologram(..., RelicGlowState glow)`): así
`DORMANT` atenúa todo el brillo junto y no deja un modelo a plena potencia con el
aura apagada, que era la incoherencia más visible de 1.0.5.

**Destello de evento** (`RelicAnimatable.flash`, escalado por
`visuals.flashIntensity`): los eventos ya existían — sellos de `gameTime` que el
servidor replica y que el cliente compara con el último visto para disparar la
animación. El destello les engancha un valor 0..1,2 que sube de golpe y decae con
`e^(-dt/0.42 s)` en tiempo real, con `dt` topado a 0,25 s:

| Evento | Pico | Dónde se dispara |
|---|---|---|
| `/relic release` | 0,80 | `snapshot.release()` |
| `/relic pulse` | 0,60 | `snapshot.pulse()` (solo con la reliquia despierta) |
| subida de nivel | 0,40 | `snapshot.bump()` |
| recibir daño | 0,30 | `snapshot.hit()` |
| variación de reposo | 0 / 0,15 / 0,30 / 0,40 | según la que salga |

Despertar, dormir y los cambios de estado **no** destellan: era lo que producía
un fogonazo blanco justo al entrar al mundo.

Se aplica en tres sitios y siempre con el mismo número: aura (`×(1+0,35·flash)` y
se abre un 10% en diámetro), anillo (`ring + 0,7·flash`, y crece un 25%) y modelo
(halo y GLSL, `×(1+0,2·flash)`). El peso está en el anillo porque es una línea:
se ve el pulso sin encender medio núcleo. El anillo se dibuja si `ring + 0,8·flash` pasa de
0,01, así que un golpe enciende el anillo aunque `CALM`/`DORMANT` no lo tengan.
El pico nunca baja: dos golpes seguidos no se apagan entre sí.

### C. Core shader propio (fresnel + scanlines de holograma) — hecho en 1.0.3

`.vsh`/`.fsh` propios cargados con `ShaderInstance` y un
`ShaderStateShard(() -> shader)`, con uniform de tiempo para el barrido y fresnel
en el vértice. El detalle completo está en el apéndice A, que ahora describe lo
que hay en el jar y no un esbozo.

Se implementó como **cuarto pase opcional**, no como reemplazo: si el shader no
carga o hay shaderpack, los otros tres pases siguen ahí y la reliquia se ve como
en 1.0.2. Esa decisión es la importante: el riesgo de este camino es que con
shaderpack el programa acaba en el *fallback* del pack o **invisible** (le pasó a
Forge con su shader «unlit», Oculus #630), y así el fallo no se nota.

Desde 1.0.8 el borde no depende del atributo `Normal`: se calcula con la
**posición del vértice**, que ya apunta hacia fuera porque la reliquia está
centrada en el origen del modelo. Motivo: si el modelo rellena `Normal` igual en
todas las caras, el fresnel deja de seguir la silueta y se convierte en un tinte
plano; con la posición, el borde aparece siempre. La normal sigue entrando con un
25% de peso por si viene bien puesta. Además el rim entra también en la **alpha**,
así que la silueta brilla aunque ahí la textura emisiva sea transparente, y el
tono del borde se mezcla con el color del estado.

**1.0.28, segunda vuelta al shader.** Cuatro cambios, ninguno a ojo:

* **Dos bordes en vez de uno.** `edge²` tiñe la cara y `edge⁴` se queda pegado a
  la silueta; el de `edge⁴` además se va al violeta (`mix` al 35%), así que la
  silueta tiene dos tonos. Se calculan multiplicando, no con `pow`: dos `pow` en
  el fragment shader para esto es gastar lo que no hace falta, y el corte queda
  más limpio.
* **El barrido va en espacio de vista, no en UV0.** Con `UV0` el barrido se
  repetía por cara: en un modelo de 98 huesos cada cara trae sus propias UV, así
  que en vez de una banda que recorre la reliquia salían cuatro por cara. Ahora
  el vértice pasa `viewY` (= `viewPos.y`) y el fragment hace el `fract` sobre eso.
* **La rejilla, igual.** Anclada a `viewY`, las líneas siguen de una cara a otra
  en vez de pelearse entre caras al girar la cámara. De paso baja de 160 a 90
  ciclos, que a distancia hacía muaré.
* **El borde respira** (`0.85 + 0.15·sin(t·1.6)`) y el núcleo no: el latido es
  del contorno, que es lo que se lee como holograma.

El ruido del dither sigue **sin tiempo dentro** a propósito: si cambia por frame
deja de romper el banding y se ve hervir.

**1.0.46, unidades en el aura.** Convenio: `time()` son ticks y todas las constantes de
frecuencia del aura están en **radianes por tick** (`SPIN` 0.035 = 1 vuelta / 9 s,
`pulseAt` 0.08 = 3,9 s, latido del anillo 0.15 = 2,1 s). La órbita de chispas estaba en
0.75: 2,8 vueltas por segundo, sin continuidad entre fotogramas. Baja a 0.20 (1,6 s / vuelta)
y se multiplica por `visuals.sparkSpeed` (0–3). Lo que se añada después: o va en rad/tick,
o pasa por `seconds()`.

**1.0.45, undécimo estado con VFX propio.** `FREEZING` sale de `Entity.getTicksFrozen() > 0`:
el contador solo sube cuando el juego ya decidió que te estás helando, así que no hay que
mirar biomas ni bloques (y en cliente el dato llega sincronizado). Paleta `0.62 / 0.88 / 1.00`
mezclada al 55%, `HoloTint` 0.90 y energía de vaivén 0.55. Los copos son el cuarto VFX del
mismo lote aditivo: siete quads, `0.038` de tamaño, caída `0.28/s` (un cruce cada 3,6 s con
`seconds()`) y zigzag `sin(t × 1,1) × 0,09`, que es lo que los separa de las gotas. La
diferencia de diseño: los copos **se encienden al llegar abajo** (como uno que se posa) y las
gotas se apagan.

**1.0.43, el factor 20.** `time()` devuelve `level.getGameTime() + partialTick`, o sea
ticks, y así se pensaron el anillo (`beatSpeed` 0.15 rad/tick = 2 s) y las chispas
(`SPARK_SPEED` 0.75 rad/tick). Los efectos que se añadieron después venían de cabecera en
unidades de «por segundo»: gotas 1.10, brasas 0.65, parpadeo 9.0 y el vaivén 1.7. Usados
sobre ticks, eso es 20× (el parpadeo, 35 Hz, por debajo del refresco: se promedia a gris).
`seconds(ticks) = ticks / 20` y los seis usos pasan por ahí. El vaivén queda en
`sin(segundos × 1.7)`: 3,7 s por ciclo, 2,2% de amplitud; el ladeo, 9 s por grado.

**1.0.42, el destello como interfaz de prueba.** El relámpago de tormenta no inventa
ningún efecto nuevo: llama a `boostFlash(0.55)` cada 100–220 ticks con el RNG del propio
portador (`RandomSource`), y el destello ya alimenta la onda de choque, el eco del anillo,
el shader (`HoloGlitch`) y el apretón de escala. Por eso una tormenta se ve con pulso sin
tocar el shader ni el aura. `/relic vfx shock [fuerza]` hace lo mismo a mano: es la única
forma de mirar la onda con la fuerza que se quiera (0.1–1) sin esperar a que ocurra un
evento, y sirve de banco de pruebas para cualquier efecto futuro que cuelgue del destello.

**1.0.41, el barrido era un aro y el ritmo no se podía bajar.** El barrido de 1.0.8–1.0.40
era `smoothstep(0.40, 0.62, fract(viewY * 0.9 - HoloTime * 0.25))`: como `viewY` recorre
medio bloque, esa ventana de 0.22 de fase son ~0.22 bloques de alto, o sea una faja que
cruza el modelo entero y que el ojo lee como un anillo planetario. La línea de lectura es
`readNear = min(readPos, 1 - readPos)` con `readLine` a 0.020 y `readHalo` a 0.110, y las
dos se multiplican por `texAlpha`: el halo ya no existe fuera del cuerpo, que era la otra
mitad del aro (la silueta tiene alpha por el borde). El brillo: el blend es
`(srcrgb: srcalpha, dstrgb: one)`, así que el rgb va **sin** premultiplicar; premultiplicarlo
daba alpha² y obligaba a ganancias de 0.28/0.45 para que se viera, que es lo que quemaba el
centro. Ahora 0.16/0.24 y alpha de silueta 0.42/0.20. El dither pasa de `(hash − 0.5) × 0.03`
a `hash × 0.015`: en aditivo el negativo lo recorta el framebuffer.

El ritmo del bucle: `speedFor` devuelve la base del estado por `visuals.animSpeed`
(0.65 por defecto). `idle` son 48 s y `idle_alert` 8 s, así que sin multiplicador global no
había forma de recuperar el flotado lento.

**1.0.40, onda de choque sin estado y estela de chispas.** La onda (`drawShockwave`)
reutiliza el destello como línea de tiempo: `t = 1 − flash`, radio `0.16 + 0.46 × t`,
brillo `flash × 0.55`, ocho quads en elipse (eje `up` × 0.8) que giran a 0.35 rad/s y
encogen un 45% al abrirse. Cero estado: ni listas, ni iteradores, ni `new` en el render;
cuando `flash < 0.02` no se llama. La estela es la misma idea con la órbita de las
chispas: cada chispa repite su posición con la fase retrasada `0.22 × motion` y 42% de
brillo, solo si `motion > 0.35`. El techo de quads del aura pasa de ~10 a ~18 y el suelo
sigue en 10 (o 4 con la calidad en LITE).

**1.0.39, décimo estado: ardiendo.** `BURNING` sale de `Entity.isOnFire()`, que es
vanilla y ya cubre fuego, lava y flechas de Fuego. Paleta cálida (`1.00 / 0.42 / 0.16`,
mezclada al 60%: el único estado que tira a naranja) y `HoloTint` a **1.05**, el único
que pasa de 1, porque el borde tiene que encenderse y no apagarse. El VFX es `drawEmbers`:
seis brasas que suben de −0.30 a +0.40 en el eje `up`, se mecen ±0.06, se encogen al 65% y
parpadean con `0.55 + 0.45 × sin(tiempo × 9 + i × 2.7)`. Ese parpadeo a 9 rad/s es lo que
distingue una brasa de una burbuja naranja: sin él, el movimiento es idéntico al del agua.

**1.0.38, gotas para la lluvia y ronda temporizada.** La lluvia era el único estado que
parecía reposo: cambiaba de color y bajaba el anillo, pero las chispas seguían en órbita.
Ahora `RelicAura.drawDrops` dibuja seis gotas que caen de +0.40 a −0.32 en el eje `up` de
la cámara, con viento lateral por fase (`sin(tiempo × 0.9 + i × 1.9) × 0.07`), creciendo
el brillo al bajar y apagándose de golpe abajo, y a ×1.4 si el portador corre. Se reutiliza
el lote aditivo del aura, así que el coste son seis quads y ningún pase nuevo.
La otra mitad es `/relic mood cycle [segundos]`: la ronda temporizada va por ticks de
cliente (`tickForcedCycle`, 20 por segundo) y avisa por la barra de acción, de modo que una
grabación queda etiquetada sola.

**1.0.37, la energía de movimiento.** Un eje más, ortogonal a los estados de brillo:
`RelicAnimatable.motion()` (0–1) sale de `isSprinting`, `isSwimming`, `isCrouching` y la
velocidad horizontal, suavizado con tiempo real (τ 0,30 s). Entra por `RelicAura.render`
y multiplica tres ritmos que ya existían: `beatSpeed` del anillo ×1.7, la velocidad
orbital de las chispas ×1.45, la subida de las burbujas ×1.50 y la amplitud del vaivén
de `applyAliveMotion` ×1.6. Ningún draw ni pase nuevo: el aura ya estaba ahí, esto solo
le cambia la frecuencia con la que respira.

**1.0.35, noveno estado: portal.** `PORTAL` es el único estado que mira **bloques** y no
el cielo o el jugador: busca `NETHER_PORTAL`, `END_PORTAL` o `END_GATEWAY` en una caja de
9×6×9 alrededor de los pies. Para que eso no cueste, el escaneo se hace cada 20 ticks y
se guarda el resultado, y la posición es un `MutableBlockPos` de campo (un `BlockPos` por
bloque serían 486 asignaciones por segundo y portador). En el shader solo cambia el
`HoloTint` (0.96, el borde casi como en reposo: el violeta ya destaca solo), y en
`RelicAura` las chispas giran 1.5× más rápido con el vaivén vertical ×1.8: estirarlas
en vertical es lo que hace que se lean como el borde de un portal y no como una órbita.

**1.0.34, ver los ocho estados de un tirón.** Sin tocar shaders: la tecla M cicla el
estado forzado (`RelicAnimatable.cycleForcedMood`, la misma ronda que
`/relic mood next`) y avisa por la barra de acción. Para comparar dos estados sin
soltar la reliquia basta con pulsar M con `/relic preview 2` abierto: el tinte del
borde (`HoloTint` 0.62–1.08), el color del aura y las chispas cambian con la misma
interpolación de ≈0.30 s de siempre, así que se ve la transición y no un salto.
`/relic mood list` es la otra mitad: dice cuál manda y si es forzado (oro) o de la
escena (azul). De paso, las sugerencias del comando ya salen del enum: se habían
quedado sin `night` ni `submerged` durante dos versiones.

**1.0.33, octavo estado: bajo el agua, con VFX propio.** Primera vez que un estado
cambia *qué* se dibuja y no solo de qué color.

* **`submerged`** se detecta con `isEyeInFluid(FluidTags.WATER)`, que es vanilla y no
depende de que el jugador esté entero dentro: basta con los ojos. Manda sobre la luz
y el tiempo (solo pierde con herido y tormenta): bajo el agua la escena es el agua.
En el shader es una rama más del `HoloTint` (0.74, el borde se apaga) y en
`RelicGlowState` una paleta verde azulada con el anillo a −0.20.
* **Burbujas (`RelicAura.drawBubbles`)** en vez de chispas: siete quads que suben de
−0.32 a +0.40 en el eje `up` de la cámara, con un vaivén lateral de ±0.10,
creciendo de 0.6× a 1.2× y apagándose (`1 − rise`) para que se lean como burbujas
que se van. `rise` sale de `fract(tiempo × 0.28 + i/7)`, sin asignar nada
(`Math.floor` devuelve `double`). Se reutiliza el mismo lote aditivo y la misma
textura del aura: cero estados de render nuevos, y por tanto cero draws extra.
* **Ritmo**: el bucle de animación baja a 0.66× (el más lento de los ocho) y el
flotado a energía 0.50, que es el agua frenándolo todo.

**1.0.32, séptimo estado y glitch al cambiar de estado.** Sin tocar el GLSL: el
estado nuevo (`night`) y el glitch del cambio reutilizan lo que ya había.

* **`night`** (cielo encima, de noche, sin lluvia) no introduce color nuevo en el
shader: el tinte del estado en `RelicGlowState` sale de la paleta del bucle, así que
la noche se ve como el reposo pero más pálida. Lo que sí cambia son las **chispas**
de `RelicAura.drawSparks`, que ahora reciben el `Mood` en vez de un booleano de
tormenta: a 0.45× de velocidad orbital, con una de cada dos apagada y teñidas hacia
el hielo (rojo ×0.65, verde y azul casi intactos). Menos chispas y más lentas se lee
como polvo en suspensión, no como chispas de soldadura.
* **La oscuridad pide cielo tapado.** `Mood.DARK` exigía solo luz de bloque < 4, y a
cielo abierto de noche la luz de bloque es 0: la reliquia se ponía «en la oscuridad»
mirando las estrellas. Ahora pide además luz de cielo < 8, que es lo que distingue una
cueva de un campo abierto. Sin ese corte `night` no se alcanzaba nunca.
* **Glitch al cambiar de estado.** El bloque que detecta el cambio de `Mood` ahora
encola `GLITCH` en el controlador `state` además de subir el destello. El destello ya
alimenta `HoloGlitch` (`min(1, flash × 1.5)`), así que la parte del shader sale gratis:
es exactamente el mismo camino que el pulso de 1.0.29. Se reutiliza la animación en vez
de añadir una capa nueva porque los `.json` exportados están bloqueados por CI contra el
zip del modelo (`Validate assets unchanged`); una animación nueva se hace en Blockbench.

**1.0.30, tinte por estado de brillo.** Uniform `HoloTint` (vec4, blanco por
defecto) que el renderer rellena según el `Mood`: 1.08 en la oscuridad (el borde se
marca más, que es donde más se nota), 1.05 en tormenta, 0.62 bajo la lluvia y 0.88–0.92
en resonancia/herido. Se aplica al `rimTint` del borde, que hasta 1.0.29 se quedaba
siempre con el mismo azul claro y desentonaba cuando el resto del aura cambiaba de
color.

**1.0.29, glitch de evento en el shader.** Uniform nuevo `HoloGlitch` (0–1) que el
renderer rellena con `min(1, flash × 1.5)`: el mismo destello que ya sube el halo y
el aura. Con `HoloGlitch > 0.01` la UV se parte por bandas horizontales
(`floor(viewY × 48)` con hash del tiempo, o sea el mismo corte para toda la banda) y
los canales R y B se separan ±0.010 en la X. Como la condición es sobre un uniform,
la rama es la misma para todo el dibujo: sin evento se sigue muestreando la textura
**una vez**; con evento, tres. El resplandor de las chispas y el eco del anillo van
por fuera del shader, en `RelicAura`, sumando al mismo lote aditivo.

### D. Post-proceso / bloom real de pantalla

`PostChain` + framebuffer: renderizar la reliquia a un target, desenfocar, sumar.
Técnicamente posible (`shaders/post/*.json`), pero:

* afecta a **toda** la pantalla y hay que recortar por la zona de la reliquia;
* se pelea con Iris/OptiFine (ellos ya gestionan el pipeline y los targets);
* cuesta FPS siempre, incluso cuando la reliquia no se ve.

Veredicto: **no**. Para eso está el shaderpack del jugador, que lo hace mejor.

### E. Integrarse con el shaderpack

Lo que **sí** conviene y ya está hecho:

* usar `entityTranslucentEmissive` (tipo conocido) para los pases normales: Iris
  lo manda a `gbuffers_entities(_translucent)` y el pack aplica su bloom;
* entregar el lightmap a tope (`FULL_BRIGHT`), que es la señal que usan los packs
  para detectar emisivos;
* no inventar `RenderType`s con shaders desconocidos en los pases principales.

Con Complementary + Iris el resultado ya debería ser bloom de verdad alrededor
del núcleo. Ajuste fino: subir el brillo de `relic_hologram_glowing.png` (o subir
`haloIntensity`) si el pack lo recorta.

## 4. Compatibilidad, resumido

| Escenario | Base + emisivo | Halo aditivo (A) | Aura billboard (B) | Core shader (C) | Post-proceso (D) |
|---|---|---|---|---|---|
| Sin shaderpack | ✅ | ✅ | ✅ | ✅ shader propio | ✅ (caro) |
| Iris/Oculus + Complementary | ✅ bloom del pack | ✅ (como geometría translúcida) | ✅ | ⛔ se apaga solo | ❌ |
| OptiFine sin pack | ✅ | ✅ | ✅ | ⛔ se apaga solo | ❌ |
| Servidor sin el mod cliente | — | — | — | — | — |

## 5. Plan por fases

1. **Hecho (1.0.1)**: halo aditivo con `glowHalo` + `haloIntensity`.
2. **Hecho (1.0.2)**: aura de tres billboards con `glowAura` + `auraIntensity`.
3. **Hecho (1.0.3)**: shader propio con detección de pack (apéndice A).
4. Medir FPS en un portátil y decidir si el halo del modelo se queda activo por
   defecto en `LITE` (ahora se omite; el aura sí se dibuja, son tres quads).
5. Pendiente de juicio visual: cuánto fresnel/barrido aguanta sin verse «sucio».
   Es lo único que el CI no puede valorar. Versión actual: dos bordes, una banda
   y rejilla; si al mirarlo de cerca el violeta del canto molesta, se quita el
   `mix` de `rimTight` (una línea).
6. **Hecho (1.0.28)**: en la banda de desvanecido (últimos 8 bloques antes de
   `maxRenderDistance`, `fading = fade < 0.55`) el modelo se queda en dos pases:
   el halo y el GLSL se saltan. Son dos recorridos más de los 977 cubos y a esa
   opacidad no se distinguen; `/relic stats` lo enseña como menos «pases por
   dibujo».

## 6. Cómo probarlo

```
/give @s holocore:holographic_core      # equipar en el slot charm
/relic quality full                     # o lite, para comparar
/relic pulse                            # animacion de una sola vez
/relic info                             # offset y escala actuales
```

En `config/holocore-client.toml` (sección `[visuals]`):

```toml
    glowLayer = true
    glowHalo = true
    haloIntensity = 0.35
    glowAura = true
    auraIntensity = 0.55
    glowRing = true
    ringIntensity = 0.55
    shaderGlow = true
    shaderIntensity = 0.55
```

Qué mirar, en orden:

1. **`latest.log`** debe tener `Shader del aura compilado (holocore_relic_glow)`.
   Si no está, el pase GLSL no compiló en ese equipo (y el CI lo habría cazado).
2. **Silueta contra pared oscura**, de noche: halo y aura se tienen que ver sin
   cambiar la luz del mundo.
3. **De canto**: el borde del núcleo debe brillar más que la cara frontal
   (fresnel). Si molesta, bajar `shaderIntensity`.
4. **Con y sin shaderpack**, mismo mundo y hora: con pack el pase GLSL se apaga
   solo y el bloom lo pone el pack; sin pack manda el aditivo propio.
5. **Estados**: en reposo el anillo es azul y lento; pega un golpe a un mob y debe
   pasar a ámbar con giro rápido (`idle_charged`); acércate a un monstruo sin
   pelear y debe ponerse rojo y latir (`idle_alert`); con `G` (dormida) el aura se
   apaga a gris y no hay anillo.
6. **Destello**: `/relic pulse` y `/relic release` deben notarse como un fogonazo
   corto (el anillo se enciende aunque esté en calma). Recibir daño de un mob hace
   lo mismo con menos fuerza; con `flashIntensity=0` no debe verse ninguno.
7. **Sobre nieve o arena** (el peor fondo posible para un aditivo): el aura debe
   seguir leyéndose **azul/cian**. Si se ve blanca, está sumando demasiado:
   baja `auraIntensity` (0.2–0.3) o `haloIntensity`.
8. **Standby**: sin tocar nada, en reposo, cada 20–60 s debe hacer algo —
   temblor corto, glitch, un pulso. Con `idleVariations=false`, solo glitches.
9. **Animaciones sueltas**: `/relic anim list` y luego `layer_shake`, `layer_bump`,
   `layer_hit`, `glitch`, `release`. Las tres `layer_*` son las que estuvieron
   rotas hasta 1.0.11 (nombre equivocado): si el núcleo tiembla, están bien.

## Apéndice A — el GLSL que lleva el mod desde 1.0.3 (revisado en 1.0.8)

Esto es exactamente lo que compila el mod (`visuals.shaderGlow`), con el
razonamiento de por qué cada pieza está donde está. Todo contrastado con las
fuentes de 1.20.1 (`ShaderInstance`, `Program`, `RenderStateShard`, `RenderType`,
`VertexBuffer`) y con el *access transformer* de Forge.

### A.1 Dónde van los ficheros (y por qué ahí)

`ShaderInstance` construye siempre la ruta como
`new ResourceLocation("shaders/core/" + nombre + ".json")`, y el nombre **no
puede llevar namespace**: si se pasa `holocore:relic_glow` la ruta queda
`shaders/core/holocore:relic_glow.json` y `ResourceLocation` revienta (el `/` no
es válido en el namespace). O sea que los ficheros van en el namespace
`minecraft`, con nombre propio para no pisar ningún core shader del juego:

```
assets/minecraft/shaders/core/holocore_relic_glow.json
assets/minecraft/shaders/core/holocore_relic_glow.vsh
assets/minecraft/shaders/core/holocore_relic_glow.fsh
```

El JSON, mismo formato que los core shaders de vanilla (`vertex` y `fragment` son
nombres planos, sin namespace):

```json
{
  "blend": { "func": "add", "srcrgb": "srcalpha", "dstrgb": "one" },
  "vertex": "holocore_relic_glow",
  "fragment": "holocore_relic_glow",
  "attributes": ["Position", "Color", "UV0", "UV1", "UV2", "Normal"],
  "samplers": [{ "name": "Sampler0" }],
  "uniforms": [
    { "name": "ModelViewMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "ProjMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "ColorModulator", "type": "float", "count": 4, "values": [1,1,1,1] },
    { "name": "HoloTime", "type": "float", "count": 1, "values": [0.0] },
    { "name": "HoloGlitch", "type": "float", "count": 1, "values": [0.0] },
    { "name": "HoloTint", "type": "float", "count": 4, "values": [1,1,1,1] }
  ]
}
```

`holocore_relic_glow.vsh` — borde a partir de la posición del vértice:

```glsl
#version 150

// Atributos de DefaultVertexFormat.NEW_ENTITY que se usan. UV1 (overlay) y UV2
// (lightmap) se dejan sin declarar a proposito: en las shaders de entidad son
// ivec2 y declararlos como vec2 rompe el enlace del atributo.

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in vec3 Normal;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 texCoord;
out vec4 vertexColor;
out float edge;
out float viewY;

void main() {
    vec4 viewPos = ModelViewMat * vec4(Position, 1.0);
    vec3 viewDir = normalize(-viewPos.xyz + vec3(0.0, 0.0, 0.0001));

    // Direccion hacia fuera: la reliquia esta centrada en el origen del modelo
    // (preRender no aplica desplazamiento), asi que la posicion del vertice ya
    // apunta hacia fuera. Se usa esto y no solo la normal porque el atributo
    // Normal puede venir igual en todas las caras segun lo rellene el modelo:
    // entonces el fresnel dejaria de seguir la silueta y seria un tinte plano.
    vec3 outward = normalize(Position + vec3(0.0, 0.0, 0.0001));
    vec3 viewOutward = normalize(mat3(ModelViewMat) * outward);

    // Un cuarto de normal (si viene bien puesta) matiza el borde sin depender
    // de ella. El epsilon va dentro del normalize y no en un ternario: hay
    // drivers que evaluan las dos ramas y normalize(vec3(0.0)) da NaN.
    vec3 viewNormal = normalize(mat3(ModelViewMat) * Normal + vec3(0.0, 0.0, 0.0001));
    vec3 basis = normalize(viewOutward * 0.75 + viewNormal * 0.25);

    // 1 de canto (borde de la silueta), 0 de frente.
    edge = 1.0 - clamp(abs(dot(viewDir, basis)), 0.0, 1.0);

    // Altura en espacio de vista, en bloques. El barrido y la rejilla del
    // fragment se hacen con esto y no con UV0: las UV de un modelo de 98 huesos
    // se repiten por cara, asi que salian cuatro bandas por cara en vez de una
    // que recorre la reliquia entera.
    viewY = viewPos.y;

    gl_Position = ProjMat * viewPos;
    texCoord = UV0;
    vertexColor = Color;
}
```

`holocore_relic_glow.fsh` — textura × color, borde por silueta, dos barridos y
líneas finas:

```glsl
#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;
uniform float HoloGlitch;
uniform vec4 HoloTint;

in vec2 texCoord;
in vec4 vertexColor;
in float edge;
in float viewY;

out vec4 fragColor;

// Ruido barato y deterministico: rompe el banding que deja el blend aditivo
// cuando el degradado es muy suave. Sin tiempo dentro a proposito: si cambia por
// frame, en vez de dither se ve hervir.
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // Glitch de evento (destello, pulso, golpe): la UV se parte por bandas
    // horizontales y los canales se separan. Va en una rama sobre un uniform, o
    // sea la misma para todos los pixeles del dibujo, asi que el camino normal
    // sigue muestreando la textura una sola vez.
    vec2 uv = texCoord;
    if (HoloGlitch > 0.01) {
        float band = floor(viewY * 48.0);
        float tear = (hash(vec2(band, floor(HoloTime * 14.0))) - 0.5) * HoloGlitch * 0.08;
        uv.x += tear;
    }

    vec4 tex = texture(Sampler0, uv);
    vec3 texRgb = tex.rgb;
    if (HoloGlitch > 0.01) {
        float split = HoloGlitch * 0.010;
        texRgb = vec3(texture(Sampler0, uv + vec2(split, 0.0)).r,
                      tex.r,
                      texture(Sampler0, uv - vec2(split, 0.0)).b);
    }
    float texAlpha = tex.a * vertexColor.a;

    // Dos bordes por multiplicacion, no por pow: el suave tine la cara y el
    // cuarto se queda pegado a la silueta. Dos multiplicaciones cuestan menos
    // que dos pow y el corte del borde queda mas limpio.
    float e = clamp(edge, 0.0, 1.0);
    float rimSoft = e * e;
    float rimTight = rimSoft * rimSoft;

    // El borde entra tambien en la alpha: la silueta brilla aunque ahi la
    // textura emisiva sea transparente. Es lo que lo hace leer como contorno de
    // holograma y no como un brillo pegado encima de las caras opacas.
    // 1.0.41: menos peso que antes (0.55/0.30). El borde se comia el modelo.
    float alpha = max(texAlpha, rimSoft * 0.42 + rimTight * 0.20);
    if (alpha < 0.02) {
        discard;
    }

    // Linea de lectura: UNA linea fina que baja por la reliquia, con un halo suave
    // alrededor. Hasta 1.0.40 esto era una banda ancha (smoothstep entre 0.40 y
    // 0.62): en un modelo de medio bloque son mas de 20 cm de alto cruzando de lado
    // a lado, y se leia como el anillo de un planeta, no como un holograma.
    float readPos = fract(viewY * 0.9 - HoloTime * 0.25);
    float readNear = min(readPos, 1.0 - readPos);
    float readLine = 1.0 - smoothstep(0.0, 0.020, readNear);
    float readHalo = 1.0 - smoothstep(0.0, 0.110, readNear);
    // Rejilla fina y lenta, anclada al espacio de vista: las lineas siguen de una
    // cara a otra y no se pelean entre caras al girar la camara. A 90 rad/bloque y
    // 0.02 de peso hervia al caminar (el patron se corre 6 rad por tick): ahora son
    // 60 y la mitad de peso, o sea textura y no interferencia.
    float grid = 0.5 + 0.5 * sin(viewY * 60.0 - HoloTime * 1.4);
    // Latido lento del borde. No toca el nucleo: eso es la textura por el tinte.
    float breath = 0.85 + 0.15 * sin(HoloTime * 1.6);

    vec3 tint = vertexColor.rgb;
    // HoloTint lo pone el renderer por estado de brillo (0.62 en lluvia, 0.74 bajo
    // el agua, 0.84 de noche, 1.08 en la oscuridad): el tinte del borde lo respeta,
    // si no todos los estados acababan con el mismo azul en la silueta.
    vec3 rimTint = mix(vec3(0.55, 0.85, 1.0), tint, 0.55) * HoloTint.rgb;
    // Al raspar, el borde se va al violeta: dos tonos en la misma silueta.
    rimTint = mix(rimTint, vec3(0.78, 0.62, 1.0), rimTight * 0.35);

    // La linea y el halo se pesan por texAlpha: existen sobre el cuerpo, no en el
    // aire de la silueta, y por eso ya no dibujan un aro alrededor de la reliquia.
    vec3 rgb = texRgb * tint
             + rimSoft * rimTint * 0.16 * breath
             + rimTight * rimTint * 0.24
             + (readLine * 0.05 + readHalo * 0.03) * texAlpha * rimTint
             + grid * texAlpha * 0.010
             // Dither para el banding del aditivo. Solo suma: con -0.5 el negativo
             // lo recorta el framebuffer, o sea que no ditherizaba nada, solo
             // ensuciaba (el "moteado" de 1.0.40).
             + hash(texCoord * 613.0) * 0.015;

    // El blend es (srcalpha, one): la alpha entra una vez, por el blend. El rgb va
    // SIN premultiplicar. Hasta 1.0.40 se multiplicaba aqui tambien y el resultado
    // era alpha^2: el borde perdia fuerza y, para compensarlo, estaba subido de
    // ganancia, que es lo que hacia que brillara de mas por el centro.
    fragColor = vec4(rgb * ColorModulator.rgb, alpha);
}
```

### A.1b Los cuatro pases: uno anima, tres dibujan

Estudiado en el código de GeckoLib 4.8 (`GeoRenderer.defaultRender` /
`reRender` y `GeoObjectRenderer.actuallyRender`), porque la primera versión
llamaba cuatro veces a `defaultRender`:

* `defaultRender(...)` llama a `actuallyRender(..., isReRender = false, ...)`, y
  **ahí** está `model.handleAnimations(...)`: evaluar las animaciones y posar los
  98 huesos. También llama a `doPostRenderCleanup()`, que pone
  `this.animatable = null` (de ahí que cada pase lo reasigne).
* `reRender(model, ...)` llama a `actuallyRender(..., isReRender = true, ...)`.
  `GeoObjectRenderer` solo hace `handleAnimations` cuando `isReRender` es falso,
  así que este camino **reutiliza la pose** y solo recorre los huesos para
  emitir vértices con otro `RenderType`. Es exactamente para lo que existe
  («alternate RenderType layers» en su javadoc).

Con eso: una evaluación de animación por portador y frame en vez de cuatro, y los
cuatro pases son literalmente la misma pose. Ese último punto importa en un
contorno aditivo: si cada pase evaluara por su cuenta, `RenderUtils.getCurrentTick()`
(`Blaze3D.getTime() * 20`) daría tiempos ligeramente distintos y los pases se
verían desalineados como flecos de color en los bordes.

El tinte de los pases extra se pasa explícito a `reRender` porque en ese camino
GeckoLib no consulta `getRenderColor`; solo lo lee `defaultRender`.

### A.1c Lo que sí se paga por frame: geometría, no memoria

Quitar tres evaluaciones de animación deja el coste donde de verdad está: emitir
vértices. Con 977 cubos son 5 866 quads por pase, y con los cuatro pases
encendidos ~23 000 quads por reliquia y frame (4 506 por pase en `lite`). Eso no
se puede evitar sin cambiar el modelo, así que las palancas siguen siendo
`maxRenderDistance`, `quality`, `glowHalo` y `shaderGlow`.

Lo que **sí** se podía quitar es la basura que generaba el camino de render, y
desde 1.0.17 no se reserva nada por frame y portador:

* `RelicAura` giraba los ejes del billboard creando cuatro `Vector3f` por quad
  (`left*cos + up*sin` y `up*cos - left*sin`) más un `record Frame` por frame.
  Ahora `Frame` es una instancia reutilizada (el render corre en el hilo de
  render, un portador detrás de otro) y el giro son seis multiplicaciones en
  `float`. Entre tint, aditivo y anillo eran **35 objetos por portador y frame**;
  a 240 FPS con diez reliquias en pantalla, ~88 000 objetos por segundo que solo
  alimentaban al recolector.
* `RelicGlowState.targetFor(...)` creaba un `Target` por frame; los cinco
  destinos son ahora `static final`.
* `RelicGeoRenderer.getRenderColor(...)` llamaba a `Color.ofRGBA(...)`, que en
  GeckoLib 4.8.1 construye un `record Color` nuevo. Como el pase base va siempre
  en blanco, se empaqueta el ARGB igual que GeckoLib y se reutiliza el mismo
  objeto mientras el tinte no cambie.

Todo esto se puede ver en el juego: `/relic stats` da los pases por dibujo y los
milisegundos por dibujo, con modelo y aura por separado, así que comparar 1.0.15
con esta versión en el mismo sitio es una medida y no una impresión.

Nada de esto cambia un píxel: son las mismas cuentas con menos objetos. El CI lo
comprueba con dos pasos nuevos —`Validate render path allocations` (prohíbe
`new` en `RelicAura` y `RelicGlowState` salvo en constantes de clase) y
`Validate single animation evaluation` (un solo `defaultRender`, ningún
`actuallyRender`, tres `renderExtra`)—, así que la mejora de 1.0.16 y esta no
pueden perderse en silencio.

### A.2 Cómo se carga

El juego sólo precompila sus propios core shaders, así que hay que construir el
`ShaderInstance` a mano en un listener de *resource reload* (así se recompila al
cambiar de pack) y rellenar el uniform propio en cada frame:

```java
ShaderInstance shader = new ShaderInstance(resourceManager, "holocore_relic_glow",
        DefaultVertexFormat.NEW_ENTITY);

// por frame:
shader.safeGetUniform("HoloTime").set((level.getGameTime() % 20000) / 20.0F);
```

…y usarlo en un `RenderType` con `.setShaderState(new ShaderStateShard(() -> shader))`.
Ojo: `ShaderStateShard` es `protected` en `RenderStateShard`, igual que
`TextureStateShard` y `TransparencyStateShard`; por eso hace falta la clase
auxiliar que hereda de `RenderType` (la misma que ya usa `RelicRenderTypes`), no
basta con instanciarlas desde fuera.

### A.3 Cómo queda conectado (y sus límites)

* `RelicShaders` registra un `PreparableReloadListener` en
  `RegisterClientReloadListenersEvent`: el shader se compila en cada recarga de
  recursos. El programa anterior **no** se cierra en el acto: se jubila y se
  cierra en el primer pase del frame siguiente (`reap()`), porque cerrarlo dentro
  de la recarga puede liberar el `Program` que todavía referencia un lote de
  vértices sin volcar. Si la compilación falla se registra el error y se sigue
  sin el pase, no se cae el cliente.
* **Matrices y color no hay que subirlos a mano**: `BufferUploader` →
  `VertexBuffer.drawWithShader` rellena `ModelViewMat`, `ProjMat` y
  `ColorModulator` en cada dibujo, y `Sampler0` sale del `TextureStateShard`. El
  único uniform propio que se toca por frame es `HoloTime`.
* El blend lo decide el JSON (`add` / `srcalpha` / `one`): `ShaderInstance.apply()`
  lo aplica *después* de los estados del `RenderType`, así que gana el del shader.
* **Fade por distancia**: la reliquia de otros jugadores se apaga en los 8
  bloques previos a `maxRenderDistance` (multiplica intensidades y alpha) en vez
  de desaparecer de golpe. La del jugador local nunca se atenúa.
* **Se apaga solo** si hay shaderpack: `IrisApi.isShaderPackInUse()` por
  reflexión cuando Oculus está presente (si la API no está, se asume activo) y
  detección de OptiFine por `ModList` y por la clase `optifine.Installer`.
  Comprobación cacheada 5 s para no reflejar en cada frame.
* El CI valida el JSON (blend, uniforms con `count` correcto, atributos dentro de
  `NEW_ENTITY`), comprueba que los bloques de este apéndice son **copia literal**
  de los ficheros del jar, y **exige la marca `Shader del aura compilado` en el
  log del smoke test**: si el GLSL deja de compilar, el build falla aunque el
  cliente arranque.
