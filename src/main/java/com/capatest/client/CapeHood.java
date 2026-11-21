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
    static final Pose REST = new Pose(REST_PITCH, 0, 0);

    // Angles in the baked frame; positive pitch moves the crown away from
    // the neck. The collar teeth, returns, mount and cloth roots stay sewn.
    record Pose(double pitch, double yaw, double roll) {}

    private CapeHood() {}

    static boolean moves(String name) {
        return name.startsWith("v17_cowl_back_") || name.startsWith("v17_cowl_front_");
    }

    static Pose pose(double ticks, double stride, double pace, double turn, double side, int seed) {
        double breathe = Math.sin(BREATH_RATE * ticks + BREATH_OFFSET * seed);
        double step = 2 * Math.PI * stride - STEP_DELAY;
        return new Pose(REST_PITCH + BREATH * breathe + pace * (OPEN + ROCK * Math.cos(step)),
                TURN_YAW * turn + ROCK_YAW * pace * Math.sin(step),
                SIDE_ROLL * side - TURN_ROLL * turn + ROCK_ROLL * pace * Math.sin(step));
    }
}
