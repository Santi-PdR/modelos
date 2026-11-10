package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.texture.AutoGlowingTexture;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Capa emisiva con "respiración" de energía.
 *
 * El AutoGlowingGeoLayer original re-renderiza siempre con color (1,1,1,1).
 * Aquí modulamos suavemente el alpha y el canal verde del re-render para que
 * las venas de la capa latan y se vuelvan más violetas en los valles del ciclo.
 * Al correr, la amplitud del latido aumenta (el portador está "cargado").
 *
 * Ojo: GeckoLib sólo usa el ALFA del *_glowmask.png; el color del brillo sale
 * de la textura base, por eso tools/texture_pipeline.py potencia esos píxeles.
 */
public class CapaGlowLayer extends AutoGlowingGeoLayer<CapaDeteriorerItem> {
    private static final double PERIOD_MS = 3200.0;

    public CapaGlowLayer(GeoArmorRenderer<CapaDeteriorerItem> renderer) {
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
        RenderType emissive = AutoGlowingTexture.getRenderType(getTextureResource(animatable));

        Entity wearer = this.renderer instanceof GeoArmorRenderer<?> armor
                ? armor.getCurrentEntity()
                : null;
        boolean charged = wearer != null && wearer.isSprinting();

        double phase = (System.currentTimeMillis() % PERIOD_MS) / PERIOD_MS * Math.PI * 2.0;
        float amplitude = charged ? 0.22F : 0.12F;
        float brightness = 0.88F + amplitude * (float) Math.sin(phase);
        float violet = 0.90F + 0.08F * (1.0F - brightness);

        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                1.0F, violet, 1.0F, brightness);
    }
}
