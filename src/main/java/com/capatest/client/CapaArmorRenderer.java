package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    public CapaArmorRenderer() {
        // Apunta automáticamente a:
        // assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json
        // assets/capatest/animations/item/armor/capa_deteriorer_evilsaiyan.animation.json
        // assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png
        // y AutoGlowingGeoLayer carga *_glowmask.png automáticamente.
        super(new DefaultedItemGeoModel<>(
                new ResourceLocation(CapaTestMod.MOD_ID, "armor/capa_deteriorer_evilsaiyan")
        ));

        addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }

    @Override
    public @Nullable GeoBone getHeadBone() {
        return this.model.getBone("helmet").orElse(null);
    }

    @Override
    public @Nullable GeoBone getBodyBone() {
        return this.model.getBone("chestplate").orElse(null);
    }

    @Override
    public @Nullable GeoBone getRightArmBone() {
        return this.model.getBone("rightArm").orElse(null);
    }

    @Override
    public @Nullable GeoBone getLeftArmBone() {
        return this.model.getBone("leftArm").orElse(null);
    }

    @Override
    public @Nullable GeoBone getRightLegBone() {
        return this.model.getBone("rightLeg").orElse(null);
    }

    @Override
    public @Nullable GeoBone getLeftLegBone() {
        return this.model.getBone("leftLeg").orElse(null);
    }

    @Override
    public @Nullable GeoBone getRightBootBone() {
        return this.model.getBone("rightBoot").orElse(null);
    }

    @Override
    public @Nullable GeoBone getLeftBootBone() {
        return this.model.getBone("leftBoot").orElse(null);
    }
}
