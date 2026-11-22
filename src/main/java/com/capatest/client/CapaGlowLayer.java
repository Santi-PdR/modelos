package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.multiplayer.ClientLevel;
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
    // Render-thread histories survive a transfer from chest to Curios. A
    // weak key keeps the clock specific to this wearer and this loaded world.
    private static final Map<Entity, CapeWornLight> LIGHTS = new WeakHashMap<>();
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
        if (mode == CapeBloom.Mode.OFF || ceiling == CapeBloom.Mode.OFF)
            return;
        if (ceiling == CapeBloom.Mode.CORE)
            mode = CapeBloom.Mode.CORE;
        try {
            // GeckoLib needn't balance its internal pushes on an exception.
            // Give this optional pass its own stack with the exact same top.
            PoseStack copy = new PoseStack();
            copy.last().pose().set(poseStack.last().pose());
            copy.last().normal().set(poseStack.last().normal());
            renderGlow(copy, animatable, bakedModel, bufferSource, mode, partialTick, packedLight);
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
                            CapeBloom.Mode pass,
                            float partialTick,
                            int packedLight) {
        // Match the unshifted opaque depth; the glow only writes color.
        RenderType emissive = CapeBloom.wornLight(pass);

        if (!(getRenderer() instanceof GeoArmorRenderer<?> armor))
            return;
        Entity wearer = armor.getCurrentEntity();
        CapeState mode = CapaDeteriorerItem.stateFor(wearer, armor.getCurrentStack());
        CapeState.Glow glow;
        CapeNocturne.Gains halo;
        if (wearer == null) {
            glow = mode.glow(0);
            halo = CapeNocturne.gains(0, 0, 0);
        } else {
            float sky = wearer.level() instanceof ClientLevel world ? world.getSkyDarken(partialTick) : 1.0F;
            var light = LIGHTS.computeIfAbsent(wearer, key -> new CapeWornLight());
            var frame = light.sample(mode, LightTexture.block(packedLight), LightTexture.sky(packedLight),
                    sky, wearer.tickCount, partialTick, wearer.getId());
            glow = frame.glow();
            halo = frame.halo();
        }
        // Packed per vertex for batching. The vanilla fallback still gets
        // ordinary fullbright lightmap coordinates, not the halo payload.
        int vertexLight = pass == CapeBloom.Mode.HALO ? halo.packed() : LightTexture.FULL_BRIGHT;
        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                vertexLight, OverlayTexture.NO_OVERLAY, glow.red(), glow.green(), glow.blue(), 1.0F);
    }
}
