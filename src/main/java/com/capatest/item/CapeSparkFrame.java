package com.capatest.item;

/** Tick-time approximation of the vanilla 1.20.1 player render frame, without client classes. */
public final class CapeSparkFrame {
    public record Offset(double x, double y, double z) {}

    private static final double PLAYER_SCALE = 0.9375D;
    // LivingEntityRenderer's -1.501 plus GeckoLib's 24/16 armor origin, with Y flipped.
    private static final double FEET_Y = (1.501F - 1.5F) * PLAYER_SCALE;
    // Vanilla HumanoidModel crouches around body (24 model units up), then
    // PlayerRenderer lowers the entire draw by another eighth of a block.
    private static final double CROUCH_PITCH = .5;
    private static final double BODY_PIVOT = 1.5;
    private static final float CROUCH_BODY_Y = 3.2F; // model units, downward
    private static final double CROUCH_RENDER_DROP = .125;
    private static final double CROUCH_COS = Math.cos(CROUCH_PITCH), CROUCH_SIN = Math.sin(CROUCH_PITCH);
    // Measured against the lower ribbons of the authored AIR/SWIM clips. The
    // server does not know the animated bones or a client's cloth response.
    private static final double GLIDE_HEM_UP = .77D;
    private static final double GLIDE_HEM_BACK = .64D;
    private static final double SWIM_HEM_UP = .09D;
    private static final double SWIM_HEM_BACK = .22D;

    private final double yawCos, yawSin, pitchCos, pitchSin, turnCos, turnSin;
    private final double heightScale, hemUp, hemBack;
    private final boolean posed, swimShift, crouching;

    private CapeSparkFrame(double yaw, double pitch, double turn, double heightScale,
                           boolean posed, boolean swimShift, boolean crouching, double hemUp, double hemBack) {
        double radians = Math.toRadians(yaw);
        yawCos = Math.cos(radians);
        yawSin = Math.sin(radians);
        radians = Math.toRadians(pitch);
        pitchCos = Math.cos(radians);
        pitchSin = Math.sin(radians);
        turnCos = Math.cos(turn);
        turnSin = Math.sin(turn);
        this.heightScale = heightScale;
        this.posed = posed;
        this.swimShift = swimShift;
        this.crouching = crouching;
        this.hemUp = hemUp;
        this.hemBack = hemBack;
    }

    public static CapeSparkFrame upright(double yaw, double hitboxHeight) {
        return new CapeSparkFrame(yaw, 0, 0, Math.max(.36D, Math.min(1, hitboxHeight / 1.80D)),
                false, false, false, 0, 0);
    }

    public static CapeSparkFrame crouch(double yaw) {
        // Still the upright family for collar eligibility. Only the birth
        // point follows the bent torso; impulses remain in world-up axes.
        return new CapeSparkFrame(yaw, 0, 0, PLAYER_SCALE, false, false, true, 0, 0);
    }

    public static CapeSparkFrame glide(double yaw, double viewPitch, double flightTicks,
                                       double lookX, double lookZ, double motionX, double motionZ) {
        double tilt = Math.min(1, flightTicks * flightTicks / 100.0D);
        double length = Math.hypot(lookX, lookZ) * Math.hypot(motionX, motionZ);
        double turn = 0;
        if (length > 0) {
            double cosine = (lookX * motionX + lookZ * motionZ) / length;
            double cross = motionX * lookZ - motionZ * lookX;
            turn = Math.signum(cross) * Math.acos(Math.max(-1, Math.min(1, cosine)));
        }
        double cloth = Math.min(1, flightTicks / CapePlayback.FIRST_BLEND);
        return new CapeSparkFrame(yaw, tilt * (-90 - viewPitch), turn, PLAYER_SCALE,
                true, false, false, cloth * GLIDE_HEM_UP, cloth * GLIDE_HEM_BACK);
    }

    /** Use the visual blend, not just isInWater; wading with no blend is upright. */
    public static CapeSparkFrame swim(double yaw, double viewPitch, double amount,
                                      boolean immersed, boolean visuallySwimming) {
        double cloth = immersed ? amount : 0;
        return new CapeSparkFrame(yaw, amount * (immersed ? -90 - viewPitch : -90), 0, PLAYER_SCALE,
                true, visuallySwimming, false, cloth * SWIM_HEM_UP, cloth * SWIM_HEM_BACK);
    }

    /** True only for the root rotations of glide or swim, not a crouched torso. */
    public boolean posed() { return posed; }

    public Offset birth(CapeState.Spark spark) {
        return point(spark.side(), spark.height() + hemUp, spark.depth() + hemBack);
    }

    /** Project a virtual point on the relaxed rig, in blocks and with the legacy side sign. */
    public Offset point(double side, double height, double back) {
        if (crouching) {
            double y = height - BODY_PIVOT;
            double up = BODY_PIVOT - CROUCH_BODY_Y / 16.0 + y * CROUCH_COS + back * CROUCH_SIN;
            double depth = back * CROUCH_COS - y * CROUCH_SIN;
            return yaw(side * PLAYER_SCALE, up * PLAYER_SCALE + FEET_Y - CROUCH_RENDER_DROP, depth * PLAYER_SCALE);
        }
        if (!posed) return yaw(side, height * heightScale, back);

        // Ry(180-bodyYaw) · Rx(pitch) · Ry(turn) · T(swim) · S(player).
        // The renderer's local X is -side; a short collision box doesn't shrink the mesh.
        double x = side * PLAYER_SCALE;
        double y = height * PLAYER_SCALE + FEET_Y - (swimShift ? 1 : 0);
        double z = back * PLAYER_SCALE + (swimShift ? .3F : 0);
        double lateral = x * turnCos - z * turnSin;
        double depth = x * turnSin + z * turnCos;
        return yaw(lateral, y * pitchCos - depth * pitchSin, y * pitchSin + depth * pitchCos);
    }

    /** Detached ash keeps the original world-up lift and body-yaw drift. */
    public Offset impulse(double side, double lift, double back) {
        return yaw(side, lift, back);
    }

    private Offset yaw(double side, double height, double back) {
        return new Offset(yawSin * back + yawCos * side, height, -yawCos * back + yawSin * side);
    }
}
