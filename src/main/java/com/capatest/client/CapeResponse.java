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
    private static final double SEGMENT_POWER = 1.45;

    private final double[] values = new double[7];
    private double lastSeconds = Double.NaN;
    private double hemTurn;
    private double hemSpeed;
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
        lastSeconds = seconds;
        if (!Double.isFinite(dt) || dt < 0.0 || dt > .5) {
            // Primer frame, cambio de mundo o portador fuera de cámara.
            // No heredar el impulso viejo ni arrastrar el salto del reloj.
            values[0] = speed;
            values[1] = lift;
            values[2] = turn;
            values[3] = crouch;
            values[4] = water;
            values[5] = air;
            values[6] = sprint;
            hemTurn = turn;
            hemSpeed = speed;
            hemAir = air;
            sideNear = sideHem = side;
        } else if (dt > 0.0) {
            values[0] = toward(values[0], speed, dt, 8.0);
            values[1] = toward(values[1], lift, dt, 6.2);
            values[2] = toward(values[2], turn, dt, 9.0);
            values[3] = toward(values[3], crouch, dt, 8.0);
            values[4] = toward(values[4], water, dt, 4.4);
            values[5] = toward(values[5], air, dt, 8.0);
            values[6] = toward(values[6], sprint, dt, 8.0);
            hemTurn = toward(hemTurn, turn, dt, 4.2);
            hemSpeed = toward(hemSpeed, speed, dt, 3.1);
            hemAir = toward(hemAir, air, dt, 3.55);
            sideNear = toward(sideNear, side, dt, SIDE_NEAR_RATE);
            sideHem = toward(sideHem, side, dt, SIDE_HEM_RATE);
        }
        pitchBase = (values[3] + values[4]) * .72 - (values[6] * 1.3 + values[5] * .9
                + values[1] * .65 + values[0] * .62);
        // A slower tail keeps the opening briefly during braking or landing.
        // No new force at steady speed; water damps the extra rotation.
        pitchLag = Math.max(0, Math.max(3.8 * (hemSpeed - values[0]), 3.1 * (hemAir - values[5])))
                * (1 - .65 * values[4]);
        return values;
    }

    /** Degrees in the baked rig's X convention (negative opens the drape). */
    public double pitchAt(double weight) {
        double bias = pitchBase - pitchLag * weight;
        return weight * Math.max(-MAX_BACK, Math.min(MAX_IN, bias));
    }

    /** The upper fold answers a turn first; inertia delays the free hem. */
    public double turnAt(double weight) {
        return values[2] + weight * (hemTurn - values[2]);
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
