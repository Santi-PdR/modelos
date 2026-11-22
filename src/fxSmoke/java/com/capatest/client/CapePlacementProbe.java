package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.util.Mth;
import net.minecraftforge.client.event.ViewportEvent;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Actual equipped mesh and vanilla sleeves, with independent camera and aim controls. */
final class CapePlacementProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    private static final Method POSITION = positionMethod();
    private Matrix4f projection, chest, inverseChest;
    private final Map<String, List<Vector3f>> rigid = new LinkedHashMap<>();
    private final Map<GeoBone, Matrix4f> solid = new LinkedHashMap<>();
    private final List<GeoBone> tracked = new ArrayList<>();
    private final Map<String, Matrix4f> sections = new LinkedHashMap<>();
    private final StringBuilder faces = new StringBuilder(), boxes = new StringBuilder(), withoutEdge = new StringBuilder();
    private final StringBuilder headTop = new StringBuilder(), fixedPlates = new StringBuilder(), fixedChain = new StringBuilder();
    private Matrix4f mount;
    private boolean measuringShoulders;
    private boolean measuringContact;
    private boolean measuringMotion;
    private boolean active;
    private final CapaArmorRenderer renderer;

    private CapePlacementProbe(CapaArmorRenderer renderer) {
        super(renderer);
        this.renderer = renderer;
    }

    private static Method positionMethod() {
        try {
            var method = Camera.class.getDeclaredMethod("setPosition", double.class, double.class, double.class);
            method.setAccessible(true);
            return method;
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private static boolean plate(String name) {
        return name.equals(CapePlateFit.SMALL) || name.equals(CapePlateFit.WIDE);
    }

    private static boolean anchor(String name) {
        return name.equals(CapeFit.BONE) || name.equals(CapeFit.DRAPE_BONE);
    }

    private static boolean tracked(String name) {
        return anchor(name) || plate(name) || name.startsWith("v17_cowl_") || name.startsWith("v18_chain_")
                || name.startsWith("v19_cuellito_") || name.startsWith("v20_mount_") || name.equals(CapeFit.GUSSET_BONE);
    }

    private static CapePlacementProbe of(CapaArmorRenderer renderer) {
        return renderer.getRenderLayers().stream().filter(CapePlacementProbe.class::isInstance)
                .map(CapePlacementProbe.class::cast).findFirst().orElseGet(() -> {
                    var probe = new CapePlacementProbe(renderer);
                    renderer.addRenderLayer(probe);
                    return probe;
                });
    }

    static void arm(CapaArmorRenderer renderer, boolean hidePlates, boolean hideShoulderCloth,
                    boolean measureContact, boolean measureMotion, boolean measureShoulders) {
        var p = of(renderer);
        p.active = true;
        p.measuringShoulders = measureShoulders;
        p.measuringMotion = measureMotion;
        p.measuringContact = measureContact || measureMotion;
        p.inverseChest = null;
        p.projection = new Matrix4f(RenderSystem.getProjectionMatrix()).mul(RenderSystem.getModelViewMatrix());
        p.rigid.clear();
        p.solid.clear();
        p.sections.clear();
        p.faces.setLength(0);
        p.boxes.setLength(0);
        p.withoutEdge.setLength(0);
        p.headTop.setLength(0);
        p.fixedPlates.setLength(0);
        p.fixedChain.setLength(0);
        p.mount = null;
        for (var registered : renderer.getGeoModel().getAnimationProcessor().getRegisteredBones()) {
            if (!(registered instanceof GeoBone b) || !(tracked(b.getName()) || measureMotion && sprintEdge(b) != null)) continue;
            if (plate(b.getName())) b.setHidden(hidePlates);
            if (CapeFit.SHOULDERS_BONE.equals(b.getName())) b.setHidden(hideShoulderCloth);
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
            chest = new Matrix4f(pose.last().pose());
            inverseChest = new Matrix4f(chest).invert();
            return;
        }
        if (measuringMotion && CapeFit.BONE.equals(n)) mount = new Matrix4f(pose.last().pose());
        if (measuringMotion && (n.equals("cape_top") || n.equals("cape_mid") || n.equals("cape_bottom"))) {
            sections.put(n, new Matrix4f(pose.last().pose()));
            return;
        }
        boolean rigidPiece = tracked(n);
        boolean sewnRoot = measuringContact && n.startsWith("v17_ribbon_") && n.endsWith("_seg0");
        if ((!rigidPiece && !sewnRoot && !measuringMotion)
                || (!anchor(n) && (bone.isHidden() || bone.getCubes().isEmpty()))) return;
        require(inverseChest != null, "missing live torso transform");
        List<Vector3f> points = new ArrayList<>();
        var edge = measuringMotion ? sprintEdge(bone) : null;
        if (rigidPiece || edge != null)
            require(solid.put(bone, new Matrix4f(bone.getModelSpaceMatrix())) == null, "cape piece drawn twice: " + n);
        if (rigidPiece) rigid.put(n, points);
        PoseStack control = null;
        if (edge != null && renderer.sprintEdge() > 0) {
            // A/B at the same animation time and limb pose: rebuild only this
            // leaf from its live parent without the render-time edge offset.
            var parent = sections.get(bone.getParent().getName());
            require(parent != null, "missing sleeve-control section: " + n);
            control = new PoseStack();
            control.last().pose().set(parent);
            RenderUtils.prepMatrixForBone(control, bone);
            var expected = new PoseStack();
            double amount = renderer.sprintEdge();
            expected.last().pose().set(parent).translate((float) (amount * edge.x() / 16), 0,
                    (float) (amount * edge.z() / 16));
            RenderUtils.prepMatrixForBone(expected, bone);
            require(expected.last().pose().equals(pose.last().pose(), .0001F), "wrong live edge fit: " + n);
        }
        if (anchor(n)) {
            // The basis of each empty attachment bone, before the real animated cloth.
            var model = new Matrix4f(inverseChest).mul(pose.last().pose());
            for (var point : new Vector3f[]{new Vector3f(), new Vector3f(1,0,0), new Vector3f(0,1,0), new Vector3f(0,0,1)})
                points.add(model.transformPosition(point).mul(16));
        }
        PoseStack fixedPlate = null;
        if (measuringShoulders && plate(n)) {
            // Same pose, with just the sleeve hinge disabled: the .37
            // projection. This is a mesh control, not another live JAR.
            fixedPlate = new PoseStack();
            fixedPlate.last().pose().set(chest);
            renderer.placeShoulderRest(fixedPlate, CapeMountPlacement.plate(false, CapePlateFit.WIDE.equals(n)));
            RenderUtils.prepMatrixForBone(fixedPlate, bone);
        }
        var chainControl = measuringMotion && CapeHood.chainLink(n) ? chainControl(renderer, mount, bone) : null;
        boolean omitLip = renderer.hidesInteriorLip(bone);
        for (int i = 0; i < bone.getCubes().size(); ++i) {
            if (omitLip && i == CapeMountPlacement.LINING_LIP_CUBE) continue;
            var cube = bone.getCubes().get(i);
            pose.pushPose();
            try {
                cubePose(pose, cube);
                var model = new Matrix4f(inverseChest).mul(pose.last().pose());
                var clip = new Matrix4f(projection).mul(pose.last().pose());
                var lo = new Vector3f(Float.POSITIVE_INFINITY);
                var hi = new Vector3f(Float.NEGATIVE_INFINITY);
                for (var face : cube.quads()) {
                    if (face == null) continue;
                    var verts = face.vertices();
                    for (var vert : verts) {
                        if (rigidPiece) points.add(model.transformPosition(vert.position(), new Vector3f()).mul(16));
                        if (measuringContact) {
                            lo.min(vert.position());
                            hi.max(vert.position());
                        }
                    }
                    if (plate(n) || CapeFit.SHOULDERS_BONE.equals(n))
                        quad(faces, n, clip, verts[0].position(), verts[1].position(), verts[2].position(), verts[3].position());
                }
                if (measuringContact) box(boxes, n, model, lo, hi);
                if (control != null) controlBox(withoutEdge, n, control, cube, lo, hi);
                if (fixedPlate != null) controlBox(fixedPlates, n, fixedPlate, cube, lo, hi);
                if (chainControl != null) controlBox(fixedChain, n, chainControl, cube, lo, hi);
            } finally {
                pose.popPose();
            }
        }
    }

    private void controlBox(StringBuilder out, String name, PoseStack control, GeoCube cube, Vector3f lo, Vector3f hi) {
        control.pushPose();
        try {
            cubePose(control, cube);
            box(out, name, new Matrix4f(inverseChest).mul(control.last().pose()), lo, hi);
        } finally {
            control.popPose();
        }
    }

    static PoseStack chainControl(CapaArmorRenderer renderer, Matrix4f mount, GeoBone link) {
        // Rebuild the .40 link from the live parent and nape stroke. No
        // second animation sampling, different limbs, camera or light.
        require(mount != null && link.getParent() != null && CapeFit.BONE.equals(link.getParent().getName()),
                "missing live chain mount");
        var control = new PoseStack();
        var trim = renderer.napeFor(link.getName());
        control.last().pose().set(mount);
        if (trim != CapeHood.FIXED) control.translate(trim.x()/16, trim.y()/16, trim.z()/16);
        RenderUtils.prepMatrixForBone(control, link);
        return control;
    }

    private static CapeSprintEdge.Offset sprintEdge(GeoBone bone) {
        return bone.getParent() == null ? null : CapeSprintEdge.offset(bone.getName(), bone.getParent().getName());
    }

    private static void cubePose(PoseStack pose, GeoCube cube) {
        RenderUtils.translateToPivotPoint(pose, cube);
        RenderUtils.rotateMatrixAroundCube(pose, cube);
        RenderUtils.translateAwayFromPivotPoint(pose, cube);
    }

    record Draw(Map<String,List<Vector3f>> rigid, String faces, String boxes, float pitch, float yaw,
                double hoodClearance, String withoutEdge, String headTop, double rearTuck, String fixedPlates, String fixedChain) {}

    static Draw finish(CapaArmorRenderer renderer, PoseStack armor, PlayerModel<?> player) {
        var p = of(renderer);
        p.active = false;
        require(p.inverseChest != null && p.rigid.containsKey("v20_mount_seat") && p.rigid.containsKey(CapeFit.DRAPE_BONE),
                "missing original seat or cloth attachment");
        for (var b : p.tracked) {
            Matrix4f solid = p.solid.get(b);
            if (solid != null) require(solid.equals(b.getModelSpaceMatrix(), .0001F),
                    "solid and emissive matrices differ: " + b.getName());
            b.setTrackingMatrices(false);
            if (plate(b.getName()) || CapeFit.SHOULDERS_BONE.equals(b.getName())) b.setHidden(false);
        }
        p.tracked.clear();
        require(player != null, "missing live vanilla model");
        var copy = new PoseStack();
        copy.last().pose().set(armor.last().pose());
        p.playerPart(copy, player.leftSleeve, "left_sleeve", .25F, true);
        p.playerPart(copy, player.rightSleeve, "right_sleeve", .25F, true);
        if (p.measuringContact) {
            p.playerPart(copy, player.jacket, "jacket", .25F, false);
            p.playerPart(copy, player.body, "body", 0, false);
        }
        if (p.measuringMotion) {
            // Base skin and optional outer layer are separate obstacles.
            p.playerPart(copy, player.head, "head", 0, false);
            p.playerPart(copy, player.hat, "hat", .5F, false);
            p.playerPart(copy, player.leftArm, "left_arm", 0, false);
            p.playerPart(copy, player.rightArm, "right_arm", 0, false);
            p.playerPart(copy, player.leftLeg, "left_leg", 0, false);
            p.playerPart(copy, player.rightLeg, "right_leg", 0, false);
        }
        return new Draw(Map.copyOf(p.rigid), p.faces.toString(), p.boxes.toString(), (float) Math.toDegrees(player.head.xRot),
                (float) Math.toDegrees(player.head.yRot), renderer.hoodClearance(), p.withoutEdge.toString(),
                p.headTop.toString(), renderer.rearTuck(), p.fixedPlates.toString(), p.fixedChain.toString());
    }

    private void playerPart(PoseStack stack, ModelPart part, String name, float inflate, boolean sleeve) {
        // Use the real torso without its optional jacket as the back plane.
        // The sleeve coverage gate still uses the vanilla .25 outer layer.
        part.visit(stack, (pose, path, id, cube) -> {
            float x0 = (cube.minX-inflate)/16, x1 = (cube.maxX+inflate)/16;
            float y0 = (cube.minY-inflate)/16, y1 = (cube.maxY+inflate)/16;
            float z0 = (cube.minZ-inflate)/16, z1 = (cube.maxZ+inflate)/16;
            if (measuringContact) box(boxes, name, new Matrix4f(inverseChest).mul(pose.pose()),
                    new Vector3f(x0,y0,z0), new Vector3f(x1,y1,z1));
            if (name.equals("head")) {
                var screen = new Matrix4f(projection).mul(pose.pose());
                quad(headTop, "top", screen, new Vector3f(x0,y0,z0), new Vector3f(x1,y0,z0),
                        new Vector3f(x1,y0,z1), new Vector3f(x0,y0,z1));
            }
            if (!sleeve) return;
            // Top and upper-front strip only, for the front-coverage gate.
            var clip = new Matrix4f(projection).mul(pose.pose());
            float edge = y0 + 3/16F;
            quad(faces, name, clip, new Vector3f(x0,y0,z0), new Vector3f(x1,y0,z0),
                    new Vector3f(x1,edge,z0), new Vector3f(x0,edge,z0));
            quad(faces, name, clip, new Vector3f(x0,y0,z0), new Vector3f(x1,y0,z0),
                    new Vector3f(x1,y0,z1), new Vector3f(x0,y0,z1));
        });
    }

    private static final int[] BOX_CORNERS = {0, 1, 3, 2, 4, 5, 7, 6};

    private static void box(StringBuilder out, String name, Matrix4f transform, Vector3f lo, Vector3f hi) {
        out.append(name);
        for (int i : BOX_CORNERS) {
            var v = transform.transformPosition((i&1) == 0 ? lo.x : hi.x, (i&2) == 0 ? lo.y : hi.y,
                    (i&4) == 0 ? lo.z : hi.z, new Vector3f()).mul(16);
            out.append('\t').append(v.x).append('\t').append(v.y).append('\t').append(v.z);
        }
        out.append('\n');
    }

    private static void quad(StringBuilder out, String name, Matrix4f clip, Vector3f... points) {
        out.append(name);
        for (var point : points) {
            var v = clip.transformProject(new Vector3f(point));
            out.append('\t').append((1+v.x)/2).append('\t').append((1-v.y)/2);
        }
        out.append('\n');
    }

    private static void require(boolean pass, String reason) {
        if (!pass) throw new AssertionError(reason);
    }

    static void orbit(ViewportEvent.ComputeCameraAngles event, LocalPlayer player,
                              float yaw, float pitch, double radius, double center) {
        double radY = Math.toRadians(yaw), radX = Math.toRadians(pitch);
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

    /** Sample the real crouch/sprint pose and unmodified third-person top view. */
    static final class PoseAudit {
        private record Phase(String name, float pitch, float yaw, boolean crouch, boolean sprint,
                             boolean vanillaCamera, int samples) {}
        private static final List<Phase> PHASES = List.of(
                new Phase("reposo", 8, 0, false, false, true, 8),
                new Phase("cenital", 79, 22, false, false, true, 8),
                new Phase("mirada-alta", -64, 0, false, false, false, 8),
                new Phase("giro", -35, 55, false, false, false, 8),
                new Phase("agachado", 0, 0, true, false, false, 12),
                new Phase("agachado-cenital", 79, 22, true, false, true, 8),
                new Phase("carrera", 0, 0, false, true, false, 24));
        private final StringBuilder trace = new StringBuilder(
                "sample\tphase\ttick\tpose\tsprint\tspeed\tpitch\tyaw\tvanilla\tcamera_pitch\tcamera_yaw\tpliegue\timage\n");
        private final StringBuilder boxes = new StringBuilder(), withoutEdge = new StringBuilder(), fixedPlates = new StringBuilder(), fixedChain = new StringBuilder();
        private int phase, frame, sample;
        private int start = -1, lastTick = -1;

        private boolean done() { return phase >= PHASES.size(); }

        void drive(Minecraft game) {
            if (done()) return;
            var q = PHASES.get(phase);
            if (start < 0) start = game.player.tickCount;
            game.options.keyShift.setDown(q.crouch());
            game.options.keyUp.setDown(q.sprint());
            game.options.keySprint.setDown(q.sprint());
        }

        void aim(LocalPlayer p) {
            if (done()) return;
            var q = PHASES.get(phase);
            p.setYBodyRot(0);
            p.yBodyRotO = 0;
            p.setYRot(q.yaw());
            p.yRotO = q.yaw();
            p.setYHeadRot(q.yaw());
            p.yHeadRotO = q.yaw();
            p.setXRot(q.pitch());
            p.xRotO = q.pitch();
        }

        void camera(ViewportEvent.ComputeCameraAngles event, LocalPlayer p) {
            if (done()) return;
            var q = PHASES.get(phase);
            if (!q.vanillaCamera()) {
                float yaw = switch (q.name()) {
                    case "mirada-alta" -> 90;
                    case "giro" -> 63;
                    default -> -62;
                };
                orbit(event, p, yaw, 10, 2.95, .97);
            }
        }

        boolean capture(Minecraft game, Path root, String name, Draw draw, float partial) throws IOException {
            var q = PHASES.get(phase);
            var p = game.player;
            float speed = p.walkAnimation.speed(partial);
            if (start < 0 || p.tickCount - start < (q.sprint() ? 15 : 7) || p.tickCount == lastTick
                    || !p.onGround() || p.isCrouching() != q.crouch() || p.isSprinting() != q.sprint()
                    || (q.sprint() ? speed < .48F : speed > .025F)) return false;
            require(draw != null && !draw.boxes().isEmpty(), "missing motion geometry");
            require(Math.abs(draw.pitch()-q.pitch()) < .02 && Math.abs(draw.yaw()-q.yaw()) < .02,
                    q.name() + ": wrong live aim " + draw.pitch() + "/" + draw.yaw());
            var cam = game.gameRenderer.getMainCamera();
            if (q.vanillaCamera()) require(Math.abs(cam.getXRot() - q.pitch()) < .02
                    && Math.abs(cam.getYRot() - q.yaw()) < .02, q.name() + ": vanilla F5 camera not applied");

            String image = "-";
            if (frame == 0 || q.sprint() && (frame % 6 == 0 || frame == q.samples()-1)) {
                image = String.format(Locale.ROOT, "%s-%s-%02d.png", name, q.name(), frame);
                try (var shot = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                    shot.writeToFile(root.resolve(image));
                }
            }
            trace.append(sample).append('\t').append(q.name()).append('\t').append(p.tickCount)
                    .append('\t').append(p.getPose().name()).append('\t').append(p.isSprinting())
                    .append('\t').append(speed).append('\t').append(draw.pitch()).append('\t').append(draw.yaw())
                    .append('\t').append(q.vanillaCamera()).append('\t').append(cam.getXRot())
                    .append('\t').append(cam.getYRot()).append('\t').append(draw.hoodClearance()).append('\t').append(image).append('\n');
            draw.boxes().lines().forEach(box -> boxes.append(sample).append('\t').append(box).append('\n'));
            draw.withoutEdge().lines().forEach(box -> withoutEdge.append(sample).append('\t').append(box).append('\n'));
            draw.fixedPlates().lines().forEach(box -> fixedPlates.append(sample).append('\t').append(box).append('\n'));
            draw.fixedChain().lines().forEach(box -> fixedChain.append(sample).append('\t').append(box).append('\n'));
            sample++;
            lastTick = p.tickCount;
            if (++frame < q.samples()) return false;
            phase++;
            frame = 0;
            start = -1;
            if (!done()) return false;
            game.options.keyShift.setDown(false);
            game.options.keyUp.setDown(false);
            game.options.keySprint.setDown(false);
            p.setSprinting(false);
            Files.writeString(root.resolve(name + "-posturas.tsv"), trace);
            Files.writeString(root.resolve(name + "-cubos.tsv"), boxes);
            Files.writeString(root.resolve(name + "-sin-holgura-brazos.tsv"), withoutEdge);
            Files.writeString(root.resolve(name + "-placas-fijas.tsv"), fixedPlates);
            Files.writeString(root.resolve(name + "-cadena-fija.tsv"), fixedChain);
            return true;
        }
    }

    /** Seven camera orbits at neutral aim; a separate aim sweep at one viewpoint. */
    static final class Route {
        private static final String[] VIEWS = {"espalda", "frente", "izquierda", "derecha", "arriba", "abajo", "diagonal"};
        private static final float[] CAMERA_YAW = {0,180,90,-90,22,-24,-43,66};
        private static final float[] CAMERA_PITCH = {8,9,8,8,79,-51,17,8};
        private static final int SWEEP = 37, TURN = 12;
        private int shot, frame;
        private Map<String, List<Vector3f>> rest;
        private float jumpHeight, maxDiff;
        private double ground = Double.NaN;
        private final StringBuilder trace = new StringBuilder("mode\tsample\tpitch\tyaw\tcamera_pitch\tcamera_yaw\tlift\tdrift\n");

        boolean calibration() { return shot == 0; }
        boolean control() { return view() < VIEWS.length && shot % 2 == 1; }
        boolean shoulderClothControl() { return shot == VIEWS.length * 2; }
        boolean standing() { return view() < VIEWS.length || frame < SWEEP + TURN; }

        void aim(LocalPlayer p) {
            p.setYBodyRot(0);
            p.yBodyRotO = 0;
            p.setYRot(yaw());
            p.yRotO = yaw();
            p.setYHeadRot(yaw());
            p.yHeadRotO = yaw();
            p.setXRot(pitch());
            p.xRotO = pitch();
        }

        private int view() { return Math.min(shot / 2, VIEWS.length); }
        private float pitch() {
            return view() < VIEWS.length || shoulderClothControl() ? 0 : frame < SWEEP ? -89 + frame*(178F/(SWEEP-1)) : -64;
        }
        private float yaw() {
            return view() < VIEWS.length || shoulderClothControl() || frame < SWEEP || frame >= SWEEP + TURN
                    ? 0 : 74*Mth.sin((float) ((frame-SWEEP)*Math.PI/5));
        }

        void camera(ViewportEvent.ComputeCameraAngles event, LocalPlayer player) {
            int view = shoulderClothControl() ? 1 : view();
            orbit(event, player, CAMERA_YAW[view], CAMERA_PITCH[view],
                    view == 5 ? 1.62 : view == 6 ? 2.80 : 2.95, view == 5 ? 1.34 : 1.00);
        }

        void drive(Minecraft game) {
            if (standing() || !Double.isNaN(ground) || !game.player.onGround()) return;
            ground = game.player.getY();
            game.options.keyJump.setDown(true);
        }

        boolean capture(Minecraft game, Path root, String fixture, Draw draw) throws IOException {
            require(draw != null, "missing live chest/Curios draw");
            if (standing() && !game.player.onGround()) return false;
            if (standing()) require(Math.abs(draw.pitch()-pitch()) < .02 && Math.abs(draw.yaw()-yaw()) < .02,
                    "pose not applied to live head: " + draw.pitch() + "/" + draw.yaw());
            if (shoulderClothControl()) {
                save(game, root, fixture + "-frente-sin-tela-hombros");
                shot++;
                return false;
            }
            if (!control()) {
                if (rest == null) rest = draw.rigid();
                require(rest.keySet().equals(draw.rigid().keySet()) && rest.keySet().containsAll(List.of(CapePlateFit.SMALL, CapePlateFit.WIDE)),
                        "a rigid cape piece disappeared");
                float diff = 0;
                for (var entry : rest.entrySet()) {
                    var current = draw.rigid().get(entry.getKey());
                    var start = entry.getValue();
                    require(start.size() == current.size(), "changed cube topology");
                    if (CapeHood.moves(entry.getKey())) continue;
                    for (int i=0; i<start.size(); i++) diff = Math.max(diff, start.get(i).distance(current.get(i)));
                }
                double lift = Double.isNaN(ground) ? 0 : game.player.getY() - ground;
                maxDiff = Math.max(diff, maxDiff);
                require(diff < .006F, "cape refitted relative to torso: " + fixture + "/" + shot + "/" + frame + ": " + diff);
                trace.append(view() < VIEWS.length ? "orbit" : standing() ? "aim" : "jump").append('\t')
                        .append(shot*100 + frame).append('\t').append(draw.pitch()).append('\t').append(draw.yaw())
                        .append('\t').append(CAMERA_PITCH[view()]).append('\t').append(CAMERA_YAW[view()])
                        .append('\t').append(lift).append('\t').append(diff).append('\n');
            }
            if (view() < VIEWS.length) {
                String name = fixture + "-" + VIEWS[view()] + (control() ? "-sin-placas" : "");
                save(game, root, name);
                if (!control()) Files.writeString(root.resolve(name + "-caras.tsv"), draw.faces());
                if (calibration()) Files.writeString(root.resolve(fixture + "-encastre.tsv"), draw.boxes());
                shot++;
                return false;
            }
            if (standing()) {
                if (frame == 0) save(game, root, fixture + "-mirada-alta");
                if (frame == SWEEP + 2) save(game, root, fixture + "-giro-alto");
                frame++;
                return false;
            }
            if (Double.isNaN(ground)) return false;
            float lift = (float) (game.player.getY() - ground);
            if (lift > .05F) game.options.keyJump.setDown(false);
            if (lift > .65F && jumpHeight <= .65F) save(game, root, fixture + "-salto");
            jumpHeight = Math.max(jumpHeight,lift);
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
            return VIEWS.length + " vistas independientes; " + (SWEEP + TURN) + " poses de mirada; salto " + jumpHeight
                    + " bloques; desplazamiento máximo en el torso " + maxDiff + "u";
        }
    }
}
