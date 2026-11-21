package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.minecraft.Util;
import net.minecraft.client.renderer.RenderStateShard;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;

import java.util.function.Function;

/**
 * RenderTypes propios del mod.
 *
 * <p>El pase normal usa {@link RenderType#entityTranslucentEmissive}, que es un
 * tipo de vanilla/Forge y por tanto lo reconocen todos los shaderpacks: Iris y
 * Oculus lo mandan a {@code gbuffers_entities(_translucent)} y el pack aplica
 * su bloom a lo que venga con el lightmap a tope.</p>
 *
 * <p>El halo necesita <b>sumar</b> luz en vez de mezclarla (blend aditivo), y eso
 * no existe en ningun RenderType publico de 1.20.1 con el formato de vertice de
 * entidades. La unica via es construir uno: en 1.20.1 {@code RenderType.create}
 * no es publico, asi que se hace lo mismo que hace Forge en
 * {@code ForgeRenderTypes}: una clase interna que hereda de {@link RenderType}
 * solo para tener acceso a los estados protegidos ({@code ADDITIVE_TRANSPARENCY},
 * {@code LIGHTMAP}, {@code NO_CULL}, {@code COLOR_WRITE}) y a {@code create(...)}.</p>
 *
 * <p>Se usa a proposito el shader de entidad translucida estandar
 * ({@code RENDERTYPE_ENTITY_TRANSLUCENT_SHADER}) y no un shader propio: un
 * programa GLSL que el shaderpack no conozca puede acabar sustituido por su
 * fallback o directamente invisible (le paso a Forge con su shader "unlit", ver
 * Oculus #630). Con un shader conocido, el halo se ve igual con y sin pack.</p>
 */
public final class RelicRenderTypes {

    private RelicRenderTypes() {
    }

    /**
     * Pase aditivo sobre una textura: no escribe profundidad y suma su color al
     * framebuffer, que es lo que produce el efecto de brillo acumulado ("bloom"
     * barato) sin necesidad de post-proceso.
     */
    public static final Function<ResourceLocation, RenderType> ADDITIVE_GLOW =
            Util.memoize(Internal::additiveGlow);

    private static final class Internal extends RenderType {

        private Internal(String name, VertexFormat format, VertexFormat.Mode mode, int bufferSize,
                         boolean affectsCrumbling, boolean sortOnUpload,
                         Runnable setupState, Runnable clearState) {
            super(name, format, mode, bufferSize, affectsCrumbling, sortOnUpload, setupState, clearState);
            // Solo existe para heredar los campos protegidos de RenderType.
            throw new IllegalStateException("RelicRenderTypes no se instancia");
        }

        private static RenderType additiveGlow(ResourceLocation texture) {
            CompositeState state = CompositeState.builder()
                    .setShaderState(RENDERTYPE_ENTITY_TRANSLUCENT_SHADER)
                    .setTextureState(new RenderStateShard.TextureStateShard(texture, false, false))
                    .setTransparencyState(ADDITIVE_TRANSPARENCY)
                    .setCullState(NO_CULL)
                    .setLightmapState(LIGHTMAP)
                    .setOverlayState(OVERLAY)
                    .setDepthTestState(LEQUAL_DEPTH_TEST)
                    // Sin escritura de profundidad: el halo no tapa lo de detras
                    // ni se tapa a si mismo.
                    .setWriteMaskState(COLOR_WRITE)
                    .createCompositeState(false);
            return create("holocore_additive_glow", DefaultVertexFormat.NEW_ENTITY,
                    VertexFormat.Mode.QUADS, 256, false, true, state);
        }
    }
}
