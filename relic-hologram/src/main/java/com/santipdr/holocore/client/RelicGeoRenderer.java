package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.ShaderInstance;
import net.minecraft.client.renderer.texture.OverlayTexture;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.core.object.Color;
import software.bernie.geckolib.renderer.GeoObjectRenderer;

/**
 * Renderer del modelo centrado (origen = centro del nucleo).
 *
 * <p>{@link GeoObjectRenderer} traslada medio bloque porque asume objetos
 * centrados en un bloque; aqui se anula ese desplazamiento en
 * {@link #preRender}. La colocacion en el hombro la hace
 * {@link RelicCurioRenderer} sobre el PoseStack.</p>
 */
public class RelicGeoRenderer extends GeoObjectRenderer<RelicAnimatable> {

    public RelicGeoRenderer(RelicGeoModel model) {
        super(model);
    }

    @Override
    public long getInstanceId(RelicAnimatable animatable) {
        return RelicAnimatable.INSTANCE_ID;
    }

    @Override
    public void preRender(PoseStack poseStack, RelicAnimatable animatable, BakedGeoModel model,
                          MultiBufferSource bufferSource, VertexConsumer buffer, boolean isReRender,
                          float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha) {
        // Sin desplazamiento: el .geo.json ya viene centrado.
    }

    /** Tinte del pase que se esta dibujando (lo lee {@link #getRenderColor}). */
    private float tintRed = 1.0F;
    private float tintGreen = 1.0F;
    private float tintBlue = 1.0F;
    private float tintAlpha = 1.0F;

    /**
     * Pases sobre el mismo esqueleto ya posado:
     * <ol>
     *   <li>textura base (incluye el aura tenue translucida);</li>
     *   <li>textura emisiva, que excluye el aura para que no se sume dos veces;</li>
     *   <li>halo: la misma textura emisiva pero con blend <b>aditivo</b>, que suma
     *       luz en vez de mezclarla. Eso es lo que da el aspecto de brillo
     *       acumulado sin necesidad de post-proceso ni de shaderpack;</li>
     *   <li>shader propio (opcional): el mismo blend aditivo, pero con fresnel y
     *       linea de barrido calculados en GLSL. Ver {@link RelicShaders}.</li>
     * </ol>
     *
     * <p>{@code glow} es el estado de brillo interpolado del portador, el mismo
     * que usa {@link RelicAura}: aporta el factor de intensidad (dormida brilla
     * menos, cargada mas) y el color, asi que halo y pase GLSL se tiñen con el
     * estado en vez de quedarse azules fijos mientras el aura se pone roja.</p>
     * Ninguno de los pases vuelve a animar: GeckoLib detecta que es el mismo
     * frame y conserva las matrices de los huesos.
     */
    void renderHologram(PoseStack poseStack, RelicAnimatable animatable,
                        MultiBufferSource bufferSource, float partialTick, int packedLight,
                        RelicGlowState glow) {
        // El programa jubilado por una recarga se cierra aqui: en el primer pase
        // del frame, con los lotes anteriores ya volcados.
        RelicShaders.reap();

        renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                RenderType.entityTranslucentEmissive(RelicGeoModel.texture()),
                1.0F, 1.0F, 1.0F, 1.0F);

        if (RelicConfig.GLOW_LAYER.get()) {
            renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                    RenderType.entityTranslucentEmissive(RelicGeoModel.glowTexture()),
                    1.0F, 1.0F, 1.0F, 1.0F);
        }

        // Factor de brillo del modelo: estado (0.35 dormida .. 1.15 cargada) por
        // el destello del evento, que llega a +60%.
        float amount = Math.max(0.0F, Math.min(1.25F, glow.aura()))
                * (1.0F + 0.2F * glow.flashScaled());

        if (haloEnabled()) {
            float i = RelicConfig.HALO_INTENSITY.get().floatValue() * amount;
            // Nucleo de luz fria por defecto, pero arrastrado a medias hacia el
            // color del estado: cargada se ve ambarienta, alerta rojiza.
            renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                    RelicRenderTypes.ADDITIVE_GLOW.apply(RelicGeoModel.glowTexture()),
                    tint(0.55F, glow.red()) * i, tint(0.78F, glow.green()) * i,
                    tint(1.00F, glow.blue()) * i, 1.0F);
        }

        // Cuarto pase opcional con GLSL propio: fresnel en el borde y linea de
        // barrido. Se salta solo si hay shaderpack (el pack sustituiria el
        // programa) o si el shader no compilo.
        ShaderInstance glowShader = RelicShaders.ready() ? RelicShaders.shader() : null;
        if (glowShader != null) {
            glowShader.safeGetUniform("HoloTime").set(RelicShaders.timeSeconds(partialTick));
            float i = RelicConfig.SHADER_INTENSITY.get().floatValue() * amount;
            renderPass(poseStack, animatable, bufferSource, partialTick, packedLight,
                    RelicRenderTypes.GLOW_SHADER.apply(RelicGeoModel.glowTexture()),
                    tint(0.65F, glow.red()) * i, tint(0.85F, glow.green()) * i,
                    tint(1.00F, glow.blue()) * i, 1.0F);
        }
    }

    /**
     * Mezcla el tono frio de base con el componente del estado (un cuarto de
     * peso: se nota el cambio de color sin perder el azul de nucleo). Se hace por
     * canal y no con un {@code mix} de vectores porque el tinte se pasa a
     * GeckoLib como cuatro floats.
     */
    private static float tint(float cool, float state) {
        return cool * 0.75F + state * 0.25F;
    }

    /**
     * El halo es el pase mas caro (tercera pasada sobre 977 cubos), asi que se
     * salta en calidad LITE y con los efectos reducidos.
     */
    private boolean haloEnabled() {
        return RelicConfig.GLOW_HALO.get()
                && RelicConfig.QUALITY.get() == RelicConfig.Quality.FULL
                && !RelicConfig.REDUCED_EFFECTS.get();
    }

    private void renderPass(PoseStack poseStack, RelicAnimatable animatable,
                            MultiBufferSource bufferSource, float partialTick, int packedLight,
                            RenderType renderType, float red, float green, float blue, float alpha) {
        tintRed = red;
        tintGreen = green;
        tintBlue = blue;
        tintAlpha = alpha;
        // defaultRender limpia this.animatable al terminar, hay que reasignarlo.
        this.animatable = animatable;
        defaultRender(poseStack, animatable, bufferSource,
                renderType, null, 0.0F, partialTick, packedLight);
    }

    /**
     * GeckoLib pasa este color como color de vertice de cada cubo, asi que sirve
     * para atenuar el pase aditivo sin tocar estado global de OpenGL (un
     * {@code RenderSystem.setShaderColor} afectaria a todo lo que se dibuje
     * despues).
     */
    @Override
    public Color getRenderColor(RelicAnimatable animatable, float partialTick, int packedLight) {
        return Color.ofRGBA(tintRed, tintGreen, tintBlue, tintAlpha);
    }

    @Override
    public int getPackedOverlay(RelicAnimatable animatable, float u, float partialTick) {
        return OverlayTexture.NO_OVERLAY;
    }
}
