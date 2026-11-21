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

* **Tres capas, no una**: diámetros 1.05 / 1.55 / 2.10 bloques con aportes
  0.55 / 0.32 / 0.18. Una sola capa se ve como una pegatina plana.
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

**Anillo de estado** (`RelicAura.drawRing`, textura `relic_ring.png` de
`tools/make_ring.py`): un solo billboard, más grande que el aura (2.05 bloques),
que solo se dibuja cuando el estado tiene algo que decir. El estado sale de
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

## Apéndice A — el GLSL que lleva el mod desde 1.0.3

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
  "attributes": ["Position", "Color", "UV0", "UV2", "Normal"],
  "samplers": [{ "name": "Sampler0" }],
  "uniforms": [
    { "name": "ModelViewMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "ProjMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "ColorModulator", "type": "float", "count": 4, "values": [1,1,1,1] },
    { "name": "HoloTime", "type": "float", "count": 1, "values": [0.0] }
  ]
}
```

`holocore_relic_glow.vsh` — fresnel calculado en espacio de vista:

```glsl
#version 150

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in vec3 Normal;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;

out vec2 texCoord;
out vec4 vertexColor;
out float fresnel;

void main() {
    vec4 viewPos = ModelViewMat * vec4(Position, 1.0);
    vec3 viewNormal = normalize(mat3(ModelViewMat) * Normal);
    float facing = abs(dot(normalize(-viewPos.xyz), viewNormal));
    fresnel = pow(1.0 - facing, 2.5);
    gl_Position = ProjMat * viewPos;
    texCoord = UV0;
    vertexColor = Color;
}
```

`holocore_relic_glow.fsh` — textura × color, borde y barrido que sube:

```glsl
#version 150

uniform sampler2D Sampler0;
uniform vec4 ColorModulator;
uniform float HoloTime;

in vec2 texCoord;
in vec4 vertexColor;
in float fresnel;

out vec4 fragColor;

void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float alpha = clamp(tex.a * vertexColor.a, 0.0, 1.0);
    float scan = smoothstep(0.45, 0.5, fract(texCoord.y * 6.0 - HoloTime));
    vec3 rgb = tex.rgb * vertexColor.rgb + fresnel * 0.35 + scan * 0.08;
    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
```

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
  recursos y el anterior se cierra con `close()`. Si la compilación falla se
  registra el error y se sigue sin el pase, no se cae el cliente.
* **Matrices y color no hay que subirlos a mano**: `BufferUploader` →
  `VertexBuffer.drawWithShader` rellena `ModelViewMat`, `ProjMat` y
  `ColorModulator` en cada dibujo, y `Sampler0` sale del `TextureStateShard`. El
  único uniform propio que se toca por frame es `HoloTime`.
* El blend lo decide el JSON (`add` / `srcalpha` / `one`): `ShaderInstance.apply()`
  lo aplica *después* de los estados del `RenderType`, así que gana el del shader.
* **Se apaga solo** si hay shaderpack: `IrisApi.isShaderPackInUse()` por
  reflexión cuando Oculus está presente (si la API no está, se asume activo) y
  detección de OptiFine por `ModList` y por la clase `optifine.Installer`.
  Comprobación cacheada 5 s para no reflejar en cada frame.
* El CI valida el JSON (blend, uniforms con `count` correcto, atributos dentro de
  `NEW_ENTITY`) y **exige la marca `Shader del aura compilado` en el log del
  smoke test**: si el GLSL deja de compilar, el build falla aunque el cliente
  arranque.
