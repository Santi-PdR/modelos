package com.capatest.client;

import com.capatest.item.CapeState;

final class CapeWornMotionTest {
    private static CapeState.Wearer wearer(boolean run, boolean air, boolean water, double fall) {
        return new CapeState.Wearer(false, false, water, air, false, run, .08, fall);
    }

    private static void near(double expected, double actual, double tolerance, String what) {
        if (!(Math.abs(expected - actual) <= tolerance))
            throw new AssertionError(what + ": " + actual + " (expected " + expected + ")");
    }

    private static void sample(CapeWornMotion gait, CapeState.Wearer mode, double time, float pos, float speed) {
        gait.sample(mode, (int) time, (float) (time % 1), pos, speed);
        double sum = 0;
        for (CapeState state : CapeWornMotion.MODES) sum += gait.weight(state);
        near(1, sum, 1e-12, "normalized blend");
    }

    public static void main(String[] args) {
        var walk = wearer(false, false, false, 0);
        var sprint = wearer(true, false, false, 0);
        var air = wearer(false, true, false, .22);
        var fall = wearer(false, true, false, -.2);
        var water = wearer(false, false, true, 0);
        var a = new CapeWornMotion();
        var b = new CapeWornMotion();
        sample(a, walk, 16, 10F, 0);
        near(1, a.weight(CapeState.IDLE), 0, "standing");
        sample(a, walk, 17, 10.1F, .20F);
        if (a.weight(CapeState.WALK) <= 0 || a.weight(CapeState.IDLE) <= 0) throw new AssertionError("no walk fade");
        sample(a, walk, 18, 10.6F, .82F);
        near(1, a.weight(CapeState.WALK), 0, "full walk");
        sample(a, sprint, 18.125, 10.71F, .89F);
        near(0, a.weight(CapeState.SPRINT), 0, "first sprint frame");
        double expected = 10.71F * CapeWornMotion.STRIDE_RADIANS / (2 * Math.PI);
        near(expected, a.stride(), 1e-10, "actual stride phase");
        for (int i = 1; i <= 24; i++) {
            double t = 18.125 + .25 * i;
            float pos = 10.71F + i * .24F;
            sample(a, sprint, t, pos, .97F);
            double weight = a.weight(CapeState.SPRINT);
            double phase = a.phase(CapeState.SPRINT, 14.4);
            near(phase, a.phase(CapeState.WALK, 20), 0, "same phase at two speeds");
            sample(b, water, 9 + i * .25, 129, .21F);
            sample(a, sprint, t, pos, .97F);
            near(weight, a.weight(CapeState.SPRINT), 0, "same-frame duplicate after another wearer");
            near(phase, a.phase(CapeState.SPRINT, 14.4), 0, "independent clocks");
        }
        near(1, a.weight(CapeState.SPRINT), 0, "full sprint");
        sample(a, air, 24.25, 16.7F, .97F);
        near(0, a.weight(CapeState.AIR), 0, "take-off starts from old blend");
        sample(a, air, 25.25, 16.8F, .90F);
        double inAir = a.weight(CapeState.AIR);
        sample(a, fall, 25.25, 16.8F, .90F);
        near(inAir, a.weight(CapeState.AIR), 1e-12, "interrupted transition");
        near(0, a.weight(CapeState.FALL), 1e-12, "fall starts from old blend");
        sample(a, water, 29, 17.6F, .8F);
        near(1, a.weight(CapeState.FALL), 0, "fall independent of step speed");
        sample(a, water, 33, 18.F, .7F);
        near(1, a.weight(CapeState.SWIM), 0, "water blend");
        sample(a, walk, 88, 1, 0);
        near(1, a.weight(CapeState.IDLE), 0, "resume without stale pose");
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
        // At a wrap, the sub-tick beyond the clip end is not thrown away.
        sample(a, walk, 100.25, 0, 0);
        near(.0025, a.phase(CapeState.IDLE, 100), 1e-12, "loop remainder");
        System.out.println("CapeWornMotion: fase vanilla, arranque, carrera, aire, nado, repetición e independencia comprobados");
    }
}
