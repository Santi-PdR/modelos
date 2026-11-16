package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

/**
 * Efecto emisivo del item plegado v1.8.0.
 *
 * Re-renderiza el bulto con `cape_folded_glowmask.png` mediante
 * {@link RenderType#eyes(ResourceLocation)}: la textura es transparente salvo
 * en el broche, la constelación, los nervios y los ribetes, así que sólo esas
 * zonas brillan. A diferencia de {@code AutoGlowingTexture}, NO modifica el
 * atlas base: si esta capa fallara, el item sigue viéndose completo.
 *
 * El brillo "respira" con un periodo de 2.6 s y se vuelve algo más violeta en
 * los valles. v1.9.0 añade un destello cian más lento (Blight Star) en el
 * canal azul/verde. Es decorativo: cualquier error se registra y se desactiva.
 */
public class CapaItemGlowLayer extends GeoRenderLayer<CapaDeteriorerItem> {
    private static final ResourceLocation GLOW = new ResourceLocation(
            CapaTestMod.MOD_ID, "textures/item/cape_folded_glowmask.png");
    private static final double PERIOD_MS = 2600.0;
    private boolean disabled;

    public CapaItemGlowLayer(GeoRenderer<CapaDeteriorerItem> renderer) {
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
        if (disabled || bakedModel == null) {
            return;
        }
        try {
            RenderType eyes = RenderType.eyes(GLOW);
            double phase = (System.currentTimeMillis() % PERIOD_MS) / PERIOD_MS * Math.PI * 2.0;
            // v1.43.0: se suma un shimmer lento a mayor frecuencia y muy
            // baja amplitud, con fase distinta, para que el destello del
            // broche no sea un pulso llano. Se CLAMPEA a 1.0 para que el
            // alpha del re-render emisivo NO supere el pleno (el item
            // sigue opaco y nunca se vuelve transparente).
            // v1.44.0: se suma un SEGUNDO shimmer a frecuencia mayor y
            // amplitud aún menor, con fase distinta, para que el destello
            // tenga el temblor del grano del broche. También se CLAMPEA
            // a 1.0: el alpha del re-render emisivo NO supera el pleno.
            // v1.45.0: se suma un TERCER shimmer a frecuencia mayor y
            // amplitud aún menor, con fase distinta, para que el destello
            // tenga el temblor del grano ultrafino del broche. También se
            // CLAMPEA a 1.0: el alpha del re-render emisivo NO supera
            // el pleno (el item sigue opaco).
            // v1.46.0: se suma un CUARTO shimmer a frecuencia mayor y
            // amplitud aún menor, con fase distinta, para que el destello
            // tenga el temblor del grano extremo del broche. También se
            // CLAMPEA a 1.0: el alpha del re-render emisivo NO supera
            // el pleno (el item sigue opaco).
            float brightness = Math.min(1.0F, 0.72F + 0.28F * (float) Math.sin(phase)
                    + 0.05F * (float) Math.sin(phase * 2.3D + 0.9D)
                    + 0.04F * (float) Math.sin(phase * 3.7D + 1.8D)
                    + 0.03F * (float) Math.sin(phase * 4.9D + 2.7D)
                    + 0.02F * (float) Math.sin(phase * 6.1D + 3.6D));
            float violet = 0.88F + 0.10F * (1.0F - brightness);
            float cyan = 0.10F + 0.10F * (float) Math.cos(phase * 0.5D);
            float red = 1.0F - cyan * 0.12F;
            float green = Math.min(1.0F, violet + cyan * 0.28F);
            float blue = Math.min(1.0F, brightness + cyan * 0.14F);
            // v1.47.0: DRIFT DE MATIZ lento del destello del broche. Un
            // ciclo secundario muy lento desliza el balance de color,
            // así el brillo no es un color fijo. Sólo toca el COLOR
            // (r,g,b); el alpha ya está CLAMPEADO a 1.0.
            float drift = 0.05F * (float) Math.sin(phase * 0.31D + 1.6D);
            red = Math.min(1.0F, red + drift * 0.3F);
            green = Math.min(1.0F, green + drift * 0.15F);
            blue = Math.min(1.0F, blue - drift * 0.4F);
            getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, eyes,
                    bufferSource.getBuffer(eyes), partialTick,
                    LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                    red, green, blue, brightness);
        } catch (Exception | LinkageError error) {
            disabled = true;
            CapaTestMod.LOGGER.error("Blight Star Mantle: efecto emisivo del item desactivado", error);
        }
    }
}
