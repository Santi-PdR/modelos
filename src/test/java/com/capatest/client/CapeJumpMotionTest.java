package com.capatest.client;

import com.capatest.item.CapeState;

/** Simulated 1.20.1 gravity and repeated render passes, without a game client. */
final class CapeJumpMotionTest {
    private enum Route { STILL, SPRINT, LEDGE, REPEAT }

    public static void main(String[] args) {
        for (Route route : Route.values()) verify(route);
        flightAndGaps();
        System.out.println("CapeJumpMotion: despegue, ápice, caída, aterrizaje y repetición continuos; planeo intacto");
    }

    private static void verify(Route route) {
        var dense = new CapeWornMotion();
        var slow = new CapeWornMotion();
        double floor = route == Route.LEDGE ? -8 : 0;
        float pace = route == Route.SPRINT ? .84F : 0;
        double y = 0, dy = -.0784, peak = 0, last = 0;
        int airTicks = 0, firstLanding = -1;
        boolean airborne = false;
        for (int tick = 1; tick <= 70; ++tick) {
            // A ledge removes the support; a jump supplies the same .42
            // blocks/tick impulse as vanilla. Repeat before fully settled.
            if (tick == 20 || tick == 34 && route == Route.REPEAT) {
                airborne = true;
                if (route != Route.LEDGE) dy = .42;
            }
            double before = y;
            if (airborne) {
                y = Math.max(floor, y + dy);
                dy = (dy - .08) * .98;
                if (y <= floor) {
                    airborne = false;
                    dy = -.0784;
                    if (firstLanding < 0) firstLanding = tick;
                }
            }
            if (airborne) airTicks++;
            CapeState.Wearer pose = pose(airborne, route == Route.SPRINT, Math.min(dy, y - before));
            for (int i = 0; i <= 16; ++i) {
                float part = i / 16F;
                sample(dense, pose, tick, part, pace);
                double fall = dense.weight(CapeState.FALL);
                near(0, dense.weight(CapeState.AIR), 0, "a jump is not Elytra: " + route);
                peak = Math.max(peak, fall);
                near(1, dense.weight(route == Route.SPRINT ? CapeState.SPRINT : CapeState.IDLE) + fall,
                        1e-12, "maintain the underlying gait");
                near(1, dense.strideSupport(), 0, "full FALL must not switch off the eased limb envelope");
                if (route == Route.SPRINT) {
                    double room = CapeStride.groundedEnvelope(0, dense.stride(), dense.amplitude(),
                            dense.limbAmplitude(), dense.strideSupport(), 1.4);
                    near(room, CapeStride.groundedEnvelope(42, dense.stride(), dense.amplitude(),
                            dense.limbAmplitude(), dense.strideSupport(), 1.4), 1e-12, "not pulled by each running footfall");
                }
                if (i == 0) near(last, fall, 1e-12, "no jump at a tick boundary");
                else check(fall - last <= .14/16 + 1e-10 && last - fall <= .16/16 + 1e-10, "air response lost its slew limit");
                if (airborne && Math.abs(pose.vertical()) <= .09 && route != Route.REPEAT)
                    check(fall > .18 && fall < .25 || route == Route.LEDGE, "cloth kicks at the apex");
                if (i == 8) {
                    sample(slow, pose, tick, part, pace);
                    near(fall, slow.weight(CapeState.FALL), 0, "depends on render frequency");
                    sample(dense, pose, tick, .125F, pace);
                    near(fall, dense.weight(CapeState.FALL), 0, "earlier repeated draw rewound the blend");
                }
                if (tick == firstLanding + 2 && firstLanding > 0 && i == 16)
                    check(fall > .20, "do not freeze the cloth at touchdown");
                last = fall;
            }
        }
        check(airTicks >= 10 && firstLanding >= 30, "invalid fixture");
        check(route == Route.LEDGE ? peak >= .99 : peak > .73 && peak < .94, "drop magnitude doesn't follow travel: " + peak);
        near(0, last, 0, "cloth never returned to ground pose");
    }

    private static void flightAndGaps() {
        var step = new CapeWornMotion();
        var sparse = new CapeWornMotion();
        var land = CapeState.Wearer.STILL;
        var deep = pose(true, false, -.85);
        sample(step, land, 90, 1, 0);
        sample(sparse, land, 90, 1, 0);
        for (int t = 91; t <= 96; t++) sample(step, deep, t, 1, 0);
        sample(sparse, deep, 91, 1, 0);
        sample(sparse, deep, 96, 1, 0);
        near(step.weight(CapeState.FALL), sparse.weight(CapeState.FALL), 1e-12, "constant load across missed frames");
        var glide = new CapeState.Wearer(false, true, false, true, false, false, .2, -.80);
        for (int t = 97; t <= 101; t++) {
            sample(step, glide, t, 1, 0);
            near(1, step.weight(CapeState.IDLE) + step.weight(CapeState.AIR) + step.weight(CapeState.FALL), 1e-12,
                    "normalized when transitioning into Elytra");
        }
        near(1, step.weight(CapeState.AIR), 0, "full authored gliding pose");
        near(0, step.strideSupport(), 0, "do not predict footfalls in Elytra");
        near(0, step.weight(CapeState.FALL), 0, "no falling overlay on full glide");
        sample(step, deep, 125, .5F, 0);
        near(1, step.weight(CapeState.FALL), 0, "returning to view in mid-drop");
        sample(step, land, 142, .5F, 0);
        near(0, step.weight(CapeState.FALL) + step.weight(CapeState.AIR), 0, "motion persisted off screen");
    }

    private static CapeState.Wearer pose(boolean air, boolean sprint, double dy) {
        return new CapeState.Wearer(false, false, false, air, false, sprint, sprint ? .085 : 0, dy);
    }

    private static void sample(CapeWornMotion motion, CapeState.Wearer pose, int tick, float part, float pace) {
        motion.sample(pose, tick, part, (tick - 1) * pace, tick * pace, pace, pace, 0, 0);
    }

    private static void near(double want, double got, double tolerance, String label) {
        check(Math.abs(want - got) <= tolerance, label + ": " + got + " (expected " + want + ")");
    }

    private static void check(boolean good, String label) {
        if (!good) throw new AssertionError(label);
    }
}
