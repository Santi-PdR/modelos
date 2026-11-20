package com.capatest.client;

/**
 * Restore the compact attachment line of the v1.28.0 worn rig, in chestplate
 * space. The large plate has a compact rest shape even when the head turns
 * or the sleeves move. The closeness of the collar/roots varies only to
 * clear the wearer; the authored cloth tracks and the free hem stay intact.
 */
final class CapeTorsoFit {
    // Geckolib model coordinates (16 per block), after mirroring GEO X.
    private static final double[][] PIVOTS = {
            {0, 22.35, 4.45},
            {4.57, 22.95, 3.55},
            {-4.26, 22.45, 3.75}
    };
    static final Shape NONE = new Shape(0, null, null, null, null);

    record Affine(float x, float y, float z, float dx, float dy, float dz, float sx, float sy, float sz) {}
    record Shape(float seat, Affine collar, Affine facing, Affine small, Affine wide) {
        Affine forBone(String name) {
            return switch (name) {
                case CapePlateFit.SMALL -> small;
                case CapePlateFit.WIDE -> wide;
                // The fixed crosspiece is already fitted to the sleeves.
                case "v17_cowl_return" -> null;
                default -> name.startsWith("v17_cowl_tooth_") ? facing :
                        name.startsWith("v17_cowl_") || name.startsWith("v19_cuellito_")
                                || name.startsWith("v18_chain_") ? collar : null;
            };
        }
    }

    private CapeTorsoFit() {}

    // The additional depth stroke is for the visible pieces. Keep the
    // returns, yoke and buried mount under the previous structural fit.
    static boolean followsSeat(String name) {
        return name.equals(CapeFit.DRAPE_BONE) || name.equals(CapePlateFit.SMALL) || name.equals(CapePlateFit.WIDE)
                || (!name.equals("v17_cowl_return") && (name.startsWith("v17_cowl_")
                        || name.startsWith("v19_cuellito_") || name.startsWith("v18_chain_")));
    }

    static Shape shape(double bodyPitch, double headPitch, double relativeYaw, double depth,
                       double previousSeat, double plateFit, double armBack, double sleeve,
                       double dry, boolean elytra) {
        if (elytra || dry <= 0 || !Double.isFinite(bodyPitch) || !Double.isFinite(headPitch)
                || !Double.isFinite(relativeYaw) || !Double.isFinite(depth)
                || !Double.isFinite(armBack) || !Double.isFinite(sleeve) || !Double.isFinite(dry)
                || !Double.isFinite(previousSeat) || !Double.isFinite(plateFit)) return NONE;
        double stance = bodyPitch / CapeFit.CROUCH_RADIANS;
        double down = Math.toDegrees(headPitch), turn = Math.abs(Math.toDegrees(Math.IEEEremainder(relativeYaw, 2*Math.PI)));
        double space = (1 - smooth(.02, .40, depth)) * (1 - smooth(.05, .36, stance))
                * (1 - smooth(44, 57, turn)) * (1 - .82 * smooth(62, 88, down) * smooth(24, 36, turn));
        double stroke = dry * space * (1 - smooth(2.85, 6, armBack));
        double reach = space * (1 - smooth(2.85, 6, sleeve));
        double tuck = dry * (1 - .48 * smooth(.62, .995, previousSeat)) * (1 - smooth(.09, .32, stance))
                * (1 - smooth(.10, .82, depth)) * (1 - smooth(10, 25, sleeve));
        double trim = reach * smooth(24, 43, down);
        // Keep the compact footprint independent of ordinary sleeve swing;
        // open Z and raise the wide lower edge as a sleeve sweeps under it.
        double rest = dry * (1 - smooth(.72, 1, plateFit)) * (1 - smooth(.10, .50, stance))
                * (1 - smooth(14, 33, -down)) * (1 - smooth(70, 86, turn));
        double sweep = smooth(5, 25, sleeve), advance = reach * smooth(12, 42, down);
        double upright = 1 - smooth(0, 23, down);
        return new Shape((float) (.68 * smooth(23, 43, down) * stroke),
                collar(tuck, trim), collar(tuck, trim * .32),
                affine(1, rest, .94, .92, 1 - .17 * advance, 0, 0,  -.24 * advance),
                affine(2, rest, .40, .41, 1 - .14 * advance, 0,
                        .065 + .37*sweep - .47*upright, -.24*advance + .52*sweep + .22*upright));
    }

    private static Affine collar(double amount, double reach) {
        return affine(0, amount, .965, .41, 1 - .12 * reach, 0, -.58, -1.62 * reach);
    }

    private static Affine affine(int i, double k, double sx, double sy, double sz,
                                 double dx, double dy, double dz) {
        if (k <= 0) return null;
        double[] pivot = PIVOTS[i];
        return new Affine((float)pivot[0], (float)pivot[1], (float)pivot[2], (float)(k*dx), (float)(k*dy), (float)(k*dz),
                (float)(1 + k*(sx-1)), (float)(1 + k*(sy-1)), (float)(1 + k*(sz-1)));
    }

    private static double smooth(double start, double end, double value) {
        double t = Math.max(0, Math.min(1, (value-start)/(end-start)));
        return t*t*(3-2*t);
    }
}
