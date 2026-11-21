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

### B. Aura en billboard (siguiente paso natural)

Dos quads mirando a cámara con una textura radial (64×64 con degradado alfa),
escala ~1.4× el núcleo, uno girando lento y otro con pulso. Es geometría normal:
no depende de shaders, no se rompe con packs y se ve a distancia. Necesita una
textura nueva (se puede generar con `tools/make_icon.py`, que ya usa Pillow) y un
`RenderType` aditivo sin `LIGHTMAP`. Es el cambio que más «bloom» aparente da por
línea de código.

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

1. **Hecho**: halo aditivo con `glowHalo` + `haloIntensity`.
2. Aura en billboard (necesita textura nueva y un pase sin lightmap).
3. Medir FPS en un portátil con `quality=LITE` y decidir si el halo se queda
   activo por defecto en LITE (ahora se omite).
4. Sólo si hace falta: shader propio con detección de pack.

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
