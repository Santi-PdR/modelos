package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/**
 * Renderer 3D de la capa plegada para inventario, hotbar, mano y suelo.
 *
 * v1.8.0: el geo de 34 huesos es un BULTO de tela con grosor real (forro,
 * 7 franjas con relieve, yugo, cuello, broche de diamante, cadenas, tiras,
 * 3 rollos y 5 puntas), no un abanico plano. El icono y el atlas plegado ya
 * no estiran el canvas 96×48 a un cuadrado: usan una composición con la
 * proporción correcta y los mismos motivos que la capa equipada.
 *
 * Se mantienen la corrección v1.6.1 del crash
 * {@code GeckoLibException: capatest:geo/item/cape_folded.geo.json: Error
 * loading model file}: el hueso raíz no escribe {@code "parent": null},
 * porque Gson intenta {@code JsonNull.getAsString()} y lanza.
 *
 * Dos mejoras de legibilidad in-game:
 *  - {@link CapaItemGlowLayer} re-renderiza el glowmask del item con un
 *    pulso suave, sin modificar el atlas base.
 *  - fuera de la GUI se fuerza {@link LightTexture#FULL_SKY}: en las capturas
 *    nocturnas el bulto se veía como una lámina casi negra.
 */
public class CapaItemRenderer extends GeoItemRenderer<CapaDeteriorerItem> {
    public CapaItemRenderer() {
        super(new DefaultedItemGeoModel<>(
                new ResourceLocation(CapaTestMod.MOD_ID, "cape_folded")
        ));
        this.useAlternateGuiLighting();
        this.addRenderLayer(new CapaItemGlowLayer(this));
        this.scaleWidth = 1.05F;
        this.scaleHeight = 1.05F;
    }

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext transformType,
                             PoseStack poseStack, MultiBufferSource bufferSource,
                             int packedLight, int packedOverlay) {
        int light = transformType == ItemDisplayContext.GUI
                ? packedLight
                : LightTexture.FULL_SKY;
        super.renderByItem(stack, transformType, poseStack, bufferSource,
                light, packedOverlay);
    }
}
