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
    // Vanilla changes getSwimAmount by .09/tick. Match that blend in the
    // water, but don't jump on a wet/dry boundary (e.g. crawling into water).
    private static final double SWIM_PER_TICK = .10;
    // Ordinary jumps never borrow the gliding hinge. A small lift builds at
    // takeoff, then the FALL pose opens progressively with downward travel.
    private static final double JUMP_LOFT = .22;
    private static final double FALL_START = .06;
    private static final double FALL_FULL = .58; // blocks/tick downward
    private static final double FALL_OPEN = .14;
    private static final double FALL_SETTLE = .16;
    static final CapeState[] MODES = CapeState.values();
    private final double[] from = new double[MODES.length];
    private final double[] weights = new double[MODES.length];
    private CapeState target;
    private boolean sprint;
    private int lastTick;
    private float partial;
    private double start, span, sprintStart, sprintFrom;
    private double paceFrom, paceTo, swimFrom, swimTo;
    private double fallFrom, fallTo, previousFall;
    private double time, stride, amplitude, limbAmplitude, ground, strideSupport;

    final CapeResponse response = new CapeResponse();

    void sample(CapeState.Wearer wearer, int tick, float fraction,
                float stepFrom, float stepTo, float speedFrom, float speedTo,
                float vanillaSwimFrom, float vanillaSwimTo) {
        boolean aquatic = wearer.water() && !wearer.elytra();
        double swimBefore = aquatic && Float.isFinite(vanillaSwimFrom) ? unit(vanillaSwimFrom) : 0;
        double swimNow = aquatic && Float.isFinite(vanillaSwimTo) ? unit(vanillaSwimTo) : 0;
        long gap = (long) tick - lastTick;
        boolean fresh = target == null || gap < 0 || gap > MAX_GAP;
        // Extra passes at an earlier fractional time are not a new game tick.
        // Keep their gait, blends and inertia together, including while paused.
        float fractionInTick = Float.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
        partial = fresh || gap != 0 ? fractionInTick : Math.max(partial, fractionInTick);
        time = tick + (double) partial;
        if (fresh) {
            response.reset();
            target = null;
            paceTo = unit(speedFrom);
            swimTo = swimBefore;
            fallTo = previousFall = fallGoal(wearer);
        }
        if (fresh || gap > 0) {
            // Tick input, not render frequency. If a frame was skipped, use
            // the previous inputs for the elapsed ticks we didn't see.
            int missed = fresh ? 0 : (int) gap - 1;
            paceFrom = approach(paceTo, unit(speedFrom), missed);
            paceTo = approach(paceFrom, unit(speedTo), 1);
            swimFrom = slew(swimTo, swimBefore, SWIM_PER_TICK * missed);
            swimTo = slew(swimFrom, swimNow, SWIM_PER_TICK);
            fallFrom = approachFall(fallTo, previousFall, missed);
            previousFall = fallGoal(wearer);
            fallTo = approachFall(fallFrom, previousFall, 1);
            selectBase(wearer, tick);
            lastTick = tick;
        }
        blendFamily(weights, time);
        int idle = CapeState.IDLE.ordinal(), blight = CapeState.BLIGHT.ordinal();
        // A FALL clip doesn't stop the vanilla stride from carrying through
        // a jump. Keep the eased limb envelope independent of fall weight,
        // otherwise a deep drop puts the top hinge back on each live footfall.
        strideSupport = weights[idle] + weights[blight];
        // Keep the grounded gait under the drop throughout takeoff and
        // landing. The same free-hem response is still applied afterwards.
        // During a transition into Elytra, don't displace its AIR share.
        double fall = fallFrom + (fallTo - fallFrom) * partial;
        if (fall > 0) {
            int glide = CapeState.AIR.ordinal();
            for (int i = 0; i < weights.length; i++)
                if (i != glide) weights[i] *= 1 - fall;
            weights[CapeState.FALL.ordinal()] = fall * (1 - weights[glide]);
        }
        // SWIM is a layer on the other families, not a competing transition
        // that can lag the body or stay selected after it becomes upright.
        double swim = swimFrom + (swimTo - swimFrom) * partial;
        if (swim > 0) {
            for (int i = 0; i < weights.length; i++) weights[i] *= 1 - swim;
            weights[CapeState.SWIM.ordinal()] = swim;
            strideSupport *= 1 - swim;
        }
        stride = (stepFrom + ((double) stepTo - stepFrom) * partial) * STRIDE_RADIANS / TURN;
        amplitude = paceFrom + (paceTo - paceFrom) * partial;
        limbAmplitude = unit(speedFrom + ((double) speedTo - speedFrom) * partial);
        ground = weights[idle] + weights[blight];
        double step = smooth((amplitude - .04) / .49);
        double run = runWeight(time);
        weights[idle] *= 1 - step;
        weights[blight] *= 1 - step;
        weights[CapeState.WALK.ordinal()] = ground * step * (1 - run);
        weights[CapeState.SPRINT.ordinal()] = ground * step * run;
    }

    private void selectBase(CapeState.Wearer wearer, int tick) {
        CapeState family = wearer.elytra() ? CapeState.AIR : wearer.crouching() ? CapeState.SNEAK
                : wearer.blight() ? CapeState.BLIGHT : CapeState.IDLE;
        boolean running = !wearer.water() && wearer.sprinting();
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

    private static double fallGoal(CapeState.Wearer wearer) {
        if (!wearer.airborne() || wearer.elytra() || wearer.water()) return 0;
        double descent = Double.isFinite(wearer.vertical()) ? -wearer.vertical() : 0;
        return JUMP_LOFT + (1 - JUMP_LOFT) * smooth((descent - FALL_START) / (FALL_FULL - FALL_START));
    }

    private static double approachFall(double old, double goal, int ticks) {
        return slew(old, goal, ticks * (goal >= old ? FALL_OPEN : FALL_SETTLE));
    }

    private static double slew(double old, double goal, double step) {
        double delta = goal - old;
        return Math.abs(delta) <= step ? goal : old + Math.copySign(step, delta);
    }

    double weight(CapeState mode) { return weights[mode.ordinal()]; }
    double time() { return time; }
    float partial() { return partial; }
    double stride() { return stride; }
    double ground() { return ground; }
    double strideSupport() { return strideSupport; }
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
