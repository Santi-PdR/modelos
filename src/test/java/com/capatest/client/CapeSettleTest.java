package com.capatest.client;

/** Deterministic stop and touchdown probes, with the pre-v1.67.3 envelope for comparison. */
public final class CapeSettleTest {
    private enum Motion { BRAKE, LAND }

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            for (Motion motion : Motion.values()) {
                CapeResponse response = new CapeResponse();
                double[] m = begin(response, motion, 0);
                for (int tick = 0; tick <= 30; tick++) {
                    double t = tick / 20.0;
                    if (tick > 0) m = stop(response, motion, t, 0);
                    System.out.print(motion + "\t" + t);
                    for (int segment = 1; segment <= 4; segment++) {
                        double w = weight(segment);
                        System.out.print("\t" + oldPitch(m, w) + "\t" + response.pitchAt(w));
                    }
                    System.out.println();
                }
            }
            return;
        }
        for (Motion motion : Motion.values()) {
            CapeResponse response = new CapeResponse();
            double[] moving = begin(response, motion, 0);
            double steady = response.pitchAt(1);
            check(steady == oldPitch(moving, 1), "steady gait changed");
            stop(response, motion, 0, 0);
            check(steady == response.pitchAt(1), "same-frame sample advanced the fold");
            double[] stopped = stop(response, motion, .2, 0);
            double tip = oldPitch(stopped, 1) - response.pitchAt(1);
            double upper = oldPitch(stopped, weight(1)) - response.pitchAt(weight(1));
            check(tip > .65 && tip > 10 * upper && upper > 0, "no progressive settling");
            check(response.pitchAt(0) == 0, "sewn root moved");
            check(Math.abs(simulate(motion, 30) - simulate(motion, 144)) < 1e-12, "settling depends on FPS");
            var wet = new CapeResponse();
            begin(wet, motion, 1);
            double[] submerged = stop(wet, motion, .2, 1);
            check((oldPitch(submerged, 1) - wet.pitchAt(1)) < .4 * tip, "no damping in water");
            for (int i = 5; i <= 40; i++) {
                double[] m = stop(response, motion, i/20.0, 0);
                for (int s = 1; s <= 4; s++) {
                    double w = weight(s), x = response.pitchAt(w);
                    check(x >= -CapeResponse.MAX_BACK * w && x <= oldPitch(m, w), "pitch outside fit envelope");
                }
            }
            check(Math.abs(response.pitchAt(1)) < (motion == Motion.BRAKE ? .01 : .09), "didn't settle");
            double[] m = stop(response, motion, 10, 0);
            check(response.pitchAt(1) == oldPitch(m, 1), "old fold persisted after leaving view");
        }
        var accelerate = new CapeResponse();
        stop(accelerate, Motion.BRAKE, 0, 0);
        accelerate.sample(.01, .88, 0, 0, 0, 0, 1, 1);
        var m = accelerate.sample(.15, .88, 0, 0, 0, 0, 1, 1);
        check(accelerate.pitchAt(1) == oldPitch(m, 1), "settling kicked on acceleration");
        System.out.println("CapeSettle: frenada, aterrizaje, amortiguación y raíces fijas, con las cotas previas");
    }

    private static double simulate(Motion motion, int fps) {
        CapeResponse r = new CapeResponse();
        begin(r, motion, 0);
        for (int i = 1; i <= fps / 2; i++) stop(r, motion, i / (double) fps, 0);
        return r.pitchAt(1);
    }

    private static double[] begin(CapeResponse r, Motion m, double water) {
        return m == Motion.BRAKE ? r.sample(0, .88, 0, 0, 0, water, 0, 1)
                : r.sample(0, .12, .62, 0, 0, water, 1, 0);
    }

    private static double[] stop(CapeResponse r, Motion m, double t, double water) {
        return r.sample(t, m == Motion.LAND ? .12 : 0, 0, 0, 0, water, 0, 0);
    }

    private static double oldPitch(double[] m, double weight) {
        double x = -(m[6] * 1.3 + m[5] * .9 + m[1] * .65 + m[0] * .62) + (m[3] + m[4]) * .72;
        return Math.max(-CapeResponse.MAX_BACK, Math.min(CapeResponse.MAX_IN, x)) * weight;
    }

    private static double weight(int s) { return Math.pow(s / 4.0, 1.45); }

    private static void check(boolean test, String message) {
        if (!test) throw new AssertionError(message);
    }
}
