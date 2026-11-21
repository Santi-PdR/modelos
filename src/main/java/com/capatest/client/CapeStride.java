package com.capatest.client;

/** Bounded, rotation-only clearance at the sewn top and middle hinges. */
public final class CapeStride {
    private static final double ARM_GAIN = 1.23;
    private static final double ARM_INSET = 8.0;
    private static final double ARM_FIT = 2.0;
    private static final double LEG_GAIN = 1.05;
    private static final double LEG_INSET = 9.0;
    private static final double LEG_FIT = 1.0;
    private static final double LEG_SHARE = 0.70;
    private static final double TOP_LIMIT = 49.5;
    private static final double MID_TARGET_LIMIT = 64.0;
    private static final double SOFT_EDGE = 2.0;

    private CapeStride() {}

    /** The backward component of a limb's down axis (vanilla ZYX ModelPart). */
    public static double backDegrees(double pitch, double yaw) {
        double back = Math.sin(pitch) * Math.cos(yaw);
        return Double.isFinite(back) ? Math.toDegrees(Math.asin(clamp(back, 1))) : 0;
    }

    /** Keep room for the whole imminent step, instead of dropping the two
     * heavy hinges between each pair of feet. The live limb is still a
     * lower bound (it can also be holding an item, attacking or sitting). */
    static double walkEnvelope(double actual, double stride, double amplitude, double ground, double scale) {
        double wave = Math.cos(2 * Math.PI * stride);
        double shape = Math.sqrt(.85 + .15 * wave * wave);
        double anticipated = Math.toDegrees(amplitude * scale) * shape * ground;
        return actual + raise(anticipated - actual);
    }

    /** Drive the heavy hinges from the eased gait, not whichever foot is
     * furthest back in this render sample. Keep clearance for non-gait limb
     * excursions (e.g. an arm gesture), and fade toward the rendered limbs
     * when leaving the grounded gait. */
    static double groundedEnvelope(double actual, double stride, double pace, double amplitude, double ground, double scale) {
        double wave = Math.cos(2 * Math.PI * stride);
        double gait = Math.toDegrees(pace * scale) * Math.sqrt(.85 + .15 * wave * wave);
        double extra = raise(actual - Math.toDegrees(amplitude * scale) - 1.5);
        return actual + ground * (gait + extra - actual);
    }

    public static double armGoal(double arm, double bodyPitch, double depth) {
        return Math.max(0, ARM_GAIN * arm - ARM_INSET - lean(bodyPitch) - ARM_FIT * depth);
    }

    public static double legGoal(double leg, double bodyPitch, double depth) {
        return clamp(LEG_GAIN * leg - LEG_INSET - lean(bodyPitch) - LEG_FIT * depth, MID_TARGET_LIMIT);
    }

    static double topGoal(double armGoal, double legGoal) {
        return clamp(Math.max(armGoal, LEG_SHARE * legGoal), TOP_LIMIT);
    }

    /** Only lift when the clip and the existing torso fit haven't already cleared the stride. */
    public static double topLift(double authoredTop, double armGoal, double legGoal) {
        double goal = topGoal(armGoal, legGoal);
        return goal > 0 ? raise(goal - authoredTop) : 0;
    }

    public static double midLift(double liftedTop, double authoredMid, double legGoal) {
        return legGoal > 0 ? raise(legGoal - liftedTop - authoredMid) : 0;
    }

    private static double lean(double pitch) {
        return Double.isFinite(pitch) ? Math.toDegrees(clamp(pitch, CapeFit.CROUCH_RADIANS)) : 0;
    }

    private static double raise(double gap) {
        if (gap <= 0) return 0;
        if (gap >= SOFT_EDGE) return gap;
        // Zero derivative when contact starts; matches the linear ramp at the far end.
        double t = gap / SOFT_EDGE;
        return gap * t * (2 - t);
    }

    private static double clamp(double x, double max) {
        return Math.max(0, Math.min(max, x));
    }
}
