package com.capatest.client;

/** Fixed offsets on the original rig, in authored model pixels (16 per block). */
final class CapeMountPlacement {
    // The authored drape hinge, not the head pivot. Both tilts act about
    // that hinge; the original clip still rotates on top of the fixed seat.
    static final double PIVOT_Y = 22.82;
    static final double PIVOT_Z = 4.89;
    private static final double PIN_Y = 16;
    private static final double PIN_Z = 2.04;
    private static final double JOIN_Y = 21.34;
    private static final double JOIN_Z = 5.55;
    private static final double REAR = 1.82;
    private static final double DROP = 1.56;
    private static final double TILT = 12;
    private static final double FALL = 13;

    // The plates no longer cover the outer ribbon roots. Seat the existing
    // internal saddle under those roots; do not enlarge the exterior trim.
    static final String SADDLE_BONE = "v20_mount_saddle";
    static final double SADDLE_WIDTH = 1.08;
    static final double SADDLE_DEPTH = .66;
    static final double WING_SADDLE_DEPTH = .33;

    // Carry the neutral trim from the previous fitted pose, but do not
    // run the former head-dependent trim, return, or plate strokes.
    static final double TRIM_Y = 22.35;
    static final double TRIM_Z = 4.45;
    static final double TRIM_DROP = .58;
    static final double TRIM_WIDTH = .965;
    static final double TRIM_HEIGHT = .41;

    // Translate/rotate the complete authored plates in chest space, so the
    // faces sit over the shoulders rather than behind the vanilla sleeves.
    // These are GEO coordinates; CapaArmorRenderer mirrors X on draw.
    static final Plate SMALL = new Plate(CapePlateFit.SMALL, -5.84, 22.35, 4.46, -1.30, 1.15, -5.88, 14, 4, -14);
    static final Plate WIDE = new Plate(CapePlateFit.WIDE, 7.24, 22.43, 4.16, -.54, .32, -4.30, 8, 86, 10);
    record Plate(String bone, double x, double y, double z, double dx, double dy, double dz, float pitch, float yaw, float roll) {}

    record Pose(double depth, double dy, double pitch, double drape, double linkPitch, double linkScale) {}
    private static final Pose BACK = fixed();
    // Preserve the neutral fold with Elytra fitted. Only the existing
    // lower-cloth wing guide responds to the actual wing angles.
    private static final Pose WINGS = new Pose(0, 0, 0, 0, 0, 1);

    private CapeMountPlacement() {}

    static Pose worn(boolean elytra) { return elytra ? WINGS : BACK; }

    static boolean trim(String name) {
        return name.startsWith("v17_cowl_") && !name.startsWith("v17_cowl_tooth_") && !name.equals("v17_cowl_return")
                || name.startsWith("v19_cuellito_") || name.startsWith("v18_chain_");
    }

    private static Pose fixed() {
        // Keep the foot of the existing interior gusset against the chest;
        // carry its upper end to the same fixed point on the rigid saddle.
        double y = JOIN_Y - PIVOT_Y, z = JOIN_Z - PIVOT_Z;
        double rad = Math.toRadians(TILT), c = Math.cos(rad), s = Math.sin(rad);
        double endY = PIVOT_Y - PIN_Y - DROP + c*y - s*z;
        double endZ = PIVOT_Z - PIN_Z + REAR + s*y + c*z;
        double baseY = JOIN_Y - PIN_Y, baseZ = JOIN_Z - PIN_Z;
        double link = Math.toDegrees(Math.atan2(endZ, endY) - Math.atan2(baseZ, baseY));
        double scale = Math.hypot(endY, endZ) / Math.hypot(baseY, baseZ);
        return new Pose(REAR, -DROP, TILT, TILT + FALL, link, scale);
    }
}
