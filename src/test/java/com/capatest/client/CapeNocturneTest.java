package com.capatest.client;

public final class CapeNocturneTest {
    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            for (double light = 0; light <= 15; light += .5) {
                double dusk = CapeNocturne.darkness(light);
                for (double time : new double[]{0, .19, .61, 1.7, 2.33, 3.4}) {
                    for (int id : new int[]{0, 3, 41}) {
                        var g = CapeNocturne.gains(dusk, time, id);
                        System.out.println(light + "\t" + time + "\t" + id + "\t" + dusk
                                + "\t" + g.edge() + "\t" + g.inner() + "\t" + g.packed());
                    }
                }
            }
            return;
        }
        double last = 1;
        for (int light = 0; light <= 15; light++) {
            double d = CapeNocturne.darkness(light);
            check(d <= last && d >= 0, "non-monotone exposure");
            last = d;
        }
        var cave = new CapeNocturne().sample(1, 0, 1, 0, 0);
        var night = new CapeNocturne().sample(0, 15, .2F, 0, 0);
        var day = new CapeNocturne().sample(0, 15, 1, 0, 0);
        var torch = new CapeNocturne().sample(14, 0, .2F, 0, 0);
        equal(cave, night, "raw skylight masked the night");
        equal(day, torch, "a torch didn't tame the halo");
        check(cave.edge() > day.edge() * 3 && cave.inner() > day.inner() * 3, "not enough dark contrast");
        check(CapeNocturne.gains(1, .61, 0).edge() > cave.edge(), "skirt doesn't peak after the lip");
        check(CapeNocturne.gains(1, .61, 0).inner() < cave.inner(), "both layers peak together");
        equal(cave, CapeNocturne.gains(1, 3.4, 0), "wrap discontinuity");
        equal(cave, CapeNocturne.gains(1, 0, 0, new CapeResponse.SpeedWake(.008, .008, 0)),
                "the wake dead zone changed");
        check(CapeNocturne.darkness(Double.NaN) == 0
                        && CapeNocturne.darkness(Double.POSITIVE_INFINITY) == 0,
                "invalid light-map input must fail closed to no extra glow");
        var malformed = CapeNocturne.gains(Double.NaN, Double.POSITIVE_INFINITY, 0,
                new CapeResponse.SpeedWake(Double.NaN, Double.POSITIVE_INFINITY, Double.NaN));
        check(Double.isFinite(malformed.edge()) && Double.isFinite(malformed.inner()),
                "non-finite wake or clock poisoned the glow frame");
        var saturated = CapeNocturne.gains(1, 0, 0,
                new CapeResponse.SpeedWake(Double.MAX_VALUE, Double.MAX_VALUE, 0));
        check(Double.isFinite(saturated.edge()) && Double.isFinite(saturated.inner())
                        && saturated.edge() < 2.3 && saturated.inner() < 2.3,
                "overflowing wake escaped the capped light budget");
        equal(malformed, CapeNocturne.hemGains(Double.NaN, malformed, Double.NaN, 0, Double.NaN),
                "invalid hem impulse altered a safe base frame");
        var missingBase = CapeNocturne.hemGains(1, null, .3, 4, .5);
        check(Double.isFinite(missingBase.edge()) && Double.isFinite(missingBase.inner()),
                "missing hem base frame was not safely reconstructed");
        check(!cave.equals(CapeNocturne.gains(1, 0, 1)), "synchronized wearers");
        int packed = cave.packed();
        check(Math.abs((short) packed / 4096.0 - cave.edge()) <= .5 / 4096, "UV2 edge layout");
        check(Math.abs((short) (packed >>> 16) / 4096.0 - cave.inner()) <= .5 / 4096, "UV2 lip layout");

        CapeNocturne filter = new CapeNocturne();
        equal(day, filter.sample(0, 15, 1, 0, 0), "first exposure");
        var fade = filter.sample(0, 0, 1, .1, 0);
        check(fade.edge() > day.edge() && fade.edge() < cave.edge(), "abrupt entrance into darkness");
        equal(fade, filter.sample(0, 0, 1, .1, 0), "rerender advanced the fade");
        equal(day, filter.sample(14, 0, 1, .8, 0), "old exposure carried across a clock gap");
        equal(cave, filter.sample(0, 0, 1, 0, 0), "old exposure carried across a clock reset");
        CapeNocturne invalidClock = new CapeNocturne();
        var clockFrame = invalidClock.sample(0, 0, 1, .25, 9);
        equal(clockFrame, invalidClock.sample(15, 15, 1, Double.NaN, 9),
                "invalid render time rewound or poisoned exposure");
        var invalidLight = new CapeNocturne().sample(0, 15, Float.NaN, .25, 9);
        check(Double.isFinite(invalidLight.edge()) && Double.isFinite(invalidLight.inner()),
                "non-finite sky brightness poisoned exposure");
        verifyFiniteDomain();
        equal(simulate(30), simulate(144), "adaptation depends on the frame rate");
        System.out.println("CapeNocturne: día, antorcha, noche, cueva, pulso de borde y exposición sin saltos verificados");
    }

    private static void verifyFiniteDomain() {
        double[] inputs = {Double.NEGATIVE_INFINITY, -1, 0, .5, 1, 2,
                Double.MAX_VALUE, Double.POSITIVE_INFINITY, Double.NaN};
        for (double dusk : inputs) for (double time : inputs) for (double wake : inputs) {
            var g = CapeNocturne.gains(dusk, time, 17,
                    new CapeResponse.SpeedWake(wake, wake, wake));
            check(Double.isFinite(g.edge()) && Double.isFinite(g.inner()), "non-finite output in input sweep");
            check(g.edge() >= 0 && g.edge() < 3 && g.inner() >= 0 && g.inner() < 3,
                    "light gain escaped the packed UV2 range");
            int packed = g.packed();
            check((short) packed >= 0 && (short) (packed >>> 16) >= 0,
                    "packed light gain became negative");
        }
    }

    private static CapeNocturne.Gains simulate(int fps) {
        CapeNocturne filter = new CapeNocturne();
        CapeNocturne.Gains last = filter.sample(0, 15, 1, 0, 0);
        for (int i = 1; i <= fps; i++) {
            last = filter.sample(i <= fps / 2 ? 0 : 14, 0, 1, i / (double) fps, 0);
        }
        return last;
    }

    private static void equal(CapeNocturne.Gains a, CapeNocturne.Gains b, String label) {
        check(Math.abs(a.edge() - b.edge()) < 1e-12 && Math.abs(a.inner() - b.inner()) < 1e-12, label);
    }

    private static void check(boolean test, String label) {
        if (!test) throw new AssertionError(label);
    }
}
