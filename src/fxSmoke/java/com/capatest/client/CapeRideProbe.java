package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapePlayback;
import com.capatest.item.CapeState;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.vehicle.Boat;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.ViewportEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.CompletableFuture;

/** Live boat seat, vanilla W/Shift and the unmodified v1.67.36 clip inputs on the same ticks. */
final class CapeRideProbe {
    private static final int FORWARD = 24, COAST = 56, DISMOUNT = 89, END = 110;
    private final BlockPos pool;
    private final CapeWornMotion earlier = new CapeWornMotion();
    private final CapePlayback fallbackOld = new CapePlayback(), fallbackNow = new CapePlayback();
    private final StringBuilder rows = new StringBuilder("tick\tfase\tpasajero\tsuelo\tfx\tclip_36\tclip_37"
            + "\tfall_36\tfall_37\twalk_37\trun_37\tswim_37\tpaso_xz\tvel_xz\trespuesta_punta_deg\tasiento_z\n");
    private int start = -1;
    private boolean requested, quietShot, travelShot, exitShot;

    CapeRideProbe(BlockPos pool) { this.pool = pool; }

    static BlockPos pool(BlockPos pane, boolean curios) {
        return pane.offset(curios ? 31 : 19, 3, -7);
    }

    static void prepare(ServerPlayer player, BlockPos pool) {
        var world = player.serverLevel();
        player.stopRiding();
        for (int x = -4; x <= 4; x++) for (int z = -3; z <= 24; z++) {
            world.setBlock(pool.offset(x, -1, z), Blocks.PRISMARINE.defaultBlockState(), 2);
            boolean edge = Math.abs(x) == 4 || z == -3 || z == 24;
            world.setBlock(pool.offset(x, 0, z), (edge ? Blocks.PRISMARINE : Blocks.WATER).defaultBlockState(), 2);
        }
        player.getAbilities().flying = false;
        player.onUpdateAbilities();
        player.stopFallFlying();
        player.setSprinting(false);
        player.setDeltaMovement(Vec3.ZERO);
        double x = pool.getX() + .5, z = pool.getZ() + .5;
        var boat = new Boat(world, x, pool.getY() + 1.01, z);
        boat.setYRot(0);
        if (!world.addFreshEntity(boat)) throw new AssertionError("could not spawn the vanilla boat");
        // Board only once the player really left the ground; do not inject
        // onGround, model angles, or the rider's or vehicle's velocity.
        player.teleportTo(world, x, pool.getY() + 2.1, z, 0, 0);
    }

    CompletableFuture<?> drive(Minecraft game) {
        var p = game.player;
        if (start < 0) {
            if (p.getVehicle() instanceof Boat && requested) start = p.tickCount;
            else if (!requested && !p.onGround() && p.getY() > pool.getY() + .5
                    && Math.abs(p.getX() - pool.getX() - .5) < .6 && Math.abs(p.getZ() - pool.getZ() - .5) < .6) {
                requested = true;
                var server = game.getSingleplayerServer();
                var user = p.getUUID();
                return server.submit(() -> {
                    ServerPlayer player = server.getPlayerList().getPlayer(user);
                    var boats = player.serverLevel().getEntitiesOfClass(Boat.class, new AABB(pool).inflate(3));
                    if (boats.size() != 1 || !player.startRiding(boats.get(0), true))
                        throw new AssertionError("could not board the vanilla boat");
                });
            } else return null;
        }
        int t = p.tickCount - start;
        game.options.keyUp.setDown(t >= FORWARD && t < COAST);
        game.options.keyShift.setDown(t >= DISMOUNT && t < DISMOUNT + 4);
        return null;
    }

    void camera(ViewportEvent.ComputeCameraAngles event, LocalPlayer player) {
        float yaw = Mth.rotLerp((float) event.getPartialTick(), player.yBodyRotO, player.yBodyRot);
        CapePlacementProbe.orbit(event, player, yaw + 63, 13, 3.9, .85);
    }

    boolean capture(Minecraft game, float partial, CapeWalkProbe.Draw pose, ItemStack stack, Path dir, String name) throws IOException {
        if (start < 0) return false;
        var p = game.player;
        boolean seats = p.getVehicle() instanceof Boat;
        if (p.getAbilities().flying || p.isFallFlying() || (p.isPassenger() && !seats))
            throw new AssertionError(name + ": not the vanilla boat route");
        int tick = p.tickCount - start;
        var motion = CapaArmorModel.wornMotion(p);
        var raw = CapaDeteriorerItem.readWearer(p, stack);
        var worn = CapaDeteriorerItem.readClothWearer(p, stack);
        boolean moves = !p.isPassenger() && p.isAlive();
        boolean swim = moves && !p.isAutoSpinAttack();
        earlier.sample(raw, p.tickCount, partial, p.walkAnimation.position(0), p.walkAnimation.position(1),
                moves ? p.walkAnimation.speed(0) : 0, moves ? p.walkAnimation.speed(1) : 0,
                swim ? p.getSwimAmount(0) : 0, swim ? p.getSwimAmount(1) : 0);
        double displacement = Math.hypot(p.getX() - p.xo, p.getZ() - p.zo);
        String phase = tick < FORWARD ? "quieto" : tick < COAST ? "remo" : tick < DISMOUNT ? "freno" : "bajar";
        rows.append(tick + (double) partial).append('\t').append(phase).append('\t').append(seats ? 1 : 0).append('\t')
                .append(p.onGround() ? 1 : 0).append('\t').append(raw.cosmeticState()).append('\t')
                .append(fallbackOld.sample(raw, p.tickCount, swim && p.isVisuallySwimming())).append('\t')
                .append(fallbackNow.sample(worn, p.tickCount, swim && p.isVisuallySwimming())).append('\t')
                .append(earlier.weight(CapeState.FALL)).append('\t').append(pose.fall()).append('\t')
                .append(pose.walk()).append('\t').append(pose.run()).append('\t').append(pose.swim()).append('\t')
                .append(displacement).append('\t').append(p.getDeltaMovement().horizontalDistance()).append('\t')
                .append(motion.response.pitchAt(1)).append('\t').append(pose.collarZ()).append('\n');
        if (!quietShot && seats && tick >= 16 && tick < FORWARD) {
            shot(game, dir, name, "quieto");
            quietShot = true;
        }
        if (!travelShot && seats && tick >= 39 && tick < COAST && displacement > .19) {
            shot(game, dir, name, "remo");
            travelShot = true;
        }
        if (!exitShot && !seats && tick >= DISMOUNT) {
            shot(game, dir, name, "bajar");
            exitShot = true;
        }
        if (tick < END) return false;
        Files.writeString(dir.resolve(name + ".tsv"), rows);
        if (!quietShot || !travelShot || !exitShot || seats)
            throw new AssertionError(name + ": missing still, rowing, or dismount " + quietShot + "/" + travelShot + "/" + exitShot);
        return true;
    }

    private static void shot(Minecraft game, Path dir, String scene, String phase) throws IOException {
        try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
            image.writeToFile(dir.resolve(scene + "-" + phase + ".png"));
        }
    }
}
