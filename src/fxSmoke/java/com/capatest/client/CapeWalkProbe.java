package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Live F5 recording. Inputs move the player; no keyframes or limb poses are injected. */
final class CapeWalkProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    static final String BODY = "chestplate", SEAT = "cape_seat_fit", TOP = "cape_top",
            MID = "cape_mid", BOTTOM = "cape_bottom", TIP = "v17_ribbon_6_seg4", HOOD = "v17_cowl_back_1";
    static final int DURATION = 225;
    static final int CROUCH_IN = 310, CROUCH_OUT = 382, QUIET_END = 401;
    private final Matrix4f[] matrices = new Matrix4f[5];
    private Vector3f crown;
    private Matrix4f mount;
    private CapeChain.Motion chain;
    private final CapaArmorRenderer renderer;
    private boolean active;
    private boolean testedRepeat;

    private CapeWalkProbe(CapaArmorRenderer renderer) {
        super(renderer);
        this.renderer = renderer;
    }

    static void arm(CapaArmorRenderer renderer) {
        CapeWalkProbe probe = get(renderer);
        java.util.Arrays.fill(probe.matrices, null);
        probe.crown = null;
        probe.mount = null;
        probe.chain = CapeChain.REST;
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
        if (CapeFit.BONE.equals(bone.getName())) mount = new Matrix4f(stack.last().pose());
        if (bone.getName().equals("v18_chain_4") && !bone.getCubes().isEmpty() && !bone.isHidden()) {
            var fixed = CapePlacementProbe.chainControl(renderer, mount, bone);
            var basis = new Matrix4f(mount).invert();
            var live = new Matrix4f(basis).mul(stack.last().pose());
            var rest = basis.mul(fixed.last().pose());
            var shift = live.getTranslation(new Vector3f()).sub(rest.getTranslation(new Vector3f())).mul(16);
            var expected = renderer.chain();
            if (!shift.equals(new Vector3f(0, (float)-expected.drop(), (float)expected.away()), .0002F))
                throw new AssertionError("walk chain shift did not reach the rendered link: " + shift + " / " + expected);
            chain = expected == CapeChain.REST ? CapeChain.REST : new CapeChain.Motion(-shift.y(), shift.z());
        }
        if (HOOD.equals(bone.getName()) && !bone.getCubes().isEmpty()) {
            // These vertices are in GEO space, not offsets from this bone.
            // Measure a real crown corner, not a point below the mannequin.
            var cube = bone.getCubes().get(0);
            Vector3f point = null;
            for (var face : cube.quads()) if (face != null)
                for (var v : face.vertices()) if (point == null || v.position().y() > point.y()) point = v.position();
            if (point == null) throw new AssertionError("missing crown vertex");
            stack.pushPose();
            try {
                RenderUtils.translateToPivotPoint(stack, cube);
                RenderUtils.rotateMatrixAroundCube(stack, cube);
                RenderUtils.translateAwayFromPivotPoint(stack, cube);
                crown = stack.last().pose().transformPosition(point, new Vector3f());
            } finally {
                stack.popPose();
            }
        }
    }

    static Draw finish(CapaArmorRenderer renderer, float partial, boolean withoutCrown) {
        CapeWalkProbe probe = get(renderer);
        probe.active = false;
        var matrices = probe.matrices;
        for (var matrix : matrices) if (matrix == null) throw new AssertionError("missing live walk matrix");
        var inverseBody = new Matrix4f(matrices[0]).invert();
        var seat = new Matrix4f(inverseBody).mul(matrices[1]);
        var tip = new Matrix4f(inverseBody).mul(matrices[4]);
        if (withoutCrown != (probe.crown == null)) throw new AssertionError("unexpected crown in test draw");
        var hood = withoutCrown ? new Vector3f() : inverseBody.transformPosition(probe.crown, new Vector3f()).mul(16);
        var player = Minecraft.getInstance().player;
        CapeWornMotion motion = CapaArmorModel.wornMotion(player);
        if (!probe.testedRepeat && motion.weight(CapeState.WALK) > .98) {
            probe.testedRepeat = true;
            verifyInterleavedSample(renderer, player, partial);
        }
        var mode = motion.weight(CapeState.SPRINT) > .5 ? CapeState.SPRINT
                : motion.weight(CapeState.WALK) > .5 ? CapeState.WALK
                : motion.weight(CapeState.SNEAK) > .5 ? CapeState.SNEAK : CapeState.IDLE;
        requireClock(player, partial, motion);
        return new Draw(mode.name(), motion.stride(), motion.amplitude(), motion.weight(CapeState.WALK), motion.weight(CapeState.SPRINT),
                motion.weight(CapeState.SWIM), motion.weight(CapeState.AIR), motion.weight(CapeState.FALL),
                seat.transformPosition(0, 25/16F, 7.4F/16, new Vector3f()).z() * 16,
                -Math.toDegrees(renderer.getGeoModel().getBone(TOP).orElseThrow().getRotX()),
                -Math.toDegrees(renderer.getGeoModel().getBone(MID).orElseThrow().getRotX()),
                tip.transformPosition(0, 0, .36F, new Vector3f()).mul(16), hood,
                loosePitch(renderer, 2), loosePitch(renderer, 9), motion.weight(CapeState.SNEAK),
                -Math.toDegrees(renderer.getGeoModel().getBone(BOTTOM).orElseThrow().getRotX()), motion.clearancePace(),
                motion.response.turnWake(1), probe.chain, motion.response.braking(), motion.chainSupport());
    }

    private static double loosePitch(CapaArmorRenderer renderer, int ribbon) {
        var bone = renderer.getGeoModel().getBone("v17_ribbon_" + ribbon + "_seg4").orElseThrow();
        return -Math.toDegrees(bone.getRotX() - bone.getInitialSnapshot().getRotX());
    }

    private static void requireClock(LivingEntity wearer, float partial, CapeWornMotion motion) {
        if (Math.abs(motion.time() - (wearer.tickCount + (double) partial)) > .0001)
            throw new AssertionError("walking cape and player are on different render ticks");
    }

    private static void verifyInterleavedSample(CapaArmorRenderer renderer, LivingEntity walker, float partial) {
        var model = renderer.getGeoModel();
        var stack = renderer.getCurrentStack();
        var item = (CapaDeteriorerItem) stack.getItem();
        var bones = new GeoBone[] {model.getBone(TOP).orElseThrow(), model.getBone(MID).orElseThrow(), model.getBone(TIP).orElseThrow()};
        var original = java.util.Arrays.stream(bones).map(CapeWalkProbe::rotation).toList();
        var hood = ((CapaArmorModel) model).hood();
        var chain = ((CapaArmorModel) model).chain();
        // Exercise a second wearer on the same actual baked rig, at the
        // same partial tick, then replay the visible wearer in the same frame.
        var still = new ArmorStand(walker.level(), walker.getX(), walker.getY(), walker.getZ());
        model.handleAnimations(item, Long.MIN_VALUE, state(item, still, stack, partial));
        if (rotation(bones[2]).distance(original.get(2)) < .0002F)
            throw new AssertionError("another wearer inherited the walk pose");
        if (((CapaArmorModel) model).chain() != CapeChain.REST)
            throw new AssertionError("another wearer inherited the chain swing");
        model.handleAnimations(item, renderer.getInstanceId(item), state(item, walker, stack, partial));
        for (int i = 0; i < bones.length; ++i)
            if (!original.get(i).equals(rotation(bones[i]), .000002F))
                throw new AssertionError("repeated same-frame animation changed " + bones[i].getName());
        if (!hood.equals(((CapaArmorModel) model).hood()))
            throw new AssertionError("repeated same-frame animation changed hood");
        if (!chain.equals(((CapaArmorModel) model).chain()))
            throw new AssertionError("repeated same-frame animation changed chain");
    }

    private static AnimationState<CapaDeteriorerItem> state(CapaDeteriorerItem item, LivingEntity wearer,
                                                           ItemStack stack, float partial) {
        var state = new AnimationState<>(item, 0, 0, partial, false);
        state.setData(DataTickets.ENTITY, wearer);
        state.setData(DataTickets.ITEMSTACK, stack);
        return state;
    }

    private static Vector3f rotation(GeoBone bone) {
        return new Vector3f(bone.getRotX(),bone.getRotY(),bone.getRotZ());
    }

    record Draw(String clip, double stride, double pace, double walk, double run, double swim, double air, double fall,
                double collarZ, double top, double mid, Vector3f tip, Vector3f hood, double edge2, double edge9,
                double sneak, double bottom, double clearancePace, double turnWake, CapeChain.Motion chain,
                double braking, double chainSupport) {}

    static final class Route {
        private final StringBuilder rows = new StringBuilder("time\tleg_pos\tleg_speed\tclip\tstride\twalk\trun\tcollar_z\ttop\tmid\ttip_x\ttip_y\ttip_z\tpace\thood_x\thood_y\thood_z\tedge2\tedge9\tsneak\tbottom\tage\tcrouching\tclearance_pace\tgiro_punta_deg\tcadena_caida_u\tcadena_salida_u\tfreno_lento\tapoyo_cadena\n");
        private final boolean quietStudy;
        private int start = -1;
        private int shot;
        private int count, lastMotionShot = -1;
        private final int[] landmarks = {16, 44, 63, 84, 110, 149};

        Route(boolean quietStudy) { this.quietStudy = quietStudy; }

        void drive(Minecraft game) {
            var p = game.player;
            if (start < 0) start = p.tickCount;
            int t = p.tickCount - start;
            boolean sprint = t >= 96 && t < 130 || t >= 175 && t < 194;
            game.options.keyUp.setDown(t >= 20 && t < 73 || t >= 96 && t < 130 || t >= 158 && t < 208);
            game.options.keyLeft.setDown(t >= 73 && t < 92);
            game.options.keySprint.setDown(sprint);
            game.options.keyShift.setDown(quietStudy && t >= CROUCH_IN && t < CROUCH_OUT);
            if (!sprint) p.setSprinting(false);
            // Real movement in two directions; turn smoothly during the strafe.
            float turn = 30 * Math.max(0F, Math.min(1F, (t - 74) / 17F));
            p.setYRot(3 + turn);
            p.setXRot(quietStudy && t >= DURATION ? 8 : 79);
        }

        boolean capture(Minecraft game, float partial, Draw draw, Path dir, String name) throws IOException {
            if (start < 0) return false;
            var p = game.player;
            double t = (double) p.tickCount - start + partial;
            rows.append(t).append('\t').append(p.walkAnimation.position(partial)).append('\t')
                    .append(p.walkAnimation.speed(partial)).append('\t').append(draw.clip()).append('\t')
                    .append(draw.stride()).append('\t').append(draw.walk()).append('\t').append(draw.run()).append('\t').append(draw.collarZ()).append('\t')
                    .append(draw.top()).append('\t').append(draw.mid()).append('\t').append(draw.tip().x()).append('\t')
                    .append(draw.tip().y()).append('\t').append(draw.tip().z()).append('\t').append(draw.pace()).append('\t')
                    .append(draw.hood().x()).append('\t').append(draw.hood().y()).append('\t').append(draw.hood().z())
                    .append('\t').append(draw.edge2()).append('\t').append(draw.edge9())
                    .append('\t').append(draw.sneak()).append('\t').append(draw.bottom())
                    .append('\t').append((double) p.tickCount + partial).append('\t').append(p.isCrouching() ? 1 : 0)
                    .append('\t').append(draw.clearancePace()).append('\t').append(draw.turnWake())
                    .append('\t').append(draw.chain().drop()).append('\t').append(draw.chain().away())
                    .append('\t').append(draw.braking()).append('\t').append(draw.chainSupport()).append('\n');
            count++;
            if (shot < landmarks.length && t >= landmarks[shot]) {
                try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                    image.writeToFile(dir.resolve(String.format(Locale.ROOT, "%s-%02d.png", name, landmarks[shot])));
                }
                shot++;
            }
            // One real F5 frame every two ticks for a short, reviewable sequence.
            int tick = (int) t;
            boolean gaitShot = tick % 2 == 0 && (tick >= 40 && tick < 64 || tick >= 106 && tick < 130);
            boolean changeShot = tick % 2 == 0 && tick >= 192 && tick < 218;
            boolean stillShot = tick >= 230 && tick < 302 && (tick-230) % 6 == 0
                    || tick >= 318 && tick < 370 && (tick-318) % 4 == 0;
            if (quietStudy && tick != lastMotionShot && (gaitShot || changeShot || stillShot)) {
                lastMotionShot = tick;
                String track = gaitShot ? "ciclo" : changeShot ? "cambio" : "calma";
                try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                    image.writeToFile(dir.resolve(String.format(Locale.ROOT, "%s-%s-%03d.png", name, track, tick)));
                }
            }
            if (t < (quietStudy ? QUIET_END : DURATION)) return false;
            if (count < 135) throw new AssertionError("too few walk frames: " + count);
            Files.writeString(dir.resolve(name + ".tsv"), rows);
            return true;
        }
    }

}
