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
import org.joml.Vector3f;

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
     * Cuanto mas cubre el pase de tinte que el aditivo. El tinte tiene que
     * notarse sobre nieve (donde el aditivo no puede hacer nada) y a la vez no
     * parecer una mancha en una cueva: 2.2 sobre los mismos pesos deja un 20-30%
     * de cobertura en el centro.
     */
    private static final float TINT_ALPHA_BOOST = 2.2F;
    /** El tinte va con un color mas oscuro que el brillo, o no oscurece nada. */
    private static final float TINT_DARKEN = 0.55F;

    private RelicAura() {
    }

    /** Solo se apaga si el jugador apaga las dos cosas: son cuatro quads en total. */
    static boolean enabled() {
        return RelicConfig.GLOW_AURA.get() || RelicConfig.GLOW_RING.get();
    }

    static void render(PoseStack poseStack, MultiBufferSource bufferSource, float partialTick,
                       RelicAnimatable.LoopState state, RelicGlowState glow, float fade) {
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

        // 1) Tinte: mezcla normal con un color mas oscuro. Es el unico pase que
        //    se ve de color sobre nieve/arena; sobre fondo oscuro casi no se nota
        //    y el que manda es el aditivo de abajo.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE));
            for (int layer = 0; layer < DIAMETER.length; layer++) {
                float coverage = Math.min(1.0F,
                        WEIGHT[layer] * pulseAt(time, layer) * intensity * TINT_ALPHA_BOOST);
                billboard(tint, frame, DIAMETER[layer] * spread, time * SPIN[layer],
                        glow.red() * TINT_DARKEN, glow.green() * TINT_DARKEN,
                        glow.blue() * TINT_DARKEN, coverage);
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
                    glow.red() * TINT_DARKEN, glow.green() * TINT_DARKEN,
                    glow.blue() * TINT_DARKEN, coverage);
        }

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
        billboard(buffer, frame, size, angle,
                glow.red() * amount, glow.green() * amount, glow.blue() * amount, 1.0F);
    }

    /** Latido lento de cada capa del aura: 0.82 .. 1.0, desfasado entre capas. */
    private static float pulseAt(float time, int layer) {
        return 0.82F + 0.18F * sin(time * 0.08F + layer * 1.7F);
    }

    // ------------------------------------------------------------------
    // Geometria
    // ------------------------------------------------------------------

    /** Origen, escala y ejes de camara de este frame. */
    private record Frame(float originX, float originY, float originZ, float scale,
                         Vector3f left, Vector3f up) {
    }

    private static Frame frame(PoseStack poseStack) {
        Matrix4f matrix = poseStack.last().pose();
        float originX = matrix.m30();
        float originY = matrix.m31();
        float originZ = matrix.m32();
        // Escala uniforme aproximada: longitud de la primera columna.
        float scale = (float) Math.sqrt(
                matrix.m00() * matrix.m00() + matrix.m01() * matrix.m01() + matrix.m02() * matrix.m02());
        if (!(scale > 0.0F) || Float.isNaN(scale)) {
            scale = 1.0F;
        }

        Camera camera = Minecraft.getInstance().gameRenderer.getMainCamera();
        return new Frame(originX, originY, originZ, scale,
                new Vector3f(camera.getLeftVector()), new Vector3f(camera.getUpVector()));
    }

    /**
     * Emite un quad que mira a camara, centrado en el origen del frame y girado
     * {@code angle} radianes alrededor del eje de vision.
     */
    private static void billboard(VertexConsumer buffer, Frame frame, float diameter, float angle,
                                  float red, float green, float blue, float alpha) {
        float cos = (float) Math.cos(angle);
        float sin = (float) Math.sin(angle);

        // Ejes del quad girados alrededor del eje de vision.
        Vector3f axisX = new Vector3f(frame.left()).mul(cos).add(new Vector3f(frame.up()).mul(sin));
        Vector3f axisY = new Vector3f(frame.up()).mul(cos).sub(new Vector3f(frame.left()).mul(sin));

        float half = diameter * 0.5F * frame.scale();
        float x = half * axisX.x();
        float y = half * axisX.y();
        float z = half * axisX.z();
        float ux = half * axisY.x();
        float uy = half * axisY.y();
        float uz = half * axisY.z();

        float ox = frame.originX();
        float oy = frame.originY();
        float oz = frame.originZ();

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

    private static float sin(float value) {
        return (float) Math.sin(value);
    }

    private static float time(float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        return (minecraft.level == null ? 0.0F : minecraft.level.getGameTime()) + partialTick;
    }
}
