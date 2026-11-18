package com.capatest.client;

/** Head/torso sign, clamping, neutral pose and interpolation without Minecraft. */
public final class CapeFitTest {
    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
    }

    private static double fold(double stance, double lookUp, double turn) {
        return CapeFit.foldDegrees(stance * CapeFit.CROUCH_RADIANS, 0,
                -Math.toRadians(lookUp), Math.toRadians(turn));
    }

    public static void main(String[] args) {
        check(fold(0, 0, 0) == 0, "la bisagra altera la pose neutra");
        check(fold(1, 0, 0) > fold(0, 0, 0), "el torso agachado no compensa");
        check(fold(0, 60, 35) > fold(0, -60, 35), "el signo de mirada está invertido");
        check(fold(1, 90, 20) == fold(2, 95, 20), "faltan cotas");
        check(CapeFit.foldDegrees(Double.NaN, 0, 0, 0) == 0, "entrada no finita");
        double bodyYaw = Math.toRadians(177);
        double turn = CapeFit.foldDegrees(.5, bodyYaw, -.31, Math.toRadians(-163));
        check(Math.abs(turn - fold(1, Math.toDegrees(.31), 20)) < 1e-12, "giro relativo o al cruzar 180°");
        for (double stance : new double[]{0,.23,.5,.79,1}) {
            for (int pitch=-90; pitch<=90; pitch++) {
                for (int yaw=-90; yaw<=90; yaw+=3) {
                    double angle = fold(stance, pitch, yaw);
                    check(angle >= 0 && angle <= 30, "fuera de la amplitud probada");
                    check(Math.abs(angle - fold(stance, pitch+.01, yaw+.01)) < .06,
                            "salto en la corrección interpolada");
                }
            }
        }
        System.out.println("CapeFit: reposo, signos, giro relativo, límites e interpolación verificados");
    }
}
