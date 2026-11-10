package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/**
 * Renderer 3D de la capa plegada para inventario, hotbar, mano y suelo.
 *
 * v1.6.0 conserva el geo de 33 huesos (7 pliegues, nervios, yugo, cuello,
 * alas, broche, cadenas, costuras y puntas), pero su atlas y el icono ahora
 * muestrean el MISMO canvas 96×48 que la capa equipada: un único medallón y
 * la misma filigrana. El balanceo vive en
 * animations/item/cape_folded.animation.json, así que aquí sólo hacen falta
 * la iluminación de entidad para GUI y la escala del modelo.
 */
public class CapaItemRenderer extends GeoItemRenderer<CapaDeteriorerItem> {
    public CapaItemRenderer() {
        super(new DefaultedItemGeoModel<>(
                new ResourceLocation(CapaTestMod.MOD_ID, "cape_folded")
        ));
        this.useAlternateGuiLighting();
        this.scaleWidth = 1.0F;
        this.scaleHeight = 1.0F;
    }
}
