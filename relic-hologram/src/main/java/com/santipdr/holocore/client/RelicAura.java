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
 * <p>La posicion se toma de la traslacion de la matriz del {@code PoseStack} y la
 * escala de su primera columna; en el render de entidades el {@code PoseStack}
 * esta en coordenadas de mundo, asi que los vertices se emiten sin matriz.</p>
 */
public final class RelicAura {

    private static final ResourceLocation AURA_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_aura.png");
    private static final ResourceLocation RING_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_ring.png");

    /** Diametro de cada capa del aura, en bloques (antes de la escala de la config). */
    private static final float[] DIAMETER = {1.05F, 1.55F, 2.10F};
    /** Cuanto aporta cada capa (0 = nada). */
    private static final float[] WEIGHT = {0.55F, 0.32F, 0.18F};
    /** Velocidad de giro de cada capa, en radianes por tick. Negativa = al reves. */
    private static final float[] SPIN = {0.035F, -0.022F, 0.010F};
    /** Diametro del anillo de estado. */
    private static final float RING_DIAMETER = 2.05F;

    private RelicAura() {
    }

    /**
     * Aspecto por estado: color, fuerza del aura, fuerza del anillo y giro de
     * este (radianes por tick; 0 = no se dibuja).
     */
    private record Style(float red, float green, float blue, float aura, float ring, float spin) {
    }

    private static Style styleFor(RelicAnimatable.LoopState state) {
        return switch (state) {
            case CALM -> new Style(0.42F, 0.60F, 0.78F, 0.70F, 0.00F, 0.000F);
            case CHARGED -> new Style(1.00F, 0.72F, 0.30F, 1.15F, 1.10F, 0.075F);
            case ALERT -> new Style(1.00F, 0.34F, 0.28F, 1.05F, 0.85F, -0.055F);
            case DORMANT -> new Style(0.34F, 0.44F, 0.60F, 0.35F, 0.00F, 0.000F);
            case IDLE -> new Style(0.55F, 0.78F, 1.00F, 1.00F, 0.45F, 0.028F);
        };
    }

    /** Solo se apaga si el jugador apaga las dos cosas: son cuatro quads en total. */
    public static boolean enabled() {
        return RelicConfig.GLOW_AURA.get() || RelicConfig.GLOW_RING.get();
    }

    public static void render(PoseStack poseStack, MultiBufferSource bufferSource, float partialTick,
                              RelicAnimatable.LoopState state) {
        Style style = styleFor(state);
        float time = time(partialTick);
        Frame frame = frame(poseStack);

        if (RelicConfig.GLOW_AURA.get()) {
            drawAura(bufferSource, frame, time, style);
        }
        if (RelicConfig.GLOW_RING.get() && style.ring() > 0.0F) {
            drawRing(bufferSource, frame, time, state, style);
        }
    }

    // ------------------------------------------------------------------
    // Aura: tres capas girando a distinta velocidad
    // ------------------------------------------------------------------

    private static void drawAura(MultiBufferSource bufferSource, Frame frame, float time, Style style) {
        float intensity = RelicConfig.AURA_INTENSITY.get().floatValue() * style.aura();
        if (intensity <= 0.001F) {
            return;
        }

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));

        for (int layer = 0; layer < DIAMETER.length; layer++) {
            // Latido lento: 0.82 .. 1.0, desfasado entre capas.
            float pulse = 0.82F + 0.18F * sin(time * 0.08F + layer * 1.7F);
            float weight = WEIGHT[layer] * pulse * intensity;
            billboard(buffer, frame, DIAMETER[layer], time * SPIN[layer],
                    style.red() * weight, style.green() * weight, style.blue() * weight);
        }
    }

    // ------------------------------------------------------------------
    // Anillo: uno solo, girando segun el estado
    // ------------------------------------------------------------------

    private static void drawRing(MultiBufferSource bufferSource, Frame frame, float time,
                                 RelicAnimatable.LoopState state, Style style) {
        float weight = RelicConfig.RING_INTENSITY.get().floatValue() * style.ring();
        if (weight <= 0.001F) {
            return;
        }

        // En alerta el anillo late como un aviso; en los demas estados, respira.
        boolean alert = state == RelicAnimatable.LoopState.ALERT;
        float beatSpeed = alert ? 0.45F : 0.15F;
        float beat = 0.72F + 0.28F * (0.5F + 0.5F * sin(time * beatSpeed));
        float size = RING_DIAMETER * (alert ? 1.0F + 0.03F * sin(time * beatSpeed) : 1.0F);
        float glow = weight * beat;

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
        billboard(buffer, frame, size, time * style.spin(),
                style.red() * glow, style.green() * glow, style.blue() * glow);
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
                                  float red, float green, float blue) {
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
                red, green, blue);
    }

    private static void quad(VertexConsumer buffer,
                             float x0, float y0, float z0,
                             float x1, float y1, float z1,
                             float x2, float y2, float z2,
                             float x3, float y3, float z3,
                             float red, float green, float blue) {
        vertex(buffer, x0, y0, z0, 0.0F, 0.0F, red, green, blue);
        vertex(buffer, x1, y1, z1, 0.0F, 1.0F, red, green, blue);
        vertex(buffer, x2, y2, z2, 1.0F, 1.0F, red, green, blue);
        vertex(buffer, x3, y3, z3, 1.0F, 0.0F, red, green, blue);
    }

    /**
     * El RenderType aditivo usa el mismo formato de vertice que las entidades
     * ({@code NEW_ENTITY}), asi que hay que rellenar color, UV, overlay,
     * lightmap y normal en ese orden aunque aqui solo usemos la UV. En 1.20.1 el
     * metodo del overlay se llama {@code overlayCoords}, no {@code overlay}.
     */
    private static void vertex(VertexConsumer buffer, float x, float y, float z,
                               float u, float v, float red, float green, float blue) {
        buffer.vertex(x, y, z)
                .color(red, green, blue, 1.0F)
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
