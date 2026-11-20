package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.util.Mth;
import net.minecraftforge.client.event.ViewportEvent;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Live wearer and framebuffer; only the orbiting test camera is synthetic. */
final class CapePlacementProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    private static final Method POSITION = positionMethod();
    private Matrix4f projection;
    private Matrix4f inverseChest;
    private float rootZ, collarZ;
    private final List<Vector3f> vertices = new ArrayList<>();
    private final Map<GeoBone, Matrix4f> matrices = new LinkedHashMap<>();
    private final List<GeoBone> tracked = new ArrayList<>();
    private final StringBuilder faces = new StringBuilder();
    private boolean active;

    private CapePlacementProbe(CapaArmorRenderer renderer) { super(renderer); }

    private static Method positionMethod() {
        try {
            var method = Camera.class.getDeclaredMethod("setPosition", double.class, double.class, double.class);
            method.setAccessible(true);
            return method;
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private static boolean ribbonRoot(String name) {
        return name.startsWith("v17_ribbon_") && name.endsWith("_seg0");
    }

    private static boolean tracked(String name) {
        return name.startsWith("v17_cowl_") || name.startsWith("v18_pad_") || ribbonRoot(name)
                || name.equals("v20_mount_seat") || name.equals(CapeFit.GUSSET_BONE);
    }

    private static CapePlacementProbe of(CapaArmorRenderer renderer) {
        return renderer.getRenderLayers().stream().filter(CapePlacementProbe.class::isInstance)
                .map(CapePlacementProbe.class::cast).findFirst().orElseGet(() -> {
                    var probe = new CapePlacementProbe(renderer);
                    renderer.addRenderLayer(probe);
                    return probe;
                });
    }

    static void arm(CapaArmorRenderer renderer, int control) {
        var p = of(renderer);
        p.active = true;
        p.inverseChest = null;
        p.rootZ = p.collarZ = Float.POSITIVE_INFINITY;
        p.projection = new Matrix4f(RenderSystem.getProjectionMatrix()).mul(RenderSystem.getModelViewMatrix());
        p.matrices.clear();
        p.vertices.clear();
        p.faces.setLength(0);
        // GeckoLib calls this per-bone layer only in the diffuse pass. Keep the
        // same live model-space matrices under observation through the glow.
        for (var registered : renderer.getGeoModel().getAnimationProcessor().getRegisteredBones()) {
            if (!(registered instanceof GeoBone b)) continue;
            String n = b.getName();
            if (!tracked(n) || b.getCubes().isEmpty()) continue;
            boolean hide = control == 1 && n.startsWith("v18_pad_");
            b.setHidden(hide);
            b.setTrackingMatrices(true);
            p.tracked.add(b);
        }
    }

    @Override
    public void renderForBone(PoseStack pose, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer out, float partial, int light, int overlay) {
        if (!active) return;
        String n = bone.getName();
        if (n.equals("chestplate")) {
            inverseChest = new Matrix4f(pose.last().pose()).invert();
            return;
        }
        if (bone.isHidden() || !tracked(n) || bone.getCubes().isEmpty()) return;
        require(inverseChest != null, "missing live torso transform");
        matrices.put(bone, new Matrix4f(bone.getModelSpaceMatrix()));
        for (var cube : bone.getCubes()) {
            pose.pushPose();
            try {
                RenderUtils.translateToPivotPoint(pose, cube);
                RenderUtils.rotateMatrixAroundCube(pose, cube);
                RenderUtils.translateAwayFromPivotPoint(pose, cube);
                var model = new Matrix4f(inverseChest).mul(pose.last().pose());
                var clip = new Matrix4f(projection).mul(pose.last().pose());
                for (var face : cube.quads()) {
                    if (face == null) continue;
                    faces.append(n);
                    for (var vert : face.vertices()) {
                        var point = model.transformPosition(vert.position(), new Vector3f()).mul(16);
                        if (n.equals("v20_mount_seat")) vertices.add(point);
                        if (ribbonRoot(n)) rootZ = Math.min(rootZ, point.z);
                        if (n.startsWith("v17_cowl_back_")) collarZ = Math.min(collarZ, point.z);
                        var v = clip.transformProject(new Vector3f(vert.position()));
                        faces.append('\t').append((1+v.x)/2).append('\t').append((1-v.y)/2);
                    }
                    faces.append('\n');
                }
            } finally {
                pose.popPose();
            }
        }
    }

    record Draw(List<Vector3f> vertices, String faces, float rootZ, float collarZ) {}

    static Draw finish(CapaArmorRenderer renderer) {
        var p = of(renderer);
        p.active = false;
        require(p.inverseChest != null && !p.vertices.isEmpty()
                && Float.isFinite(p.rootZ) && Float.isFinite(p.collarZ), "missing original seat, collar or ribbon roots");
        for (var b : p.tracked) {
            Matrix4f solid = p.matrices.get(b);
            require(solid == null && b.isHidden() || solid != null && solid.equals(b.getModelSpaceMatrix(), .0001F),
                    "solid and emissive matrices differ: " + b.getName());
            b.setTrackingMatrices(false);
            b.setHidden(false);
            b.setChildrenHidden(false);
        }
        p.tracked.clear();
        return new Draw(List.copyOf(p.vertices), p.faces.toString(), p.rootZ, p.collarZ);
    }

    private static void require(boolean pass, String reason) {
        if (!pass) throw new AssertionError(reason);
    }

    /** Four slot/skin fixtures, each with separately controlled head and camera. */
    static final class Route {
        private static final String[] VIEWS = {"espalda", "frente", "izquierda", "derecha", "arriba", "abajo"};
        private static final int SWEEP = 37;
        private static final int TURN = 12;
        private int shot, frame;
        private List<Vector3f> rest;
        private float jumpHeight, maxDiff;
        private double ground = Double.NaN;
        private final StringBuilder trace = new StringBuilder("sample\tpitch\tyaw\tlift\tseat_drift\troot_z\tcollar_z\n");

        int control() { return shot < VIEWS.length * 2 ? shot % 2 : 0; }

        void aim(LocalPlayer p) {
            float turn = yaw(), pitch = pitch();
            p.setYBodyRot(0);
            p.yBodyRotO = 0;
            p.setYRot(turn);
            p.yRotO = turn;
            p.setYHeadRot(turn);
            p.yHeadRotO = turn;
            p.setXRot(pitch);
            p.xRotO = pitch;
        }

        private int view() { return Math.min(shot / 2, VIEWS.length); }

        private float pitch() {
            return switch (view()) {
                case 4 -> 83;
                case 2, 3 -> -72;
                case 5 -> -83;
                case 6 -> frame < SWEEP ? -89 + frame * (178F / (SWEEP - 1)) : -79;
                default -> 0;
            };
        }

        private float yaw() {
            if (view() != 6) return 0;
            if (frame < SWEEP) return 0;
            return frame < SWEEP + TURN ? 73 * Mth.sin((float) ((frame - SWEEP) * Math.PI / 5)) : 0;
        }

        void camera(ViewportEvent.ComputeCameraAngles event, LocalPlayer player) {
            float yaw = switch (view()) {
                case 1 -> 180;
                case 2 -> 90;
                case 3 -> -90;
                case 4 -> 22;
                case 5 -> -24;
                default -> 0;
            };
            float pitch = switch (view()) {
                case 4 -> 79;
                case 5 -> -51;
                case 6 -> frame >= SWEEP ? -10 : 8;
                default -> 8;
            };
            double radY = Math.toRadians(yaw), radX = Math.toRadians(pitch);
            double radius = view() == 5 ? 1.62 : 2.95;
            double center = view() == 5 ? 1.34 : 1.00;
            double t = event.getPartialTick();
            double x = Mth.lerp(t, player.xo, player.getX()) + radius * Math.sin(radY)*Math.cos(radX);
            double y = Mth.lerp(t, player.yo, player.getY()) + center + radius * Math.sin(radX);
            double z = Mth.lerp(t, player.zo, player.getZ()) - radius * Math.cos(radY)*Math.cos(radX);
            try {
                POSITION.invoke(event.getCamera(), x, y, z);
            } catch (ReflectiveOperationException e) {
                throw new AssertionError("could not set the Forge probe camera", e);
            }
            event.setYaw(yaw);
            event.setPitch(pitch);
        }

        void drive(Minecraft game) {
            if (view() != 6 || frame < SWEEP + TURN || !Double.isNaN(ground) || !game.player.onGround()) return;
            ground = game.player.getY();
            game.options.keyJump.setDown(true);
        }

        boolean capture(Minecraft game, Path root, String fixture, Draw draw) throws IOException {
            require(draw != null, "missing live chest/Curios draw");
            if (control() == 0) {
                if (rest == null) rest = draw.vertices();
                require(rest.size() == draw.vertices().size(), "the original anchor changed topology");
                float diff = 0;
                for (int i = 0; i < rest.size(); i++) diff = Math.max(diff, rest.get(i).distance(draw.vertices().get(i)));
                if (pitch() <= 0) {
                    maxDiff = Math.max(diff, maxDiff);
                    require(diff < .006F, "the upward fit pulled the seat off the chest: " + fixture + "/" + frame + ": " + diff);
                }
                double lift = Double.isNaN(ground) ? 0 : game.player.getY() - ground;
                trace.append(shot * 100 + frame).append('\t').append(pitch()).append('\t').append(yaw())
                        .append('\t').append(lift).append('\t').append(diff).append('\t').append(draw.rootZ())
                        .append('\t').append(draw.collarZ()).append('\n');
            }
            if (view() < VIEWS.length) {
                String name = fixture + "-" + VIEWS[view()] + (control() == 1 ? "-sin-placas" : "");
                save(game, root, name);
                if (control() == 0) Files.writeString(root.resolve(name + "-caras.tsv"), draw.faces());
                shot++;
                return false;
            }
            if (frame < SWEEP + TURN) {
                if (frame == 0) save(game, root, fixture + "-mirada-alta");
                if (frame == SWEEP + 2) save(game, root, fixture + "-giro-alto");
                frame++;
                return false;
            }
            if (Double.isNaN(ground)) return false;
            float lift = (float) (game.player.getY() - ground);
            if (lift > .05F) game.options.keyJump.setDown(false);
            if (lift > .65F && jumpHeight <= .65F) save(game, root, fixture + "-salto");
            jumpHeight = Math.max(jumpHeight, lift);
            frame++;
            if (jumpHeight <= .65F || !game.player.onGround()) return false;
            Files.writeString(root.resolve(fixture + "-recorrido.tsv"), trace);
            return true;
        }

        private static void save(Minecraft game, Path root, String file) throws IOException {
            try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                image.writeToFile(root.resolve(file + ".png"));
            }
        }

        String summary() {
            return "seis vistas; " + SWEEP + " poses de mirada; salto " + jumpHeight
                    + " bloques; desplazamiento máximo del asiento mirando arriba " + maxDiff + "u";
        }
    }
}
