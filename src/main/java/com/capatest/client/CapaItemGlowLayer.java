package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

/**
 * Efecto emisivo del item plegado v1.8.0.
 *
 * Re-renderiza el bulto con `cape_folded_glowmask.png` mediante
 * {@link RenderType#eyes(ResourceLocation)}: la textura es transparente salvo
 * en el broche, la constelación, los nervios y los ribetes, así que sólo esas
 * zonas brillan. A diferencia de {@code AutoGlowingTexture}, NO modifica el
 * atlas base: si esta capa fallara, el item sigue viéndose completo.
 *
 * El brillo "respira" con un periodo de 2.6 s y se vuelve algo más violeta en
 * los valles. Es decorativo: cualquier error se registra y se desactiva.
 */
public class CapaItemGlowLayer extends GeoRenderLayer<CapaDeteriorerItem> {
    private static final ResourceLocation GLOW = new ResourceLocation(
            CapaTestMod.MOD_ID, "textures/item/cape_folded_glowmask.png");
    private static final double PERIOD_MS = 2600.0;
    private boolean disabled;

    public CapaItemGlowLayer(GeoRenderer<CapaDeteriorerItem> renderer) {
        super(renderer);
    }

    @Override
    public void render(PoseStack poseStack,
                       CapaDeteriorerItem animatable,
                       BakedGeoModel bakedModel,
                       RenderType renderType,
                       MultiBufferSource bufferSource,
                       VertexConsumer buffer,
                       float partialTick,
                       int packedLight,
                       int packedOverlay) {
        if (disabled || bakedModel == null) {
            return;
        }
        try {
            RenderType eyes = RenderType.eyes(GLOW);
            double phase = (System.currentTimeMillis() % PERIOD_MS) / PERIOD_MS * Math.PI * 2.0;
            float brightness = 0.72F + 0.28F * (float) Math.sin(phase);
            float violet = 0.88F + 0.10F * (1.0F - brightness);
            getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, eyes,
                    bufferSource.getBuffer(eyes), partialTick,
                    LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                    1.0F, violet, brightness, brightness);
        } catch (Exception | LinkageError error) {
            disabled = true;
            CapaTestMod.LOGGER.error("Manto de la Estrella Moribunda: efecto emisivo del item desactivado", error);
        }
    }
}
