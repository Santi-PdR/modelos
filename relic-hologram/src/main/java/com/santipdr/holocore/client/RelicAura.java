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
 * Aura de la reliquia: tres quads que miran a camara y suman luz.
 *
 * <p>Esto es el "bloom propio" que se puede hacer sin post-proceso: no se
 * desenfoca la pantalla, se <b>suma</b> una textura radial sobre lo ya dibujado,
 * que es exactamente como se ve un resplandor. Como es geometria normal, no
 * depende de shaders ni de que el jugador tenga un shaderpack, y se dibuja con
 * {@link RelicRenderTypes#ADDITIVE_GLOW}.</p>
 *
 * <p>Los tres quads giran a distinta velocidad y en distinto sentido (el central
 * al reves) para que la textura, que lleva tres arcos, parezca orbitar. Al ser
 * billboards se ven siempre de frente: no hay que tocar el modelo ni sus
 * animaciones.</p>
 *
 * <p>El tamano se toma de la matriz del {@code PoseStack} (que ya incluye la
 * escala de la config), y la posicion, de su traslacion: en el render de
 * entidades el {@code PoseStack} esta en coordenadas de mundo, asi que los
 * vertices se emiten directamente sin matriz.</p>
 */
public final class RelicAura {

    private static final ResourceLocation TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_aura.png");

    /** Diametro de cada quad en bloques (antes de la escala de la config). */
    private static final float[] DIAMETER = {1.05F, 1.55F, 2.10F};
    /** Cuanto aporta cada capa (0 = nada). */
    private static final float[] WEIGHT = {0.55F, 0.32F, 0.18F};
    /** Velocidad de giro, en radianes por tick. Negativa = al reves. */
    private static final float[] SPIN = {0.035F, -0.022F, 0.010F};

    private RelicAura() {
    }

    /**
     * Solo se apaga desde la config: son tres quads, no compensa quitarlo en
     * calidad LITE (el halo aditivo del modelo, que si cuesta, es otra cosa).
     */
    public static boolean enabled() {
        return RelicConfig.GLOW_AURA.get();
    }

    public static void render(PoseStack poseStack, MultiBufferSource bufferSource,
                              float partialTick, float intensity) {
        if (intensity <= 0.001F) {
            return;
        }

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

        Minecraft minecraft = Minecraft.getInstance();
        Camera camera = minecraft.gameRenderer.getMainCamera();
        Vector3f left = new Vector3f(camera.getLeftVector());
        Vector3f up = new Vector3f(camera.getUpVector());

        float time = minecraft.level == null ? 0.0F : minecraft.level.getGameTime() + partialTick;

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(TEXTURE));

        for (int layer = 0; layer < DIAMETER.length; layer++) {
            float angle = time * SPIN[layer];
            float cos = (float) Math.cos(angle);
            float sin = (float) Math.sin(angle);

            // Ejes del quad girados alrededor del eje de vision.
            Vector3f axisX = new Vector3f(left).mul(cos).add(new Vector3f(up).mul(sin));
            Vector3f axisY = new Vector3f(up).mul(cos).sub(new Vector3f(left).mul(sin));

            float half = DIAMETER[layer] * 0.5F * scale;

            // Latido lento: 0.82 .. 1.0, desfasado entre capas.
            float pulse = 0.82F + 0.18F * (float) Math.sin(time * 0.08F + layer * 1.7F);
            float weight = WEIGHT[layer] * pulse * intensity;
            // Azul frio, como el nucleo.
            float red = 0.55F * weight;
            float green = 0.78F * weight;
            float blue = 1.00F * weight;

            float x = half * axisX.x();
            float y = half * axisX.y();
            float z = half * axisX.z();
            float ux = half * axisY.x();
            float uy = half * axisY.y();
            float uz = half * axisY.z();

            quad(buffer,
                    originX - x - ux, originY - y - uy, originZ - z - uz,
                    originX - x + ux, originY - y + uy, originZ - z + uz,
                    originX + x + ux, originY + y + uy, originZ + z + uz,
                    originX + x - ux, originY + y - uy, originZ + z - uz,
                    red, green, blue);
        }
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
}
