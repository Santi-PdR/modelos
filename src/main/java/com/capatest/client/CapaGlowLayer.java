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
        // por debajo del pleno); ahora 0.86-1.14 con más ganancia al
        // esprintar: la capa "respira" luz en la noche sin quemar color.
        // v1.33.0: el brillo NO va en el alpha (lo fue, y causaba el fantasma
        // translúcido en F5); va en el COLOR (r,g,b), que se satura en el
        // pico del ciclo. El glowmask determina qué se dibuja (solo venas).
        float amplitude = charged ? 0.26F : 0.14F;
        float breathe = 1.0F + amplitude * (float) Math.sin(phase);
        // v1.29.0: SHIMMER viajante. Sobre el latido global se suma una
        // barreda lenta de luz (periodo 2x, fase distinta) para que el
        // brillo no sea un pulso llano: parece una onda de energia que
        // recorre el paño, no una bombilla encendida y apagada.
        // v1.31.0: se suma un SEGUNDO shimmer a mayor frecuencia y baja
        // amplitud, con fase distinta, para que la luz recorriendo el
        // paño no sea una onda simple: tiene el temblor de la tela.
        float shimmer = 0.05F * (float) Math.sin(phase * 0.5 + 1.2)
                + 0.03F * (float) Math.sin(phase * 1.7 + 0.4);
        // v1.32.0: se suma un TERCER shimmer a frecuencia doble y muy
        // baja amplitud, con fase distinta, para que el brillo recorriendo
        // el paño tenga el temblor de los hilos finos: no es una onda
        // lisa ni un pulso llano, es el resplandor de un tejido vivo.
        shimmer += 0.02F * (float) Math.sin(phase * 3.3 + 2.1);
        // v1.34.0: se suma un CUARTO shimmer a frecuencia aún mayor y muy
        // baja amplitud, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor casi microscópico de los hilos finos: no
        // es una onda lisa ni un pulso llano, es el brillo de un tejido vivo.
        shimmer += 0.015F * (float) Math.sin(phase * 4.9 + 3.0);
        // v1.35.0: se suma un QUINTO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo el
        // paño tenga el temblor casi imperceptible de los hilos más finos:
        // el brillo de un tejido vivo, no un pulso llano ni una onda lisa.
        shimmer += 0.012F * (float) Math.sin(phase * 6.1 + 4.2);
        // v1.36.0: se suma un SEXTO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor casi imperceptible de los hilos más
        // finos: el brillo de un tejido vivo, no un pulso llano ni una
        // onda lisa.
        shimmer += 0.010F * (float) Math.sin(phase * 7.3 + 5.1);
        // v1.37.0: se suma un SÉPTIMO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor casi imperceptible de los hilos más
        // finos: el brillo de un tejido vivo, no un pulso llano ni una
        // onda lisa.
        shimmer += 0.008F * (float) Math.sin(phase * 8.5 + 5.9);
        // v1.38.0: se suma un OCTAVO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor casi imperceptible de los hilos más
        // finos: el brillo de un tejido vivo, no un pulso llano ni una
        // onda lisa.
        shimmer += 0.006F * (float) Math.sin(phase * 9.7 + 6.7);
        // v1.43.0: se suma un NOVENO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor casi microscópico de los hilos más
        // estrechos: el brillo de un tejido vivo, no un pulso llano ni
        // una onda lisa. El brillo va SOLO en el COLOR (r,g,b): el alpha
        // del re-render sigue FIJO en 1.0, así que la capa sigue opaca
        // en F5 (corrección v1.33.0 intacta).
        shimmer += 0.004F * (float) Math.sin(phase * 10.9 + 7.5);
        // v1.44.0: se suma un DÉCIMO shimmer a frecuencia mayor y amplitud
        // aún menor, con fase distinta, para que el resplandor recorriendo
        // el paño tenga el temblor sub-texel del grano del tejido: el
        // brillo de un tejido vivo, no un pulso llano ni una onda lisa.
        // El brillo va SOLO en el COLOR (r,g,b): el alpha del re-render
        // sigue FIJO en 1.0 (corrección v1.33.0 intacta).
        shimmer += 0.003F * (float) Math.sin(phase * 12.1 + 8.3);
        // v1.45.0: se suma un DÉCIMACUARTO shimmer a frecuencia mayor y
        // amplitud aún menor, con fase distinta, para que el resplandor
        // recorriendo el paño tenga el temblor del grano ultrafino del
        // tejido: el brillo de un tejido vivo, no un pulso llano ni una
        // onda lisa. El brillo va SOLO en el COLOR (r,g,b): el alpha del
        // re-render sigue FIJO en 1.0 (corrección v1.33.0 intacta).
        shimmer += 0.002F * (float) Math.sin(phase * 13.3 + 9.1);
        // v1.46.0: se suma un DÉCIMACINCO shimmer a frecuencia mayor y
        // amplitud aún menor, con fase distinta, para que el resplandor
        // recorriendo el paño tenga el temblor del grano extremo del
        // tejido: el brillo de un tejido vivo, no un pulso llano ni una
        // onda lisa. El brillo va SOLO en el COLOR (r,g,b): el alpha del
        // re-render sigue FIJO en 1.0 (corrección v1.33.0 intacta).
        shimmer += 0.0015F * (float) Math.sin(phase * 14.5 + 10.3);
        // v1.33.0: CORRECCIÓN DEL FANTASTA TRANSLÚCIDO EN F5.
        // Antes pasábamos `brightness` como ALPHA global del re-render. Ese
        // alpha se aplicaba a TODO el mesh (no solo a las venas emisivas),
        // así que en la vista trasera (F5) el re-render translúcido se
        // dibujaba sobre el cuerpo: la capa parecía transparente y "adentro"
        // del jugador. Ahora el alpha es FIJO 1.0 y el brillo pulsante se
        // aplica al COLOR (r,g,b). Como el glowmask tiene alpha 0 fuera de
        // las venas, esas regiones NO se dibujan: no hay re-render fantasma
        // sobre el cuerpo y la capa sigue siendo opaca en F5. El brillo
        // pulsante (breathe + 3 shimmer) se mantiene sobre las venas.
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
        float red = Math.min(1.0F, (1.0F - blight * 0.30F) * brightness);
        float green = Math.min(1.0F, (Math.min(1.0F, violet * cool + blight * 0.55F)) * brightness);
        float blue = Math.min(1.0F, (cool + blight * 0.40F) * brightness);
        // v1.47.0: DRIFT DE MATIZ lento del resplandor. Un ciclo secundario
        // muy lento desliza el balance entre el violeta y el cian, así el
        // brillo no es un color fijo: es el resplandor de un tejido vivo.
        // Sólo toca el COLOR (r,g,b); el alpha del re-render sigue FIJO
        // en 1.0 (corrección v1.33.0 intacta).
        float hueDrift = 0.06F * (float) Math.sin(phase * 0.27D + 2.1D);
        red = Math.min(1.0F, red + hueDrift * 0.25F);
        green = Math.min(1.0F, green + hueDrift * 0.10F);
        blue = Math.min(1.0F, blue - hueDrift * 0.35F);

        getRenderer().reRender(bakedModel, poseStack, bufferSource, animatable, emissive,
                bufferSource.getBuffer(emissive), partialTick,
                LightTexture.FULL_SKY, OverlayTexture.NO_OVERLAY,
                red, green, blue, 1.0F);
    }
}
