package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeSparkFrame;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Compare both birth projections against the same worn pose in the real Shift route. */
final class CapeSparkCrouchProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    private final List<Quad> ribbons = new ArrayList<>();
    private Matrix4f fromDraw, torso;

    private CapeSparkCrouchProbe(CapaArmorRenderer renderer) { super(renderer); }

    @Override
    public void renderForBone(PoseStack pose, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer out, float partial, int light, int overlay) {
        if (fromDraw == null) return;
        String name = bone.getName();
        if (CapeWalkProbe.BODY.equals(name)) torso = new Matrix4f(fromDraw).mul(pose.last().pose());
        if (bone.isHidden() || !name.startsWith("v17_ribbon_")) return;
        for (var cube : bone.getCubes()) {
            pose.pushPose();
            try {
                RenderUtils.translateToPivotPoint(pose, cube);
                RenderUtils.rotateMatrixAroundCube(pose, cube);
                RenderUtils.translateAwayFromPivotPoint(pose, cube);
                var matrix = new Matrix4f(fromDraw).mul(pose.last().pose());
                for (var face : cube.quads()) {
                    if (face == null) continue;
                    var v = face.vertices();
                    var a = vec(matrix.transformPosition(v[0].position(), new Vector3f()));
                    var b = vec(matrix.transformPosition(v[1].position(), new Vector3f())).subtract(a);
                    var c = vec(matrix.transformPosition(v[3].position(), new Vector3f())).subtract(a);
                    if (b.lengthSqr() > 1e-12 && c.lengthSqr() > 1e-12) {
                        require(Math.abs(b.dot(c)) < .002 * b.length() * c.length(), "ribbon quad is not rectangular");
                        ribbons.add(new Quad(a, b, c));
                    }
                }
            } finally {
                pose.popPose();
            }
        }
    }

    private double nearest(Vec3 p) {
        double best = Double.POSITIVE_INFINITY;
        for (var quad : ribbons) best = Math.min(best, quad.distanceSquared(p));
        return Math.sqrt(best);
    }

    private record Quad(Vec3 origin, Vec3 u, Vec3 v) {
        double distanceSquared(Vec3 p) {
            Vec3 d = p.subtract(origin);
            double s = Mth.clamp(d.dot(u) / u.lengthSqr(), 0, 1);
            double t = Mth.clamp(d.dot(v) / v.lengthSqr(), 0, 1);
            return d.subtract(u.scale(s)).subtract(v.scale(t)).lengthSqr();
        }
    }

    static final class Route {
        private static final int FRAMES = 6;
        private CapeSparkCrouchProbe draw;
        private int frames, lastTick;
        private final StringBuilder rows = new StringBuilder("tick\tzona\terror_marco_35\terror_marco_36\tdistancia_35\tdistancia_36\n");

        void beginFrame() {
            if (draw != null) draw.fromDraw = null;
            draw = null;
        }

        void arm(CapaArmorRenderer renderer, LocalPlayer p, Matrix4f root, Vec3 renderOffset) {
            if (frames >= FRAMES || (frames != 0 && p.tickCount < lastTick + 4) || root == null || renderOffset == null
                    || !p.onGround() || !p.isCrouching() || p.getSwimAmount(1) != 0
                    || p.getDeltaMovement().horizontalDistanceSqr() > .000004
                    || Math.abs(Mth.wrapDegrees(p.yBodyRot - p.yBodyRotO)) > .05) return;
            draw = renderer.getRenderLayers().stream().filter(CapeSparkCrouchProbe.class::isInstance)
                    .map(CapeSparkCrouchProbe.class::cast).findFirst().orElseGet(() -> {
                        var layer = new CapeSparkCrouchProbe(renderer);
                        renderer.addRenderLayer(layer);
                        return layer;
                    });
            draw.ribbons.clear();
            draw.torso = null;
            // RenderPlayer.Pre is relative to the posed player, including
            // PlayerRenderer's offset; compare all points to the actual feet.
            draw.fromDraw = new Matrix4f().translation((float) renderOffset.x, (float) renderOffset.y,
                    (float) renderOffset.z).mul(new Matrix4f(root).invert());
        }

        void record(LocalPlayer p, CapeWalkProbe.Draw pose) {
            if (draw == null || pose == null || pose.sneak() < .999) return;
            require(draw.torso != null && draw.ribbons.size() > 100, "missing live crouched mesh");
            var earlier = CapeSparkFrame.upright(p.yBodyRot, p.getBbHeight());
            var current = CapaDeteriorerItem.auraFrame(p);
            require(!current.posed(), "grounded crouch is not a glide or swim");
            // In the actual quiet pulse, 0 is the collar, 2 the low hem
            // and 6 the flank. Use the 27 combinations of extremal/median jitter.
            double[] jitter = {0, .5, 1};
            for (int pulse : new int[]{0, 2, 6}) {
                for (double x : jitter) for (double y : jitter) for (double z : jitter) {
                    var s = CapeState.SNEAK.spark(pulse, 0, true, x, y, z);
                    var point = vec(draw.torso.transformPosition((float) -s.side(), (float) s.height(),
                            (float) s.depth(), new Vector3f()));
                    var old = vec(earlier.birth(s));
                    var now = vec(current.birth(s));
                    double error = now.distanceTo(point);
                    require(error < .004, "crouched birth does not match the torso: " + error
                            + " (point=" + now + ", torso=" + point + ", yaw=" + p.yBodyRot + ")");
                    String band = pulse == 0 ? "cuello" : pulse == 2 ? "dobladillo" : "costado";
                    rows.append(String.format(Locale.ROOT, "%d\t%s\t%.8f\t%.8f\t%.8f\t%.8f%n",
                            p.tickCount, band, old.distanceTo(point), error, draw.nearest(old), draw.nearest(now)));
                }
            }
            lastTick = p.tickCount;
            frames++;
        }

        void save(Path shots, String slot) throws IOException {
            require(frames == FRAMES, "missing stable Shift frames in " + slot + ": " + frames);
            Files.writeString(shots.resolve("nacimiento-agachado-" + slot + ".tsv"), rows);
        }
    }

    private static Vec3 vec(Vector3f p) { return new Vec3(p.x, p.y, p.z); }
    private static Vec3 vec(CapeSparkFrame.Offset p) { return new Vec3(p.x(), p.y(), p.z()); }
    private static void require(boolean ok, String what) {
        if (!ok) throw new AssertionError("crouched embers: " + what);
    }
}
