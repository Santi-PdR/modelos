package com.capatest.client;

import com.capatest.item.CapeState;

final class CapeWornMotionTest {
    private static final int TICKS = 152;
    private static final float[] SPEED = new float[TICKS + 1], STEP = new float[TICKS + 1];

    private static CapeState.Wearer wearer(int tick) {
        boolean sprint = tick >= 39 && tick < 64;
        boolean air = tick >= 105 && tick < 112;
        return new CapeState.Wearer(false, false, tick >= 112 && tick < 127, air, tick >= 94 && tick < 105,
                sprint, SPEED[tick] * SPEED[tick] * .12, air ? tick < 108 ? .22 : -.2 : 0);
    }

    private static void near(double expected, double actual, double tolerance, String what) {
        if (!(Math.abs(expected - actual) <= tolerance))
            throw new AssertionError(what + ": " + actual + " (expected " + expected + ")");
    }

    private static void sample(CapeWornMotion gait, int tick, float fraction) {
        gait.sample(wearer(tick), tick, fraction, STEP[tick-1], STEP[tick], SPEED[tick-1], SPEED[tick]);
        double sum = 0;
        for (CapeState state : CapeWornMotion.MODES) sum += gait.weight(state);
        near(1, sum, 1e-12, "normalized blend");
    }

    public static void main(String[] args) {
        for (int tick = 1; tick <= TICKS; ++tick) {
            double goal = tick < 16 || tick >= 80 ? 0 : tick >= 39 && tick < 64 ? 1 : .86;
            SPEED[tick] = (float) (SPEED[tick-1] + (goal - SPEED[tick-1]) * .4);
            STEP[tick] = STEP[tick-1] + SPEED[tick];
        }
        var a = new CapeWornMotion();
        var b = new CapeWornMotion();
        var interleaved = new CapeWornMotion();
        double precedingPace = 0, precedingPhase = 0;
        double[] previous = new double[CapeWornMotion.MODES.length];
        for (int tick = 1; tick <= TICKS; ++tick) {
            for (int i = 0; i <= 64; ++i) {
                float fraction = i / 64F;
                sample(a, tick, fraction);
                if (i == 0 && tick > 1) {
                    near(precedingPace, a.amplitude(), 1e-12, "continuous across tick edge");
                    near(precedingPhase, a.stride(), 1e-12, "unbroken phase across tick edge");
                    for (CapeState mode : CapeWornMotion.MODES)
                        near(previous[mode.ordinal()], a.weight(mode), 1e-12, "continuous clip mix: " + mode);
                }
                double expected = (STEP[tick-1] + (STEP[tick] - (double) STEP[tick-1]) * fraction)
                        * CapeWornMotion.STRIDE_RADIANS / (2 * Math.PI);
                near(expected, a.stride(), 1e-12, "phase paired with vanilla gait");
                near(a.phase(CapeState.WALK, 20), a.phase(CapeState.SPRINT, 14.4), 0, "one phase at two speeds");
                if (i == 32) {
                    sample(b, tick, fraction); // first frame of this tick, at reduced FPS
                    near(a.amplitude(), b.amplitude(), 0, "pace independent of render rate");
                    for (CapeState mode : CapeWornMotion.MODES)
                        near(a.weight(mode), b.weight(mode), 0, "transition independent of render rate");
                    sample(interleaved, tick, .25F);
                    sample(a, tick, .125F); // out-of-order layer / pause interpolation
                    near(fraction, a.partial(), 0, "earlier pass doesn't rewind clock");
                    near(expected, a.stride(), 0, "interleaved pass kept stride");
                    near(b.amplitude(), a.amplitude(), 0, "interleaved pass kept inertia");
                    for (CapeState mode : CapeWornMotion.MODES)
                        near(b.weight(mode), a.weight(mode), 0, "interleaved pass kept blend");
                }
                if (i > 0 && !(a.amplitude() - precedingPace <= .106 / 64
                        && precedingPace - a.amplitude() <= .071 / 64))
                    throw new AssertionError("cape gait accelerated in one frame at " + tick + "+" + fraction);
                precedingPace = a.amplitude();
                precedingPhase = a.stride();
            }
            for (CapeState mode : CapeWornMotion.MODES) previous[mode.ordinal()] = a.weight(mode);
            switch (tick) {
                case 15 -> near(1, a.weight(CapeState.IDLE), 0, "standing");
                case 34, 75 -> near(1, a.weight(CapeState.WALK), 0, "full walk");
                case 48 -> near(1, a.weight(CapeState.SPRINT), 0, "full sprint");
                case 104 -> near(1, a.weight(CapeState.SNEAK), 0, "crouch");
                case 110 -> near(1, a.weight(CapeState.FALL), 0, "fall independent of step speed");
                case 119 -> near(1, a.weight(CapeState.SWIM), 0, "swim");
            }
        }
        var still = CapeState.Wearer.STILL;
        a.sample(still, 10, .25F, 0, 0, 0, 0);
        near(1, a.weight(CapeState.IDLE), 0, "rewound wearer has no stale pose");
        a.sample(wearer(50), 50, .75F, 3, 4, 1, 1);
        near(1, a.weight(CapeState.SPRINT), 0, "returning visible wearer resumes current gait");
        a.sample(still, 100, .25F, 4, 4, 0, 0);
        near(.0025, a.phase(CapeState.IDLE, 100), 1e-12, "loop remainder");
        double maxJump = 0, prev = 0;
        for (int i = 0; i <= 100; i++) {
            double phase = .01 * i;
            double actual = 44 * Math.abs(Math.cos(phase * Math.PI * 2));
            double clearance = CapeStride.walkEnvelope(actual, phase, .8, 1, 1);
            if (clearance < actual) throw new AssertionError("gait removed clearance for an actual limb");
            if (i > 0) maxJump = Math.max(maxJump, Math.abs(clearance - prev));
            prev = clearance;
        }
        if (maxJump > .27) throw new AssertionError("stride envelope jumps: " + maxJump);
        double eased = CapeStride.groundedEnvelope(0, .2, .20, .70, 1, 1);
        near(eased, CapeStride.groundedEnvelope(39, .2, .20, .70, 1, 1), 1e-12,
                "raw limb cannot jerk the heavy hinge during a footfall");
        near(49, CapeStride.groundedEnvelope(49, .2, .20, .70, 0, 1), 0,
                "non-grounded pose keeps actual limb clearance");
        if (CapeStride.groundedEnvelope(55, .2, .20, .70, 1, 1) < eased + 10)
            throw new AssertionError("clearance for additional arm gesture lost");
        System.out.println("CapeWornMotion: ticks, fracciones, cambio de paso, frenado, pausa e independencia comprobados");
    }
}
