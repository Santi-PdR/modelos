package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Inputs only: a standing jump, a running jump, then a real drop from a ledge. */
final class CapeJumpProbe {
    private static final int JUMP = 20, SPRINT = 54, RUN_JUMP = 74, BRAKE = 147, END = 169;
    private static final int EDGE = 19;
    private final StringBuilder rows = new StringBuilder("time\ton_ground\theight\tvertical\tspeed\tpace\tleg_pos\tstride\trun\tair\tfall"
            + "\tcollar_z\ttop\tmid\ttip_x\ttip_y\ttip_z\tvy\taterrizaje_deg\taterrizaje_eco\n");
    private final StringBuilder boxes = new StringBuilder(), fixedChain = new StringBuilder(), fixedHem = new StringBuilder();
    private final BlockPos deck;
    private NativeImage apex, contact, sample80, sample90, sample92, sample120, sample138, sample140;
    private int start = -1, fitTick = -1;
    private boolean rose;

    CapeJumpProbe(BlockPos deck) {
        this.deck = deck;
    }

    static BlockPos deck(BlockPos pane) {
        return pane.offset(-14, 6, -14);
    }

    static void prepare(ServerPlayer p, BlockPos deck) {
        var level = p.serverLevel();
        for (int x = -2; x <= 2; ++x)
            for (int z = -4; z <= EDGE; ++z)
                level.setBlock(deck.offset(x, 0, z), (x == 0 ? Blocks.SMOOTH_STONE : Blocks.STONE_BRICKS).defaultBlockState(), 2);
        p.getAbilities().flying = false;
        p.onUpdateAbilities();
        p.stopFallFlying();
        p.setSprinting(false);
        p.setDeltaMovement(Vec3.ZERO);
        p.teleportTo(level, deck.getX() + .5, deck.getY() + 1.001, deck.getZ() + .5, 0, 17);
    }

    void drive(Minecraft game) {
        var p = game.player;
        if (start < 0) {
            // Don't start from the previous scene while the equip/teleport
            // packets arrive. The route begins with both feet on the runway.
            if (!p.onGround() || Math.abs(p.getY() - deck.getY() - 1) > .03
                    || Math.abs(p.getX() - deck.getX() - .5) > .1 || Math.abs(p.getZ() - deck.getZ() - .5) > .1) return;
            start = p.tickCount;
        }
        int t = p.tickCount - start;
        boolean run = t >= SPRINT && t < BRAKE;
        game.options.keyUp.setDown(run);
        game.options.keySprint.setDown(run);
        game.options.keyJump.setDown(t >= JUMP && t < JUMP + 2 || t >= RUN_JUMP && t < RUN_JUMP + 2);
        if (!run) p.setSprinting(false);
    }

    boolean measureFit(int tick) {
        int t = tick - start;
        if (start < 0 || fitTick == tick || (t & 1) != 0) return false;
        // The standing-jump capture must not include sprint startup at t=54.
        // The verifier caps valid flight at <23 ticks, so JUMP+30 keeps the
        // entire flight and seven recovery ticks without mixing in the run.
        return t >= JUMP - 2 && t <= JUMP + 30 || t >= RUN_JUMP - 4 && t <= RUN_JUMP + 36
                || t >= 102 && t <= BRAKE + 6;
    }

    boolean capture(Minecraft game, float partial, CapeWalkProbe.Draw draw, CapePlacementProbe.Draw fit,
                    Path dir, String name) throws IOException {
        if (start < 0) return false;
        var p = game.player;
        if (p.isInWater() || p.isFallFlying() || p.getAbilities().flying)
            throw new AssertionError(name + ": jumping fixture is not on vanilla physics");
        double t = (double) p.tickCount - start + partial;
        double height = Mth.lerp(partial, p.yo, p.getY()) - deck.getY() - 1;
        var travel = CapaDeteriorerItem.readWearer(p, null); // only velocity, independent of slot
        var tip = draw.tip();
        rows.append(t).append('\t').append(p.onGround() ? 1 : 0).append('\t').append(height).append('\t')
                .append(travel.vertical()).append('\t').append(Math.sqrt(travel.horizontalSquared())).append('\t')
                .append(draw.pace()).append('\t').append(p.walkAnimation.position(partial)).append('\t').append(draw.stride()).append('\t')
                .append(draw.run()).append('\t').append(draw.air()).append('\t').append(draw.fall()).append('\t')
                .append(draw.collarZ()).append('\t').append(draw.top()).append('\t').append(draw.mid()).append('\t')
                .append(tip.x()).append('\t').append(tip.y()).append('\t').append(tip.z()).append('\t')
                .append(p.getDeltaMovement().y).append('\t').append(draw.landing().pitch()).append('\t')
                .append(draw.landing().heat()).append('\n');
        if (fit != null) {
            fitTick = p.tickCount;
            int elapsed = fitTick - start;
            fit.boxes().lines().forEach(box -> boxes.append(elapsed).append('\t').append(box).append('\n'));
            fit.fixedChain().lines().forEach(box -> fixedChain.append(elapsed).append('\t').append(box).append('\n'));
            fit.fixedHem().lines().forEach(box -> fixedHem.append(elapsed).append('\t').append(box).append('\n'));
        }
        if (t >= JUMP && t < JUMP + 19) {
            if (!p.onGround() && height > .7) rose = true;
            if (rose && apex == null && !p.onGround() && height > 1 && travel.vertical() < .10)
                apex = Screenshot.takeScreenshot(game.getMainRenderTarget());
            if (rose && contact == null && p.onGround() && height < .12)
                contact = Screenshot.takeScreenshot(game.getMainRenderTarget());
        }
        // Preserve fixed checkpoints around the sprint jump and later motion
        // where arm SAT maxima have appeared; they are review images, not gates.
        if (sample80 == null && t >= 80 && t < 81)
            sample80 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (sample90 == null && t >= 90 && t < 91)
            sample90 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (sample92 == null && t >= 92 && t < 93)
            sample92 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (sample120 == null && t >= 120 && t < 121)
            sample120 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (sample138 == null && t >= 138 && t < 139)
            sample138 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (sample140 == null && t >= 140 && t < 141)
            sample140 = Screenshot.takeScreenshot(game.getMainRenderTarget());
        if (t < END) return false;
        if (apex == null || contact == null) throw new AssertionError(name + ": missing apex or touchdown");
        try (var shotA = apex; var shotB = contact; var shot80 = sample80; var shot90 = sample90; var shot92 = sample92;
             var shot120 = sample120; var shot138 = sample138; var shot140 = sample140) {
            shotA.writeToFile(dir.resolve(name + "-apice.png"));
            shotB.writeToFile(dir.resolve(name + "-contacto.png"));
            if (shot80 != null) shot80.writeToFile(dir.resolve(name + "-muestra-t80.png"));
            if (shot90 != null) shot90.writeToFile(dir.resolve(name + "-muestra-t90.png"));
            if (shot92 != null) shot92.writeToFile(dir.resolve(name + "-muestra-t92.png"));
            if (shot120 != null) shot120.writeToFile(dir.resolve(name + "-muestra-t120.png"));
            if (shot138 != null) shot138.writeToFile(dir.resolve(name + "-muestra-t138.png"));
            if (shot140 != null) shot140.writeToFile(dir.resolve(name + "-muestra-t140.png"));
        }
        Files.writeString(dir.resolve(name + ".tsv"), rows);
        Files.writeString(dir.resolve(name + "-cubos.tsv"), boxes);
        Files.writeString(dir.resolve(name + "-cadena-fija.tsv"), fixedChain);
        Files.writeString(dir.resolve(name + "-dobladillo-fijo.tsv"), fixedHem);
        return true;
    }
}
