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
    // A crouched torso can present the tall rear band through the top face
    // of the vanilla head. Tuck it under the collar instead of increasing
    // the upright fold (which lifts it through that tilted face).
    static final double REAR_DROP = 1.50;
    static final double REAR_INSET = .25;
    static final double REAR_FOLD = 16;
    private static final double REAR_LEAN_START = 17;
    private static final double REAR_LEAN_FULL = 28.5;
    private static final double REAR_UP_START = 5;
    private static final double REAR_UP_FULL = 28;
    private static final double REAR_TURN_START = 7;
    private static final double REAR_TURN_FULL = 27;
    private static final double NAPE_UP_START = 4;
    private static final double NAPE_UP_FULL = 18;
    private static final double NAPE_TURN_START = 9;
    private static final double NAPE_TURN_FULL = 26;
    private static final double NAPE_TURN_RELEASE = 56;
    private static final double NAPE_TURN_END = 72;
    private static final double CHAIN_RELEASE = 45;
    private static final double CHAIN_END = 55;
    private static final double CHAIN_INSET = 1.45;
    private static final double NAPE_INSET = 1.15;
    private static final double NAPE_SIDE = .55;
    static final Pose REST = new Pose(REST_PITCH, 0, 0);
    static final Shift FIXED = new Shift(0, 0, 0);
    static final Nape NO_NAPE = new Nape(FIXED, FIXED);

    // Angles in the baked frame; positive pitch moves the crown away from
    // the neck. The collar teeth, returns, mount and cloth roots stay sewn.
    record Pose(double pitch, double yaw, double roll) {}
    record Shift(double x, double y, double z) {}
    record Nape(Shift chain, Shift lip) {
        Shift forBone(String name) {
            if (chainLink(name)) return chain;
            // The edges exposed at the nape, not the entire hood or collar.
            return switch (name) {
                case "v17_cowl_back_0", "v17_cowl_back_1", "v17_cowl_front_0",
                        "v17_cowl_front_2", "v17_cowl_front_3" -> lip;
                default -> FIXED;
            };
        }
    }

    private CapeHood() {}

    static boolean chainLink(String name) { return name.startsWith("v18_chain_"); }

    /** Retract the lower trim into its sewn seat, independently of the crown fold. */
    static Nape nape(double up, double yaw, double lean) {
        if (!Double.isFinite(up) || !Double.isFinite(yaw) || !Double.isFinite(lean)) return NO_NAPE;
        double turn = Math.IEEEremainder(yaw, 360), absTurn = Math.abs(turn);
        double weight = smooth(REAR_LEAN_START, REAR_LEAN_FULL, lean) * smooth(NAPE_UP_START, NAPE_UP_FULL, up)
                * smooth(NAPE_TURN_START, NAPE_TURN_FULL, absTurn);
        double lip = weight * (1 - smooth(NAPE_TURN_RELEASE, NAPE_TURN_END, absTurn));
        if (lip == 0) return NO_NAPE;
        double open = 1 - smooth(CHAIN_RELEASE, CHAIN_END, absTurn);
        double chain = weight * open * CHAIN_INSET;
        double aim = Math.toRadians(turn), bend = Math.toRadians(lean);
        // Translate along the head's horizontal heading, expressed in torso
        // axes. The extra inboard stroke keeps the cowl tip off the near side.
        double x = Math.sin(aim), along = Math.cos(aim);
        double y = along * Math.sin(bend), z = -along * Math.cos(bend);
        return new Nape(chain == 0 ? FIXED : new Shift(chain*x, chain*y, chain*z),
                new Shift(lip*(NAPE_INSET*x + Math.copySign(NAPE_SIDE*(1 + open), turn)), lip*NAPE_INSET*y, lip*NAPE_INSET*z));
    }

    static boolean rear(String name) { return name.startsWith("v17_cowl_back_"); }

    static boolean moves(String name) {
        return rear(name) || name.startsWith("v17_cowl_front_");
    }

    /** Rear-band tuck for a sustained upward turn; the front seam stays put. */
    static double rearTuck(double up, double yaw, double lean) {
        if (!Double.isFinite(up) || !Double.isFinite(yaw) || !Double.isFinite(lean)) return 0;
        return smooth(REAR_LEAN_START, REAR_LEAN_FULL, lean) * smooth(REAR_UP_START, REAR_UP_FULL, up)
                * smooth(REAR_TURN_START, REAR_TURN_FULL, Math.abs(Math.IEEEremainder(yaw, 360)));
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
