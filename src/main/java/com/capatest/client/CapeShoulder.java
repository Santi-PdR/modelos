package com.capatest.client;

/** Small rigid hinge above each sleeve, in the baked torso's model-pixel axes. */
final class CapeShoulder {
    static final double HINGE_X = 5.50, HINGE_Y = 24.25, HINGE_Z = .53;
    private static final double START = .020, FULL = .235;
    private static final double PITCH = 17, ROLL = 13;
    private static final double OUT = .16, LIFT = .24, FOLLOW_UP = .17, FOLLOW_Z = .38, SWEEP = .30;
    private static final double UP_LIMIT = .75, Z_LIMIT = .55;

    record Pose(double x, double y, double z, double pitch, double roll) {}
    static final Pose REST = new Pose(0, 0, 0, 0, 0);

    private CapeShoulder() {}

    static double side(boolean wide) { return wide ? -1 : 1; }

    static Pose pose(boolean wide, double sleeveDownY, double sleeveDownZ, double jointRise, double jointZ) {
        if (!Double.isFinite(sleeveDownY) || !Double.isFinite(sleeveDownZ)
                || !Double.isFinite(jointRise) || !Double.isFinite(jointZ)) return REST;
        // The sleeve points down at rest. Using its direction rather than
        // Euler angles handles wrapped strokes and leaves vanilla idle bob alone.
        double t = clamp((1 + sleeveDownY - START) / (FULL - START), 0, 1);
        if (t == 0) return REST;
        double weight = t * t * (3 - 2 * t);
        double side = side(wide);
        double swing = clamp(sleeveDownZ, -1, 1);
        // Raise the exposed edge around the sewn side of the plate; the
        // near edge needn't follow the elbow through the entire arm swing.
        return new Pose(side * OUT * weight, (LIFT + FOLLOW_UP * clamp(jointRise, 0, UP_LIMIT)) * weight,
                (FOLLOW_Z * clamp(jointZ, -Z_LIMIT, Z_LIMIT) - SWEEP * swing) * weight,
                -PITCH * swing * weight, side * ROLL * weight);
    }

    private static double clamp(double x, double min, double max) {
        return Math.max(min, Math.min(max, x));
    }
}
