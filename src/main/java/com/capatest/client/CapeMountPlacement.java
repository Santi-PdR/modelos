package com.capatest.client;

/** Places the original v1.67.14 rig in the live chest frame, in model pixels. */
final class CapeMountPlacement {
    static final double PIVOT_Y = 21.95;
    static final double PIVOT_Z = 2.30;
    private static final double PIN_Y = 16;
    private static final double PIN_Z = 2.04;
    private static final double JOIN_Y = 21.34;
    private static final double JOIN_Z = 5.55;
    private static final double LEAVE_AT = 5;
    private static final double SEATED_AT = 41;
    private static final double RELIEF_START = 60;
    private static final double RELIEF_END = 84;
    private static final double TILT = 33;
    private static final double DROP = 1.29;
    private static final double EXTRA_DROP = 1.85;
    private static final double REAR = 1.01;
    private static final double EXTRA_REAR = 1.20;
    private static final double DIAGONAL = .55;
    private static final double DRAPE = 23;
    private static final double EXTRA_DRAPE = 8;

    // GeckoLib X is mirrored from the authored GEO. Translate each whole
    // plate, including its bevel and raised rim; do not resize any cube.
    static final Shift SMALL = new Shift(.24, 1.33, -.88);
    static final Shift WIDE = new Shift(-.58, 1.72, -1.08);
    record Shift(double x, double y, double z) {}
    record Pose(double depth, double settledDepth, double fitPitch, double dy, double pitch,
                double drape, double linkPitch, double linkScale, double plate) {
        boolean movesMount() { return pitch != 0; }
    }

    static final Pose REST = unchanged(0, 0);

    private CapeMountPlacement() {}

    static Pose solve(double bodyPitch, double bodyYaw, double headPitch, double headYaw,
                      double effort, double dry, boolean enabled) {
        double original = CapeFit.backset(bodyPitch, bodyYaw, headPitch, headYaw);
        if (!enabled || dry <= 0 || !Double.isFinite(dry) || !Double.isFinite(effort)
                || !Double.isFinite(bodyPitch) || !Double.isFinite(bodyYaw)
                || !Double.isFinite(headPitch) || !Double.isFinite(headYaw))
            return unchanged(original, headPitch);

        double look = -Math.toDegrees(headPitch);
        double yaw = Math.abs(Math.toDegrees(Math.IEEEremainder(headYaw - bodyYaw, Math.PI * 2)));
        double lean = bodyPitch / CapeFit.CROUCH_RADIANS;
        double plate = dry * (1 - smooth(.05, .45, lean)) * (1 - smooth(3, 21, yaw))
                * (1 - smooth(19, 39, -look)) * (1 - smooth(.2, 2.45, original)) * (1 - smooth(4, 22, effort));
        double amount = dry * smooth(LEAVE_AT, SEATED_AT, look) * (1 - smooth(.08, .50, lean));
        if (amount == 0) return new Pose(original, original, headPitch, 0, 0, 0, 0, 1, plate);

        // Exchange most of the old straight rear slide for an arc below
        // the neck. Ease out of it in crouch and leave the wing fit alone.
        double relief = smooth(RELIEF_START, RELIEF_END, look);
        double fitPitch = headPitch * (1 - amount);
        double settled = CapeFit.backset(bodyPitch, bodyYaw, fitPitch, headYaw);
        double room = REAR + relief * (EXTRA_REAR + DIAGONAL * smooth(19, 43, yaw));
        double depth = original * (1 - amount) + amount * (settled + amount * room);
        double pitch = TILT * amount, dy = -(DROP + EXTRA_DROP * relief) * amount;
        double drape = pitch + (DRAPE + EXTRA_DRAPE * relief) * amount;

        // The existing inner gusset was already elastic in depth. Keep its
        // lower pin in the shirt and carry its upper end along with the
        // same rigid transform as the collar, instead of exposing the strap.
        double baseY = JOIN_Y - PIN_Y;
        double baseZ = (JOIN_Z - PIN_Z) * CapeFit.gussetScale(depth);
        double y = JOIN_Y - PIVOT_Y, z = PIN_Z + baseZ - depth - PIVOT_Z;
        double rad = Math.toRadians(pitch), c = Math.cos(rad), s = Math.sin(rad);
        double endY = PIVOT_Y - PIN_Y + dy + c*y - s*z;
        double endZ = PIVOT_Z - PIN_Z + depth + s*y + c*z;
        double linkPitch = Math.toDegrees(Math.atan2(endZ, endY) - Math.atan2(baseZ, baseY));
        double linkScale = Math.hypot(endY, endZ) / Math.hypot(baseY, baseZ);
        return new Pose(depth, settled, fitPitch, dy, pitch, drape, linkPitch, linkScale, plate);
    }

    private static Pose unchanged(double depth, double headPitch) {
        return new Pose(depth, depth, headPitch, 0, 0, 0, 0, 1, 0);
    }

    private static double smooth(double start, double end, double value) {
        double t = Math.max(0, Math.min(1, (value - start) / (end - start)));
        return t*t*(3 - 2*t);
    }
}
