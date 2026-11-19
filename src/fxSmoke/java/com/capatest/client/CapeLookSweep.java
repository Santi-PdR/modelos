package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Measures the live model matrix in F5; no test poses or code enter the JAR. */
final class CapeLookSweep {
    private static final int LEG = 16, LAST = 4 * LEG;
    private final float[] depth = new float[LAST + 1];
    private final StringBuilder trace = new StringBuilder("frame\tpitch\tyaw\tseating\tdepth_scale\n");
    private int frame;

    record Pose(float pitch, float yaw) {}
    record Draw(float depth, boolean passesAgree) {}

    Pose pose() {
        // Lift and lower the head, then turn and return. The torso stays put;
        // set the matching camera and vanilla head pose in CapeFxSmoke.
        if (frame <= 2 * LEG) {
            float t = 1 - Math.abs(frame - LEG) / (float) LEG;
            return new Pose(80 - 34 * t, 3);
        }
        float t = 1 - Math.abs(frame - 3 * LEG) / (float) LEG;
        return new Pose(80, 3 + 50 * t);
    }

    boolean capture(Minecraft game, Path root, String name, double seating, Draw draw) throws IOException {
        require(draw != null && draw.passesAgree(), name + ": opaque/emissive seat matrices differ");
        float scale = draw.depth();
        require(Math.abs(scale - CapeFit.seatDepthScale(seating)) < .001,
                name + ": seat depth not applied to live model: " + scale + " at frame " + frame);
        depth[frame] = scale;
        Pose p = pose();
        trace.append(frame).append('\t').append(p.pitch()).append('\t').append(p.yaw())
                .append('\t').append(seating).append('\t').append(scale).append('\n');
        if (frame % (LEG / 2) == 0) {
            try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                image.writeToFile(root.resolve(String.format(Locale.ROOT, "%s-%02d.png", name, frame)));
            }
        }
        if (frame < LAST) {
            frame++;
            return false;
        }
        Files.writeString(root.resolve(name + ".tsv"), trace);
        for (int i : new int[]{0, 2 * LEG, LAST})
            require(depth[i] < .58F, name + ": mount did not close again at " + i);
        for (int i : new int[]{LEG, 3 * LEG})
            require(depth[i] > .98F, name + ": mount did not open at " + i);
        for (int i : new int[]{LEG / 2, 5 * LEG / 2})
            require(depth[i] > .63F && depth[i] < .88F, name + ": missing partial fit at " + i);
        for (int i = 1; i <= LAST; i++) {
            float step = depth[i] - depth[i - 1];
            boolean opening = ((i - 1) / LEG) % 2 == 0;
            require(Math.abs(step) < .081F && (opening ? step >= -.018F : step <= .018F),
                    name + ": unexpected depth jump/reversal at " + i + ": " + step);
        }
        return true;
    }

    String summary() {
        float jump = 0;
        for (int i = 1; i <= LAST; i++) jump = Math.max(jump, Math.abs(depth[i] - depth[i - 1]));
        return String.format(Locale.ROOT,
                "%d fotogramas; profundidad %.1f%% → %.1f%% → %.1f%%; paso máximo %.1f pp; sólido y brillo alineados",
                LAST + 1, 100 * depth[0], 100 * depth[LEG], 100 * depth[LAST], 100 * jump);
    }

    private static void require(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }

    static final class Probe extends GeoRenderLayer<CapaDeteriorerItem> {
        private Matrix4f opaque;
        private boolean armed;

        private Probe(CapaArmorRenderer renderer) { super(renderer); }

        static void arm(CapaArmorRenderer renderer) {
            Probe probe = renderer.getRenderLayers().stream().filter(Probe.class::isInstance)
                    .map(Probe.class::cast).findFirst().orElseGet(() -> {
                        Probe p = new Probe(renderer);
                        renderer.addRenderLayer(p);
                        return p;
                    });
            probe.opaque = null;
            probe.armed = true;
            seat(renderer).setTrackingMatrices(true);
        }

        // GeckoLib only calls per-bone layers during the original draw.
        @Override
        public void renderForBone(PoseStack poseStack,
                                  CapaDeteriorerItem item, GeoBone bone,
                                  RenderType renderType,
                                  MultiBufferSource buffers,
                                  VertexConsumer consumer,
                                  float partialTick, int light, int overlay) {
            if (armed && bone.getName().equals(CapeFit.SEAT_FRAME))
                opaque = new Matrix4f(bone.getModelSpaceMatrix());
        }

        static Draw finish(CapaArmorRenderer renderer) {
            Probe probe = renderer.getRenderLayers().stream().filter(Probe.class::isInstance)
                    .map(Probe.class::cast).findFirst().orElseThrow();
            GeoBone seat = seat(renderer);
            // Post runs after the depth-tested glow layer has reused the rig.
            Matrix4f last = seat.getModelSpaceMatrix();
            seat.setTrackingMatrices(false);
            probe.armed = false;
            return probe.opaque == null ? new Draw(Float.NaN, false) : new Draw(
                    probe.opaque.getScale(new Vector3f()).z, probe.opaque.equals(last, .00008F));
        }

        private static GeoBone seat(CapaArmorRenderer renderer) {
            return renderer.getGeoModel().getBone(CapeFit.SEAT_FRAME).orElseThrow();
        }
    }
}
