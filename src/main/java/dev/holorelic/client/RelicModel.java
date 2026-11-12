package dev.holorelic.client;

import dev.holorelic.HoloRelic;
import dev.holorelic.RelicConfig;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.model.GeoModel;

final class RelicModel extends GeoModel<RelicVisual> {
    private static final ResourceLocation GEO = resource("geo/relic_hologram.geo.json");
    private static final ResourceLocation TEXTURE = resource("textures/relic_hologram.png");
    private static final ResourceLocation ANIMATIONS = resource("animations/relic_hologram.animation.json");
    private static final String[] OPTIONAL_BONES = {
            "drift_01", "drift_02", "drift_03", "drift_04", "drift_05", "drift_06", "drift_07", "drift_08",
            "ring_tilt_5", "ring_tilt_6"
    };
    private static ResourceLocation resource(String path) { return new ResourceLocation(HoloRelic.ID, path); }
    @Override public ResourceLocation getModelResource(RelicVisual visual) { return GEO; }
    @Override public ResourceLocation getTextureResource(RelicVisual visual) { return TEXTURE; }
    @Override public ResourceLocation getAnimationResource(RelicVisual visual) { return ANIMATIONS; }
    @Override public RenderType getRenderType(RelicVisual visual, ResourceLocation texture) {
        // No directional shading; texture alpha is preserved. This is not dynamic world lighting.
        return RenderType.entityTranslucentEmissive(texture);
    }
    @Override public void setCustomAnimations(RelicVisual visual, long id, AnimationState<RelicVisual> state) {
        boolean hidden = RelicConfig.LOW_QUALITY.get();
        // Restore visibility explicitly: the baked model is shared between wearer instances.
        for (String name : OPTIONAL_BONES) getBone(name).ifPresent(b -> b.setHidden(hidden));
    }
}
