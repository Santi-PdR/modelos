package com.capatest.client;

import java.util.Locale;

/** Head/torso sign, clamping, neutral pose and interpolation without Minecraft. */
public final class CapeFitTest {
    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
    }

    private static double depth(double stance, double lookUp, double turn) {
        return CapeFit.backset(stance * CapeFit.CROUCH_RADIANS, 0,
                -Math.toRadians(lookUp), Math.toRadians(turn));
    }

    private static double axis(double minimum, double spread) {
        return minimum + (1-minimum)*spread;
    }

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--shoulders")) {
            for (double stance : new double[]{0,.18,.5,.81,1})
                for (double pitch : new double[]{-90,-66,-51.5,-33,0,26,90})
                    for (double yaw : new double[]{-187,-94,-43,0,2.25,42,51,65,89,196})
                        for (int wings = 0; wings <= 1; wings++)
                          for (double arm : new double[]{-11,0,2.9,4.8,5.3,6.1,42}) {
                            double k = CapeFit.shoulderReach(stance * CapeFit.CROUCH_RADIANS,
                                    1.2, -Math.toRadians(pitch), 1.2 + Math.toRadians(yaw), wings == 1);
                            CapeFit.YokeShape yoke = CapeFit.yokeShape(stance * CapeFit.CROUCH_RADIANS,
                                    -Math.toRadians(pitch), arm, wings == 1);
                            System.out.printf(Locale.ROOT, "%.6f\t%.6f\t%.6f\t%d\t%.6f\t%.10f\t%.10f\t%.10f\t%.10f\t%.10f%n",
                                    stance, pitch, yaw, wings, arm, axis(CapeFit.SHOULDER_HEIGHT,k), k,
                                    yoke.width(),yoke.height(),yoke.depth());
                        }
            return;
        }
        if (args.length == 1 && args[0].equals("--samples")) {
            for (double stance : new double[]{0,.18,.5,.81,1})
                for (double pitch : new double[]{-90,-51.5,-3,0,18.75,63,90})
                    for (double yaw : new double[]{-97,-36.75,0,3.75,30,69,92}) {
                        double d = depth(stance, pitch, yaw);
                        System.out.printf(Locale.ROOT, "%.10f\t%.10f\t%.10f\t%.10f\t%.10f\t%.10f%n",
                                stance, pitch, yaw, d, CapeFit.gussetScale(d), CapeFit.drapeDegrees(d));
                    }
            return;
        }
        check(depth(0, 0, 0) == 0, "la montura altera la pose neutra");
        check(depth(0, -90, 0) == 0, "se despega mirando al suelo");
        check(CapeFit.gussetScale(0) == 1 && CapeFit.drapeDegrees(0) == 0,
                "el fuelle deforma la pose neutra");
        check(depth(1, 0, 0) > depth(0, 0, 0), "el torso agachado no compensa");
        check(depth(0, 60, 35) > depth(0, -60, 35), "el signo de mirada está invertido");
        check(depth(1, 90, 20) == depth(2, 95, 20), "faltan cotas");
        check(CapeFit.backset(Double.NaN, 0, 0, 0) == 0, "entrada no finita");
        double bodyYaw = Math.toRadians(177);
        double turn = CapeFit.backset(.5, bodyYaw, -.31, Math.toRadians(-163));
        check(Math.abs(turn - depth(1, Math.toDegrees(.31), 20)) < 1e-12, "giro relativo o al cruzar 180°");
        for (double stance : new double[]{0,.23,.5,.79,1}) {
            for (int pitch=-90; pitch<=90; pitch++) {
                for (int yaw=-90; yaw<=90; yaw+=3) {
                    double offset = depth(stance, pitch, yaw);
                    check(offset >= 0 && offset < 8, "fuera de la amplitud probada");
                    check(Math.abs(offset - depth(stance, pitch+.01, yaw+.01)) < .015,
                            "salto en la corrección interpolada");
                }
            }
        }
        check(CapeFit.yokeShape(0, 0, 2.9, false).width() == 1, "el forro no se extiende en reposo");
        check(CapeFit.yokeShape(0, 0, 6.1, false).width() == .51F, "el forro no deja pasar el brazo");
        check(CapeFit.yokeShape(0, 0, 0, true).width() == .51F, "el forro no se recoge con élitros");
        System.out.println("CapeFit: reposo, signos, giro relativo, límites e interpolación verificados");
    }
}
