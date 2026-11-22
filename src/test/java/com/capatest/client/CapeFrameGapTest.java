package com.capatest.client;

import java.util.Locale;

/** Same input timeline with and without intermediate draws. Runs against both released JAR and source. */
public final class CapeFrameGapTest {
    private static final int GAP = 8;
    private static final int SEED = 1;

    private record Sample(double upper, double hem, double side, double roll, double pitch, double edge, double inner) {
        double[] values() { return new double[]{upper, hem, side, roll, pitch, edge, inner}; }
    }

    private static final class Route {
        final CapeResponse motion = new CapeResponse();
        final CapeNocturne halo = new CapeNocturne();

        Sample at(double tick, int direction) {
            boolean shade = direction < 0;
            double seconds = tick / 20.0;
            motion.sample(seconds, shade ? .2 : .86, 0, direction, 0, 0, 0, shade ? 0 : 1, direction);
            var gain = halo.sample(shade ? 0 : 15, 0, 1, seconds, SEED);
            return new Sample(motion.turnAt(.18), motion.turnAt(1), motion.sideAt(1),
                    CapeResponse.sideRoll(0, motion.sideAt(1), 1), motion.pitchAt(1), gain.edge(), gain.inner());
        }
    }

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            var route = new Route();
            System.out.println("tick\tsentido\tgiro_alto\tgiro_extremo\tlateral"
                    + "\troll_grados\tpitch_grados\thalo_borde\thalo_interior");
            row(0, 1, route.at(0, 1));
            for (int tick = GAP; tick <= GAP + 6; ++tick) row(tick, -1, route.at(tick, -1));
            for (int tick = 2 * GAP + 6; tick <= 2 * GAP + 12; ++tick) row(tick, 1, route.at(tick, 1));
            return;
        }
        for (int gap = 2; gap <= 10; ++gap) {
            for (int direction : new int[]{-1, 1}) {
                var sparse = new Route();
                var dense = new Route();
                var first = sparse.at(0, direction);
                close(first, sparse.at(0, -direction), "same-time replay changed the pose/light");
                for (int tick = 0; tick < gap; ++tick) dense.at(tick, direction);
                var changed = sparse.at(gap, -direction);
                close(dense.at(gap, -direction), changed, "new input filled the frame gap");
                check(Math.abs(changed.hem - first.hem) > .3 && Math.abs(changed.hem - first.hem) < .4,
                        "the new turn was ignored or over-applied");
                for (int tick = gap + 1; tick <= gap + 8; ++tick)
                    close(dense.at(tick, -direction), sparse.at(tick, -direction), "response did not resume");
            }
        }
        // Off a whole tick, subtracting two times can put exactly ten
        // ticks a rounding bit above .5 seconds, but it isn't a view cut.
        var fractional = new Route();
        fractional.at(11.375, 1);
        var oneTick = new Route();
        oneTick.at(20.375, 1);
        close(oneTick.at(21.375, -1), fractional.at(21.375, -1), "rounded half-second gap caused a reset");
        close(new Route().at(31.5, 1), fractional.at(31.5, 1), "a longer gap didn't reset");

        // A fade already in progress must keep running through the gap,
        // even if the first observed input after the gap reverses it.
        var sparse = new Route();
        var dense = new Route();
        for (var route : new Route[]{sparse, dense}) {
            route.at(0, 1);
            route.at(1, -1);
        }
        for (int tick = 2; tick <= GAP; ++tick) dense.at(tick, -1);
        close(dense.at(GAP + 1, 1), sparse.at(GAP + 1, 1), "unfinished fade did not advance on old input");
        close(new Route().at(40, -1), sparse.at(40, -1), "long absence retained stale state");
        close(new Route().at(0, 1), sparse.at(0, 1), "rewind retained stale state");
        System.out.println("Pausa de render: ambos sentidos, 2–10 ticks, fundido anterior, repetición y cortes de reloj.");
    }

    private static void row(int tick, int direction, Sample pose) {
        System.out.printf(Locale.ROOT, "%d\t%d\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f%n", tick, direction,
                pose.upper, pose.hem, pose.side, pose.roll, pose.pitch, pose.edge, pose.inner);
    }

    private static void close(Sample a, Sample b, String reason) {
        double[] left = a.values(), right = b.values();
        for (int i = 0; i < left.length; ++i) {
            check(Math.abs(left[i] - right[i]) <= 1e-12, reason + ": " + a + " / " + b);
        }
    }

    private static void check(boolean ok, String reason) {
        if (!ok) throw new AssertionError(reason);
    }
}
