package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/**
 * Renderer 3D de la capa plegada para inventario, hotbar, mano y suelo.
 *
 * v1.3.0 sustituye la placa de dos cubos por un modelo de 8 huesos: dorso,
 * cinco pliegues a distinta profundidad, yugo y broche. Cada pliegue muestrea
 * una franja vertical del atlas de 128x128, así que las caras delanteras
 * reconstruyen UNA sola ilustración de capa en vez de repetir un cuadrado.
 * Los pliegues reciben una oscilación mínima y usan iluminación de entidad
 * en GUI para que el relieve se lea correctamente.
 */
public class CapaItemRenderer extends GeoItemRenderer<CapaDeteriorerItem> {
    private static final float[] FOLD_BASE_Z = {
            -4.4F, -1.6F, 0.0F, 1.6F, 4.4F
    };
    private static final float[] FOLD_BASE_X = {1.2F, 0.4F, 0.0F, 0.4F, 1.2F};

    public CapaItemRenderer() {
        super(new DefaultedItemGeoModel<>(
                new ResourceLocation(CapaTestMod.MOD_ID, "cape_folded")
        ));
        this.useAlternateGuiLighting();
        this.scaleWidth = 1.0F;
        this.scaleHeight = 1.0F;
    }

    @Override
    public void actuallyRender(PoseStack poseStack, CapaDeteriorerItem animatable,
                               BakedGeoModel model, RenderType renderType,
                               MultiBufferSource bufferSource, VertexConsumer buffer,
                               boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                               float red, float green, float blue, float alpha) {
        if (!isReRender && model != null) {
            // Balanceo casi imperceptible; las rotaciones de GeckoLib son radianes.
            double t = (System.currentTimeMillis() % 100000L) / 1000.0;
            for (int i = 0; i < FOLD_BASE_Z.length; i++) {
                CoreGeoBone fold = model.getBone("fold_" + i).orElse(null);
                if (fold == null) {
                    continue;
                }
                float wobbleX = (float) (Math.sin(t * 0.55 + i * 0.9) * 0.012D);
                float wobbleZ = (float) (Math.cos(t * 0.42 + i * 0.7) * 0.018D);
                fold.updateRotation(
                        (float) Math.toRadians(FOLD_BASE_X[i]) + wobbleX,
                        0.0F,
                        (float) Math.toRadians(FOLD_BASE_Z[i]) + wobbleZ);
            }
        }

        super.actuallyRender(poseStack, animatable, model, renderType, bufferSource, buffer,
                isReRender, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
    }
}
