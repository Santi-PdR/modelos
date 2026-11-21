package com.capatest.client;

/** Positions of the original pieces, in model pixels (16 per block). */
final class CapeMountPlacement {
    // Move the whole garment from its seat frame. The collar, chain and
    // cloth keep their original dimensions and registration to each other.
    static final double BACK_FORWARD = 2.27;
    static final double BACK_DROP = .25;
    // Move the existing inner support, intact, to catch the flexing roots.
    static final double SADDLE_SET = .32;
    static final String SADDLE_BONE = "v20_mount_saddle";
    static final double WING_SADDLE_WIDTH = 1.08;
    static final double WING_SADDLE_DEPTH = .33;
    // Present a little of the existing shoulder fabric above the sleeves.
    static final double SHOULDER_LIFT = .50;
    static final double SHOULDER_FORWARD = .76;
    // Both halves of the old backing have an upper, forward-facing lip.
    // The fitted seat/saddle already cover its seam; this lip pierces the
    // nape at a steep downward aim. Keep the other two cubes and the asset.
    static final int LINING_LIP_CUBE = 1;
    static final int LINING_CUBES = 3;

    // Rigid whole-plate poses over the sleeves; X is mirrored on draw.
    static final Plate SMALL = new Plate(CapePlateFit.SMALL, -5.84, 22.35, 4.46,
            -.61, 1.95, -4.06, -9, 24, 1.5, .26);
    // The wearer's left, on the right of the front F5 view. Set the inner
    // lip lower and back from the head's sweep; keep the outer edge over
    // the sleeve. This is one rigid rest pose, not a head-driven hinge.
    static final Plate WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16,
            -.49, -.08, -3.49, -12.75, 79.65, .65, -.15);

    // Keep the independent fit with Elytra.
    static final Plate WING_SMALL = new Plate(CapePlateFit.SMALL, -5.84, 22.35, 4.46,
            -1.30, 1.15, -5.88, 14, 4, -14, .65);
    static final Plate WING_WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16,
            -.54, .32, -4.30, 8, 86, 10, 0);

    record Plate(String bone, double x, double y, double z, double dx, double dy, double dz,
                 double pitch, double yaw, double roll, double slimDx) {
        double shiftX(boolean slim) { return dx + (slim ? slimDx : 0); }
    }

    private CapeMountPlacement() {}

    static Plate plate(boolean elytra, boolean wide) {
        return elytra ? (wide ? WING_WIDE : WING_SMALL) : (wide ? WIDE : SMALL);
    }
}
