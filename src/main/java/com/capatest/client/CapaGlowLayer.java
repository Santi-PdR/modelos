package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.texture.AutoGlowingTexture;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/** Modula sólo el RGB del pase emisivo; el glowmask y la opacidad no cambian. */
public class CapaGlowLayer extends AutoGlowingGeoLayer<CapaDeteriorerItem> {
    private boolean disabled;

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
        if (disabled || bakedModel == null)
            return;
        try {
            renderGlow(poseStack, animatable, bakedModel, bufferSource,
                    partialTick, packedLight, packedOverlay);
        } catch (Exception | LinkageError error) {
            // El pass emisivo es decorativo: nunca debe tumbar el render.
            disabled = true;
            com.capatest.CapaTestMod.LOGGER.error(
                    "Blight Star Mantle: capa emisiva desactivada", error);
        }
    }

    private void renderGlow(PoseStack poseStack,
                            CapaDeteriorerItem animatable,
                            BakedGeoModel bakedModel,
                            MultiBufferSource bufferSource,
                            float partialTick,
                            int packedLight,
                            int packedOverlay) {
        ResourceLocation texture = getTextureResource(animatable);
        if (texture == null)
            return;
        RenderType emissive = AutoGlowingTexture.getRenderType(texture);
        if (emissive == null)
            return;

        if (!(getRenderer() instanceof GeoArmorRenderer<?> armor))
            return;
        Entity wearer = armor.getCurrentEntity();
        CapeState mode = CapaDeteriorerItem.stateFor(wearer, armor.getCurrentStack());
        double seconds = wearer == null ? 0.0 : (wearer.tickCount + (double) partialTick) / 20.0;
        CapeState.Glow glow = mode.glow(seconds);

        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                glow.red(), glow.green(), glow.blue(), 1.0F);
    }
}
