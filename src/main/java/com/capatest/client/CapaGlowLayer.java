package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

import java.util.Map;
import java.util.WeakHashMap;

/** Separate, depth-tested light on the same solids, without editing the opaque atlas. */
public class CapaGlowLayer extends GeoRenderLayer<CapaDeteriorerItem> {
    // A colour history follows the entity that is rendered, not the last player in the renderer.
    private final Map<Entity, CapeTint> colors = new WeakHashMap<>();
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
        if (disabled || bakedModel == null || bufferSource == null)
            return;
        try {
            renderGlow(poseStack, animatable, bakedModel, bufferSource,
                    partialTick);
        } catch (Exception | LinkageError error) {
            // El pass emisivo es decorativo: nunca debe tumbar el render.
            disabled = true;
            CapaTestMod.LOGGER.error(
                    "Blight Star Mantle: capa emisiva desactivada", error);
        }
    }

    private void renderGlow(PoseStack poseStack,
                            CapaDeteriorerItem animatable,
                            BakedGeoModel bakedModel,
                            MultiBufferSource bufferSource,
                            float partialTick) {
        // The texture holds colored emission and coverage. Do not derive it
        // with AutoGlowingTexture: that path re-uploads a modified base image.
        // Match the unshifted opaque depth; the glow only writes color.
        RenderType emissive = CapeBloom.wornLight();

        if (!(getRenderer() instanceof GeoArmorRenderer<?> armor))
            return;
        Entity wearer = armor.getCurrentEntity();
        CapeState mode = CapaDeteriorerItem.stateFor(wearer, armor.getCurrentStack());
        double seconds = wearer == null ? 0.0 : (wearer.tickCount + (double) partialTick) / 20.0;
        CapeState.Glow glow = wearer == null ? mode.glow(seconds) :
                colors.computeIfAbsent(wearer, key -> new CapeTint()).sample(mode, seconds);

        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY,
                glow.red(), glow.green(), glow.blue(), 1.0F);
    }
}
