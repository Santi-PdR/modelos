package com.capatest.client;

/** Checks the halo-only wake at the same phase and exposure as the old halo. */
public final class CapeHaloWakeTest {
    private static final int ID = 3;
    private static final double SPEED = .352;

    public static void main(String[] args) {
        if (args.length == 5 && args[0].equals("--samples")) {
            export(Double.parseDouble(args[1]), Double.parseDouble(args[2]),
                    Double.parseDouble(args[3]), Double.parseDouble(args[4]));
            return;
        }
        var response = new CapeResponse();
        sample(response, 0, 0, 0);
        int lipOn = 0, edgeOn = 0, lipOff = 0, edgeOff = 0;
        double maxLipOn = 0, maxEdgeOn = 0, maxLipOff = 0, maxEdgeOff = 0;
        for (int i = 1; i <= 240; ++i) {
            double time = i / 40.0;
            sample(response, time, i <= 120 ? SPEED : 0, 0);
            var wake = response.speedWake();
            var base = CapeNocturne.gains(1, time, ID);
            var lit = CapeNocturne.gains(1, time, ID, wake);
            double edge = lit.edge() - base.edge(), lip = lit.inner() - base.inner();
            check(edge >= 0 && edge < .55 && lip >= 0 && lip < .55, "unbounded additional light");
            check((short) lit.packed() > 0 && (short) (lit.packed() >>> 16) > 0, "UV2 overflow");
            check(CapeNocturne.gains(0, time, ID, wake).equals(CapeNocturne.gains(0, time, ID)), "wake in daylight");
            for (double dusk : new double[]{.28, 1}) {
                var dry = CapeNocturne.gains(dusk, time, ID, wake);
                var wet = CapeNocturne.gains(dusk, time, ID, new CapeResponse.SpeedWake(wake.edge(), wake.inner(), 1));
                var still = CapeNocturne.gains(dusk, time, ID);
                close(dry.edge() - still.edge(), edge * dusk * dusk, "mixed light");
                close(wet.edge() - still.edge(), .20 * edge * dusk * dusk, "wet edge");
                close(wet.inner() - still.inner(), .20 * lip * dusk * dusk, "wet lip");
            }
            if (i <= 120) {
                if (lip > maxLipOn) { lipOn = i; maxLipOn = lip; }
                if (edge > maxEdgeOn) { edgeOn = i; maxEdgeOn = edge; }
            } else {
                if (lip > maxLipOff) { lipOff = i - 120; maxLipOff = lip; }
                if (edge > maxEdgeOff) { edgeOff = i - 120; maxEdgeOff = edge; }
            }
            if (i >= 112 && i <= 120 || i >= 232)
                check(lit.equals(base), "the new wake did not settle at constant speed");
        }
        check(maxLipOn > .27 && maxEdgeOn > .27 && maxLipOff > .27 && maxEdgeOff > .27, "weak or missing wake");
        check(edgeOn - lipOn >= 8 && edgeOff - lipOff >= 8, "the edge did not lag both speed changes");
        var low = new CapeResponse();
        sample(low, 0, 0, 0);
        sample(low, .05, .008, 0);
        check(CapeNocturne.gains(1, .05, ID, low.speedWake()).equals(CapeNocturne.gains(1, .05, ID)), "motion noise");
        var wet = new CapeResponse();
        sample(wet, 0, 0, 0);
        sample(wet, .05, SPEED, 1);
        check(wet.speedWake().water() > .1 && wet.speedWake().water() < .3, "water entry was not filtered");

        for (int fps : new int[]{30, 60, 144}) {
            var r = new CapeResponse();
            sample(r, 0, 0, 0);
            for (int i = 1; i <= fps; ++i) sample(r, i / (double) fps, SPEED, 0);
            var expected = new CapeResponse();
            sample(expected, 0, 0, 0);
            for (int i = 1; i <= 20; ++i) sample(expected, i / 20.0, SPEED, 0);
            sameWake(expected.speedWake(), r.speedWake(), "FPS changed the response");
        }
        for (int gap = 2; gap <= 10; ++gap) {
            var sparse = new CapeResponse();
            var dense = new CapeResponse();
            for (var r : new CapeResponse[]{sparse, dense}) {
                sample(r, 0, 0, 0);
                sample(r, .05, SPEED, 0);
            }
            for (int tick = 2; tick <= gap; ++tick) sample(dense, tick / 20.0, SPEED, 0);
            double time = (gap + 1) / 20.0;
            sample(dense, time, 0, 0);
            sample(sparse, time, 0, 0);
            sameWake(dense.speedWake(), sparse.speedWake(), "braking assumed before the skipped ticks");
            sample(sparse, time, 1, 1);
            sameWake(dense.speedWake(), sparse.speedWake(), "same-pose replay mutated the wake");
        }
        sample(response, 6.05, SPEED, 0);
        check(response.speedWake().inner() > 0, "missing activity before cut");
        response.reset();
        sample(response, 6.1, SPEED, 0);
        check(response.speedWake().equals(CapeResponse.SpeedWake.NONE), "teleport carried an old flare");
        sample(response, 6.15, 0, 0);
        sample(response, 7, SPEED, 0);
        check(response.speedWake().equals(CapeResponse.SpeedWake.NONE), "long absence carried an old flare");
        sample(response, 7.05, 0, 0);
        sample(response, 0, SPEED, 0);
        check(response.speedWake().equals(CapeResponse.SpeedWake.NONE), "rewind carried an old flare");
        System.out.println("Halo reactivo: arranque y frenada, retardo del borde, luz/agua, reposo, replays y cortes.");
    }

    private static void export(double on, double off, double duration, double speed) {
        // An input seen on a render sample applies over the preceding small
        // interval. Switch after the boundary to match the analytic viewer.
        for (double wet : new double[]{0, 1}) {
            var r = new CapeResponse();
            for (int i = 0; i <= Math.round(40 * duration); ++i) {
                double t = i / 40.0;
                sample(r, t, t > on && t <= off ? speed : 0, wet);
                for (double dusk : new double[]{0, .44, 1}) {
                    var g = CapeNocturne.gains(dusk, t, ID, r.speedWake());
                    System.out.println(t + "\t" + wet + "\t" + dusk + "\t" + ID + "\t" + g.edge() + "\t" + g.inner() + "\t" + g.packed());
                }
            }
        }
    }

    private static void sample(CapeResponse r, double time, double speed, double water) {
        r.sample(time, speed, 0, 0, 0, water, 0, 0);
    }

    private static void sameWake(CapeResponse.SpeedWake a, CapeResponse.SpeedWake b, String message) {
        close(a.edge(), b.edge(), message);
        close(a.inner(), b.inner(), message);
        close(a.water(), b.water(), message);
    }

    private static void close(double a, double b, String message) {
        check(Math.abs(a - b) < 1e-12, message + ": " + a + " / " + b);
    }

    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
}
