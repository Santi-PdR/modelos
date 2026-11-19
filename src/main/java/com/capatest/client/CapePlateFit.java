package com.capatest.client;

/** Bring the actual shoulder plates onto the sleeve line without moving the yoke or the cloth. */
final class CapePlateFit {
    static final String SMALL = "v18_pad_0", WIDE = "v18_pad_1";
    private static final double DOWN_START = 41, DOWN_FULL = 77;
    private static final double TURN_START = 18, TURN_END = 60;
    private static final double LEAN_START = .14, LEAN_END = .60;
    private static final double ARM_START = 2.85, ARM_END = 5.30;

    // Rendered X/Y/Z of the inner sewn pivot; fitted width/height/depth; Y/Z
    // adjustment; pitch/yaw. Applied before the common cape_seat_fit scale.
    // Fold the broad unsupported end in. Extend the compact front lip
    // without pulling the back edge away from the cloth roots.
    // The exporter reads this table for the body-space preview, not keyframes.
    private static final double[][] TARGETS = {
            {4.53, 23.15, 4.95, 1, 1, 1.27, .06, -.275, 0, -3.5},
            {-4.24, 23.15, 4.95, .514, .92, 1, .02, -1.065, 5.5, 11.4}
    };
    private static final Plate COMPACT = plate(0), BROAD = plate(1);

    private CapePlateFit() {}

    record Plate(float x, float y, float z, float width, float height, float depth, float lift, float advance,
                 float pitch, float yaw) {}

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
        double[] a = TARGETS[index];
        return new Plate((float)a[0], (float)a[1], (float)a[2], (float)a[3], (float)a[4],
                (float)a[5], (float)a[6], (float)a[7], (float)a[8], (float)a[9]);
    }

    private static double smooth(double a, double b, double value) {
        double t = Math.max(0, Math.min(1, (value-a)/(b-a)));
        return t * t * (3 - 2 * t);
    }
}
