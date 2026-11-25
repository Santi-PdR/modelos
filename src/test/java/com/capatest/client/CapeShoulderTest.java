package com.capatest.client;

/** The hinge is local, mirrored and continuous even across large arm strokes. */
public final class CapeShoulderTest {
    public static void main(String[] args) {
        boolean samples = args.length == 1 && args[0].equals("--samples");
        for (int angle = -180; angle <= 180; ++angle) {
            double rad = Math.toRadians(angle);
            double y = -Math.cos(rad), z = Math.sin(rad);
            for (double rise : new double[]{-.3, .45, 1}) for (double fore : new double[]{-.75, 0, .4}) {
                var right = CapeShoulder.pose(false, y, z, rise, fore);
                var left = CapeShoulder.pose(true, y, z, rise, fore);
                check(right.x() == -left.x() && right.roll() == -left.roll() && right.y() == left.y()
                        && right.z() == left.z() && right.pitch() == left.pitch(), "el lado cambia la respuesta");
                check(right.x() >= 0 && right.x() <= .25 && right.y() >= 0 && right.y() <= .05
                        && Math.abs(right.z()) <= .31 && Math.abs(right.pitch()) <= 4.5
                        && Math.abs(right.roll()) <= 6,
                        "placa fuera del recorrido suave");
                if (Math.abs(angle) <= 20) check(right == CapeShoulder.REST && left == CapeShoulder.REST,
                        "la marcha normal debe dejar la placa asentada");
                if (Math.abs(angle) == 45) check(right.x() > .06 && right.x() < .09
                                && right.roll() > 1.6 && right.roll() < 1.8 && right.pitch() * angle < 0,
                        "la carrera no debe arrancar con un golpe de hombro");
                if (Math.abs(angle) == 60) check(right.x() > .19 && right.x() < .22
                                && right.roll() > 4.9 && right.roll() < 5.4,
                        "la placa pierde su apoyo cuando el brazo sí se eleva");
                if (samples && angle % 5 == 0) {
                    print(0, y, z, rise, fore, right);
                    print(1, y, z, rise, fore, left);
                }
            }
            var edge = CapeShoulder.pose(false, y, z, 0, 0);
            rad += Math.toRadians(.01);
            var next = CapeShoulder.pose(false, -Math.cos(rad), Math.sin(rad), 0, 0);
            check(Math.abs(edge.pitch() - next.pitch()) <= .012 && Math.abs(edge.roll() - next.roll()) <= .012,
                    "salto al empezar o terminar el balanceo");
        }
        check(CapeShoulder.pose(false, Double.NaN, 0, 0, 0) == CapeShoulder.REST, "pose no finita");
        if (!samples) System.out.println("Hombreras: reposo, inversión, respuesta simétrica y recorrido continuo verificados");
    }

    private static void print(int side, double y, double z, double rise, double fore, CapeShoulder.Pose fit) {
        System.out.println(side + "\t" + y + "\t" + z + "\t" + rise + "\t" + fore + "\t"
                + fit.x() + "\t" + fit.y() + "\t" + fit.z() + "\t" + fit.pitch() + "\t" + fit.roll());
    }

    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
}
