package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    public CapaArmorRenderer() {
        // Apunta a:
        // assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json
        // assets/capatest/animations/item/armor/capa_deteriorer_evilsaiyan.animation.json
        // assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png
        // y *_glowmask.png (GeckoLib 4.8 usa el sufijo "_glowmask").
        // CapaArmorModel oculta las losas originales y anima los paneles
        // continuos v15_* sin tocar el geo aprobado.
        super(new CapaArmorModel(
                new ResourceLocation(CapaTestMod.MOD_ID, "armor/capa_deteriorer_evilsaiyan")
        ));

        // Emisivo pulsante en vez del AutoGlowingGeoLayer plano.
        addRenderLayer(new CapaGlowLayer(this));
    }

    private GeoBone bone(String name) {
        return getGeoModel().getBone(name).orElse(null);
    }

    @Override
    public @Nullable GeoBone getHeadBone() {
        return bone("helmet");
    }

    @Override
    public @Nullable GeoBone getBodyBone() {
        return bone("chestplate");
    }

    @Override
    public @Nullable GeoBone getRightArmBone() {
        return bone("rightArm");
    }

    @Override
    public @Nullable GeoBone getLeftArmBone() {
        return bone("leftArm");
    }

    @Override
    public @Nullable GeoBone getRightLegBone() {
        return bone("rightLeg");
    }

    @Override
    public @Nullable GeoBone getLeftLegBone() {
        return bone("leftLeg");
    }

    @Override
    public @Nullable GeoBone getRightBootBone() {
        return bone("rightBoot");
    }

    @Override
    public @Nullable GeoBone getLeftBootBone() {
        return bone("leftBoot");
    }
}
