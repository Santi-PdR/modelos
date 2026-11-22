package com.capatest.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.ViewportEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;

/** Diagnostic only: turn the head as sprint gives way to a crouched walk, stop, then stand. */
final class CapeCombinedProbe {
    private static final int GO = 12, SHIFT = 50, STOP = 69, STAND = 90, END = 109;
    private static final int[] SHOTS = {27, 52, 63, 77, 103};
    private final BlockPos runway;
    private final int direction;
    private final boolean followNape;
    private final boolean followNeutral = "1".equals(System.getenv("CAPA_REPOSO_NUCA"));
    private final StringBuilder rows = new StringBuilder("time\tleg_pos\tleg_speed\tstride\tground\tsprinting\tcrouching\t"
            + "walk\trun\tsneak\tair\tfall\tswim\ttop\tmid\ttip_x\ttip_y\ttip_z\tseat_z\tpitch\tyaw\tfit\tcrouch_floor\trear_tuck\timage\n");
    private final StringBuilder boxes = new StringBuilder(), head = new StringBuilder();
    private final Map<GeoBone, List<GeoCube>> omitted = new LinkedHashMap<>();
    private int start = -1, fitTick = -1, nextShot;
    private LocalPlayer aimed;
    private float originalHead, originalHeadOld, originalPitch, originalPitchOld;

    CapeCombinedProbe(BlockPos runway, int direction, boolean followNape) {
        this.runway = runway;
        this.direction = direction;
        this.followNape = followNape;
    }

    static BlockPos runway(BlockPos spawn) { return spawn.offset(-6, -1, -6); }

    static void prepare(ServerPlayer p, BlockPos floor) {
        var level = p.serverLevel();
        for (int x = -7; x <= 7; x++)
            for (int z = -6; z <= 20; z++)
                level.setBlock(floor.offset(x, 0, z), Blocks.SNOW_BLOCK.defaultBlockState(), 2);
        p.getAbilities().flying = false;
        p.onUpdateAbilities();
        p.setSprinting(false);
        p.setDeltaMovement(Vec3.ZERO);
        p.teleportTo(level, floor.getX() + .5, floor.getY() + 1.001, floor.getZ() + .5, 0, 0);
    }

    void drive(Minecraft game) {
        var p = game.player;
        if (start < 0) {
            if (!p.onGround() || Math.abs(p.getY() - runway.getY() - 1) > .04
                    || Math.abs(p.getX() - runway.getX() - .5) > .10
                    || Math.abs(p.getZ() - runway.getZ() - .5) > .10) return;
            start = p.tickCount;
        }
        int t = p.tickCount - start;
        boolean run = t >= GO && t < SHIFT;
        game.options.keyUp.setDown(t >= GO && t < STOP);
        game.options.keySprint.setDown(run);
        game.options.keyShift.setDown(t >= SHIFT && t < STAND);
        if (!run) p.setSprinting(false);
    }

    private static float ease(float t) {
        t = Mth.clamp(t, 0, 1);
        return t*t*(3-2*t);
    }

    private static float turn(int t) {
        return ease((t-34)/13F) * (1-ease((t-STOP)/17F));
    }

    void aim(LocalPlayer p) {
        if (start < 0) return;
        // Only the look changes for the draw. Movement keys, body/limb poses,
        // equip route, and crouch physics all go through the real client.
        int t = p.tickCount - start;
        aimed = p;
        originalHead = p.getYHeadRot();
        originalHeadOld = p.yHeadRotO;
        originalPitch = p.getXRot();
        originalPitchOld = p.xRotO;
        p.setYHeadRot(p.yBodyRot + direction*55*turn(t));
        p.yHeadRotO = p.yBodyRotO + direction*55*turn(t-1);
        p.setXRot(-35*turn(t));
        p.xRotO = -35*turn(t-1);
    }

    void restoreAim() {
        if (aimed == null) return;
        aimed.setYHeadRot(originalHead);
        aimed.yHeadRotO = originalHeadOld;
        aimed.setXRot(originalPitch);
        aimed.xRotO = originalPitchOld;
        aimed = null;
    }

    void camera(ViewportEvent.ComputeCameraAngles event, LocalPlayer p) {
        float yaw = Mth.rotLerp((float) event.getPartialTick(), p.yBodyRotO, p.yBodyRot);
        CapePlacementProbe.orbit(event, p, yaw + direction*57, 13, 3.3, .97);
    }

    // Counterfactual only, compiled in the disposable Forge client. Omit
    // the same cubes in both passes, then restore the shared baked lists.
    void omit(CapaArmorRenderer renderer, String prefix) {
        if (!omitted.isEmpty()) throw new AssertionError("nape control was not restored");
        try {
            for (var registered : renderer.getGeoModel().getAnimationProcessor().getRegisteredBones()) {
                if (!(registered instanceof GeoBone bone) || !bone.getName().startsWith(prefix)) continue;
                var cubes = bone.getCubes();
                if (cubes.isEmpty()) throw new AssertionError("missing control piece: " + bone.getName());
                omitted.put(bone, List.copyOf(cubes));
                cubes.clear();
            }
            if (omitted.size() != (prefix.equals("v18_chain_") ? 8 : 5))
                throw new AssertionError("missing nape control: " + prefix);
        } catch (RuntimeException | AssertionError e) {
            restoreCubes();
            throw e;
        }
    }

    void restoreCubes() {
        omitted.forEach((bone, cubes) -> bone.getCubes().addAll(cubes));
        omitted.clear();
    }

    boolean measureFit(int tick) {
        return start >= 0 && tick - start >= 24 && tick != fitTick;
    }

    boolean capture(Minecraft game, float partial, CapeWalkProbe.Draw pose, CapePlacementProbe.Draw fit,
                    Path root, String name) throws IOException {
        if (start < 0) return false;
        var p = game.player;
        int tick = p.tickCount - start;
        double t = tick + (double) partial;
        String image = "-";
        boolean landmark = nextShot < SHOTS.length && tick >= SHOTS[nextShot];
        boolean unwind = followNape && ((tick >= 78 && tick <= 83) || (followNeutral && tick >= 87 && tick <= 89));
        if (fit != null && (landmark || unwind)) {
            if (landmark) {
                if (tick > SHOTS[nextShot] + 2) throw new AssertionError(name + ": missed screenshot near " + SHOTS[nextShot]);
                nextShot++;
            }
            image = String.format(Locale.ROOT, "%s-%03d.png", name, tick);
            head.append(tick).append('\t').append(fit.headTop());
            try (var shot = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                shot.writeToFile(root.resolve(image));
            }
        }
        if (fit != null) {
            fitTick = p.tickCount;
            fit.boxes().lines().forEach(box -> boxes.append(tick).append('\t').append(box).append('\n'));
        }
        var tip = pose.tip();
        rows.append(t).append('\t').append(p.walkAnimation.position(partial)).append('\t')
                .append(p.walkAnimation.speed(partial)).append('\t').append(pose.stride()).append('\t')
                .append(p.onGround() ? 1 : 0).append('\t').append(p.isSprinting() ? 1 : 0).append('\t')
                .append(p.isCrouching() ? 1 : 0).append('\t').append(pose.walk()).append('\t').append(pose.run())
                .append('\t').append(pose.sneak()).append('\t').append(pose.air()).append('\t').append(pose.fall())
                .append('\t').append(pose.swim()).append('\t').append(pose.top()).append('\t').append(pose.mid())
                .append('\t').append(tip.x()).append('\t').append(tip.y()).append('\t').append(tip.z())
                .append('\t').append(pose.collarZ()).append('\t').append(fit == null ? 0 : fit.pitch())
                .append('\t').append(fit == null ? 0 : fit.yaw()).append('\t').append(fit == null ? 0 : 1)
                .append('\t').append(CapaArmorModel.wornMotion(p).crouchTopFloor())
                .append('\t').append(fit == null ? 0 : fit.rearTuck()).append('\t').append(image).append('\n');
        if (tick < END) return false;
        Files.writeString(root.resolve(name + ".tsv"), rows);
        Files.writeString(root.resolve(name + "-cubos.tsv"), boxes);
        Files.writeString(root.resolve(name + "-cabeza.tsv"), head);
        return true;
    }
}
