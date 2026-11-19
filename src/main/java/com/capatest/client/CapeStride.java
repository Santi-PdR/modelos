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

    public static double armGoal(double arm, double bodyPitch, double depth) {
        return Math.max(0, ARM_GAIN * arm - ARM_INSET - lean(bodyPitch) - ARM_FIT * depth);
    }

    public static double legGoal(double leg, double bodyPitch, double depth) {
        return clamp(LEG_GAIN * leg - LEG_INSET - lean(bodyPitch) - LEG_FIT * depth, MID_TARGET_LIMIT);
    }

    /** Only lift when the clip and the existing torso fit haven't already cleared the stride. */
    public static double topLift(double authoredTop, double armGoal, double legGoal) {
        double goal = clamp(Math.max(armGoal, LEG_SHARE * legGoal), TOP_LIMIT);
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
