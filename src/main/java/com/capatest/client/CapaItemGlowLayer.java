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
 * los valles. v1.9.0 añade un destello cian más lento (Blight Star) en el
 * canal azul/verde. Es decorativo: cualquier error se registra y se desactiva.
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
            // v1.39.0: SHIMMER del brillo del item. Sobre el latido principal
            // se suma una barreda lenta de luz, para que el resplandor del
            // bulto plegado no sea un pulso llano: la energia recorre el
            // broche y los nervios como en la capa equipada.
            float shimmer = 0.05F * (float) Math.sin(phase * 0.6 + 1.1)
                    + 0.025F * (float) Math.sin(phase * 1.9 + 2.3);
            float brightness = 0.72F + 0.28F * (float) Math.sin(phase) + shimmer;
            float violet = 0.88F + 0.10F * (1.0F - brightness);
            float cyan = 0.10F + 0.10F * (float) Math.cos(phase * 0.5D)
                    + 0.04F * (float) Math.sin(phase * 1.3 + 0.7);
            float red = 1.0F - cyan * 0.12F;
            float green = Math.min(1.0F, violet + cyan * 0.28F);
            float blue = Math.min(1.0F, brightness + cyan * 0.14F);
            getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, eyes,
                    bufferSource.getBuffer(eyes), partialTick,
                    LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                    red, green, blue, brightness);
        } catch (Exception | LinkageError error) {
            disabled = true;
            CapaTestMod.LOGGER.error("Blight Star Mantle: efecto emisivo del item desactivado", error);
        }
    }
}
