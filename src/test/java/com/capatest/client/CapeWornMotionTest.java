package com.capatest.client;

import com.capatest.item.CapePlayback;
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

    private static float swimAt(int tick) {
        return Math.min(1, .09F * Math.max(0, tick - 111));
    }

    private static void sample(CapeWornMotion gait, int tick, float fraction) {
        gait.sample(wearer(tick), tick, fraction, STEP[tick-1], STEP[tick], SPEED[tick-1], SPEED[tick],
                swimAt(tick - 1), swimAt(tick));
        normalized(gait);
    }

    private static void normalized(CapeWornMotion gait) {
        double sum = 0;
        for (CapeState state : CapeWornMotion.MODES) {
            double weight = gait.weight(state);
            if (!(weight >= 0 && weight <= 1)) throw new AssertionError(state + " fuera de rango: " + weight);
            sum += weight;
        }
        near(1, sum, 1e-12, "normalized blend");
    }

    private static void swimCycle() {
        var wet = new CapeState.Wearer(false, false, true, true, false, true, 0, -.12);
        var land = CapeState.Wearer.STILL;
        var motion = new CapeWornMotion();
        var slow = new CapeWornMotion();
        float previous = 0, current = 0;
        for (int tick = 1; tick <= 50; tick++) {
            if (tick >= 8 && tick < 24) current = Math.min(1, previous + .09F);
            if (tick >= 30) current = Math.max(0, previous - .09F);
            for (int i = 0; i <= 4; i++) {
                float partial = i / 4F;
                motion.sample(wet, tick, partial, 0, 0, 0, 0, previous, current);
                double expected = previous + (current - (double) previous) * partial;
                near(expected, motion.weight(CapeState.SWIM), 1e-12, "swim follows the visual pose at " + tick + "+" + partial);
                near(1 - expected, motion.weight(CapeState.IDLE), 1e-12, "upright cloth while wet, even off the bottom");
                near(1 - expected, motion.strideSupport(), 1e-12, "horizontal swim fades the upright gait envelope");
                normalized(motion);
                if (i == 2) {
                    slow.sample(wet, tick, .5F, 0, 0, 0, 0, previous, current);
                    near(expected, slow.weight(CapeState.SWIM), 1e-12, "FPS independent swim");
                    motion.sample(wet, tick, .125F, 0, 0, 0, 0, previous, current);
                    near(expected, motion.weight(CapeState.SWIM), 1e-12, "earlier pass didn't rewind swim");
                }
            }
            previous = current;
        }
        for (int tick = 51; tick <= 58; tick++)
            motion.sample(wet, tick, 1, tick - 51, tick - 50, .8F, .8F, 0, 0);
        near(1, motion.weight(CapeState.WALK), 0, "moving upright in water walks, not sprints");
        near(0, motion.weight(CapeState.SPRINT), 0, "no sprint flare with feet in water");
        motion.sample(wet, 80, 1, 0, 0, 0, 0, 1, 1);
        near(1, motion.weight(CapeState.SWIM), 0, "resume a swimmer already horizontal");
        // Crossing onto land while the body is still horizontal must not
        // drop the cloth in one frame or leave the swimming clip stuck.
        for (int i = 0; i < 11; i++) {
            motion.sample(land, 81 + i, 0, 0, 0, 0, 0, 1, 1);
            near(Math.max(0, 1 - .10 * i), motion.weight(CapeState.SWIM), 1e-12, "no snap on the shore");
            motion.sample(land, 81 + i, 1, 0, 0, 0, 0, 1, 1);
            near(Math.max(0, .9 - .10 * i), motion.weight(CapeState.SWIM), 1e-12, "shore fades to dry crawl");
            normalized(motion);
        }
        // A dry crawl entering water already has swimAmount=1. Ramp in
        // instead of selecting the whole SWIM clip at the boundary.
        motion.sample(wet, 92, .5F, 0, 0, 0, 0, 1, 1);
        near(.05, motion.weight(CapeState.SWIM), 1e-12, "soft entry while already horizontal");
        motion.sample(land, 200, .5F, 0, 0, 0, 0, 1, 1);
        near(0, motion.weight(CapeState.SWIM), 0, "dry crawl after render gap");
        var glide = new CapeState.Wearer(false, true, true, true, false, true, .10, -.3);
        motion.sample(glide, 20, .5F, 0, 0, 0, 0, 1, 1);
        near(1, motion.weight(CapeState.AIR), 0, "glide remains the active pose");
    }

    private static void climbSupport() {
        var cloth = new CapeWornMotion();
        var fallback = new CapePlayback();
        double last = 0;
        for (int tick = 1; tick <= 44; tick++) {
            boolean holding = tick >= 9 && tick < 18;
            boolean supported = tick < 24 || tick >= 30;
            double dy = tick < 9 ? .2 : holding ? 0 : supported ? -.15 : -.2 - .08 * (tick - 24);
            var raw = new CapeState.Wearer(false, false, false, true, holding, false, 0, dy);
            var pose = supported ? raw.withSupport() : raw;
            CapeState expected = !supported ? CapeState.FALL : holding ? CapeState.SNEAK : CapeState.IDLE;
            if (fallback.sample(pose, tick) != expected)
                throw new AssertionError("fallback doesn't recognize support on a ladder");
            if (raw.cosmeticState() != (dy < -.08 ? CapeState.FALL : CapeState.AIR))
                throw new AssertionError("cloth support changed the cosmetic input");
            near(dy, pose.vertical(), 0, "a handhold is not zero vertical speed");
            for (int i = 0; i <= 4; i++) {
                cloth.sample(pose, tick, i / 4F, 0, 0, 0, 0, 0, 0);
                normalized(cloth);
                double fall = cloth.weight(CapeState.FALL);
                if (tick < 24 || tick >= 36) near(0, fall, 0, "no FALL while supported");
                if (i == 0) near(last, fall, 1e-12, "no snap at release or recapture");
                else if (fall - last > .14/4 + 1e-12 || last - fall > .16/4 + 1e-12)
                    throw new AssertionError("ladder support bypassed the fall slew limit");
                last = fall;
            }
            if (tick == 29 && last < .8) throw new AssertionError("letting go did not restore the drop");
            if (tick == 30 && last < .6) throw new AssertionError("grabbing the ladder killed the drop in one tick");
        }
    }

    private static void passengerSupport() {
        var cape = new CapeWornMotion();
        var earlier = new CapeWornMotion();
        var fallback = new CapePlayback();
        double last = 0;
        for (int tick = 1; tick <= 54; tick++) {
            boolean seated = tick < 19 || tick >= 31;
            boolean blight = tick >= 44;
            double dy = tick < 8 ? 0 : seated ? -.18 : -.38;
            var raw = new CapeState.Wearer(blight, false, false, true, tick == 7, tick < 10, .09, dy);
            var cloth = seated ? raw.asPassenger() : raw;
            near(dy, cloth.vertical(), 0, "vehicle descent is still real travel");
            if (seated && (cloth.airborne() || cloth.sprinting() || cloth.crouching() || cloth.horizontalSquared() != 0))
                throw new AssertionError("seat is not a fall, stride or crouch");
            var expected = !seated ? CapeState.FALL : blight ? CapeState.BLIGHT : CapeState.IDLE;
            if (fallback.sample(cloth, tick) != expected)
                throw new AssertionError("fallback is not using the supported cloth pose");
            earlier.sample(raw, tick, 1, 0, 0, 0, 0, 0, 0);
            if (tick == 1) near(.22, earlier.weight(CapeState.FALL), 1e-12, "previous rest in air");
            for (int i = 0; i <= 4; i++) {
                cape.sample(cloth, tick, i / 4F, 0, 0, 0, 0, 0, 0);
                normalized(cape);
                double fall = cape.weight(CapeState.FALL);
                if (tick < 19 || tick >= 37) near(0, fall, 0, "no settled FALL as a passenger");
                if (i == 0) near(last, fall, 1e-12, "seat transition is continuous across ticks");
                else if (fall - last > .14 / 4 + 1e-12 || last - fall > .16 / 4 + 1e-12)
                    throw new AssertionError("seat transition bypassed the fall slew");
                last = fall;
            }
            if (tick == 26 && last < .6) throw new AssertionError("free fall after leaving the seat was lost");
            if (tick == 31 && last < .4) throw new AssertionError("getting back on killed the drop in one tick");
            if (tick == 52) near(1, cape.weight(CapeState.BLIGHT), 0, "seated blight still plays");
        }
    }

    private static void dryTransitions() {
        var cape = new CapeWornMotion();
        var slow = new CapeWornMotion();
        double before = 0, lastRun = 0, maxOpen = 0, maxClose = 0, maxRunRate = 0;
        for (int t = 1; t <= 90; t++) {
            boolean sprint = t >= 24 && t < 41;
            boolean water = t >= 75;
            var pose = new CapeState.Wearer(false, false, water, false, false, sprint, .09, 0);
            float speed = t >= 5 && t < 56 || t >= 74 ? 1 : 0;
            float prior = t == 5 || t == 74 ? 0 : t == 56 ? 1 : speed;
            for (int i = 0; i <= 16; i++) {
                float f = i / 16F;
                cape.sample(pose, t, f, t-1, t, prior, speed, 0, 0);
                double clearance = cape.clearancePace();
                double run = cape.weight(CapeState.SPRINT);
                if (i == 0 && t > 1) {
                    near(before, clearance, 1e-12, "no break at the hinge blend's tick edge");
                    near(lastRun, run, 1e-12, "no break at the sprint toggle");
                } else if (i > 0 && !water) {
                    maxOpen = Math.max(maxOpen, 16 * (clearance - before));
                    maxClose = Math.max(maxClose, 16 * (before - clearance));
                    maxRunRate = Math.max(maxRunRate, 16 * Math.abs(run - lastRun));
                }
                if (i == 8) {
                    slow.sample(pose, t, f, t-1, t, prior, speed, 0, 0);
                    near(clearance, slow.clearancePace(), 0, "drape independent of frame rate");
                    cape.sample(pose, t, .24F, t-1, t, prior, speed, 0, 0);
                    near(clearance, cape.clearancePace(), 0, "repeat pass cannot rewind the drape");
                }
                before = clearance;
                lastRun = run;
            }
            if (t == 9 && !(cape.clearancePace() < cape.amplitude())) throw new AssertionError("hem opens with the full impulse");
            if (t == 61 && !(cape.clearancePace() > cape.amplitude())) throw new AssertionError("hem closes with the full impulse");
            if (t == 34 || t == 52) near(cape.amplitude(), cape.clearancePace(), 1e-7, "steady gait unchanged");
            if (t == 43) near(.68359375, lastRun, 1e-12, "still unwinding three ticks after sprint");
            if (t == 50) near(0, lastRun, 0, "sprint eventually settles to walking");
            if (t == 84) near(cape.amplitude(), cape.clearancePace(), 0, "no dry damping in the water");
        }
        near(.086, maxOpen, 1e-12, "bounded dry opening rate");
        near(.054, maxClose, 1e-12, "bounded dry closing rate");
        if (!(maxRunRate > .18 && maxRunRate < .188))
            throw new AssertionError("sprint has a sharp change of weight: " + maxRunRate);
        cape.sample(CapeState.Wearer.STILL, 105, 1, 0, 0, 0, 0, 0, 0);
        near(0, cape.clearancePace(), 0, "discard transition on render gap");
    }

    private static void sprintIntoCrouch() {
        var dense = new CapeWornMotion();
        var sparse = new CapeWornMotion();
        var normalWalk = new CapeWornMotion();
        var tap = new CapeWornMotion();
        double lastTop = 0;
        for (int tick = 1; tick <= 41; tick++) {
            boolean crouch = tick >= 21 && tick < 39;
            var pose = new CapeState.Wearer(false, false, false, false, crouch, tick < 19, .09, 0);
            var walk = new CapeState.Wearer(false, false, false, false, crouch, false, .09, 0);
            var shortTap = new CapeState.Wearer(false, false, false, false, tick == 21, tick < 19, .09, 0);
            float previous = tick <= 21 ? 1 : .24F;
            float speed = tick < 21 ? 1 : .24F;
            for (int i = 0; i <= 16; i++) {
                float f = i / 16F;
                dense.sample(pose, tick, f, tick-1, tick, previous, speed, 0, 0);
                tap.sample(shortTap, tick, f, tick-1, tick, previous, speed, 0, 0);
                double top = dense.crouchTopFloor();
                double leg = dense.crouchLegFloor();
                near(top, tap.crouchTopFloor(), 0, "a quick Shift tap must not drop the remaining opening");
                if (tick < 21 || tick >= 33) {
                    near(0, top, 0, "hold only during the transition");
                    near(0, leg, 0, "no stray leg clearance in a settled pose");
                } else {
                    if (tick == 21 && i == 0) {
                        near(49.5, top, 1e-8, "retain the standing sprint opening");
                        near(64, leg, 1e-8, "retain room for the legs");
                        near(0, dense.weight(CapeState.SNEAK), 0, "do not change the clip clock");
                    } else if (lastTop - top > 6.19 / 16 + 1e-10 || top > lastTop) {
                        throw new AssertionError("crouch release did not close gradually " + tick + "/" + f);
                    }
                    if (tick == 27) near(1, dense.weight(CapeState.SNEAK), 0, "six-tick blend still settles");
                }
                if (i == 8) {
                    sparse.sample(pose, tick, f, tick-1, tick, previous, speed, 0, 0);
                    dense.sample(pose, tick, .0625F, tick-1, tick, previous, speed, 0, 0);
                    near(top, sparse.crouchTopFloor(), 0, "release independent of FPS");
                    near(leg, dense.crouchLegFloor(), 0, "earlier layer didn't rewind clearance");
                    normalWalk.sample(walk, tick, f, tick-1, tick, previous, speed, 0, 0);
                    near(0, normalWalk.crouchTopFloor(), 0, "walk to crouch is unchanged");
                }
                lastTop = top;
            }
        }
        dense.sample(CapeState.Wearer.STILL, 23, .5F, 0, 0, 0, 0, 0, 0);
        near(0, dense.crouchTopFloor(), 0, "rewind clears the held pose");
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
                case 110 -> {
                    if (!(a.weight(CapeState.FALL) > .33 && a.weight(CapeState.FALL) < .40))
                        throw new AssertionError("a short fall should only partly open the cape");
                }
                case 123 -> near(1, a.weight(CapeState.SWIM), 0, "swim");
            }
        }
        var still = CapeState.Wearer.STILL;
        a.sample(still, 10, .25F, 0, 0, 0, 0, 0, 0);
        near(1, a.weight(CapeState.IDLE), 0, "rewound wearer has no stale pose");
        a.sample(wearer(50), 50, .75F, 3, 4, 1, 1, 0, 0);
        near(1, a.weight(CapeState.SPRINT), 0, "returning visible wearer resumes current gait");
        a.sample(still, 100, .25F, 4, 4, 0, 0, 0, 0);
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
        dryTransitions();
        sprintIntoCrouch();
        swimCycle();
        climbSupport();
        passengerSupport();
        System.out.println("CapeWornMotion: marcha, frenada, paso agachado, nado, escalera y asiento continuos por portador");
    }
}
