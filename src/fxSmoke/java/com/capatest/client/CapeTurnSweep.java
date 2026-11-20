package com.capatest.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Full standing head turn in the real F5 camera, with the idle arm motion left running. */
final class CapeTurnSweep {
    static final String CROWN = "v17_cowl_back_0";
    private static final int LIMIT = 79;
    private final float pitch;
    private final double[] front = new double[4 * LIMIT + 1];
    private final StringBuilder trace = new StringBuilder("frame\tpitch\tyaw\tcrown_front_z\n");
    private int frame;
    private double largestStep;

    CapeTurnSweep(float pitch) { this.pitch = pitch; }

    private static int yaw(int frame) {
        if (frame <= LIMIT) return frame;
        if (frame <= 3 * LIMIT) return 2 * LIMIT - frame;
        return frame - 4 * LIMIT;
    }

    CapeLookSweep.Pose pose() { return new CapeLookSweep.Pose(pitch, yaw(frame)); }

    boolean capture(Minecraft game, Path root, String name, CapeHistoricFitProbe.Draw solid,
                    CapeLookSweep.Draw matrix) throws IOException {
        require(solid != null && Double.isFinite(solid.crownFront()), name + ": missing live collar draw");
        require(matrix != null && matrix.passesAgree(), name + ": opaque/glow collar matrices differ");
        int turn = yaw(frame), side = Math.abs(turn);
        double z = solid.crownFront();
        front[frame] = z;
        trace.append(frame).append('\t').append(pitch).append('\t').append(turn).append('\t').append(z).append('\n');
        if (frame <= LIMIT && (side == 0 || side == 43 || side == 48 || side == 60 || side == 68 || side == LIMIT)
                || frame == 2 * LIMIT + 60 || frame == 3 * LIMIT) {
            try (var image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                image.writeToFile(root.resolve(String.format(Locale.ROOT,"%s-%+03d.png",name,turn)));
            }
        }
        if (frame < front.length - 1) {
            frame++;
            return false;
        }
        Files.writeString(root.resolve(name + ".tsv"),trace);
        require(front[43] > 3.4 && front[43] < 3.95 && front[60] > 4.10 && front[60] < 4.47
                        && front[LIMIT] > 6.65,
                name + ": lost support or opening at 43/60/79 degrees: " + front[43] + "/" + front[60] + "/" + front[LIMIT]);
        require(front[60]-front[48] < .38, name + ": large retreat between 48 and 60 degrees");
        for (int i = 1; i < front.length; i++) {
            double zStep = front[i] - front[i-1];
            largestStep = Math.max(largestStep,Math.abs(zStep));
            int outward = Math.abs(yaw(i)) - Math.abs(yaw(i-1));
            require(Math.abs(zStep) < .335 && outward*zStep >= -.025,
                    name + ": jump or reversal at frame " + i + ": " + zStep);
            require(Math.abs(front[i]-front[Math.abs(yaw(i))]) < .025,
                    name + ": differing fit on other side or on the way back");
        }
        return true;
    }

    String summary() {
        return String.format(Locale.ROOT,
                "%d cuadros F5 de 0 a +79°, −79° y de vuelta; cuello Z %.2fu a 43°, %.2fu a 48°, %.2fu a 60° y %.2fu a 79°; paso máximo %.3fu; sólido y emisión coinciden",
                front.length,front[43],front[48],front[60],front[LIMIT],largestStep);
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
