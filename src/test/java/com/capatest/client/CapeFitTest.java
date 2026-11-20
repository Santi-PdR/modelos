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

    private static float plate(double stance, double look, double yaw, double arm, boolean wings) {
        return CapePlateFit.influence(stance * CapeFit.CROUCH_RADIANS, Math.toRadians(yaw),
                -Math.toRadians(look), arm, wings);
    }

    private static void plateChecks() {
        check(plate(0,-89.5,0,2.85,false) == 1, "el canto no se asienta sobre la manga");
        check(plate(0,-89.5,0,5.3,false) == 0 && plate(0,-89.5,0,2.85,true) == 0,
                "la placa no deja pasar la manga o los élitros");
        check(plate(0,0,0,0,false) == 0 && plate(1,-89.5,0,0,false) == 0,
                "el ajuste invade la cabeza en otra postura");
        check(plate(0,-65,12,3.8,false) == plate(0,-65,372,3.8,false), "salto al dar la vuelta");
        float last = 0;
        for (double pitch = -40; pitch >= -89.5; pitch -= .25) {
            float next = plate(0,pitch,0,0,false);
            check(next >= last && next-last < .012F, "ajuste de placa no continuo");
            last = next;
        }
        check(plate(0,-89,0,Double.NaN,false) == 0, "esfuerzo no finito");
        check(CapePlateFit.rimRise(.65F) > 0 && CapePlateFit.rimReach(.65F) == 0
                && CapePlateFit.rimRise(1) == 1 && CapePlateFit.rimReach(1) == 1,
                "el canto debe elevarse antes de alcanzar la manga");
        check(CapePlateFit.forBone("cape_top") == null && CapePlateFit.forBone(CapePlateFit.WIDE) != null,
                "el ajuste no debe alcanzar el paño");
    }

    private static CapeTorsoFit.Shape torso(double stance, double look, double yaw, double arm,
                                           double sleeve, double dry, boolean wings) {
        double lean = stance * CapeFit.CROUCH_RADIANS, pitch = -Math.toRadians(look);
        double body = Math.toRadians(177), head = Math.IEEEremainder(body + Math.toRadians(yaw), 2*Math.PI);
        double sz = CapeFit.seating(lean, body, pitch, head, arm, wings) * dry;
        return CapeTorsoFit.shape(lean, pitch, head-body, CapeFit.backset(lean,body,pitch,head), sz,
                plate(stance,look,yaw,sleeve,wings) * dry, arm, sleeve, dry, wings);
    }

    private static void torsoChecks() {
        var diagonal = torso(0,-58,43,1,1,1,false);
        check(diagonal.seat() > .64F && diagonal.collar().dz() < -1.5F && diagonal.wide().sx() < .45F,
                "la unión exterior sigue en la pose abierta a tres cuartos");
        check(torso(0,-48,-48,1,1,1,false).seat() > .49F, "el ceñido falla al girar al otro lado");
        var moving = torso(0,-45,43,25,27,1,false);
        check(moving.seat() == 0 && moving.wide().sx() < .45F && moving.wide().dz() > .45F,
                "la placa se sale del hombro al andar o no deja pasar la manga");
        check(torso(0,-58,43,0,0,0,false) == CapeTorsoFit.NONE
                && torso(0,-58,43,0,0,1,true) == CapeTorsoFit.NONE, "el ajuste se mete en las alas o en el nado");
    }

    private static void writeAffine(CapeTorsoFit.Affine a) {
        if (a == null) a = new CapeTorsoFit.Affine(0,0,0,0,0,0,1,1,1);
        System.out.printf(Locale.ROOT,"\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f\t%.9f",
                a.x(),a.y(),a.z(),a.dx(),a.dy(),a.dz(),a.sx(),a.sy(),a.sz());
    }

    public static void main(String[] args) {
        torsoChecks();
        if (args.length == 1 && args[0].equals("--torso")) {
            for (double stance : new double[]{0,.09,.26,.51,1})
                for (double look : new double[]{-89.5,-78.1,-61,-58,-48,-36,-17,0,8,31,75})
                    for (double yaw : new double[]{-376,-63,-48,-43,0,16,43,48,76,371})
                        for (double arm : new double[]{0,3.3,8,37})
                            for (int mode = 0; mode < 3; mode++) {
                                boolean wings = mode == 1;
                                double dry = mode == 2 ? .25 : 1;
                                double sleeve = arm + (arm > 0 ? 2.7 : 0);
                                var fit = torso(stance,look,yaw,arm,sleeve,dry,wings);
                                System.out.printf(Locale.ROOT,"%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%d\t%.10f",
                                        stance,look,yaw,arm,sleeve,dry,wings?1:0,fit.seat());
                                writeAffine(fit.collar()); writeAffine(fit.facing()); writeAffine(fit.small()); writeAffine(fit.wide());
                                System.out.println();
                            }
            return;
        }
        if (args.length == 1 && args[0].equals("--plates")) {
            for (double stance : new double[]{0,.18,.39,.58,1})
                for (double look : new double[]{-89.5,-78,-71.2,-62,-58,-48,-41,0})
                    for (double turn : new double[]{-381,-43,-17,0,16,36,59,390})
                        for (double arm : new double[]{0,2.8,3.5,4.8,5.3,42})
                            for (int wings = 0; wings < 2; wings++) {
                                float fit = plate(stance,look,turn,arm,wings==1);
                                System.out.printf(Locale.ROOT, "%.4f\t%.4f\t%.4f\t%d\t%.4f\t%.9f\t%.9f\t%.9f%n",
                                        stance,look,turn,wings,arm,fit,CapePlateFit.rimRise(fit),CapePlateFit.rimReach(fit));
                            }
            return;
        }
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
        if (args.length == 1 && args[0].equals("--backing")) {
            for (double stance : new double[]{0,.15,.42,.71,1})
                for (double look : new double[]{-89,-86,-66,-58,-21,0,31,80,90})
                    for (double yaw : new double[]{-179,-93,-76,-43,-12,0,12,43,76,93,179})
                        for (int wings = 0; wings < 2; wings++) {
                            double p = -Math.toRadians(look), a = .7 + Math.toRadians(yaw);
                            var s = CapeBacking.shape(stance*CapeFit.CROUCH_RADIANS,.7,p,a,depth(stance,look,yaw),wings == 1);
                            System.out.printf(Locale.ROOT, "%.4f\t%.4f\t%.4f\t%d\t%.9f\t%.9f\t%.9f%n",
                                    stance,look,yaw,wings,s.left(),s.right(),s.depth());
                        }
            return;
        }
        if (args.length == 1 && args[0].equals("--seating")) {
            for (double stance : new double[]{0,.19,.27,.54,.90})
                for (double look : new double[]{-89,-76,-72.3,-63.1,-60,-58,-51.5,-48,-46,-12,47})
                    for (double turn : new double[]{-376,-45.8,-23,0,3,17.8,38,74,386})
                        for (int wings = 0; wings < 2; wings++)
                            for (double arm : new double[]{0,3.1,3.7,6.3,16.5}) {
                                double snug = CapeFit.seating(stance * CapeFit.CROUCH_RADIANS, 2.4,
                                        -Math.toRadians(look), 2.4 + Math.toRadians(turn), arm, wings == 1);
                                System.out.printf(Locale.ROOT, "%.5f\t%.5f\t%.5f\t%d\t%.5f\t%.10f\t%.10f\t%.10f\t%.10f%n",
                                        stance,look,turn,wings,arm,snug,
                                        CapeFit.seatDepthScale(snug),CapeFit.seatReturnWidth(snug),
                                        CapeFit.seatedDrapeDegrees(depth(stance,look,turn),snug));
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
        double down = Math.toRadians(76);
        check(CapeFit.seating(0, .8, down, .8 + Math.toRadians(3), 2.4, false) > .98,
                "cuello y hombreras no se ciñen con la cabeza baja y los brazos en reposo");
        double half = CapeFit.seating(0, 0, Math.toRadians(58), Math.toRadians(3), 2.8, false);
        check(half > .39 && half < .43, "sin unión progresiva al inclinar 58°: " + half);
        check(CapeFit.seating(0, 0, Math.toRadians(44), 0, 2.8, false) == 0,
                "el ceñido debe abrirse al levantar la mirada");
        check(CapeFit.seating(0, 0, down, 0, 1, true) == 0, "el ceñido invade los élitros");
        check(CapeFit.seating(0, 0, -down, 0, 1, false) == 0, "el ceñido invade la cabeza");
        check(CapeFit.seating(0, 0, down, 0, 17, false) == 0, "el ceñido invade la manga");
        check(CapeFit.seating(0, 0, down, 0, Double.NaN, false) == 0, "ángulo de brazo no finito");
        plateChecks();
        System.out.println("CapeFit: reposo, ceñido, hombreras, giro relativo, límites e interpolación verificados");
    }
}
