# Verificación de versiones y APIs

Consultado directamente en los repositorios oficiales durante esta implementación:

| Dependencia | Versión fijada | Evidencia |
|---|---|---|
| Minecraft / Java | 1.20.1 / 17 | `minecraft_version` y toolchain del proyecto Forge de GeckoLib |
| Forge | 47.4.8 | `forge_version` en las propiedades de GeckoLib 1.20.1 |
| GeckoLib Forge | 4.8.4 | `version` en las mismas propiedades |
| Curios Forge | 5.14.1+1.20.1 | `mod_version` en las propiedades de Curios 1.20.x |

Fuentes reproducibles, fijadas a commits (no documentación de otra versión):

- [GeckoLib gradle.properties](https://github.com/bernie-g/geckolib/blob/7d6f32db9168a24e14b327c0ad9f8f87dfc204de/gradle.properties)
- [GeckoLib Forge build.gradle: Java 17 y dependencias](https://github.com/bernie-g/geckolib/blob/7d6f32db9168a24e14b327c0ad9f8f87dfc204de/Forge/build.gradle)
- [Curios gradle.properties](https://github.com/TheIllusiveC4/Curios/blob/a91da6ba2396f6ed9042c8a47a471ca5efc97da8/gradle.properties)
- [ICurioRenderer](https://github.com/TheIllusiveC4/Curios/blob/a91da6ba2396f6ed9042c8a47a471ca5efc97da8/src/main/java/top/theillusivec4/curios/api/client/ICurioRenderer.java)
- [GeoObjectRenderer](https://github.com/bernie-g/geckolib/blob/7d6f32db9168a24e14b327c0ad9f8f87dfc204de/Forge/src/main/java/software/bernie/geckolib/renderer/GeoObjectRenderer.java)
- [AutoGlowingGeoLayer](https://github.com/bernie-g/geckolib/blob/7d6f32db9168a24e14b327c0ad9f8f87dfc204de/Forge/src/main/java/software/bernie/geckolib/renderer/layer/AutoGlowingGeoLayer.java)
- [AutoGlowingTexture: APPENDIX real](https://github.com/bernie-g/geckolib/blob/7d6f32db9168a24e14b327c0ad9f8f87dfc204de/Forge/src/main/java/software/bernie/geckolib/cache/texture/AutoGlowingTexture.java)

## Equivalencias importantes

- Curios tiene `ICurioRenderer`, `CuriosRendererRegistry.register` y datapacks
  `data/<namespace>/curios/{slots,entities}/`. No se usa una API de otra generación.
- El accesorio usa el ítem estándar con tag Curios; no necesita una capability propia
  ni implementar `ICurioItem` para comportamiento cosmético.
- GeckoLib utiliza un `GeoAnimatable` por portador y `GeoObjectRenderer`, no un
  `GeoItemRenderer` compartido por todos los jugadores. El ítem de inventario es plano.
- **`AutoGlowingGeoLayer` existe, pero `AutoGlowingTexture.APPENDIX` en 4.8.4 es
  `_glowmask`**, aunque el Javadoc de la capa todavía menciona `_glowing`.
  También modifica la textura base al extraer la máscara. Por eso aquí se utiliza
  una `GeoRenderLayer` explícita con `RenderType.entityTranslucentEmissive`, leyendo
  directamente el PNG `_glowing` original sin modificarlo ni generar otra máscara.
- El cargador GeckoLib convierte X del JSON Bedrock. El renderizador compensa Y
  del espacio del jugador, conserva Z hacia la espalda y permite reflejar X.
  No se modificaron la geometría ni las rotaciones exportadas. La corrección visual
  de rotaciones/espejado debe contrastarse en juego con el preview del ZIP; si los
  exports difieren de Blockbench, se necesita reexportarlos desde el `.bbmodel`.

## Alcance de la verificación

Las versiones fueron leídas de los proyectos oficiales, no inferidas de memoria.
Esto confirma sus declaraciones para 1.20.1; **no equivale a comprobar que los
artefactos Maven se descargan ni que el mod compila o arranca**. En este sandbox no
hay JDK y no se permite acceso a Maven Forge/Curios/Cloudsmith/Gradle. La ejecución
real de `./gradlew build` falla antes de iniciar Gradle por falta de Java.
`runClient`, servidor dedicado y shaders quedan pendientes de ejecución en un
entorno con Java 17, acceso a esos repositorios y, para el cliente, pantalla/OpenGL.
