package com.capatest.client;

/**
 * Head clearance in body-space model units (16 per block). The back plate
 * never follows this stroke. Its fabric gusset gives in Z while the drape
 * settles toward the legs at its own seam. No animated position or scale
 * is written to GeckoLib snapshots.
 */
public final class CapeFit {
    public static final String BONE = "cape_wearer_fit";
    public static final String SEAT_FRAME = "cape_seat_fit";
    public static final String DRAPE_BONE = "cape_drape_fit";
    public static final double SEAT_PLANE = 2.38;
    private static final double SEAT_TAKE_IN = .46;
    private static final double SEAT_RETURN_IN = .11;
    private static final double SEAT_DOWN_START = 61;
    private static final double SEAT_DOWN_FULL = 76;
    private static final double SEAT_TURN_START = 13;
    private static final double SEAT_TURN_END = 47;
    private static final double SEAT_LEAN_START = .20;
    private static final double SEAT_LEAN_END = .66;
    private static final double SEAT_ARM_START = 3.1;
    private static final double SEAT_ARM_END = 8.5;
    public static final String GUSSET_BONE = "v20_mount_gusset";
    public static final double CROUCH_RADIANS = 0.5;
    private static final double PITCH_STEP = 7.5;
    private static final double YAW_STEP = 7.5;
    private static final double GUSSET_DEPTH = 3.48;
    private static final double DRAPE_DEGREES_PER_UNIT = 1.65;
    public static final String SHOULDERS_BONE = "v20_mount_shoulders";
    public static final String UNDER_YOKE_BONE = "v20_mount_under_yoke";
    public record YokeShape(float width, float height, float depth) {}
    private static final YokeShape TUCKED_YOKE = new YokeShape(.51F, .065F, .62F);
    private static final YokeShape OPEN_YOKE = new YokeShape(1, 1, 1);
    public static final double SHOULDER_MIN = .245;
    public static final double SHOULDER_HEIGHT = .27;

    // [Torso lean 0..0.5 rad][absolute relative yaw 0..90][look up -90..90].
    // Calibrated against the inflated vanilla head, eight clips and blends.
    // The collar ends also clear the thicker outer layer of the player skin.
    // The neutral and straight-down samples stay at the authored fit.
    private static final double[][][] BACKSET = {
        {
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.34, 0.57, 0.46, 0, 0.54, 0.71, 1.38, 2.09, 3.19, 4.07, 5.35, 5.92, 5.76, 6.52, 6.18, 5.62},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.92, 1.49, 1.52, 1.98, 1.6, 1.99, 2.04, 2.29, 2.63, 3.59, 5.85, 6.84, 6.43, 6.24, 5.99, 5.43},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.11, 0.19, 0.3, 1.12, 1.43, 1.43, 1.63, 2.26, 3.11, 4.8, 5.83, 5.91, 7.16, 6.43, 5.93},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 1.24, 2.18, 1.68, 1.88, 2.13, 2.79, 4.55, 5.59, 5.66, 7.29, 6.68, 6.18},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.24, 1.12, 1.44, 2.12, 2.12, 2.18, 3.02, 4.4, 5.58, 5.69, 7.32, 6.62, 6.3},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.12, 0.5, 1.37, 2.11, 2.37, 2.3, 2.76, 4.55, 5.67, 5.82, 6.82, 6.37, 6.05},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.24, 2.74, 2.3, 2.43, 3.35, 5.02, 5.92, 6.09, 6.34, 5.93, 5.5},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.18, 0.55, 1.24, 2.3, 2.31, 2.43, 3.5, 5.45, 6.78, 6.16, 6.4, 6.05, 5.62},
            {0.37, 0.08, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.68, 1.3, 2.12, 2.45, 2.93, 3.93, 5.25, 6.08, 5.43, 5.49, 5.38, 5.24},
            {0.74, 0.58, 0.46, 0.33, 0.25, 0.25, 0.25, 0.25, 0.06, 0, 0, 0, 0.3, 1.15, 1.85, 2.04, 2.24, 3.01, 3.89, 4.4, 4.93, 4.62, 4.62, 4.49, 4.37},
            {0.8, 0.8, 0.71, 0.71, 0.68, 0.68, 0.68, 0.74, 0.67, 0.25, 0.25, 0.18, 0.3, 1.27, 1.55, 1.59, 2.51, 2.89, 3.46, 3.37, 3.99, 3.71, 3.62, 3.49, 3.49},
            {1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.08, 1.05, 1.12, 0.81, 0.76, 0.68, 0.79, 1.43, 2.07, 1.95, 2.15, 2.24, 2.55, 2.93, 2.71, 2.62, 2.55, 2.55},
            {1.62, 1.62, 1.62, 1.62, 1.68, 1.62, 1.38, 1.33, 1.25, 1.29, 1.27, 1.22, 1.3, 1.19, 1.27, 1.27, 1.3, 1.3, 1.38, 1.62, 1.68, 1.62, 1.62, 1.62, 1.62}
        },
        {
            {0, 0, 0, 0, 0, 0, 0, 0.12, 0.92, 1.32, 0.46, 0.62, 0.79, 1.4, 2.01, 2, 3.01, 4.31, 4.7, 6.23, 6.31, 6.8, 6.09, 5.55, 5.43},
            {0, 0, 0, 0, 0, 0, 0, 0, 0.92, 0.74, 1.44, 1.28, 1.42, 1.3, 1.49, 2.54, 2.97, 3.67, 6.08, 7.11, 6.17, 6.24, 5.99, 5.49, 5.18},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.07, 0.23, 0.83, 1.46, 1.74, 1.67, 1.68, 2.13, 3.15, 4.8, 5.83, 6.42, 7.16, 6.91, 5.93, 5.68},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.71, 2.08, 2.24, 1.8, 1.93, 2.26, 2.84, 4.31, 5.75, 6.26, 7.29, 7.04, 6.18, 5.93},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.17, 0.55, 1.2, 2.06, 2.38, 2.38, 2.38, 2.84, 4.32, 5.58, 6.32, 7.32, 7.07, 6.24, 5.93},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.06, 0.43, 1.07, 1.95, 2.87, 2.99, 2.55, 2.83, 4.38, 5.68, 6.46, 6.82, 6.57, 5.99, 5.68},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.33, 1.96, 2.99, 2.99, 2.55, 2.83, 4.86, 5.84, 5.86, 6.62, 5.91, 5.43, 5.18},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.15, 0.4, 1.09, 2.09, 2.99, 2.99, 2.55, 3.87, 5.53, 7.16, 6.63, 6.62, 6.28, 5.74, 5.49},
            {0.12, 0.08, 0, 0, 0, 0, 0, 0, 0, 0, 0.15, 0.52, 1.43, 1.68, 2.68, 2.8, 2.93, 4.05, 5.83, 6.91, 6.01, 5.18, 5.37, 5.12, 5.12},
            {0.49, 0.46, 0.3, 0.18, 0.17, 0, 0, 0, 0.06, 0, 0, 0.62, 2.12, 2.27, 1.85, 1.97, 2.79, 3.85, 4.83, 5.01, 4.8, 4.5, 4.37, 4.25, 4.3},
            {0.62, 0.55, 0.5, 0.43, 0.55, 0.43, 0.43, 0.43, 0.43, 0.43, 0.18, 0.93, 1.43, 2.02, 1.55, 2.09, 3.27, 3.34, 3.57, 4.07, 3.87, 3.58, 3.49, 3.49, 3.5},
            {0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.83, 0.8, 0.93, 0.8, 0.8, 1.52, 1.3, 2.22, 2.53, 2.48, 2.27, 2.43, 2.93, 2.87, 2.71, 2.62, 2.67, 2.68},
            {1.62, 1.62, 1.62, 1.62, 1.62, 1.74, 1.62, 1.46, 1.38, 1.33, 1.4, 1.35, 0.62, 1.35, 1.44, 1.36, 1.48, 1.38, 1.62, 1.74, 1.7, 1.62, 1.62, 1.68, 1.68}
        },
        {
            {0, 0, 0, 0, 0, 0, 0, 0.92, 0.52, 1.14, 1.03, 0.93, 0.9, 2.03, 2.07, 2.91, 3.56, 5.58, 6.19, 6.36, 6.74, 6.3, 5.5, 5.33, 5.74},
            {0, 0, 0, 0, 0, 0, 0, 0.74, 1.22, 0.52, 0.71, 1.29, 1.72, 1.39, 2.47, 3.15, 4.57, 5.95, 6.96, 6.55, 6.12, 5.87, 5.38, 5, 5.12},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 1.24, 1.71, 1.71, 1.62, 1.75, 2.11, 3.15, 4.72, 5.75, 6.21, 7.37, 6.33, 5.88, 5.5, 5.5},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.72, 1.31, 2.05, 1.96, 1.75, 2, 2.25, 2.68, 4.23, 5.67, 6.46, 7.49, 6.58, 6, 5.75, 5.75},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.85, 1.22, 1.92, 3.31, 2.57, 2.37, 2.5, 2.88, 4.24, 5.42, 6.37, 7.43, 6.64, 6.09, 5.87, 5.88},
            {0, 0, 0, 0, 0, 0, 0, 0, 0.05, 0.3, 0.68, 1.99, 3.44, 2.82, 2.49, 2.62, 2.93, 4.22, 5.52, 6.69, 6.58, 6.14, 5.84, 5.74, 5.62},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.02, 1.65, 3.33, 3.33, 2.5, 2.62, 3.05, 4.69, 5.68, 6.56, 6.56, 6.08, 5.25, 5.12, 5.12},
            {0, 0, 0, 0, 0, 0, 0, 0, 0, 0.18, 0.8, 1.99, 3.45, 2.84, 2.46, 2.58, 3.43, 5.61, 6.94, 6.84, 6.44, 6.21, 5.62, 5.37, 5.59},
            {0.05, 0, 0, 0, 0, 0, 0, 0, 0, 0.43, 0.8, 1.55, 2.8, 2.8, 2.33, 2.33, 3.45, 6.1, 7.12, 5.65, 5.12, 5.12, 4.99, 5.15, 5.35},
            {0.3, 0.18, 0.18, 0.18, 0.18, 0.05, 0.05, 0, 0, 0.96, 1.29, 2.07, 1.99, 1.75, 1.88, 2.79, 4.23, 4.93, 5.01, 4.71, 4.58, 4.33, 4.35, 4.43, 4.5},
            {0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 0.43, 1.22, 1.68, 1.68, 1.5, 1.85, 3.35, 3.83, 3.62, 4.07, 3.83, 3.71, 3.58, 3.5, 3.62, 3.74},
            {0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 1.01, 1.03, 1.12, 1.12, 1.43, 2.99, 2.5, 2.33, 2.58, 2.88, 2.88, 2.82, 2.83, 2.75, 2.75, 2.87},
            {1.75, 1.75, 1.75, 1.75, 1.75, 1.99, 1.87, 1.63, 1.63, 1.61, 1.59, 1.59, 1.5, 1.59, 2.01, 1.63, 1.58, 1.71, 1.87, 1.99, 1.82, 1.83, 1.75, 1.75, 1.75}
        },
        {
            {0, 0, 0, 0, 0, 0, 0.3, 0.91, 0.7, 0.55, 0.83, 1.3, 1.95, 1.84, 3.27, 3.76, 5.7, 5.71, 6.03, 6.31, 5.81, 5.38, 5.12, 5.76, 5.52},
            {0, 0, 0, 0, 0, 0, 1.1, 0.43, 0.56, 1.06, 1.33, 1, 1.31, 2.54, 2.63, 4.39, 6.2, 6.82, 6.15, 5.88, 5.74, 5.25, 4.88, 5, 6.3},
            {0, 0, 0, 0, 0, 0, 0, 0, 0.63, 1.51, 1.62, 1.38, 1.5, 1.75, 2.12, 3.15, 4.75, 5.59, 6.54, 6.96, 6.24, 5.83, 5.38, 5.49, 5.74},
            {0, 0, 0, 0, 0, 0, 0, 0, 1.07, 2.1, 2.1, 1.62, 1.75, 2, 2.38, 2.8, 4.07, 5.51, 7.04, 7.08, 6.37, 5.96, 5.62, 5.87, 6.12},
            {0, 0, 0, 0, 0, 0, 0, 0.4, 0.91, 1.85, 2.6, 2.18, 2.21, 2.37, 2.62, 3, 4.02, 5.24, 6.99, 6.99, 6.37, 5.88, 5.74, 5.75, 6},
            {0, 0, 0, 0, 0, 0, 0, 0.12, 0.5, 1.49, 2.25, 2.62, 2.33, 2.49, 2.83, 3.09, 3.98, 5.28, 6.81, 6.1, 5.99, 5.62, 5.62, 5.62, 5.75},
            {0, 0, 0, 0, 0, 0, 0, 0, 0.12, 1.37, 3.02, 3.02, 2.38, 2.5, 2.71, 3.09, 3.96, 5.7, 6.1, 6.26, 5.94, 5.12, 5, 5.12, 5.38},
            {0, 0, 0, 0, 0, 0, 0, 0, 0.05, 1.43, 2.25, 2.62, 2.33, 2.46, 2.62, 3.24, 4.85, 6.07, 6.05, 6.51, 6.07, 5.44, 5.24, 5, 5.35},
            {0, 0, 0, 0, 0, 0.05, 0.05, 0.12, 0.55, 1.49, 2, 2.55, 2.21, 2.21, 2.38, 3.77, 5.97, 6.37, 5.55, 5.24, 5, 5.1, 5.12, 5.59, 6.23},
            {0.19, 0.18, 0.19, 0.19, 0.18, 0.3, 0.3, 0.37, 0.99, 2.21, 2.33, 1.62, 1.75, 1.88, 2.75, 4.07, 5.51, 5.25, 4.81, 4.5, 4.58, 4.56, 4.86, 4.87, 5.12},
            {0.75, 0.76, 0.75, 0.75, 0.76, 0.75, 0.75, 0.75, 0.99, 1.38, 1.85, 1.38, 1.5, 1.97, 3.11, 3.91, 3.82, 4.32, 3.88, 3.81, 3.81, 3.75, 3.87, 3.99, 4.12},
            {1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 1.31, 2.6, 3.03, 2.82, 2.75, 3.17, 3.3, 3.06, 3.05, 2.96, 2.99, 3, 3.12},
            {2.12, 2, 2, 2, 2, 2, 2.18, 2.06, 1.95, 1.95, 1.95, 1.95, 1.95, 2.02, 1.95, 1.95, 1.95, 2.06, 2.18, 2, 2.12, 2.08, 2.12, 2, 2}
        },
        {
            {0, 0, 0, 0, 0, 0, 0.68, 0.67, 0.24, 0.62, 0.87, 1.28, 2.39, 2.86, 3.84, 5.27, 5.8, 5.68, 6.3, 5.63, 5.12, 5, 5.42, 5.25, 5.62},
            {0, 0, 0, 0, 0, 0.86, 0.18, 0.19, 1.01, 1.01, 1.03, 1.66, 1.75, 2.8, 3.98, 5.9, 6.75, 5.87, 5.8, 5.49, 5.12, 4.75, 4.88, 6.17, 5.74},
            {0, 0, 0, 0, 0, 0, 0, 0.43, 1.26, 1.38, 1.12, 1.38, 1.62, 2, 2.87, 4.59, 5.23, 6.62, 6.54, 5.88, 5.62, 5.24, 5.37, 5.5, 6},
            {0, 0, 0, 0, 0, 0, 0, 0.92, 2.07, 1.37, 1.49, 1.62, 1.88, 2.38, 2.8, 3.83, 5.35, 7.04, 7.04, 6.18, 5.8, 5.55, 5.62, 5.88, 6.25},
            {0, 0, 0, 0, 0, 0, 0.3, 1.69, 1.66, 2, 1.88, 2, 2.21, 2.62, 3, 3.78, 5, 6.99, 6.99, 6.06, 5.68, 5.56, 5.62, 5.88, 6.37},
            {0, 0, 0, 0, 0, 0.18, 0.55, 0.49, 1.88, 2.87, 2, 2.12, 2.46, 2.74, 3.12, 3.87, 4.96, 6.83, 6.58, 5.75, 5.49, 5.55, 5.68, 5.75, 6.24},
            {0, 0, 0, 0, 0, 0.18, 0.12, 0.55, 2.12, 2.99, 2.12, 2.25, 2.38, 2.75, 3.12, 3.74, 5.3, 6.22, 6.1, 5.55, 5.12, 5.05, 5.18, 5.38, 5.75},
            {0, 0, 0, 0, 0, 0.05, 0.3, 0.8, 2, 2.93, 2.12, 2.25, 2.38, 2.62, 2.88, 4.29, 5.21, 5.81, 6.18, 5.8, 5.3, 5.11, 5.12, 5.12, 5.56},
            {0.03, 0, 0.08, 0.08, 0.18, 0.33, 0.58, 1, 1.88, 2.62, 2.12, 2.12, 2.24, 2.38, 3.42, 5.09, 6.97, 5.68, 5.25, 5.12, 5.05, 5.11, 5.78, 6.02, 5.8},
            {0.59, 0.62, 0.59, 0.59, 0.6, 0.58, 0.71, 0.93, 1.99, 1.62, 1.74, 1.75, 1.88, 2.12, 3.54, 5.69, 6.38, 5.19, 4.71, 4.68, 4.68, 4.94, 5.32, 5.24, 5.12},
            {1.11, 1.11, 1.11, 1.11, 1.11, 1.11, 1.11, 1.25, 1.74, 1.38, 1.38, 1.5, 1.62, 2.2, 4.03, 5.1, 4.69, 4.44, 4.15, 4.18, 4.34, 4.24, 4.18, 4.37, 4.24},
            {1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 3.04, 3.34, 3.43, 3.55, 3.55, 3.25, 3.24, 3.24, 3.25, 3.33, 3.46, 3.55},
            {2.49, 2.39, 2.39, 2.39, 2.39, 2.39, 2.43, 2.55, 2.42, 2.39, 2.39, 2.39, 2.39, 2.54, 2.39, 2.41, 2.37, 2.49, 2.38, 2.37, 2.39, 2.39, 2.46, 2.46, 2.55}
        }
    };

    private CapeFit() {}

    public static double backset(double bodyPitch, double bodyYaw, double headPitch, double headYaw) {
        if (!Double.isFinite(bodyPitch) || !Double.isFinite(bodyYaw)
                || !Double.isFinite(headPitch) || !Double.isFinite(headYaw))
            return 0.0;
        double stance = clamp(bodyPitch / CROUCH_RADIANS, 1.0) * (BACKSET.length - 1);
        // Minecraft +pitch is down; the table uses +look up.
        double pitch = clamp((90 - Math.toDegrees(headPitch)) / PITCH_STEP, BACKSET[0][0].length - 1);
        double yaw = clamp(Math.abs(Math.toDegrees(Math.IEEEremainder(headYaw - bodyYaw, 2 * Math.PI)))
                / YAW_STEP, BACKSET[0].length - 1);
        int row = Math.min((int) stance, BACKSET.length - 2);
        return lerp(at(BACKSET[row], yaw, pitch), at(BACKSET[row + 1], yaw, pitch), stance - row);
    }

    /** Shorten just the shoulder returns about their stitched ends, in
     * body space. The seat remains bedded in the torso even with the wings
     * on or when the sleeves/head need room. */
    public static double shoulderReach(double bodyPitch, double bodyYaw, double headPitch, double headYaw,
                                       boolean elytra) {
        if (elytra || !Double.isFinite(bodyPitch) || !Double.isFinite(bodyYaw)
                || !Double.isFinite(headPitch) || !Double.isFinite(headYaw))
            return SHOULDER_MIN;
        double stance = clamp(bodyPitch / CROUCH_RADIANS, 1);
        double look = -Math.toDegrees(headPitch);
        double yaw = Math.abs(Math.toDegrees(Math.IEEEremainder(headYaw - bodyYaw, 2 * Math.PI)));
        double down = smooth(34, 62, -look) * (1 - .62 * smooth(44, 73, yaw)) * (1 - .52 * smooth(0, 1, stance));
        double ahead = .45 * (1 - smooth(0, 3, yaw)) * (1 - smooth(0, 42, Math.abs(look)))
                * (1 - .66 * smooth(0, .70, stance));
        return lerp(SHOULDER_MIN, 1, Math.max(ahead, down));
    }

    /** Close the inside of both shoulder seams with a tucked lining.
     * As an arm sweeps into the join, fold the lining down against the seat.
     * The wings use the fully tucked shape, inside the existing gusset. */
    public static YokeShape yokeShape(double bodyPitch, double headPitch, double armBack, boolean elytra) {
        if (elytra || !Double.isFinite(bodyPitch) || !Double.isFinite(headPitch) || !Double.isFinite(armBack))
            return TUCKED_YOKE;
        double stance = clamp(bodyPitch / CROUCH_RADIANS, 1);
        double posture = (1 - smooth(0, .60, stance)) * (1 - smooth(42, 83, -Math.toDegrees(headPitch)));
        double sleeve = 1 - smooth(2.9, 6.1, armBack);
        double spread = posture * sleeve;
        if (spread == 0) return TUCKED_YOKE;
        if (spread == 1) return OPEN_YOKE;
        // Narrow the lining before lowering it, so the moving fold never
        // sweeps down through the elbow. Crouch/looking up lower all of it.
        return new YokeShape((float) lerp(.51, 1, spread),
                (float) lerp(.065, 1, posture * smooth(0, .44, sleeve)),
                (float) lerp(.62, 1, spread));
    }

    /** Bring the visible trim and the start of the drape in together when the
     * actual head and sleeves leave room. This is a body-space fit, not an F5
     * camera correction. Do not contract into folded wings. */
    static double seating(double bodyPitch, double bodyYaw, double headPitch, double headYaw,
                          double armBack, boolean elytra) {
        if (elytra || !Double.isFinite(bodyPitch) || !Double.isFinite(headPitch)
                || !Double.isFinite(headYaw - bodyYaw) || !Double.isFinite(armBack)) return 0;
        double turn = Math.abs(Math.toDegrees(Math.IEEEremainder(headYaw - bodyYaw, 2 * Math.PI)));
        return smooth(SEAT_DOWN_START, SEAT_DOWN_FULL, Math.toDegrees(headPitch))
                * (1 - smooth(SEAT_TURN_START, SEAT_TURN_END, turn))
                * (1 - smooth(SEAT_LEAN_START, SEAT_LEAN_END, bodyPitch / CROUCH_RADIANS))
                * (1 - smooth(SEAT_ARM_START, SEAT_ARM_END, armBack));
    }

    static double seatDepthScale(double seating) { return 1 - SEAT_TAKE_IN * seating; }

    static double seatReturnWidth(double seating) { return 1 - SEAT_RETURN_IN * seating; }

    private static double smooth(double lo, double hi, double x) {
        double t = clamp((x - lo) / (hi - lo), 1);
        return t * t * (3 - 2 * t);
    }

    public static double gussetScale(double depth) {
        return 1 + depth / GUSSET_DEPTH;
    }

    public static double drapeDegrees(double depth) {
        return depth * DRAPE_DEGREES_PER_UNIT;
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
