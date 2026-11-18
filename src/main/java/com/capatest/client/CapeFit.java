package com.capatest.client;

/**
 * Pose-only clearance for the equipped cape. Samples are in degrees, from
 * a bare 8u head plus a .25u margin. Input is the live HumanoidModel pose,
 * not the camera angle or a potentially out-of-date crouching flag.
 */
public final class CapeFit {
    public static final String BONE = "cape_wearer_fit";
    public static final double CROUCH_RADIANS = 0.5;
    private static final double PITCH_STEP = 15;
    private static final double YAW_STEP = 30;

    // [body lean 0, .25, .50 rad][absolute relative yaw 0..90][look up -90..90].
    // Interpolation is stateless: bends track abrupt head motion without lag.
    private static final double[][][] FOLD = {
        {
            {0, 0, 0, 0, 0, 2.15, 0, 4.65, 6.15, 9.15, 17.9, 21.15, 19.65},
            {0, 0, 0, 0, 0, 0, 1.65, 7.9, 8.15, 8.65, 15.15, 25.65, 22.65},
            {3.15, 2.65, 1.15, 1.15, 0, 0, 1.65, 11.65, 9.15, 10.4, 19.4, 20.15, 18.65},
            {10.15, 10.15, 9.15, 7.65, 5.65, 4.65, 4.65, 4.65, 5.65, 7.65, 9.15, 10.15, 10.15}
        },
        {
            {0, 0, 0, 0, 0, 4.9, 5.15, 6.15, 9.65, 17.4, 21.65, 19.65, 18.15},
            {0, 0, 0, 0, 0, 3.3, 8.8, 8.65, 10.15, 14.65, 22.9, 22.4, 19.65},
            {1.65, 1.65, 1.15, 1.15, 0, 3.15, 8.15, 8.65, 10.15, 17.15, 20.15, 18.15, 17.65},
            {9.65, 9.15, 9.65, 10.15, 8.15, 6.65, 5.15, 6.65, 8.15, 10.15, 9.65, 9.15, 9.65}
        },
        {
            {0, 0, 0, 0, 5.65, 4.65, 5.65, 9.65, 18.9, 21.15, 18.65, 17.15, 19.15},
            {0, 0, 0, 1.65, 7.65, 11.9, 8.65, 10.65, 15.15, 21.65, 29.5, 18.65, 20.65},
            {1.65, 1.65, 2.15, 3.15, 7.65, 14.65, 8.65, 10.65, 18.9, 20.9, 17.15, 17.15, 18.65},
            {11.15, 11.15, 10.65, 10.65, 11.65, 9.65, 5.65, 9.65, 11.65, 10.65, 10.65, 11.15, 11.15}
        }
    };

    private CapeFit() {}

    public static double foldDegrees(double bodyPitch, double bodyYaw, double headPitch, double headYaw) {
        if (!Double.isFinite(bodyPitch) || !Double.isFinite(bodyYaw)
                || !Double.isFinite(headPitch) || !Double.isFinite(headYaw))
            return 0.0;
        double stance = clamp(bodyPitch / CROUCH_RADIANS, 1.0) * (FOLD.length - 1);
        // Minecraft +pitch is down; the fit table uses +look up.
        double pitch = clamp((90 - Math.toDegrees(headPitch)) / PITCH_STEP, FOLD[0][0].length - 1);
        double yaw = clamp(Math.abs(Math.toDegrees(Math.IEEEremainder(headYaw - bodyYaw, 2 * Math.PI)))
                / YAW_STEP, FOLD[0].length - 1);
        int row = Math.min((int) stance, FOLD.length - 2);
        return lerp(at(FOLD[row], yaw, pitch), at(FOLD[row + 1], yaw, pitch), stance - row);
    }

    private static double at(double[][] posture, double yaw, double pitch) {
        int yi = Math.min((int) yaw, posture.length - 2);
        int pi = Math.min((int) pitch, posture[0].length - 2);
        return lerp(lerp(posture[yi][pi], posture[yi][pi + 1], pitch - pi),
                lerp(posture[yi + 1][pi], posture[yi + 1][pi + 1], pitch - pi), yaw - yi);
    }

    private static double clamp(double x, double max) {
        return Math.max(0, Math.min(max, x));
    }

    private static double lerp(double a, double b, double t) {
        return a + (b - a) * t;
    }
}
