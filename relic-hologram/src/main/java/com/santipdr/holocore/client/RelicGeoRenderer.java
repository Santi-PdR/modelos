package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoObjectRenderer;

/**
 * Renderer del modelo centrado (origen = centro del nucleo).
 *
 * <p>{@link GeoObjectRenderer} traslada medio bloque porque asume objetos
 * centrados en un bloque; aqui se anula ese desplazamiento en
 * {@link #preRender}. La colocacion en el hombro la hace
 * {@link RelicCurioRenderer} sobre el PoseStack.</p>
 */
public class RelicGeoRenderer extends GeoObjectRenderer<RelicAnimatable> {

    public RelicGeoRenderer(RelicGeoModel model) {
        super(model);
    }

    @Override
    public long getInstanceId(RelicAnimatable animatable) {
        return RelicAnimatable.INSTANCE_ID;
    }

    @Override
    public void preRender(PoseStack poseStack, RelicAnimatable animatable, BakedGeoModel model,
                          MultiBufferSource bufferSource, VertexConsumer buffer, boolean isReRender,
                          float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha) {
        // Sin desplazamiento: el .geo.json ya viene centrado.
    }

    /**
     * Dos pases sobre el mismo esqueleto ya posado:
     * <ol>
     *   <li>textura base (incluye el aura tenue translucida);</li>
     *   <li>textura emisiva, que excluye el aura para que el halo no se sume dos
     *       veces.</li>
     * </ol>
     * El segundo pase no vuelve a animar: GeckoLib detecta que es el mismo
     * frame y conserva las matrices de los huesos.
     */
    public void renderHologram(PoseStack poseStack, RelicAnimatable animatable,
                               MultiBufferSource bufferSource, float partialTick, int packedLight) {
        renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                RelicGeoModel.texture());

        if (RelicConfig.GLOW_LAYER.get()) {
            renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                    RelicGeoModel.glowTexture());
        }
    }

    private void renderPass(PoseStack poseStack, RelicAnimatable animatable,
                            MultiBufferSource bufferSource, float partialTick, int packedLight,
                            ResourceLocation texture) {
        // defaultRender limpia this.animatable al terminar, hay que reasignarlo.
        this.animatable = animatable;
        defaultRender(poseStack, animatable, bufferSource,
                RenderType.entityTranslucentEmissive(texture), null, 0.0F, partialTick, packedLight);
    }

    @Override
    public int getPackedOverlay(RelicAnimatable animatable, float u, float partialTick) {
        return OverlayTexture.NO_OVERLAY;
    }
}
