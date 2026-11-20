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
    private static final double TURN_KEEP_AFTER = 48;
    private static final double TURN_SOFTNESS = .115;
    private static final double TURN_OPEN_FROM = 60;
    private static final double TURN_OPEN_END = 79;
    private static final double TURN_DEPTH_START = .04;
    private static final double TURN_DEPTH_END = .84;
    // Front edge and base of the exposed rear collar in model units.
    private static final double TURN_LIP_Y = 21.7;
    private static final double TURN_LIP_Z = 6.0;
    private static final double TURN_LIP_HEIGHT = .70;
    private static final double TURN_LIP_ADVANCE = .22;
    private static final double TURN_LIP_RISE = .48;
    private static final double TURN_LIP_SHIFT = .92;
    static final Shape NONE = new Shape(0, null, null, null, null, null);

    record Affine(float x, float y, float z, float dx, float dy, float dz, float sx, float sy, float sz) {}
    record Shape(float seat, Affine collar, Affine lip, Affine facing, Affine small, Affine wide) {
        Affine forBone(String name) {
            return switch (name) {
                case CapePlateFit.SMALL -> small;
                case CapePlateFit.WIDE -> wide;
                // The fixed crosspiece is already fitted to the sleeves.
                case "v17_cowl_return" -> null;
                default -> name.startsWith("v17_cowl_back_") ? lip : name.startsWith("v17_cowl_tooth_") ? facing :
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
        double signedTurn = Math.toDegrees(Math.IEEEremainder(relativeYaw, 2*Math.PI));
        double down = Math.toDegrees(headPitch), turn = Math.abs(signedTurn);
        double leanRoom = 1 - smooth(.05, .36, stance);
        double steepRoom = 1 - .82 * smooth(62, 88, down) * smooth(24, 36, turn);
        double sleeveRoom = 1 - smooth(2.85, 6, sleeve);
        double release = smooth(44, 57, turn);
        double space = (1 - smooth(.02, .40, depth)) * leanRoom * (1 - release) * steepRoom;
        double stroke = dry * space * (1 - smooth(2.85, 6, armBack));
        double reach = space * sleeveRoom;
        double tuck = dry * (1 - .48 * smooth(.62, .995, previousSeat)) * (1 - smooth(.09, .32, stance))
                * (1 - smooth(.10, .82, depth)) * (1 - smooth(10, 25, sleeve));
        double trim = reach * smooth(24, 43, down);
        // Keep the compact footprint independent of ordinary sleeve swing;
        // open Z and raise the wide lower edge as a sleeve sweeps under it.
        double rest = dry * (1 - smooth(.72, 1, plateFit)) * (1 - smooth(.10, .50, stance))
                * (1 - smooth(14, 33, -down)) * (1 - smooth(70, 86, turn));
        // Retain the original lower lip over the first cloth ribbons when
        // the earlier seat already has the compact plate against the wearer.
        double compact = rest * (1 - smooth(.54, .76, previousSeat)) * (1 - smooth(.10, .26, stance));
        double sweep = smooth(5, 25, sleeve), advance = reach * smooth(12, 42, down);
        double upright = 1 - smooth(0, 23, down);
        // At deep inclinations the neck is clear of the rear edge. Finish
        // seating the crown without pulling the teeth away from the roots.
        double crown = trim * (1 + 1.24 * smooth(.76, .995, previousSeat)
                + .46 * smooth(78, 87, down) * smooth(.79, .995, previousSeat));
        double seatStroke = .68 * smooth(23, 43, down);
        double seat = seatStroke * stroke;
        // Preserve part of the earlier collar fit, not a separate stroke
        // added as the first one releases. The loss curve x -> x*s/(x+s)
        // meets the diagonal's slope at 48° and then levels out. It opens
        // again at a profile turn, with less support when space is needed.
        double lost = Math.max(0, release - smooth(44, 57, TURN_KEEP_AFTER));
        double hold = lost*lost / (lost + TURN_SOFTNESS)
                * (1 - smooth(TURN_OPEN_FROM, TURN_OPEN_END, turn))
                * smooth(30, 45, down) * (1 - smooth(64, 78, down))
                * (1 - smooth(TURN_DEPTH_START, TURN_DEPTH_END, depth)) * leanRoom * steepRoom * sleeveRoom;
        double scale = CapeFit.seatDepthScale(Math.max(previousSeat, seat + seatStroke*dry*hold))
                / CapeFit.seatDepthScale(Math.max(previousSeat, seat));
        // This extra seat is only an affine on the collar. The actual
        // plate, teeth, stitching and drape keep their established fit.
        double shift = (1-scale) * (CapeFit.SEAT_PLANE - depth - PIVOTS[0][2]);
        // Once the sleeve fit is nearly engaged, advance the whole broad
        // plate instead of shortening its contact rim. Lift it just enough
        // to retain clearance through the sleeve's idle sway.
        double settled = dry * smooth(.78, .99, plateFit);
        double foldReach = crown + hold*smooth(24, 43, down);
        // On a deeper turn the exposed edge follows the near shoulder a
        // little; the buried fold and stitching do not travel across it.
        double side = -Math.signum(signedTurn) * TURN_LIP_SHIFT * hold * smooth(48, 57, down);
        Affine underFold = collar(tuck, foldReach, shift, scale, 0, 0, 0);
        Affine lip = hold > 0 ? collar(tuck, foldReach, shift, scale, crown, hold, side) : underFold;
        return new Shape((float) seat, underFold, lip, collar(tuck, trim * .16, 0, 1, 0, 0, 0),
                affine(1, compact, .94, .92, 1 - .17 * advance, 0, .18 * advance, -.24 * advance),
                rest == 0 && settled == 0 ? null : affine(2, 1, 1 - .60 * rest, 1 - .59 * rest,
                        1 - .14 * advance * rest, 0,
                        rest * (.065 + .37*sweep + .48*advance - .47*upright) + .07 * settled,
                        rest * (-.24*advance + .52*sweep + .22*upright) - .38 * settled));
    }

    private static Affine collar(double amount, double reach, double shift, double scale,
                                 double lipReach, double hold, double side) {
        if (amount <= 0) return null;
        double[] pivot = PIVOTS[0];
        double dy = -.58*amount, dz = shift - 1.62*reach*amount*scale;
        double sy = 1 + amount*(.41-1), sz = (1 - .12*reach*amount)*scale;
        if (hold > 0) {
            // The lower fold can compress into the seat, but do not flatten
            // the exposed lip. Retain thickness around its leading edge
            // and grow upward from the lower stitched edge.
            double thickness = 1 - .12*lipReach*amount;
            double raise = TURN_LIP_HEIGHT * hold;
            dy += raise*(pivot[1] + dy - TURN_LIP_Y) + TURN_LIP_RISE*hold;
            dz -= (thickness - sz)*(TURN_LIP_Z - pivot[2]) + TURN_LIP_ADVANCE*hold;
            sy *= 1 + raise;
            sz = thickness;
        }
        return new Affine((float)pivot[0], (float)pivot[1], (float)pivot[2], (float)side, (float)dy, (float)dz,
                (float)(1 + amount*(.965-1)), (float)sy, (float)sz);
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
