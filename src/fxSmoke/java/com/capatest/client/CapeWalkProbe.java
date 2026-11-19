package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
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

/** Live F5 recording. Inputs move the player; no keyframes or limb poses are injected. */
final class CapeWalkProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    static final String BODY = "chestplate", SEAT = "cape_seat_fit", TOP = "cape_top",
            MID = "cape_mid", TIP = "v17_ribbon_6_seg4";
    static final int DURATION = 156;
    private final Matrix4f[] matrices = new Matrix4f[5];
    private boolean active;

    private CapeWalkProbe(CapaArmorRenderer renderer) { super(renderer); }

    static void arm(CapaArmorRenderer renderer) {
        CapeWalkProbe probe = get(renderer);
        java.util.Arrays.fill(probe.matrices, null);
        probe.active = true;
    }

    private static CapeWalkProbe get(CapaArmorRenderer renderer) {
        return renderer.getRenderLayers().stream().filter(CapeWalkProbe.class::isInstance)
                .map(CapeWalkProbe.class::cast).findFirst().orElseGet(() -> {
                    CapeWalkProbe p = new CapeWalkProbe(renderer);
                    renderer.addRenderLayer(p);
                    return p;
                });
    }

    @Override
    public void renderForBone(PoseStack stack, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer consumer, float partial, int light, int overlay) {
        if (!active) return;
        int i = switch (bone.getName()) {
            case BODY -> 0;
            case SEAT -> 1;
            case TOP -> 2;
            case MID -> 3;
            case TIP -> 4;
            default -> -1;
        };
        if (i >= 0) matrices[i] = new Matrix4f(stack.last().pose());
    }

    static Draw finish(CapaArmorRenderer renderer) {
        CapeWalkProbe probe = get(renderer);
        probe.active = false;
        var matrices = probe.matrices;
        for (var matrix : matrices) if (matrix == null) throw new AssertionError("missing live walk matrix");
        var inverseBody = new Matrix4f(matrices[0]).invert();
        var seat = new Matrix4f(inverseBody).mul(matrices[1]);
        var tip = new Matrix4f(inverseBody).mul(matrices[4]);
        var player = Minecraft.getInstance().player;
        CapeWornMotion motion = CapaArmorModel.wornMotion(player);
        var mode = motion.weight(CapeState.SPRINT) > .5 ? CapeState.SPRINT
                : motion.weight(CapeState.WALK) > .5 ? CapeState.WALK : CapeState.IDLE;
        return new Draw(mode.name(), motion.stride(), motion.weight(CapeState.WALK), motion.weight(CapeState.SPRINT),
                seat.transformPosition(0, 25/16F, 7.4F/16, new Vector3f()).z() * 16,
                -Math.toDegrees(renderer.getGeoModel().getBone(TOP).orElseThrow().getRotX()),
                -Math.toDegrees(renderer.getGeoModel().getBone(MID).orElseThrow().getRotX()),
                tip.transformPosition(0, 0, .36F, new Vector3f()).mul(16));
    }

    record Draw(String clip, double stride, double walk, double run, double collarZ,
                double top, double mid, Vector3f tip) {}

    static final class Route {
        private final StringBuilder rows = new StringBuilder("time\tleg_pos\tleg_speed\tclip\tstride\twalk\trun\tcollar_z\ttop\tmid\ttip_x\ttip_y\ttip_z\n");
        private int start = -1;
        private int shot;
        private int count;
        private final int[] landmarks = {16, 44, 63, 84, 110, 149};

        void drive(Minecraft game) {
            var p = game.player;
            if (start < 0) start = p.tickCount;
            int t = p.tickCount - start;
            game.options.keyUp.setDown(t >= 20 && t < 73 || t >= 96 && t < 130);
            game.options.keyLeft.setDown(t >= 73 && t < 92);
            game.options.keySprint.setDown(t >= 96 && t < 130);
            if (t >= 130) p.setSprinting(false);
            // Real movement in two directions; turn smoothly during the strafe.
            float turn = 30 * Math.max(0F, Math.min(1F, (t - 74) / 17F));
            p.setYRot(3 + turn);
            p.setXRot(79);
        }

        boolean capture(Minecraft game, float partial, Draw draw, Path dir, String name) throws IOException {
            if (start < 0) return false;
            var p = game.player;
            double t = (double) p.tickCount - start + partial;
            rows.append(t).append('\t').append(p.walkAnimation.position(partial)).append('\t')
                    .append(p.walkAnimation.speed(partial)).append('\t').append(draw.clip()).append('\t')
                    .append(draw.stride()).append('\t').append(draw.walk()).append('\t').append(draw.run()).append('\t').append(draw.collarZ()).append('\t')
                    .append(draw.top()).append('\t').append(draw.mid()).append('\t').append(draw.tip().x()).append('\t')
                    .append(draw.tip().y()).append('\t').append(draw.tip().z()).append('\n');
            count++;
            if (shot < landmarks.length && t >= landmarks[shot]) {
                try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                    image.writeToFile(dir.resolve(String.format(Locale.ROOT, "%s-%02d.png", name, landmarks[shot])));
                }
                shot++;
            }
            if (t < DURATION) return false;
            if (count < 135) throw new AssertionError("too few walk frames: " + count);
            Files.writeString(dir.resolve(name + ".tsv"), rows);
            return true;
        }
    }

}
