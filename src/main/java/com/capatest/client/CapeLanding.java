package com.capatest.client;

/** One dry landing, observed on the worn motion's tick clock. No horizontal input. */
final class CapeLanding {
    static final String HEM = "cape_bottom";
    private static final int CONTACT_GAP = 3;
    private static final int CLOCK_GAP = 10;
    // CapeTravel.lift units. A stair or a shallow step doesn't light the hem.
    private static final double LIFT_START = .16;
    private static final double LIFT_FULL = .84;
    private static final double PITCH_LIMIT = 5.5;
    // Tick offsets from the first grounded tick, not the first render.
    private static final double OPEN_PEAK = 3.0;
    private static final double OPEN_END = 9.0;
    private static final double LIGHT_START = 1.6;
    private static final double LIGHT_PEAK = 4.4;
    private static final double LIGHT_END = 11.0;

    record Motion(double pitch, double heat) {}
    static final Motion REST = new Motion(0, 0);

    private boolean observed, air;
    private int lastTick, touchdown;
    private double lift, impact;

    Motion sample(int tick, double time, boolean dryUpright, boolean grounded, CapeTravel.Motion travel) {
        if (!dryUpright || travel.cut()) {
            observed = false;
            impact = 0;
            return REST;
        }
        long gap = (long) tick - lastTick;
        if (!observed || gap != 0) {
            if (!observed || gap < 0 || gap > CLOCK_GAP || !grounded) {
                impact = 0;
            } else if (air) {
                // Use the last observed airborne descent. Vanilla already
                // zeroes vertical velocity at contact. Don't invent a landing
                // when the wearer returns to view after an unobserved fall.
                impact = gap <= CONTACT_GAP ? strength(lift) : 0;
                touchdown = tick;
            }
            observed = true;
            lastTick = tick;
            air = !grounded;
            lift = travel.lift();
        }
        return pose(time - touchdown, impact);
    }

    static double strength(double lift) {
        return lift > LIFT_START ? smooth((lift - LIFT_START) / (LIFT_FULL - LIFT_START)) : 0;
    }

    static Motion pose(double age, double strength) {
        if (!(strength > 0 && age > 0 && age < LIGHT_END)) return REST;
        double pitch = PITCH_LIMIT * strength * pulse(age, 0, OPEN_PEAK, OPEN_END);
        double heat = strength * pulse(age, LIGHT_START, LIGHT_PEAK, LIGHT_END);
        return new Motion(pitch, heat);
    }

    private static double pulse(double t, double start, double peak, double end) {
        return smooth(Math.min((t - start) / (peak - start), (end - t) / (end - peak)));
    }

    private static double smooth(double t) {
        t = Math.max(0, Math.min(t, 1));
        return t*t*(3 - 2*t);
    }
}
