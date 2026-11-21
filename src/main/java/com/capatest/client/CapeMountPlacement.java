package com.capatest.client;

/** Fixed dress fit in authored model pixels (16 per block); no head or view input. */
final class CapeMountPlacement {
    // Fit the visible rim to the back of the *body*, not to the silhouette
    // of the head or the outer jacket. +Z points out from the spine.
    static final double BACK_PLANE = 1.90;
    static final double RIM_DEPTH = .39;
    static final double RIM_Y = 22.50;
    static final double RIM_HEIGHT = .72;
    static final double RIM_DROP = .79;
    static final double SHOULDER_HEIGHT = .98;
    static final double SHOULDER_REACH = 1.07;
    static final double SHOULDER_RISE = .48;
    static final double RETURN_DROP = .56;

    // The lining remains on the bare skin. Lift its outer edge (not the
    // edge against the neck) so the shallower rim has no air pocket.
    static final double LINING_DEPTH = .93;
    static final double LINING_LIFT = .38;
    static final double LINING_PLANE = 2.00;
    static final double LINING_DROP = .075;
    static final double GUSSET_DEPTH = .91;
    static final String SEAT_BONE = "v20_mount_seat";
    static final String SADDLE_BONE = "v20_mount_saddle";
    static final double SADDLE_WIDTH = 1.075;
    static final double SADDLE_HEIGHT = 1.36;
    static final double SADDLE_THICKNESS = 1.13;
    static final double SADDLE_DEPTH = .065;
    static final double SADDLE_DROP = .29;
    static final double WING_SADDLE_WIDTH = 1.08;
    static final double WING_SADDLE_DEPTH = .33;

    // Seat the original hinge closer to the spine, without squashing the
    // drape. A small outward bias leaves room for the moving limbs.
    static final double DRAPE_ADVANCE = .57;
    static final double DRAPE_DROP = .19;
    static final double DRAPE_PITCH = 4.4;

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
            -.58, 1.26, -4.33, 10, 1, -3, 1.20, .95, 2.10, .34);
    static final Plate WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16,
            -.87, 1.04, -4.30, 10, 3, 3, .59, .78, 1.94, -.15);

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

    static boolean rim(String name) {
        return name.startsWith("v17_cowl_") || name.startsWith("v19_cuellito_") || name.startsWith("v18_chain_");
    }
}
