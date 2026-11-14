package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.texture.AutoGlowingTexture;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Capa emisiva con "respiración" de energía.
 *
 * El AutoGlowingGeoLayer original re-renderiza siempre con color (1,1,1,1).
 * Aquí modulamos suavemente el alpha y el canal verde del re-render para que
 * las venas de la capa latan y se vuelvan más violetas en los valles del ciclo.
 * Al correr, la amplitud del latido aumenta (el portador está "cargado").
 *
 * Ojo: GeckoLib sólo usa el ALFA del *_glowmask.png; el color del brillo sale
 * de la textura base, por eso tools/texture_pipeline.py potencia esos píxeles.
 *
 * v1.9.0: además del latido violeta, un componente cian muy suave aparece al
 * perder vida o al correr, evocando la luz fría de Blight Star. La cobertura
 * del glowmask sigue intacta: sólo cambian los canales del re-render.
 */
public class CapaGlowLayer extends AutoGlowingGeoLayer<CapaDeteriorerItem> {
    private static final double PERIOD_MS = 3200.0;
    private boolean disabled;

    public CapaGlowLayer(GeoArmorRenderer<CapaDeteriorerItem> renderer) {
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
        if (disabled || bakedModel == null)
            return;
        try {
            renderGlow(poseStack, animatable, bakedModel, bufferSource,
                    partialTick, packedLight, packedOverlay);
        } catch (Exception | LinkageError error) {
            // El pass emisivo es decorativo: nunca debe tumbar el render.
            disabled = true;
            com.capatest.CapaTestMod.LOGGER.error(
                    "Blight Star Mantle: capa emisiva desactivada", error);
        }
    }

    private void renderGlow(PoseStack poseStack,
                            CapaDeteriorerItem animatable,
                            BakedGeoModel bakedModel,
                            MultiBufferSource bufferSource,
                            float partialTick,
                            int packedLight,
                            int packedOverlay) {
        ResourceLocation texture = getTextureResource(animatable);
        if (texture == null)
            return;
        RenderType emissive = AutoGlowingTexture.getRenderType(texture);
        if (emissive == null)
            return;

        Entity wearer = this.renderer instanceof GeoArmorRenderer<?> armor
                ? armor.getCurrentEntity()
                : null;
        boolean charged = wearer != null && wearer.isSprinting();

        double phase = (System.currentTimeMillis() % PERIOD_MS) / PERIOD_MS * Math.PI * 2.0;
        // v1.25.0: más luz. Antes el latido iba 0.76-1.00 (casi siempre
        // por debajo del pleno); ahora 0.82-1.22 con más ganancia al
        // esprintar: la capa "respira" luz en la noche sin quemar color.
        float amplitude = charged ? 0.26F : 0.14F;
        float breathe = 0.96F + amplitude * (float) Math.sin(phase);
        // v1.29.0: SHIMMER viajante. Sobre el latido global se suma una
        // barreda lenta de luz (periodo 2x, fase distinta) para que el
        // brillo no sea un pulso llano: parece una onda de energia que
        // recorre el paño, no una bombilla encendida y apagada.
        // v1.31.0: se suma un SEGUNDO shimmer a mayor frecuencia y baja
        // amplitud, con fase distinta, para que la luz recorriendo el
        // paño no sea una onda simple: tiene el temblor de la tela.
        float shimmer = 0.05F * (float) Math.sin(phase * 0.5 + 1.2)
                + 0.03F * (float) Math.sin(phase * 1.7 + 0.4);
        float brightness = breathe + shimmer;
        float violet = 0.90F + 0.08F * (1.0F - brightness);

        // v1.9.0: al perder vida (o al correr) el aura no vira a rojo, sino a
        // un cian frío: es la luz "blight" del planeta, no una herida.
        float health = 1.0F;
        if (wearer instanceof LivingEntity living && living.getMaxHealth() > 0.0F) {
            health = Math.max(0.0F, Math.min(1.0F, living.getHealth() / living.getMaxHealth()));
        }
        float cool = 0.55F + 0.45F * health;
        float blight = (1.0F - health) * 0.22F + (charged ? 0.06F : 0.0F);
        float red = 1.0F - blight * 0.30F;
        float green = Math.min(1.0F, violet * cool + blight * 0.55F);
        float blue = Math.min(1.0F, cool + blight * 0.40F);

        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                red, green, blue, brightness);
    }
}
