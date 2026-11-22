package com.capatest.client;

import com.capatest.item.CapeState;

import java.util.Locale;

/** Exercise the contact detector and the shared hem envelope without Minecraft. */
final class CapeLandingTest {
    private static final CapeTravel.Motion FLOOR = new CapeTravel.Motion(0, 0, 0, false);
    private static final CapeTravel.Motion DROP = new CapeTravel.Motion(0, 1, 0, false);
    private static final CapeTravel.Motion CUT = new CapeTravel.Motion(0, 0, 0, true);

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            samples();
            return;
        }
        verifyEnvelopeBoundaries();
        require(landing(.36, 0, 1).equals(landing(.36, .75, 1)), "horizontal speed supplied impact");
        require(landing(.36, 0, 1).equals(landing(.36, 0, 3)), "short gap lost the last observed descent");
        var hop = landing(.39, 0, 1);
        var ledge = landing(.92, .65, 1);
        require(hop.pitch() > 1 && hop.pitch() < 2 && ledge.pitch() == 5.5, "ordinary vs ledge landing");
        quiet(landing(.08, 0, 1), "tiny step");
        quiet(landing(-.45, 0, 1), "moving upward");
        quiet(landing(1, 0, 4), "unseen landing");
        quiet(landing(1, 0, -1), "rewound clock");

        var motion = new CapeWornMotion();
        var other = new CapeWornMotion();
        var dense = motion.landing;
        var sparse = new CapeLanding();
        quiet(dense.sample(19, 19.8, true, false, DROP), "in free fall");
        sparse.sample(19, 19.8, true, false, DROP);
        quiet(dense.sample(20, 20, true, true, FLOOR), "exact first contact");
        quiet(other.landing.sample(20, 20.25, true, true, FLOOR), "other wearer's first draw");
        for (int tick = 20; tick <= 32; ++tick) {
            for (int j = 0; j <= 12; ++j) {
                double time = tick + j / 12.0;
                var actual = dense.sample(tick, time, true, true, FLOOR);
                require(actual.equals(CapeLanding.pose(time - 20, 1)), "render frequency changed the envelope");
                require(actual.equals(dense.sample(tick, time, true, false, DROP)), "same-tick replay changed the contact");
                if (j == 6) require(sparse.sample(tick, time, true, true, FLOOR).equals(actual), "one draw per tick diverged");
                if (time < 21.6) require(actual.heat() == 0, "the light led the cloth");
                if (time >= 31) quiet(actual, "extra motion did not settle");
            }
        }

        for (boolean canLand : new boolean[]{true, false}) {
            var cancelled = new CapeLanding();
            cancelled.sample(39, 39.75, true, false, DROP);
            require(cancelled.sample(40, 40.75, true, true, FLOOR).pitch() > 0, "no pulse to cancel");
            quiet(cancelled.sample(41, 41.5, canLand, true, canLand ? CUT : FLOOR), "cut or excluded medium");
            quiet(cancelled.sample(42, 42.5, true, true, FLOOR), "old impulse leaked on re-entry");
            cancelled.sample(43, 43.5, canLand, false, canLand ? CUT : DROP);
            quiet(cancelled.sample(44, 44.5, true, true, FLOOR), "blocked fall registered as contact");
        }
        var repeated = new CapeLanding();
        repeated.sample(48, 48.5, true, false, DROP);
        repeated.sample(49, 49.5, true, true, FLOOR);
        quiet(repeated.sample(50, 50.5, true, false, new CapeTravel.Motion(.7, -.4, 0, false)), "second takeoff");
        quiet(repeated.sample(51, 51.5, true, true, FLOOR), "second landing reused the first impulse");
        verifyLight();
        System.out.println("Aterrizaje: contacto seco y reciente, arrastre y eco retardado; sin pulso en aire, al frenar ni tras corte.");
    }

    private static void verifyEnvelopeBoundaries() {
        require(CapeLanding.strength(.16) == 0 && CapeLanding.strength(.84) == 1,
                "lift thresholds are not closed at the expected bounds");
        require(CapeLanding.strength(.160001) > 0 && CapeLanding.strength(Double.NaN) == 0,
                "small or non-finite lift escaped its bounds");
        require(CapeLanding.pose(3, 1).pitch() == 5.5, "cloth pulse missed its peak");
        require(CapeLanding.pose(1.6, 1).heat() == 0 && CapeLanding.pose(4.4, 1).heat() == 1,
                "light pulse start or peak drifted");
        require(CapeLanding.pose(9, 1).pitch() == 0 && CapeLanding.pose(11, 1).equals(CapeLanding.REST),
                "cloth or light pulse did not reach its endpoint");
        quiet(CapeLanding.pose(Double.NaN, 1), "non-finite pose age");
        quiet(CapeLanding.pose(3, Double.NaN), "non-finite landing strength");
    }

    private static CapeLanding.Motion landing(double lift, double speed, int gap) {
        var m = new CapeLanding();
        m.sample(65, 65.25, true, false, new CapeTravel.Motion(speed, lift, .4, false));
        m.sample(65 + gap, 65.25 + gap, true, true, new CapeTravel.Motion(speed, 0, 0, false));
        return m.sample(68 + gap, 68.00 + gap, true, true, FLOOR);
    }

    private static void verifyLight() {
        var noWake = CapeResponse.SpeedWake.NONE;
        var wake = new CapeResponse.SpeedWake(.21, .34, 0);
        for (int level : new int[]{0, 8, 15}) {
            var calm = new CapeWornLight();
            var m = new CapeWornLight();
            var base = calm.sample(CapeState.WALK, level, 0, 1, 80, .5F, 41, wake);
            var flash = m.sample(CapeState.WALK, level, 0, 1, 80, .5F, 41, wake, 1);
            require(flash.halo().equals(base.halo()) && flash.glow().equals(base.glow()), "changed upper halo or core");
            double dusk = CapeNocturne.darkness(level), time = 80.5 / 20;
            var stationary = CapeNocturne.gains(dusk, time, 41, noWake);
            double room = .55 * dusk * dusk + 1e-12;
            require(flash.hem().edge() <= stationary.edge() + room && flash.hem().inner() <= stationary.inner() + room,
                    "brake plus landing exceeded the halo budget");
            require(level == 15 ? flash.hem().equals(flash.halo()) : flash.hem().inner() > flash.halo().inner(), "dark-only hem gain");
            require(flash.equals(m.sample(CapeState.IDLE, 15, 0, 1, 80, .25F, 41, wake, 1)), "hem re-sampled on earlier replay");
        }
    }

    private static void samples() {
        Locale.setDefault(Locale.ROOT);
        System.out.println("lift\tage\tdusk\twake\tpitch\theat\tedge\tinner\them_edge\them_inner");
        for (double lift : new double[]{-.3, .08, .16, .19, .36, .52, .67, .84, 1})
            for (int i = -2; i <= 113; i++) for (double dusk : new double[]{0, .5, 1}) for (double w : new double[]{0, .22}) {
                double age = i / 10.0;
                var m = CapeLanding.pose(age, CapeLanding.strength(lift));
                double t = 12.4 + age / 20;
                var base = CapeNocturne.gains(dusk, t, 7, new CapeResponse.SpeedWake(w*.72, w, 0));
                var hem = CapeNocturne.hemGains(dusk, base, t, 7, m.heat());
                System.out.printf("%.6f\t%.6f\t%.6f\t%.6f\t%.14f\t%.14f\t%.14f\t%.14f\t%.14f\t%.14f%n",
                        lift, age, dusk, w, m.pitch(), m.heat(), base.edge(), base.inner(), hem.edge(), hem.inner());
            }
    }

    private static void quiet(CapeLanding.Motion m, String reason) {
        require(m.equals(CapeLanding.REST), reason + ": " + m);
    }

    private static void require(boolean success, String reason) {
        if (!success) throw new AssertionError(reason);
    }
}
