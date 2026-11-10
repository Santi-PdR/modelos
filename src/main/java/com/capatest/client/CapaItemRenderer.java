package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/**
 * Modelo 3D de la capa plegada para inventario, mano y suelo.
 * Usa su propio geo/atlas/animación (cape_folded) para no arrastrar la escala
 * del modelo de armadura, y comparte el controlador de animación del item.
 */
public class CapaItemRenderer extends GeoItemRenderer<CapaDeteriorerItem> {
    public CapaItemRenderer() {
        super(new DefaultedItemGeoModel<>(
                new ResourceLocation(CapaTestMod.MOD_ID, "cape_folded")
        ));
    }
}
