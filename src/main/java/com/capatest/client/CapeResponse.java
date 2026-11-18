package com.capatest.client;

/** Filtro de pose por portador. La respuesta depende del tiempo, no de los FPS. */
public final class CapeResponse {
    // Cotas, en grados antes del peso por tramo. verify_v1600 sondea estos extremos.
    public static final double MAX_BACK = 2.10;
    public static final double MAX_IN = 1.20;
    public static final double MAX_YAW = 1.55;
    public static final double MAX_ROLL = 1.40;

    private final double[] values = new double[7];
    private double lastSeconds = Double.NaN;

    public double[] sample(double seconds, double speed, double lift, double turn,
                           double crouch, double water, double air, double sprint) {
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
        } else if (dt > 0.0) {
            values[0] = toward(values[0], speed, dt, 8.0);
            values[1] = toward(values[1], lift, dt, 6.2);
            values[2] = toward(values[2], turn, dt, 9.0);
            values[3] = toward(values[3], crouch, dt, 8.0);
            values[4] = toward(values[4], water, dt, 4.4);
            values[5] = toward(values[5], air, dt, 8.0);
            values[6] = toward(values[6], sprint, dt, 8.0);
        }
        return values;
    }

    private static double toward(double old, double target, double dt, double rate) {
        return old + (target - old) * -Math.expm1(-dt * rate);
    }
}
