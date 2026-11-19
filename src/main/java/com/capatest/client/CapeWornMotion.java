package com.capatest.client;

import com.capatest.item.CapePlayback;
import com.capatest.item.CapeState;

import java.util.Arrays;

/** Motion in game ticks. Walk and sprint share the very same stride phase. */
final class CapeWornMotion {
    static final double STRIDE_RADIANS = .6662F; // HumanoidModel.setupAnim
    private static final double TURN = 2 * Math.PI;
    private static final int SPRINT_FADE = 6;
    static final CapeState[] MODES = CapeState.values();
    private final CapePlayback selector = new CapePlayback();
    private final double[] from = new double[MODES.length];
    private final double[] weights = new double[MODES.length];
    private CapeState target;
    private boolean sprint;
    private double lastTime = Double.NaN;
    private double start, span, sprintStart, sprintFrom;
    private double time, stride, amplitude, ground;

    final CapeResponse response = new CapeResponse();

    void sample(CapeState.Wearer wearer, int tick, float partial, float walkPosition, float walkSpeed) {
        time = tick + (double) partial;
        if (!Double.isFinite(lastTime) || time < lastTime || time - lastTime > 10) {
            selector.reset();
            response.reset();
            target = null;
        }
        lastTime = time;
        CapeState pose = selector.sample(wearer, tick);
        CapeState family = switch (pose) {
            case IDLE, BLIGHT, WALK, SPRINT -> wearer.blight() ? CapeState.BLIGHT : CapeState.IDLE;
            default -> pose;
        };
        boolean running = wearer.sprinting();
        if (target == null) {
            target = family;
            Arrays.fill(from, 0);
            from[target.ordinal()] = 1;
            start = time;
            span = 1;
            sprint = running;
            sprintStart = time;
            sprintFrom = sprint ? 1 : 0;
        } else if (family != target) {
            blendFamily(from);
            span = CapePlayback.transition(target, family);
            start = time;
            target = family;
        }
        if (sprint != running) {
            sprintFrom = runWeight();
            sprintStart = time;
            sprint = running;
        }
        blendFamily(weights);
        stride = walkPosition * STRIDE_RADIANS / TURN;
        amplitude = Math.min(1, Math.max(0, walkSpeed));
        int idle = CapeState.IDLE.ordinal(), blight = CapeState.BLIGHT.ordinal();
        ground = weights[idle] + weights[blight];
        double step = smooth((amplitude - .04) / .49);
        double run = runWeight();
        weights[idle] *= 1 - step;
        weights[blight] *= 1 - step;
        weights[CapeState.WALK.ordinal()] = ground * step * (1 - run);
        weights[CapeState.SPRINT.ordinal()] = ground * step * run;
    }

    double weight(CapeState mode) { return weights[mode.ordinal()]; }
    double time() { return time; }
    double stride() { return stride; }
    double ground() { return ground; }
    double amplitude() { return amplitude; }

    double phase(CapeState mode, double duration) {
        double cycles = mode == CapeState.WALK || mode == CapeState.SPRINT ? stride : time / duration;
        return cycles - Math.floor(cycles); // retain the sub-frame remainder at each loop
    }

    private double runWeight() {
        return sprintFrom + ((sprint ? 1 : 0) - sprintFrom) * smooth((time - sprintStart) / SPRINT_FADE);
    }

    private void blendFamily(double[] into) {
        double mix = smooth((time - start) / span);
        for (int i = 0; i < into.length; ++i)
            into[i] = from[i] * (1 - mix) + (i == target.ordinal() ? mix : 0);
    }

    private static double smooth(double x) {
        double t = Math.min(1, Math.max(0, x));
        return t * t * (3 - 2 * t);
    }
}
