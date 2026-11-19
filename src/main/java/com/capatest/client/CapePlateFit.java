package com.capatest.client;

/** Bring the actual shoulder plates onto the sleeve line without moving the yoke or the cloth. */
final class CapePlateFit {
    static final String SMALL = "v18_pad_0", WIDE = "v18_pad_1";
    private static final double DOWN_START = 41, DOWN_FULL = 77;
    private static final double TURN_START = 18, TURN_END = 60;
    private static final double LEAN_START = .14, LEAN_END = .60;
    private static final double ARM_START = 2.85, ARM_END = 5.30;
    private static final double LIP_RISE_START = .40, LIP_RISE_END = .88;
    private static final double LIP_REACH_START = .75, LIP_REACH_END = 1;
    // plates[1] in the authored GEO: the bevel immediately above the plate body.
    static final int RIM_CUBE = 1;

    // Rendered X/Y/Z of the inner sewn pivot; fitted width/height/depth; Y/Z
    // adjustment; pitch/yaw. Applied before the common cape_seat_fit scale.
    // Fold the broad unsupported end in. Extend the compact front lip
    // without pulling the back edge away from the cloth roots.
    // The exporter reads this table for the body-space preview, not keyframes.
    private static final double[][] TARGETS = {
            {4.53, 23.15, 4.95, 1, 1, 1.27, .06, -.275, 0, -3.5},
            {-4.24, 23.15, 4.95, .514, .92, 1, .02, -1.065, 5.5, 11.4}
    };
    // Rear hinge of the existing crest cube (pad space), size and lift.
    // Roll the leading face over the sleeve AFTER it has risen above it.
    private static final double[][] RIMS = {
            {6.03, 23.02, 5.57, .34, -.06, -.53, 1.10, .92, 1.24, 41.5},
            {-7.79, 23.59, 5.31, -.048, .087, -.60, .90, .224, 1.18, 39.4}
    };
    private static final Plate COMPACT = plate(0), BROAD = plate(1);

    private CapePlateFit() {}

    record Plate(float x, float y, float z, float width, float height, float depth, float lift, float advance,
                 float pitch, float yaw, Rim rim) {}
    record Rim(float x, float y, float z, float across, float lift, float advance,
               float width, float height, float depth, float pitch) {}

    static float rimRise(float fit) {
        return (float) smooth(LIP_RISE_START, LIP_RISE_END, fit);
    }

    static float rimReach(float fit) {
        return (float) smooth(LIP_REACH_START, LIP_REACH_END, fit);
    }

    static Plate forBone(String name) {
        return switch (name) {
            case SMALL -> COMPACT;
            case WIDE -> BROAD;
            default -> null;
        };
    }

    static float influence(double bodyPitch, double relativeYaw, double headPitch, double arm, boolean elytra) {
        if (elytra || !Double.isFinite(bodyPitch) || !Double.isFinite(relativeYaw)
                || !Double.isFinite(headPitch) || !Double.isFinite(arm)) return 0;
        double turn = Math.abs(Math.toDegrees(Math.IEEEremainder(relativeYaw, 2 * Math.PI)));
        return (float) (smooth(DOWN_START, DOWN_FULL, Math.toDegrees(headPitch))
                * (1 - smooth(TURN_START, TURN_END, turn))
                * (1 - smooth(LEAN_START, LEAN_END, bodyPitch / CapeFit.CROUCH_RADIANS))
                * (1 - smooth(ARM_START, ARM_END, arm)));
    }

    private static Plate plate(int index) {
        double[] a = TARGETS[index], r = RIMS[index];
        return new Plate((float)a[0], (float)a[1], (float)a[2], (float)a[3], (float)a[4],
                (float)a[5], (float)a[6], (float)a[7], (float)a[8], (float)a[9],
                new Rim((float)r[0], (float)r[1], (float)r[2], (float)r[3], (float)r[4],
                        (float)r[5], (float)r[6], (float)r[7], (float)r[8], (float)r[9]));
    }

    private static double smooth(double a, double b, double value) {
        double t = Math.max(0, Math.min(1, (value-a)/(b-a)));
        return t * t * (3 - 2 * t);
    }
}
