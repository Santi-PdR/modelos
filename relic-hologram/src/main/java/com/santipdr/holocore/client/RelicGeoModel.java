package com.santipdr.holocore.client;

import com.santipdr.holocore.HoloCore;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

/**
 * Recursos del modelo. La calidad se lee en cada llamada para que el cambio en
 * la config (o por comando) se aplique al instante sin recargar recursos:
 * GeckoLib cachea el modelo horneado por ruta y reasigna su processor cuando
 * cambia (los dos .geo.json tienen los mismos 98 huesos).
 */
public class RelicGeoModel extends GeoModel<RelicAnimatable> {

    private static final ResourceLocation MODEL_FULL =
            new ResourceLocation(HoloCore.MOD_ID, "geo/relic_hologram_centered.geo.json");
    private static final ResourceLocation MODEL_LITE =
            new ResourceLocation(HoloCore.MOD_ID, "geo/relic_hologram_lite_centered.geo.json");
    private static final ResourceLocation ANIMATIONS =
            new ResourceLocation(HoloCore.MOD_ID, "animations/relic_hologram.animation.json");
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(HoloCore.MOD_ID, "textures/relic/relic_hologram.png");
    private static final ResourceLocation TEXTURE_GLOW =
            new ResourceLocation(HoloCore.MOD_ID, "textures/relic/relic_hologram_glowing.png");

    public static ResourceLocation texture() {
        return TEXTURE;
    }

    public static ResourceLocation glowTexture() {
        return TEXTURE_GLOW;
    }

    @Override
    public ResourceLocation getModelResource(RelicAnimatable animatable) {
        return RelicConfig.QUALITY.get() == RelicConfig.Quality.LITE ? MODEL_LITE : MODEL_FULL;
    }

    @Override
    public ResourceLocation getTextureResource(RelicAnimatable animatable) {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(RelicAnimatable animatable) {
        return ANIMATIONS;
    }

    /**
     * Pase principal: translucido y emisivo (sin termino difuso por normal), de
     * modo que el nucleo se ve igual de noche, en cuevas o bajo el agua. El
     * brillo extra usa la misma familia de RenderType con la textura emisiva.
     */
    @Override
    public RenderType getRenderType(RelicAnimatable animatable, ResourceLocation texture) {
        return RenderType.entityTranslucentEmissive(texture);
    }
}
