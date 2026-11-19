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
    private int resourceGeneration = -1;
    private CapeBloom.Mode ceiling = CapeBloom.Mode.HALO;

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
        if (bakedModel == null || bufferSource == null)
            return;
        int generation = CapeBloom.generation();
        if (resourceGeneration != generation) {
            resourceGeneration = generation;
            ceiling = CapeBloom.Mode.HALO;
        }
        CapeBloom.Mode mode = CapeBloom.availableMode();
        if (mode.ordinal() > ceiling.ordinal())
            mode = ceiling;
        if (mode == CapeBloom.Mode.OFF)
            return;
        try {
            // GeckoLib needn't balance its internal pushes on an exception.
            // Give this optional pass its own stack with the exact same top.
            PoseStack copy = new PoseStack();
            copy.last().pose().set(poseStack.last().pose());
            copy.last().normal().set(poseStack.last().normal());
            renderGlow(copy, animatable, bakedModel, bufferSource, mode, partialTick);
        } catch (RuntimeException | LinkageError error) {
            // Don't submit a second copy in the same frame. Retry at a lower
            // mode next frame and clear the failure on a resource reload.
            ceiling = mode == CapeBloom.Mode.HALO ? CapeBloom.Mode.CORE : CapeBloom.Mode.OFF;
            CapaTestMod.LOGGER.warn("Blight Star Mantle: falló el pase {}; siguiente pase: {}",
                    mode, ceiling, error);
        }
    }

    private void renderGlow(PoseStack poseStack,
                            CapaDeteriorerItem animatable,
                            BakedGeoModel bakedModel,
                            MultiBufferSource bufferSource,
                            CapeBloom.Mode mode,
                            float partialTick) {
        // Match the unshifted opaque depth; the glow only writes color.
        RenderType emissive = CapeBloom.wornLight(mode);

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
