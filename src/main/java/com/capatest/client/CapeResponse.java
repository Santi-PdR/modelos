package com.capatest.client;

/** Filtro de pose por portador. La respuesta depende del tiempo, no de los FPS. */
public final class CapeResponse {
    // Cotas, en grados antes del peso por tramo. verify_v1600 sondea estos extremos.
    public static final double MAX_BACK = 2.10;
    public static final double MAX_IN = 1.20;
    public static final double MAX_YAW = 1.55;
    public static final double MAX_ROLL = 1.40;
    private static final double SIDE_NEAR_RATE = 11.0;
    private static final double SIDE_HEM_RATE = 4.2;
    private static final double SIDE_YAW = 0.62;
    private static final double SIDE_ROLL = 1.32;
    private static final double SIDE_WATER_DAMPING = 0.65;
    private static final double HEM_TURN_RATE = 4.2;
    private static final double TURN_WAKE = .98, TURN_WATER_DAMPING = .60;
    private static final double SEGMENT_POWER = 1.45;
    private static final double SPEED_RATE = 8.0;
    private static final double HEM_SPEED_RATE = 3.1;
    private static final double RIM_SPEED_RATE = 1.8;
    private static final double TICK_SECONDS = 1 / 20.0;
    // Same order as the pose inputs: speed, lift, turn, crouch, water, air, sprint.
    private static final double[] RATES = {SPEED_RATE, 6.2, 9.0, 8.0, 4.4, 8.0, 8.0};

    private final double[] values = new double[RATES.length];
    private final double[] targets = new double[RATES.length + 1]; // includes lateral travel
    private double lastSeconds = Double.NaN;
    private double hemTurn;
    private double hemSpeed;
    private double rimSpeed; // Only used by the emissive pass.
    private double hemAir;
    private double pitchBase;
    private double pitchLag;
    private double sideNear;
    private double sideHem;

    public void reset() {
        lastSeconds = Double.NaN;
    }

    public double[] sample(double seconds, double speed, double lift, double turn,
                           double crouch, double water, double air, double sprint) {
        return sample(seconds, speed, lift, turn, crouch, water, air, sprint, 0);
    }

    public double[] sample(double seconds, double speed, double lift, double turn,
                           double crouch, double water, double air, double sprint, double side) {
        double dt = seconds - lastSeconds;
        if (dt == 0) return values; // An extra pass must not replace the last observed input.
        lastSeconds = seconds;
        // Allow one ULP of clock rounding at the ten-tick boundary.
        boolean reset = !Double.isFinite(dt) || dt < 0 || (dt > .5 && dt - .5 > Math.ulp(seconds));
        // We don't know when a newly observed input changed within the gap.
        // Continue the old response, then give the new input at most one tick.
        if (!reset && dt > TICK_SECONDS) advance(dt - TICK_SECONDS);
        targets[0] = speed;
        targets[1] = lift;
        targets[2] = turn;
        targets[3] = crouch;
        targets[4] = water;
        targets[5] = air;
        targets[6] = sprint;
        targets[7] = side;
        if (reset) {
            // First draw or a real clock/view cut: discard the old impulse.
            System.arraycopy(targets, 0, values, 0, values.length);
            hemTurn = turn;
            hemSpeed = rimSpeed = speed;
            hemAir = air;
            sideNear = sideHem = side;
        } else {
            advance(Math.min(dt, TICK_SECONDS));
        }
        pitchBase = (values[3] + values[4]) * .72 - (values[6] * 1.3 + values[5] * .9
                + values[1] * .65 + values[0] * .62);
        // A slower tail keeps the opening briefly during braking or landing.
        // No new force at steady speed; water damps the extra rotation.
        pitchLag = Math.max(0, Math.max(3.8 * (hemSpeed - values[0]), 3.1 * (hemAir - values[5])))
                * (1 - .65 * values[4]);
        return values;
    }

    private void advance(double dt) {
        for (int i = 0; i < values.length; ++i)
            values[i] = toward(values[i], targets[i], dt, RATES[i]);
        hemSpeed = toward(hemSpeed, targets[0], dt, HEM_SPEED_RATE);
        rimSpeed = toward(rimSpeed, targets[0], dt, RIM_SPEED_RATE);
        hemTurn = toward(hemTurn, targets[2], dt, HEM_TURN_RATE);
        hemAir = toward(hemAir, targets[5], dt, 3.55);
        sideNear = toward(sideNear, targets[7], dt, SIDE_NEAR_RATE);
        sideHem = toward(sideHem, targets[7], dt, SIDE_HEM_RATE);
    }

    record SpeedWake(double edge, double inner, double water) {
        static final SpeedWake NONE = new SpeedWake(0, 0, 0);
    }

    /** Speed changes excite the lip first and the violet edge later. */
    SpeedWake speedWake() {
        // The differences vanish at constant speed. Absolute values give
        // braking a wake too, without changing any of the pose filters.
        return new SpeedWake(Math.abs(hemSpeed - rimSpeed), Math.abs(values[0] - hemSpeed), values[4]);
    }

    /** The slow filter leads the fast one only when braking. No new clock for the chain. */
    double braking() { return Math.max(0, hemSpeed - values[0]); }

    /** Degrees in the baked rig's X convention (negative opens the drape). */
    public double pitchAt(double weight) {
        double bias = pitchBase - pitchLag * weight;
        return weight * Math.max(-MAX_BACK, Math.min(MAX_IN, bias));
    }

    /** The upper fold answers a turn first; inertia delays the free hem. */
    public double turnAt(double weight) {
        return values[2] + weight * (hemTurn - values[2]);
    }

    /** Additional yaw bias before weighting and the existing yaw limit. */
    public double turnWake(double weight) {
        // Rotate the loose pieces slightly against the turn, with the slow
        // hem clock. The first fold gets little of it and the sewn root none.
        return TURN_WAKE * weight * hemTurn * (1 - TURN_WATER_DAMPING * values[4]);
    }

    public static double weightAt(int segment, int lastSegment) {
        return Math.pow(segment / (double) lastSegment, SEGMENT_POWER);
    }

    /** The free hem keeps its previous lateral pull longer than the sewn end. */
    public double sideAt(double weight) {
        return (sideNear + weight * (sideHem - sideNear)) * (1 - SIDE_WATER_DAMPING * values[4]);
    }

    public static double sideYaw(double base, double side, double weight) {
        return weight * Math.max(-MAX_YAW, Math.min(MAX_YAW, base + side * SIDE_YAW));
    }

    public static double sideRoll(double base, double side, double weight) {
        // Positive baked Z carries a point below its pivot opposite to world
        // travel along (cos bodyYaw, sin bodyYaw). Never translate the root.
        return weight * Math.max(-MAX_ROLL, Math.min(MAX_ROLL, base + side * SIDE_ROLL));
    }

    private static double toward(double old, double target, double dt, double rate) {
        return old + (target - old) * -Math.expm1(-dt * rate);
    }
}
