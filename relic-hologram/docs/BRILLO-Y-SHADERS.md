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

Es decir: el «glowing» ya está, y el «bloom propio» en su versión barata también,
desde esta versión.

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

### C. Core shader propio (fresnel + scanlines de holograma)

Traer un `.vsh`/`.fsh` con `ShaderInstance` y un `ShaderStateShard(() -> shader)`,
con uniform propio de tiempo para las líneas de barrido y fresnel en el borde.
Es factible en 1.20.1, pero:

* **Con shaderpack se rompe o desaparece.** Iris/Oculus sustituyen los programas
  por los del pack; un programa que el pack no conoce acaba en su *fallback* o,
  como pasó con el shader «unlit» de Forge (Oculus #630), en **invisible**. Lo
  mismo aplica a OptiFine.
* Sin pack, la mejora frente al aditivo es pequeña (un fresnel más marcado).

Veredicto: sólo tiene sentido como *modo experto* que se desactive solo cuando hay
un shaderpack cargado (`ModList.get().isLoaded("oculus")` / `"optifine"`). No es
el siguiente paso.

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
| Sin shaderpack | ✅ | ✅ | ✅ | ✅ | ✅ (caro) |
| Iris/Oculus + Complementary | ✅ bloom del pack | ✅ (como geometría translúcida) | ✅ | ⚠️ fallback / invisible | ❌ |
| OptiFine sin pack | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| Servidor sin el mod cliente | — | — | — | — | — |

## 5. Plan por fases

1. **Hecho (1.0.1)**: halo aditivo con `glowHalo` + `haloIntensity`.
2. **Hecho (1.0.2)**: aura de tres billboards con `glowAura` + `auraIntensity`.
3. Medir FPS en un portátil y decidir si el halo del modelo se queda activo por
   defecto en `LITE` (ahora se omite; el aura sí se dibuja, son tres quads).
4. Sólo si hace falta: shader propio con detección de pack (apéndice A).

## Apéndice A — el GLSL que sí se podría usar (no está conectado)

Si algún día se quiere fresnel de verdad en el borde y líneas de barrido de
holograma, esto es lo que haría falta. **No está en el jar**: se deja escrito
porque el trabajo de averiguar la API ya está hecho y así no se repite.

Tres ficheros en `assets/holocore/shaders/relic/`: `glow.json`, `glow.vsh`,
`glow.fsh`. El JSON es el mismo formato que los *core shaders* del juego:

```json
{
  "blend": { "func": "add", "srcrgb": "srcalpha", "dstrgb": "one" },
  "vertex": "holocore:shaders/relic/glow",
  "fragment": "holocore:shaders/relic/glow",
  "attributes": ["Position", "Color", "UV0"],
  "samplers": [{ "name": "Sampler0" }],
  "uniforms": [
    { "name": "ModelViewMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "ProjMat", "type": "matrix4x4", "count": 16, "values": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
    { "name": "Time", "type": "float", "count": 1, "values": [0.0] },
    { "name": "ColorModulator", "type": "float", "count": 4, "values": [1,0,0,0] }
  ]
}
```

`glow.vsh`: pasa posición, color y UV, y calcula el fresnel con la normal en
espacio de vista (para el borde luminoso):

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
    fresnel = pow(1.0 - abs(normalize(viewPos.xyz).z), 2.5);
    gl_Position = ProjMat * viewPos;
    texCoord = UV0;
    vertexColor = Color;
}
```

`glow.fsh`: textura × color + borde + líneas de barrido que suben con el tiempo.
Es aditivo, así que el alfa no hace falta y todo suma:

```glsl
#version 150
uniform sampler2D Sampler0;
uniform float Time;
uniform vec4 ColorModulator;
in vec2 texCoord;
in vec4 vertexColor;
in float fresnel;
out vec4 fragColor;
void main() {
    vec4 tex = texture(Sampler0, texCoord);
    float scan = smoothstep(0.45, 0.5, fract(texCoord.y * 6.0 - Time * 0.25));
    float alpha = clamp(tex.a * vertexColor.a, 0.0, 1.0);
    vec3 rgb = tex.rgb * vertexColor.rgb + fresnel * 0.35 + scan * 0.08;
    fragColor = vec4(rgb * alpha * ColorModulator.rgb, alpha);
}
```

Para cargarlo hace falta un `ShaderInstance` construido a mano (el juego solo
precarga los suyos) y reconstruirlo cuando el jugador cambia de pack de recursos:

```java
// en un listener de reload del cliente
ShaderInstance shader = new ShaderInstance(resourceManager, "holocore:shaders/relic/glow",
        DefaultVertexFormat.NEW_ENTITY);
// ... y en cada frame:
shader.safeGetUniform("Time").set((level.getGameTime() + partialTick) / 20.0F);
```

…y un `RenderType` con `.setShaderState(new ShaderStateShard(() -> shader))`.
**Aquí está el problema**: con Iris/Oculus/OptiFine activos ese programa no está
en el pipeline del pack, así que se sustituye por el fallback o desaparece (le
pasó a Forge con su shader «unlit», Oculus #630). Por eso este camino necesita
además `ModList.get().isLoaded("oculus")` / `"optifine"` para apagarse solo, y
por eso hoy no está conectado.

## 6. Cómo probarlo

```
/give @s holocore:holographic_core      # equipar en el slot charm
/relic quality full                     # o lite, para comparar
/relic pulse                            # animacion de una sola vez
```

En `config/holocore-client.toml`:

```toml
[visuals]
    glowLayer = true
    glowHalo = true
    haloIntensity = 0.35
```

Si con el pack el halo se ve «lavado», bajar `haloIntensity`; si se ve plano sin
pack, subirlo a 0.5–0.6. Para comparar con y sin shaderpack, mismo mundo, misma
hora, y mirar la silueta contra una pared oscura.
