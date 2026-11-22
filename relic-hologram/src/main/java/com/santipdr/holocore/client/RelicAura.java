package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import org.joml.Matrix4f;

/**
 * Aura y anillo de la reliquia: billboards aditivos que miran a camara.
 *
 * <p>Esto es el "bloom propio" que se puede hacer sin post-proceso: no se
 * desenfoca la pantalla, se <b>suma</b> una textura radial sobre lo ya dibujado,
 * que es exactamente como se ve un resplandor. Como es geometria normal, no
 * depende de shaders ni de que el jugador tenga un shaderpack, y se dibuja con
 * {@link RelicRenderTypes#ADDITIVE_GLOW}.</p>
 *
 * <p>El color y la intensidad salen del estado de la reliquia
 * ({@link RelicAnimatable#loopState()}), de modo que el aura sirve tambien para
 * saber que esta pasando sin mirar el modelo: azul en reposo, ambar cargada, rojo
 * en alerta y apagada en dormido. El anillo solo aparece en los estados que
 * importan, y gira en sentidos distintos segun cual sea.</p>
 *
 * <p>Los valores no se usan en crudo: {@link RelicGlowState} los interpola, asi
 * que un cambio de estado se ve como una transicion y no como un salto de color
 * en un frame.</p>
 *
 * <p>La posicion se toma de la traslacion de la matriz del {@code PoseStack} y la
 * escala de su primera columna; en el render de entidades el {@code PoseStack}
 * esta en coordenadas de mundo, asi que los vertices se emiten sin matriz.</p>
 */
public final class RelicAura {

    private static final ResourceLocation AURA_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_aura.png");
    private static final ResourceLocation RING_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_ring.png");

    /**
     * Diametro de cada capa del aura, en bloques (antes de la escala de la
     * config). El nucleo mide ~0.7 bloques: el aura solo tiene que rodearlo, no
     * cubrir la pantalla. Hasta 1.0.10 eran {1.05, 1.55, 2.10} y el resultado
     * era una nube blanca mas grande que el propio jugador.
     */
    private static final float[] DIAMETER = {0.62F, 0.85F, 1.10F};
    /** Cuanto aporta cada capa (0 = nada). La suma es lo que se ve sobre el fondo. */
    private static final float[] WEIGHT = {0.30F, 0.17F, 0.09F};
    /** Velocidad de giro de cada capa, en radianes por tick. Negativa = al reves. */
    private static final float[] SPIN = {0.035F, -0.022F, 0.010F};
    /**
     * Diametro del anillo de estado: por fuera del aura (1.10) con margen
     * suficiente para leerse como anillo y no como el borde del resplandor.
     */
    private static final float RING_DIAMETER = 1.35F;
    /**
     * Alpha de los quads del aura. Con blend aditivo el color final es
     * {@code rgb * alpha}, asi que esto es el mando global de cuanto suma el
     * aura: con 0.55 y los pesos de arriba el aporte maximo queda en ~0.31
     * (intensidad 1.0) en vez del 0.47 de 1.0.10, y sobre un fondo claro ya no
     * satura los tres canales.
     */
    private static final float AURA_ALPHA = 0.55F;
    /**
     * Cuanto mas cubre el pase de tinte que el aditivo.
     *
     * <p>Elegido con numeros, no a ojo: {@code tools/check_aura_math.py} compone
     * las dos pasadas sobre nieve, piedra y cueva. Con 1.6 sobre los mismos pesos,
     * sobre nieve el halo queda en (0.80, 0.94, 1.00) frente al fondo
     * (0.93, 0.95, 0.97): el tono cian sube +0.20 y la luminancia solo baja 0.03,
     * o sea que se tine sin parecer una sombra. Mas cobertura oscurece de mas;
     * menos, y el color se pierde.</p>
     */
    private static final float TINT_ALPHA_BOOST = 1.6F;

    /** Chispas en orbita alrededor del nucleo. */
    private static final int SPARK_COUNT = 5;
    private static final float SPARK_RADIUS = 0.42F;
    private static final float SPARK_SIZE = 0.075F;
    private static final float SPARK_SPEED = 0.75F;
    private static final float TWO_PI = 6.2831855F;

    private RelicAura() {
    }

    /** Solo se apaga si el jugador apaga las dos cosas: son cuatro quads en total. */
    static boolean enabled() {
        return RelicConfig.GLOW_AURA.get() || RelicConfig.GLOW_RING.get();
    }

    static void render(PoseStack poseStack, MultiBufferSource bufferSource, float partialTick,
                       RelicAnimatable.LoopState state, RelicGlowState glow, float fade,
                       RelicAnimatable.Mood mood) {
        float time = time(partialTick);
        Frame frame = frame(poseStack);
        // Destello de evento: el anillo se enciende aunque el estado no lo tenga,
        // asi un pulso o un golpe se nota tambien en calma o dormida.
        float flash = glow.flashScaled();

        if (RelicConfig.GLOW_AURA.get()) {
            drawAura(bufferSource, frame, time, glow, flash, fade);
        }
        if (RelicConfig.GLOW_RING.get() && glow.ring() + flash * 0.8F > 0.01F) {
            drawRing(bufferSource, frame, time, state, glow, flash, fade);
        }
        if (RelicConfig.GLOW_AURA.get() && sparksEnabled()) {
            drawSparks(bufferSource, frame, time, glow, fade,
                    RelicAnimatable.forcedMood() == RelicAnimatable.Mood.STORM
                            || RelicAnimatable.Mood.STORM == mood);
        }
    }

    // ------------------------------------------------------------------
    // Aura: tres capas girando a distinta velocidad
    // ------------------------------------------------------------------

    private static void drawAura(MultiBufferSource bufferSource, Frame frame, float time,
                                 RelicGlowState glow, float flash, float fade) {
        float intensity = RelicConfig.AURA_INTENSITY.get().floatValue() * glow.aura()
                * (1.0F + 0.35F * flash) * fade;
        // El destello abre el aura muy poco: el fogonazo lo da el anillo, que es
        // una linea y no una mancha.
        float spread = 1.0F + 0.10F * flash;
        if (intensity <= 0.001F) {
            return;
        }

        // 1) Tinte: mezcla normal con el color del estado tal cual. Es el unico
        //    pase que se ve de color sobre nieve/arena, porque mezclar hacia un
        //    cian claro quita rojo y verde sin apagar el azul (no oscurece: tine).
        //    Sobre fondo oscuro casi no se nota y manda el aditivo de abajo.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE));
            for (int layer = 0; layer < DIAMETER.length; layer++) {
                float coverage = Math.min(1.0F,
                        WEIGHT[layer] * pulseAt(time, layer) * intensity * TINT_ALPHA_BOOST);
                billboard(tint, frame, DIAMETER[layer] * spread, time * SPIN[layer],
                        glow.red(), glow.green(), glow.blue(), coverage);
            }
        }

        // 2) Aditivo: el brillo.
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        for (int layer = 0; layer < DIAMETER.length; layer++) {
            float weight = WEIGHT[layer] * pulseAt(time, layer) * intensity;
            billboard(buffer, frame, DIAMETER[layer] * spread, time * SPIN[layer],
                    glow.red() * weight, glow.green() * weight, glow.blue() * weight, AURA_ALPHA);
        }
    }

    // ------------------------------------------------------------------
    // Anillo: uno solo, girando segun el estado
    // ------------------------------------------------------------------

    private static void drawRing(MultiBufferSource bufferSource, Frame frame, float time,
                                 RelicAnimatable.LoopState state, RelicGlowState glow, float flash,
                                 float fade) {
        float weight = RelicConfig.RING_INTENSITY.get().floatValue()
                * (glow.ring() + 0.7F * flash) * fade;
        if (weight <= 0.001F) {
            return;
        }

        // En alerta el anillo late como un aviso; en los demas estados, respira.
        boolean alert = state == RelicAnimatable.LoopState.ALERT;
        float beatSpeed = alert ? 0.45F : 0.15F;
        float beat = 0.72F + 0.28F * (0.5F + 0.5F * sin(time * beatSpeed));
        float size = RING_DIAMETER * (1.0F + 0.25F * flash)
                * (alert ? 1.0F + 0.03F * sin(time * beatSpeed) : 1.0F);
        float amount = weight * beat;

        float angle = time * glow.spin();

        // El anillo tambien lleva tinte: sobre nieve el aditivo lo dejaba en
        // blanco y se perdia. El tinte lo mantiene del color del estado.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(RING_TEXTURE));
            float coverage = Math.min(1.0F, amount * 0.9F);
            billboard(tint, frame, size, angle,
                    glow.red(), glow.green(), glow.blue(), coverage);
        }

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
        billboard(buffer, frame, size, angle,
                glow.red() * amount, glow.green() * amount, glow.blue() * amount, 1.0F);

        // Eco del anillo en los eventos (pulso, golpe, liberacion, cambio de
        // estado): un anillo mas grande que se abre y se apaga con el destello.
        // Es lo que convierte un fogonazo en una onda. Un quad, mismo lote.
        if (flash > 0.05F) {
            float echoSize = RING_DIAMETER * (1.0F + 2.4F * flash);
            float echo = weight * flash * 0.55F;
            billboard(buffer, frame, echoSize, -angle * 0.6F,
                    glow.red() * echo, glow.green() * echo, glow.blue() * echo, 1.0F);
        }
    }

    /**
     * Chispas en orbita: cinco quads aditivos del mismo tipo que el aura, o sea
     * que suman al lote que ya esta abierto. Giran en el plano de la camara, con
     * radio y altura distintos por chispa para que no se lean como un anillo
     * plano, y el giro hereda el del estado ({@code glow.spin()}): en alerta van
     * al reves que en calma.
     */
    private static void drawSparks(MultiBufferSource bufferSource, Frame frame, float time,
                                   RelicGlowState glow, float fade, boolean storm) {
        float amount = fade * (0.55F + 0.45F * glow.aura()) * (1.0F + 0.6F * glow.flashScaled());
        if (amount <= 0.01F) {
            return;
        }
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        float orbit = time * SPARK_SPEED * (1.0F + 6.0F * Math.abs(glow.spin()));
        // Con tormenta las chispas tiran a azul electrico: el color del estado es
        // casi blanco y sin esto se perderia el "hay truenos" en el aura.
        float redTint = glow.red();
        float greenTint = glow.green();
        float blueTint = glow.blue();
        if (storm) {
            redTint = redTint * 0.55F + 0.35F * 0.45F;
            greenTint = greenTint * 0.55F + 0.85F * 0.45F;
            blueTint = blueTint * 0.55F + 1.00F * 0.45F;
        }
        for (int i = 0; i < SPARK_COUNT; i++) {
            float phase = orbit + i * (TWO_PI / SPARK_COUNT);
            float radius = SPARK_RADIUS * (0.72F + 0.28F * sin(phase * 2.0F + i));
            float lift = sin(phase * 3.0F + i * 1.7F) * 0.16F;
            float offset = cos(phase) * radius;
            float height = sin(phase) * radius * 0.8F + lift;
            float cx = frame.originX + frame.leftX * offset + frame.upX * height;
            float cy = frame.originY + frame.leftY * offset + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * offset + frame.upZ * height;
            float weight = amount * (0.35F + 0.25F * sin(phase * 4.0F + i));
            billboardAt(buffer, frame, cx, cy, cz, SPARK_SIZE,
                    phase * 2.0F, redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
        }
    }

    /** Las chispas se saltan en LITE y con los efectos reducidos, como el halo. */
    private static boolean sparksEnabled() {
        return RelicConfig.QUALITY.get() == RelicConfig.Quality.FULL
                && !RelicConfig.REDUCED_EFFECTS.get();
    }

    /** Latido lento de cada capa del aura: 0.82 .. 1.0, desfasado entre capas. */
    private static float pulseAt(float time, int layer) {
        return 0.82F + 0.18F * sin(time * 0.08F + layer * 1.7F);
    }

    // ------------------------------------------------------------------
    // Geometria
    // ------------------------------------------------------------------

    /**
     * Origen, escala y ejes de camara de este frame.
     *
     * <p>Es una instancia <b>reutilizada</b>, no un {@code record}: el render corre
     * en el hilo de render, un portador detras de otro, asi que no hay dos frames
     * a la vez. Antes cada frame creaba un {@code record} y, por cada billboard,
     * cuatro {@code Vector3f} para girar los ejes: del orden de 35 objetos por
     * portador y frame, que a 240 FPS y diez reliquias en pantalla son ~88 000
     * objetos por segundo solo de basura para el recolector.</p>
     */
    private static final class Frame {
        private float originX;
        private float originY;
        private float originZ;
        private float scale;
        private float leftX;
        private float leftY;
        private float leftZ;
        private float upX;
        private float upY;
        private float upZ;
    }

    /** Unico frame vivo: se rellena en {@link #frame} y se lee en {@link #billboard}. */
    private static final Frame FRAME = new Frame();

    private static Frame frame(PoseStack poseStack) {
        Matrix4f matrix = poseStack.last().pose();
        Frame frame = FRAME;
        frame.originX = matrix.m30();
        frame.originY = matrix.m31();
        frame.originZ = matrix.m32();
        // Escala uniforme aproximada: longitud de la primera columna.
        float scale = (float) Math.sqrt(
                matrix.m00() * matrix.m00() + matrix.m01() * matrix.m01() + matrix.m02() * matrix.m02());
        frame.scale = (scale > 0.0F) && !Float.isNaN(scale) ? scale : 1.0F;

        // Ejes de la camara tal cual: se leen sus componentes en el acto, sin
        // copiarlos a ningun vector propio.
        Camera camera = Minecraft.getInstance().gameRenderer.getMainCamera();
        frame.leftX = camera.getLeftVector().x();
        frame.leftY = camera.getLeftVector().y();
        frame.leftZ = camera.getLeftVector().z();
        frame.upX = camera.getUpVector().x();
        frame.upY = camera.getUpVector().y();
        frame.upZ = camera.getUpVector().z();
        return frame;
    }

    /**
     * Emite un quad que mira a camara, centrado en el origen del frame y girado
     * {@code angle} radianes alrededor del eje de vision.
     */
    private static void billboard(VertexConsumer buffer, Frame frame, float diameter, float angle,
                                  float red, float green, float blue, float alpha) {
        billboardAt(buffer, frame, frame.originX, frame.originY, frame.originZ,
                diameter, angle, red, green, blue, alpha);
    }

    /** Igual que {@link #billboard} pero centrado en un punto cualquiera. */
    private static void billboardAt(VertexConsumer buffer, Frame frame, float centerX, float centerY,
                                    float centerZ, float diameter, float angle,
                                    float red, float green, float blue, float alpha) {
        float cos = (float) Math.cos(angle);
        float sin = (float) Math.sin(angle);

        // Ejes del quad girados alrededor del eje de vision: una combinacion
        // lineal de los ejes de la camara, sin asignar nada.
        float axX = frame.leftX * cos + frame.upX * sin;
        float axY = frame.leftY * cos + frame.upY * sin;
        float axZ = frame.leftZ * cos + frame.upZ * sin;
        float ayX = frame.upX * cos - frame.leftX * sin;
        float ayY = frame.upY * cos - frame.leftY * sin;
        float ayZ = frame.upZ * cos - frame.leftZ * sin;

        float half = diameter * 0.5F * frame.scale;
        float x = half * axX;
        float y = half * axY;
        float z = half * axZ;
        float ux = half * ayX;
        float uy = half * ayY;
        float uz = half * ayZ;

        float ox = centerX;
        float oy = centerY;
        float oz = centerZ;

        quad(buffer,
                ox - x - ux, oy - y - uy, oz - z - uz,
                ox - x + ux, oy - y + uy, oz - z + uz,
                ox + x + ux, oy + y + uy, oz + z + uz,
                ox + x - ux, oy + y - uy, oz + z - uz,
                red, green, blue, alpha);
    }

    private static void quad(VertexConsumer buffer,
                             float x0, float y0, float z0,
                             float x1, float y1, float z1,
                             float x2, float y2, float z2,
                             float x3, float y3, float z3,
                             float red, float green, float blue, float alpha) {
        vertex(buffer, x0, y0, z0, 0.0F, 0.0F, red, green, blue, alpha);
        vertex(buffer, x1, y1, z1, 0.0F, 1.0F, red, green, blue, alpha);
        vertex(buffer, x2, y2, z2, 1.0F, 1.0F, red, green, blue, alpha);
        vertex(buffer, x3, y3, z3, 1.0F, 0.0F, red, green, blue, alpha);
    }

    /**
     * El RenderType aditivo usa el mismo formato de vertice que las entidades
     * ({@code NEW_ENTITY}), asi que hay que rellenar color, UV, overlay,
     * lightmap y normal en ese orden aunque aqui solo usemos la UV. En 1.20.1 el
     * metodo del overlay se llama {@code overlayCoords}, no {@code overlay}.
     */
    private static void vertex(VertexConsumer buffer, float x, float y, float z,
                               float u, float v, float red, float green, float blue, float alpha) {
        buffer.vertex(x, y, z)
                .color(red, green, blue, alpha)
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT)
                .normal(0.0F, 1.0F, 0.0F)
                .endVertex();
    }

    /**
     * Movimiento propio del objeto, aplicado al {@code PoseStack} <b>antes</b> del
     * modelo y del aura: los dos lean la matriz, asi que se mueven juntos.
     *
     * <p>Hasta 1.0.30 la reliquia estaba clavada al hombro: la animacion movia
     * huesos, pero el conjunto no respiraba. Aqui hay dos cosas:</p>
     * <ul>
     *   <li><b>flotar</b>: 0.022 bloques de vaiven lento, con la amplitud segun el
     *       estado de brillo (tormenta 1.5x, herido 0.6x);</li>
     *   <li><b>asentarse</b>: en un evento el conjunto se achata un 4% y se ensancha
     *       un 5%, que es lo que da sensacion de golpe frente a solo cambiar de
     *       color.</li>
     * </ul>
     *
     * <p>{@code yDown} existe porque el render de la entidad hereda la convencion
     * del modelo del jugador (Y+ hacia abajo) y la vista previa esta en
     * coordenadas de mundo (Y+ hacia arriba): el vaiven tiene que ir al reves.</p>
     */
    static void applyAliveMotion(PoseStack poseStack, float partialTick, float flash,
                                 RelicAnimatable.Mood mood, boolean yDown) {
        float time = time(partialTick);
        float energy = switch (mood) {
            case STORM -> 1.5F;
            case RESONANT -> 1.2F;
            case DARK -> 0.9F;
            case RAIN -> 0.8F;
            case WOUNDED -> 0.6F;
            case NEUTRAL -> 1.0F;
        };
        float lift = 0.022F * energy * sin(time * 1.7F);
        poseStack.translate(0.0D, yDown ? -lift : lift, 0.0D);
        // Un grado escaso de ladeo, desfasado del vaiven: si no, parece un pez.
        // Se rota la matriz en el sitio: pasar un eje a mulPose crea un Quaternionf
        // por reliquia y frame, y el camino de render no asigna nada.
        poseStack.last().pose().rotateY((float) Math.toRadians(1.1F * sin(time * 0.7F)));
        if (flash > 0.01F) {
            float squeeze = Math.min(1.0F, flash);
            poseStack.scale(1.0F + 0.05F * squeeze, 1.0F - 0.04F * squeeze, 1.0F + 0.05F * squeeze);
        }
    }

    private static float sin(float value) {
        return (float) Math.sin(value);
    }

    private static float cos(float value) {
        return (float) Math.cos(value);
    }

    private static float time(float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        return (minecraft.level == null ? 0.0F : minecraft.level.getGameTime()) + partialTick;
    }
}
