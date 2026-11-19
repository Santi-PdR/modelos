package com.capatest.client;

/** Measured motion of the wearer, in world blocks per tick. No server state. */
final class CapeTravel {
    private static final double SIDE_DEAD_ZONE = .018;
    private static final double SIDE_FULL = .14;
    private static final double MAX_STEP_XZ = 3.0;
    private static final double MAX_STEP_Y = 5.0;

    record Step(double x, double y, double z) {
        boolean finite() { return Double.isFinite(x) && Double.isFinite(y) && Double.isFinite(z); }
    }

    record Motion(double speed, double lift, double side, boolean cut) {}
    private static final Motion CUT = new Motion(0, 0, 0, true);

    private CapeTravel() {}

    static Motion measure(Step velocity, Step displacement, boolean tracked, double bodyYaw) {
        // Packet interpolation can move a remote player while deltaMovement is
        // zero (or stale). Use the last visible step, even when it is a stop.
        // A large discontinuity is not a giant stride. Drop the old inertia.
        if (!displacement.finite() || Math.abs(displacement.y()) > MAX_STEP_Y
                || Math.hypot(displacement.x(), displacement.z()) > MAX_STEP_XZ) return CUT;
        Step move = tracked ? displacement : velocity;
        if (!move.finite() || !Double.isFinite(bodyYaw)) return CUT;
        double yaw = Math.toRadians(bodyYaw);
        double cross = Math.cos(yaw) * move.x() + Math.sin(yaw) * move.z();
        double amount = clamp((Math.abs(cross) - SIDE_DEAD_ZONE)/(SIDE_FULL - SIDE_DEAD_ZONE), 0, 1);
        double side = Math.copySign(amount * amount * (3 - 2 * amount), cross);
        return new Motion(clamp(Math.hypot(move.x(), move.z()) * 2.2, 0, 1),
                clamp(-move.y() * 1.3, -.45, 1), side, false);
    }

    private static double clamp(double value, double low, double high) {
        return Math.max(low, Math.min(high, value));
    }
}
