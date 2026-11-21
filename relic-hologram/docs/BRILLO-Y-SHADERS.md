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
   Es lo único que el CI no puede valorar.

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
    { "name": "HoloTime", "type": "float", "count": 1, "values": [0.0] }
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

in vec2 texCoord;
in vec4 vertexColor;
in float edge;

out vec4 fragColor;

// Ruido barato y deterministico: rompe el banding que deja el blend aditivo
// cuando el degradado es muy suave.
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float texAlpha = tex.a * vertexColor.a;

    // Borde: sale de la posicion del vertice, no de la alpha de la textura, asi
    // que la silueta brilla aunque ese texel de la textura emisiva sea
    // transparente. Es lo que hace que se lea como un contorno de holograma y no
    // como un brillo pegado encima de las caras opacas.
    float rim = pow(clamp(edge, 0.0, 1.0), 1.6);
    float alpha = max(texAlpha, rim * 0.55);
    if (alpha < 0.02) {
        discard;
    }

    // Barrido que sube: cuatro ciclos sobre la textura, uno cada 4 s.
    float sweep = smoothstep(0.42, 0.58, fract(texCoord.y * 4.0 - HoloTime * 0.25));
    // Barrido cruzado, mas rapido y mas tenue: rompe la simetria del vertical.
    float cross = smoothstep(0.46, 0.54, fract((texCoord.x + texCoord.y) * 2.0 - HoloTime * 0.41));
    // Lineas finas de holograma, solo donde ya hay algo opaco.
    float lines = (0.5 + 0.5 * sin(texCoord.y * 160.0 + HoloTime * 5.0)) * texAlpha;

    vec3 tint = vertexColor.rgb;
    vec3 rimTint = mix(vec3(0.55, 0.85, 1.0), tint, 0.55);

    vec3 rgb = tex.rgb * tint
             + rim * rimTint * 0.40
             + (sweep * 0.06 + cross * 0.045 + lines * 0.02)
             + (hash(texCoord * 613.0) - 0.5) * 0.03;

    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
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
