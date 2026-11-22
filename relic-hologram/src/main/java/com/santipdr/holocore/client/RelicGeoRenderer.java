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
     *
     * <p>{@code fade} llega de {@link RelicCurioRenderer}: para los portadores
     * que no son el jugador local se apaga en los ultimos bloques de
     * {@code maxRenderDistance}, en vez de desaparecer de golpe.</p>
     * <p><b>Solo el primer pase anima.</b> Estudiado en el codigo de GeckoLib
     * 4.8: {@code defaultRender} llama a {@code actuallyRender} con
     * {@code isReRender=false}, y es ahi donde se hace
     * {@code model.handleAnimations(...)} (evaluar las animaciones y posar los 98
     * huesos). {@code reRender}, en cambio, pasa {@code isReRender=true} y se
     * salta ese trabajo: dibuja los huesos tal como estan. Con cuatro
     * {@code defaultRender} se evaluaba la animacion cuatro veces por portador y
     * frame; con uno + tres {@code reRender} se evalua una, y ademas los cuatro
     * pases son exactamente la misma pose (sin diferencias de microsegundos entre
     * pases, que en un contorno aditivo se verian como flecos de color).</p>
     */
    void renderHologram(PoseStack poseStack, RelicAnimatable animatable,
                        MultiBufferSource bufferSource, float partialTick, int packedLight,
                        RelicGlowState glow, float fade) {
        // El programa jubilado por una recarga se cierra aqui: en el primer pase
        // del frame, con los lotes anteriores ya volcados.
        RelicShaders.reap();

        // Totalmente desvanecida: ni animacion ni pases. update() ya corrio, asi
        // que el portador sigue contando como "vivo" para el prune.
        if (fade <= 0.01F) {
            return;
        }

        // Cronometro de /relic stats: dos nanoTime por reliquia y frame, del orden
        // de decenas de nanosegundos frente a los cientos de microsegundos que
        // cuesta recorrer los 977 cubos.
        long began = System.nanoTime();
        int drawnPasses = 0;

        // Modelo horneado compartido por los cuatro pases: reRender necesita el
        // mismo objeto cuyos huesos ya poso el primer paso.
        BakedGeoModel model = getGeoModel().getBakedModel(getGeoModel().getModelResource(animatable));

        // Pase 1 (el unico que evalua la animacion).
        setTint(1.0F, 1.0F, 1.0F, 1.0F);
        this.animatable = animatable;
        defaultRender(poseStack, animatable, bufferSource,
                RenderType.entityTranslucentEmissive(RelicGeoModel.texture()),
                null, 0.0F, partialTick, packedLight);
        drawnPasses++;

        if (RelicConfig.GLOW_LAYER.get()) {
            renderExtra(model, poseStack, animatable, bufferSource, partialTick, packedLight,
                    RenderType.entityTranslucentEmissive(RelicGeoModel.glowTexture()),
                    1.0F, 1.0F, 1.0F, 1.0F);
            drawnPasses++;
        }

        // Factor de brillo del modelo: estado (0.35 dormida .. 1.15 cargada) por
        // el destello del evento, que llega a +60%.
        float amount = Math.max(0.0F, Math.min(1.25F, glow.aura()))
                * (1.0F + 0.2F * glow.flashScaled()) * fade;

        // Banda de desvanecido: los dos pases que suman luz (halo y GLSL) son dos
        // recorridos mas de los 977 cubos y a esa opacidad se ven como un pixel
        // borroso. Se saltan, y una reliquia lejana cuesta 2 pases en vez de 4.
        boolean fading = fade < 0.55F;

        if (haloEnabled() && !fading) {
            float i = RelicConfig.HALO_INTENSITY.get().floatValue() * amount;
            // Nucleo de luz fria por defecto, pero arrastrado a medias hacia el
            // color del estado: cargada se ve ambarienta, alerta rojiza.
            renderExtra(model, poseStack, animatable, bufferSource, partialTick, packedLight,
                    RelicRenderTypes.ADDITIVE_GLOW.apply(RelicGeoModel.glowTexture()),
                    tint(0.55F, glow.red()) * i, tint(0.78F, glow.green()) * i,
                    tint(1.00F, glow.blue()) * i, 1.0F);
            drawnPasses++;
        }

        // Cuarto pase opcional con GLSL propio: fresnel en el borde y linea de
        // barrido. Se salta solo si hay shaderpack (el pack sustituiria el
        // programa) o si el shader no compilo.
        ShaderInstance glowShader = RelicShaders.ready() ? RelicShaders.shader() : null;
        if (glowShader != null && !fading) {
            glowShader.safeGetUniform("HoloTime").set(RelicShaders.timeSeconds(partialTick));
            // Glitch del shader: se abre con el destello del evento (el glitch de
            // reposo, un pulso, un golpe) y se cierra solo. Es un uniform, asi que
            // una sola rama para todo el dibujo: sin eventos no cuesta muestras.
            glowShader.safeGetUniform("HoloGlitch")
                    .set(Math.min(1.0F, glow.flashScaled() * 1.5F));
            // Brillo del borde por estado de brillo: en la oscuridad sube, bajo la
            // lluvia baja. Es lo que hace que el contorno cambie con la escena.
            float gain = switch (animatable.mood()) {
                case DARK -> 1.08F;
                case STORM -> 1.05F;
                case RAIN -> 0.62F;
                case WOUNDED -> 0.92F;
                case RESONANT -> 0.88F;
                case NEUTRAL -> 1.0F;
            };
            glowShader.safeGetUniform("HoloTint").set(gain, gain, gain, 1.0F);
            float i = RelicConfig.SHADER_INTENSITY.get().floatValue() * amount;
            renderExtra(model, poseStack, animatable, bufferSource, partialTick, packedLight,
                    RelicRenderTypes.GLOW_SHADER.apply(RelicGeoModel.glowTexture()),
                    tint(0.65F, glow.red()) * i, tint(0.85F, glow.green()) * i,
                    tint(1.00F, glow.blue()) * i, 1.0F);
            drawnPasses++;
        }

        // Se anota al final, con lo que de verdad se dibujo: si el halo o el GLSL
        // estaban apagados (o el portador estaba en la banda de desvanecido), no
        // cuentan como pase.
        RelicRenderStats.model(System.nanoTime() - began, drawnPasses);
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

    /**
     * Pase adicional sobre los huesos ya posados ({@code isReRender=true}): no
     * vuelve a evaluar animaciones. El tinte se pasa explicito porque en este
     * camino GeckoLib no consulta {@link #getRenderColor}.
     */
    private void renderExtra(BakedGeoModel model, PoseStack poseStack, RelicAnimatable animatable,
                             MultiBufferSource bufferSource, float partialTick, int packedLight,
                             RenderType renderType, float red, float green, float blue, float alpha) {
        // defaultRender limpia this.animatable al terminar (doPostRenderCleanup).
        this.animatable = animatable;
        reRender(model, poseStack, bufferSource, animatable, renderType,
                bufferSource.getBuffer(renderType), partialTick, packedLight,
                OverlayTexture.NO_OVERLAY, red, green, blue, alpha);
    }

    /** Tinte del pase base, que es el unico que lee {@link #getRenderColor}. */
    private void setTint(float red, float green, float blue, float alpha) {
        tintRed = red;
        tintGreen = green;
        tintBlue = blue;
        tintAlpha = alpha;
    }

    /** Color empaquetado del ultimo frame y el objeto que se devolvio entonces. */
    private int cachedArgb;
    private Color cachedColor;

    /**
     * Igual que {@code Color.ofRGBA(float,float,float,float)} de GeckoLib 4.8.1:
     * {@code (int) (v * 255 + 0.5)} y mascara de 8 bits por canal. Se replica en
     * vez de llamarlo porque esa version crea un {@code Color} nuevo en cada
     * llamada, y esto se llama una vez por portador y frame.
     */
    private static int channel255(float value) {
        return ((int) (value * 255.0F + 0.5F)) & 0xFF;
    }

    /**
     * GeckoLib pasa este color como color de vertice de cada cubo, asi que sirve
     * para atenuar el pase aditivo sin tocar estado global de OpenGL (un
     * {@code RenderSystem.setShaderColor} afectaria a todo lo que se dibuje
     * despues).
     */
    @Override
    public Color getRenderColor(RelicAnimatable animatable, float partialTick, int packedLight) {
        // El pase base siempre va en blanco, asi que en regimen estable esto no
        // crea nada: se reutiliza el mismo Color mientras el empaquetado no cambie.
        int argb = (channel255(tintAlpha) << 24) | (channel255(tintRed) << 16)
                | (channel255(tintGreen) << 8) | channel255(tintBlue);
        if (cachedColor == null || argb != cachedArgb) {
            cachedArgb = argb;
            cachedColor = new Color(argb);
        }
        return cachedColor;
    }

    @Override
    public int getPackedOverlay(RelicAnimatable animatable, float u, float partialTick) {
        return OverlayTexture.NO_OVERLAY;
    }
}
