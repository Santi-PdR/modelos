package com.capatest.katana;

import com.capatest.CapaTestMod;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/** Cliente: la geometría y el atlas proceden del .bbmodel editable. */
public class KatanaRenderer extends GeoItemRenderer<StainKatanaItem> {
    public KatanaRenderer() {
        super(new DefaultedItemGeoModel<>(new ResourceLocation(CapaTestMod.MOD_ID, "katana_stain")));
    }
}
