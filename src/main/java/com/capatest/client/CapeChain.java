package com.capatest.client;

/** A small secondary motion on the loose part of the eight-link collar chain. */
final class CapeChain {
    private static final String PREFIX = "v18_chain_";
    // Both anchors are sewn. Links 4 and 5 share a very short overlap;
    // move that joint together rather than asking two blocks to stretch.
    private static final double[] LINK_WEIGHT = {0, .18, .56, .92, 1, 1, .48, 0};
    private static final double GAIT_START = .045;
    private static final double GAIT_FULL = .64;
    private static final double BRAKE_START = .008;
    private static final double BRAKE_FULL = .115;
    private static final double STEP_DELAY = .08; // in full vanilla gait cycles
    private static final double AWAY_DELAY = .62; // radians on the two-beat wave
    private static final double DROP = .28;
    private static final double AWAY = .36;
    private static final double BRAKE_DROP = .85;
    private static final double BRAKE_AWAY = .82;
    static final Motion REST = new Motion(0, 0);

    record Motion(double drop, double away) {}

    private CapeChain() {}

    static double weight(String name) {
        if (name.length() != PREFIX.length() + 1 || !name.startsWith(PREFIX)) return 0;
        int link = name.charAt(PREFIX.length()) - '0';
        return link >= 0 && link < LINK_WEIGHT.length ? LINK_WEIGHT[link] : 0;
    }

    static Motion pose(double stride, double pace, double support, double brake) {
        double gait = smooth(GAIT_START, GAIT_FULL, pace);
        double lag = smooth(BRAKE_START, BRAKE_FULL, brake);
        if (support <= 0 || gait == 0 && lag == 0) return REST;
        // Two footfalls per cycle. The chain drops and then swings slightly
        // outwards, never in towards the wearer. No free-running clock.
        double step = 4 * Math.PI * (stride - STEP_DELAY);
        double drop = gait * (.12 + .72 * wave(step));
        double away = gait * (.23 + .73 * wave(step - AWAY_DELAY));
        // The slow speed filter carries the chain after the legs slow down.
        // Combine, don't add, so a brake in mid-step stays inside the bound.
        return new Motion(DROP * support * (drop + (1 - drop) * BRAKE_DROP * lag),
                AWAY * support * (away + (1 - away) * BRAKE_AWAY * lag));
    }

    private static double wave(double angle) { return .5 + .5 * Math.cos(angle); }

    private static double smooth(double low, double high, double value) {
        double t = Math.max(0, Math.min(1, (value - low) / (high - low)));
        return t * t * (3 - 2 * t);
    }
}
