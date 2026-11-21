package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real ladder blocks, movement keys and gravity, without forcing the pose or velocity during the route. */
final class CapeClimbProbe {
    private static final int APPROACH = 8, HOLD = 60, SLIDE = 82, RELEASE = 91, BRAKE = 112, END = 132;
    private final BlockPos ladder;
    private final StringBuilder rows = new StringBuilder("time\tstage\tladder\tground\tshift\theight\tstep_y\tvertical"
            + "\tair\tfall\trun\tswim\tcollar_z\ttop\tmid\ttip_x\ttip_y\ttip_z\n");
    private int start = -1;
    private boolean upShot, slideShot, dropShot;

    CapeClimbProbe(BlockPos ladder) {
        this.ladder = ladder;
    }

    static BlockPos column(BlockPos pane) {
        return pane.offset(-24, -1, -20);
    }

    static void prepare(ServerPlayer p, BlockPos foot) {
        var world = p.serverLevel();
        for (int x = -2; x <= 2; x++) for (int z = -6; z <= 2; z++)
            world.setBlock(foot.offset(x, -1, z), Blocks.SMOOTH_STONE.defaultBlockState(), 3);
        for (int y = 0; y <= 9; y++) {
            world.setBlock(foot.offset(0, y, 1), Blocks.STONE_BRICKS.defaultBlockState(), 3);
            world.setBlock(foot.above(y), Blocks.LADDER.defaultBlockState().setValue(LadderBlock.FACING, Direction.NORTH), 3);
        }
        p.getAbilities().flying = false;
        p.onUpdateAbilities();
        p.stopFallFlying();
        p.setSprinting(false);
        p.setDeltaMovement(Vec3.ZERO);
        p.teleportTo(world, foot.getX() + .5, foot.getY() + .001, foot.getZ() - .5, 0, 9);
    }

    void drive(Minecraft game) {
        var p = game.player;
        if (start < 0) {
            if (!p.onGround() || Math.abs(p.getY() - ladder.getY()) > .04
                    || Math.abs(p.getX() - ladder.getX() - .5) > .1 || Math.abs(p.getZ() - ladder.getZ() + .5) > .1) return;
            start = p.tickCount;
        }
        int t = p.tickCount - start;
        game.options.keyUp.setDown(t >= APPROACH && t < HOLD);
        game.options.keyShift.setDown(t >= HOLD && t < SLIDE);
        game.options.keyDown.setDown(t >= RELEASE && t < BRAKE);
        p.setSprinting(false);
    }

    boolean capture(Minecraft game, float partial, CapeWalkProbe.Draw draw, Path dir, String name) throws IOException {
        if (start < 0) return false;
        var p = game.player;
        if (p.isFallFlying() || p.getAbilities().flying || p.isInWater())
            throw new AssertionError(name + ": ladder route left vanilla ground physics");
        double t = p.tickCount - start + (double) partial;
        boolean onLadder = p.onClimbable();
        double height = Mth.lerp(partial, p.yo, p.getY()) - ladder.getY();
        double dy = p.getY() - p.yo;
        double vertical = CapaDeteriorerItem.readWearer(p, null).vertical();
        String phase = t < HOLD ? "subida" : t < SLIDE ? "pausa" : t < RELEASE ? "desliz" : "salida";
        var tip = draw.tip();
        rows.append(t).append('\t').append(phase).append('\t').append(onLadder ? 1 : 0).append('\t')
                .append(p.onGround() ? 1 : 0).append('\t').append(p.isShiftKeyDown() ? 1 : 0).append('\t')
                .append(height).append('\t').append(dy).append('\t').append(vertical).append('\t')
                .append(draw.air()).append('\t').append(draw.fall()).append('\t').append(draw.run()).append('\t')
                .append(draw.swim()).append('\t').append(draw.collarZ()).append('\t').append(draw.top()).append('\t')
                .append(draw.mid()).append('\t').append(tip.x()).append('\t').append(tip.y()).append('\t').append(tip.z()).append('\n');
        if (!upShot && onLadder && phase.equals("subida") && height > 2.5 && dy > .08) {
            shot(game, dir, name, "subida");
            upShot = true;
        }
        if (!slideShot && onLadder && phase.equals("desliz") && dy < -.13) {
            shot(game, dir, name, "desliz");
            slideShot = true;
        }
        if (!dropShot && phase.equals("salida") && !onLadder && !p.onGround() && height > .15 && vertical < -.2) {
            shot(game, dir, name, "caida");
            dropShot = true;
        }
        if (t < END) return false;
        Files.writeString(dir.resolve(name + ".tsv"), rows);
        if (!(upShot && slideShot && dropShot)) throw new AssertionError(name + ": missing ascent/slide/drop: "
                + upShot + "/" + slideShot + "/" + dropShot);
        return true;
    }

    private static void shot(Minecraft game, Path dir, String name, String phase) throws IOException {
        try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
            image.writeToFile(dir.resolve(name + "-" + phase + ".png"));
        }
    }
}
