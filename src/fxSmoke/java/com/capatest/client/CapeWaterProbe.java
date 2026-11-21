package com.capatest.client;

import net.minecraft.client.player.LocalPlayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real wade → swim → upright, on the same uninterrupted render clock. */
final class CapeWaterProbe {
    private final StringBuilder rows = new StringBuilder("time\tstage\tvisual\tswim_amount\tclip_swim\tclip_run"
            + "\tcollar_z\ttop\tmid\ttip_x\ttip_y\ttip_z\n");
    private int start = -1;
    private int uprightSince = -1, lastTick;

    void record(LocalPlayer player, float partial, String stage, CapeWalkProbe.Draw draw) {
        int tick = player.tickCount;
        if (start < 0) start = tick;
        lastTick = tick;
        if (stage.equals("exit")) {
            if (!player.isVisuallySwimming() && player.getSwimAmount(0) == 0 && player.getSwimAmount(1) == 0) {
                if (uprightSince < 0) uprightSince = tick;
            } else {
                uprightSince = -1;
            }
        }
        var tip = draw.tip();
        rows.append(tick - start + (double) partial).append('\t').append(stage).append('\t')
                .append(player.isVisuallySwimming() ? 1 : 0).append('\t')
                .append(player.getSwimAmount(partial)).append('\t').append(draw.swim()).append('\t')
                .append(draw.run()).append('\t').append(draw.collarZ()).append('\t').append(draw.top()).append('\t')
                .append(draw.mid()).append('\t').append(tip.x()).append('\t').append(tip.y()).append('\t')
                .append(tip.z()).append('\n');
    }

    boolean settled() {
        return uprightSince >= 0 && lastTick - uprightSince >= 12;
    }

    void save(Path dir, String slot) throws IOException {
        Files.writeString(dir.resolve("nado-ciclo-" + slot + ".tsv"), rows);
    }
}
