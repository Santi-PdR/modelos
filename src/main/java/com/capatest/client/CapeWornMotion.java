package com.capatest.client;

import com.capatest.item.CapePlayback;
import com.capatest.item.CapeState;

import java.util.Arrays;

/** Motion in game ticks. Walk and sprint share the very same stride phase. */
final class CapeWornMotion {
    static final double STRIDE_RADIANS = .6662F; // HumanoidModel.setupAnim
    private static final double TURN = 2 * Math.PI;
    private static final int SPRINT_FADE = 6;
    private static final int MAX_GAP = 10;
    // Keep the mass of the drape in motion between footfalls. Vanilla's
    // limb amplitude is an input, not a step in the cape's opening angle.
    private static final double OPEN_PER_TICK = .105;
    private static final double CLOSE_PER_TICK = .070;
    private static final double PACE_RATE = .58;
    static final CapeState[] MODES = CapeState.values();
    private final CapePlayback selector = new CapePlayback();
    private final double[] from = new double[MODES.length];
    private final double[] weights = new double[MODES.length];
    private CapeState target;
    private boolean sprint;
    private int lastTick;
    private float partial;
    private double start, span, sprintStart, sprintFrom;
    private double paceFrom, paceTo;
    private double time, stride, amplitude, limbAmplitude, ground;

    final CapeResponse response = new CapeResponse();

    void sample(CapeState.Wearer wearer, int tick, float fraction,
                float stepFrom, float stepTo, float speedFrom, float speedTo) {
        long gap = (long) tick - lastTick;
        boolean fresh = target == null || gap < 0 || gap > MAX_GAP;
        // Extra passes at an earlier fractional time are not a new game tick.
        // Keep their gait, blends and inertia together, including while paused.
        float fractionInTick = Float.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
        partial = fresh || gap != 0 ? fractionInTick : Math.max(partial, fractionInTick);
        time = tick + (double) partial;
        if (fresh) {
            selector.reset();
            response.reset();
            target = null;
            paceTo = unit(speedFrom);
        }
        if (fresh || gap > 0) {
            // Tick input, not render frequency. If a frame was skipped, use
            // the previous vanilla speed for the elapsed ticks we didn't see.
            paceFrom = approach(paceTo, unit(speedFrom), fresh ? 0 : (int) gap - 1);
            paceTo = approach(paceFrom, unit(speedTo), 1);
            select(wearer, tick);
            lastTick = tick;
        }
        blendFamily(weights, time);
        stride = (stepFrom + ((double) stepTo - stepFrom) * partial) * STRIDE_RADIANS / TURN;
        amplitude = paceFrom + (paceTo - paceFrom) * partial;
        limbAmplitude = unit(speedFrom + ((double) speedTo - speedFrom) * partial);
        int idle = CapeState.IDLE.ordinal(), blight = CapeState.BLIGHT.ordinal();
        ground = weights[idle] + weights[blight];
        double step = smooth((amplitude - .04) / .49);
        double run = runWeight(time);
        weights[idle] *= 1 - step;
        weights[blight] *= 1 - step;
        weights[CapeState.WALK.ordinal()] = ground * step * (1 - run);
        weights[CapeState.SPRINT.ordinal()] = ground * step * run;
    }

    private void select(CapeState.Wearer wearer, int tick) {
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
            start = tick;
            span = 1;
            sprint = running;
            sprintStart = tick;
            sprintFrom = sprint ? 1 : 0;
        } else if (family != target) {
            blendFamily(from, tick);
            span = CapePlayback.transition(target, family);
            start = tick;
            target = family;
        }
        if (sprint != running) {
            sprintFrom = runWeight(tick);
            sprintStart = tick;
            sprint = running;
        }
    }

    private static double approach(double old, double goal, int ticks) {
        // Exactly the same one-tick step even when rendering once or many
        // times per tick. The cap also applies through a dropped frame.
        for (int i = 0; i < ticks; ++i) {
            double delta = (goal - old) * PACE_RATE;
            old += Math.max(-CLOSE_PER_TICK, Math.min(OPEN_PER_TICK, delta));
        }
        return old;
    }

    double weight(CapeState mode) { return weights[mode.ordinal()]; }
    double time() { return time; }
    float partial() { return partial; }
    double stride() { return stride; }
    double ground() { return ground; }
    double amplitude() { return amplitude; }
    double limbAmplitude() { return limbAmplitude; }

    double phase(CapeState mode, double duration) {
        double cycles = mode == CapeState.WALK || mode == CapeState.SPRINT ? stride : time / duration;
        return cycles - Math.floor(cycles); // retain the sub-frame remainder at each loop
    }

    private double runWeight(double at) {
        return sprintFrom + ((sprint ? 1 : 0) - sprintFrom) * smooth((at - sprintStart) / SPRINT_FADE);
    }

    private void blendFamily(double[] into, double at) {
        double mix = smooth((at - start) / span);
        for (int i = 0; i < into.length; ++i)
            into[i] = from[i] * (1 - mix) + (i == target.ordinal() ? mix : 0);
    }

    private static double smooth(double x) {
        double t = unit(x);
        return t * t * (3 - 2 * t);
    }

    private static double unit(double x) {
        return Math.min(1, Math.max(0, x));
    }
}
