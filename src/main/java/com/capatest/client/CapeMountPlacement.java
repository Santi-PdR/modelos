package com.capatest.client;

/** Fixed dress fit in authored model pixels (16 per block); no head or view input. */
final class CapeMountPlacement {
    // Leave the seat, gusset and drape hinge at their authored locations.
    // The original upper backing laps against the jersey, and the two
    // shoulder returns now reach from the cowl to the matching plate.
    static final double SHOULDER_HEIGHT = .98;
    static final double SHOULDER_REACH = 1.07;
    static final double RETURN_DROP = .38;

    static final String SADDLE_BONE = "v20_mount_saddle";
    static final double SADDLE_WIDTH = 1.08;
    static final double SADDLE_DEPTH = .33;

    // A shallow fold in the exterior collar, without shifting the whole
    // mount off the upper back. The cowl's teeth still meet the saddle.
    static final double TRIM_Y = 22.35;
    static final double TRIM_Z = 4.45;
    static final double TRIM_DROP = .44;
    static final double TRIM_WIDTH = .965;
    static final double TRIM_HEIGHT = .49;

    // Fit each whole authored plate to the length of the sleeve, with its
    // back edge overlapping the return. X is mirrored on draw. Slim gets
    // its own static inward offsets; nothing follows the swinging arms.
    static final Plate SMALL = new Plate(CapePlateFit.SMALL, -5.84, 22.35, 4.46,
            -.58, 1.40, -4.33, 10, 1, -3, 1.20, .95, 2.10, .34);
    static final Plate WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16,
            -.87, 1.18, -4.30, 10, 3, 3, .59, .78, 1.94, -.15);

    // Retain the shorter, forward fit when the back slot shares the torso
    // with physical Elytra, so the plate tails do not extend into the wings.
    static final Plate WING_SMALL = new Plate(CapePlateFit.SMALL, -5.84, 22.35, 4.46,
            -1.30, 1.15, -5.88, 14, 4, -14, 1, 1, 1, .65);
    static final Plate WING_WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16,
            -.54, .32, -4.30, 8, 86, 10, 1, 1, 1, 0);

    record Plate(String bone, double x, double y, double z, double dx, double dy, double dz,
                 double pitch, double yaw, double roll, double width, double height, double depth, double slimDx) {
        double shiftX(boolean slim) { return dx + (slim ? slimDx : 0); }
    }

    private CapeMountPlacement() {}

    static Plate plate(boolean elytra, boolean wide) {
        return elytra ? (wide ? WING_WIDE : WING_SMALL) : (wide ? WIDE : SMALL);
    }

    static boolean trim(String name) {
        return name.startsWith("v17_cowl_") && !name.startsWith("v17_cowl_tooth_") && !name.equals("v17_cowl_return")
                || name.startsWith("v19_cuellito_") || name.startsWith("v18_chain_");
    }
}
