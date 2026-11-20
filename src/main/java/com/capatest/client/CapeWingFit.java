package com.capatest.client;

/** Extra reach for folded vanilla elytra, measured at the existing cloth hinge. */
public final class CapeWingFit {
    private static final double FOLDED = 17.0;
    private static final double CLEAR_SPAN = 74.0;
    private static final double PITCH_BIAS = 16.0;
    private static final double PITCH_GAIN = 1.0;
    private static final double BODY_GAIN = 0.83;
    private static final double DEPTH_GAIN = 4.5;
    private static final double GOAL_LIMIT = 34.0;
    private static final double LIFT_LIMIT = 25.0;
    private static final double CARRY = 0.88;
    private static final double SOFT_EDGE = 2.0;

    private CapeWingFit() {}

    /** Rendered wing pitch/roll, torso pitch in degrees and mount depth in model units. */
    public static double topGoal(double pitch, double roll, double lean, double depth) {
        if (!Double.isFinite(pitch) || !Double.isFinite(roll)
                || !Double.isFinite(lean) || !Double.isFinite(depth)) return 0;
        // A nearly horizontal wing no longer runs alongside the cloth.
        // Use the wing's current lerped angle, including on the landing.
        double folded = clamp((CLEAR_SPAN - Math.abs(roll)) / (CLEAR_SPAN - FOLDED), 1);
        return folded * folded * (3 - 2 * folded) * clamp(PITCH_BIAS + PITCH_GAIN * clamp(pitch, 45)
                - BODY_GAIN * clamp(lean, 30) - DEPTH_GAIN * Math.max(0, depth), GOAL_LIMIT);
    }

    public static double topLift(double authored, double goal) {
        if (goal <= 0 || !Double.isFinite(authored) || !Double.isFinite(goal)) return 0;
        double gap = Math.max(0, goal - authored);
        double t = clamp(gap / SOFT_EDGE, 1);
        // Leave some authored flutter even while below the guide angle.
        return clamp(CARRY * gap * t * (2 - t), LIFT_LIMIT);
    }

    private static double clamp(double x, double cap) {
        return Math.max(0, Math.min(cap, x));
    }
}
