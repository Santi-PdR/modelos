package com.capatest.client;

/** Small articulation of the upper hood only, about its sewn lower edge. */
final class CapeHood {
    static final double PIVOT_Y = 23.20;
    static final double PIVOT_Z = 5.55;
    static final double SET_BACK = .13;
    private static final double REST_PITCH = 2.45;
    private static final double BREATH_RATE = .086;
    private static final double BREATH_OFFSET = .17;
    private static final double BREATH = .92;
    private static final double STEP_DELAY = .84;
    private static final double OPEN = 2.85;
    private static final double ROCK = 1.65;
    private static final double TURN_YAW = 1.12;
    private static final double ROCK_YAW = .48;
    private static final double SIDE_ROLL = .62;
    private static final double TURN_ROLL = .48;
    private static final double ROCK_ROLL = .32;
    private static final double LOOK_START = 21;
    private static final double LOOK_FULL = 66;
    private static final double LOOK_FOLD = 56;
    private static final double TURN_START = 28;
    private static final double TURN_END = 72;
    private static final double LEAN_START = 2;
    private static final double LEAN_END = 10;
    static final Pose REST = new Pose(REST_PITCH, 0, 0);

    // Angles in the baked frame; positive pitch moves the crown away from
    // the neck. The collar teeth, returns, mount and cloth roots stay sewn.
    record Pose(double pitch, double yaw, double roll) {}

    private CapeHood() {}

    static boolean moves(String name) {
        return name.startsWith("v17_cowl_back_") || name.startsWith("v17_cowl_front_");
    }

    /** Extra fold when the back of an upright wearer's head tilts into the crown.
     * ModelPart aim, not camera angle. Does not replace breathing or gait. */
    static double lookClearance(double up, double yaw, double lean) {
        if (!Double.isFinite(up) || !Double.isFinite(yaw) || !Double.isFinite(lean)) return 0;
        double turn = Math.abs(Math.IEEEremainder(yaw, 360));
        return LOOK_FOLD * smooth(LOOK_START, LOOK_FULL, up)
                * (1 - smooth(TURN_START, TURN_END, turn))
                * (1 - smooth(LEAN_START, LEAN_END, Math.abs(lean)));
    }

    private static double smooth(double start, double end, double x) {
        double t = Math.max(0, Math.min(1, (x - start) / (end - start)));
        return t * t * (3 - 2 * t);
    }

    static Pose pose(double ticks, double stride, double pace, double turn, double side, int seed) {
        double breathe = Math.sin(BREATH_RATE * ticks + BREATH_OFFSET * seed);
        double step = 2 * Math.PI * stride - STEP_DELAY;
        return new Pose(REST_PITCH + BREATH * breathe + pace * (OPEN + ROCK * Math.cos(step)),
                TURN_YAW * turn + ROCK_YAW * pace * Math.sin(step),
                SIDE_ROLL * side - TURN_ROLL * turn + ROCK_ROLL * pace * Math.sin(step));
    }
}
