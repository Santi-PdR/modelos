package com.capatest.client;

/** Projection, per-wearer inertia, and an exact signal for the visor's square-wave demo. */
public final class CapeSwayTest {
    private static final CapeTravel.Step STILL = new CapeTravel.Step(0, 0, 0);

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            export();
            return;
        }
        for (int yaw = -180; yaw <= 360; yaw += 15) {
            double x = Math.cos(Math.toRadians(yaw)), z = Math.sin(Math.toRadians(yaw));
            var side = new CapeTravel.Step(.14*x, 0, .14*z);
            var forward = new CapeTravel.Step(-.42*z, 0, .42*x);
            var reverse = new CapeTravel.Step(-.14*x, -.1, -.14*z);
            var local = CapeTravel.measure(side, STILL, false, yaw);
            var remote = CapeTravel.measure(STILL, side, true, yaw);
            close(local.side(), 1, "arrastre lateral en la base del torso");
            check(local.equals(remote), "un portador seguido perdió el desplazamiento");
            check(CapeTravel.measure(side, STILL, true, yaw).side() == 0, "velocidad remota vieja al frenar");
            check(CapeTravel.measure(forward, STILL, false, yaw).side() == 0, "marcha recta con arrastre lateral");
            var otherWay = CapeTravel.measure(STILL, reverse, true, yaw);
            close(otherWay.side(), -1, "sentido invertido");
            close(otherWay.lift(), .13, "caída con velocidad remota cero");
        }
        check(CapeTravel.measure(new CapeTravel.Step(.012, 0, 0), STILL, false, 0).side() == 0,
                "vibración en la zona muerta");
        var warp = CapeTravel.measure(new CapeTravel.Step(.4, 0, 0), new CapeTravel.Step(4, 0, -4), true, 0);
        check(warp.cut() && warp.side() == 0 && warp.speed() == 0, "teleport convertido en impulso");
        check(CapeTravel.measure(STILL, new CapeTravel.Step(0, Double.NaN, 0), false, 0).cut(), "delta inválido");
        check(CapeTravel.measure(STILL, STILL, false, Double.NaN).cut(), "ángulo inválido");

        var r = new CapeResponse();
        update(r, 0, 1, 0);
        update(r, 0, -1, 0);
        check(r.sideAt(1) == 1, "el mismo fotograma avanzó el paño");
        update(r, .05, -1, 0);
        update(r, .10, -1, 0);
        check(r.sideAt(weight(1)) < 0 && r.sideAt(1) > .30, "el extremo invirtió a la vez que el inicio");
        double turnTip = r.sideAt(1);
        close(turnTip, after(30), "la respuesta depende de FPS a 30");
        close(turnTip, after(120), "la respuesta depende de FPS a 120");
        var submerged = new CapeResponse();
        update(submerged, 0, 1, 1);
        update(submerged, .05, -1, 1);
        update(submerged, .10, -1, 1);
        close(submerged.sideAt(1), .35 * turnTip, "agua sin amortiguación");
        check(r.sideAt(1) != new CapeResponse().sideAt(1), "historial compartido");
        for (int tick = 3; tick <= 32; tick++) {
            double prior = r.sideAt(1);
            update(r, tick / 20.0, 0, 0);
            check(r.sideAt(1) < prior && r.sideAt(1) > 0, "rebote al parar");
        }
        check(r.sideAt(1) < .001, "el extremo no se asienta");
        r.reset();
        update(r, 1.65, 0, 0);
        check(r.sideAt(1) == 0, "un salto arrastró el impulso anterior");
        update(r, 1.70, -1, 0);
        update(r, 3, .5, 0);
        check(r.sideAt(1) == .5, "historial viejo al volver a cámara");
        for (int seg = 0; seg <= 4; seg++) {
            double q = weight(seg);
            for (double side : new double[]{-1, -.4, 0, .4, 1}) {
                for (double bias : new double[]{-2.5, -.7, 0, .7, 2.5}) {
                    check(Math.abs(CapeResponse.sideYaw(bias, side, q)) <= CapeResponse.MAX_YAW * q, "cota Y");
                    check(Math.abs(CapeResponse.sideRoll(bias, side, q)) <= CapeResponse.MAX_ROLL * q, "cota Z");
                    if (side == 0) {
                        close(CapeResponse.sideYaw(bias, 0, q), q * bound(bias, CapeResponse.MAX_YAW), "eje Y sin deriva");
                        close(CapeResponse.sideRoll(bias, 0, q), q * bound(bias, CapeResponse.MAX_ROLL), "eje Z sin deriva");
                    }
                }
            }
        }
        turnWake();
        System.out.println("CapeSway: proyección, corte, inversión con retardo y remate del giro verificados");
    }

    private static void turnWake() {
        var r = new CapeResponse();
        r.sample(0, 0, 0, 0, 0, 0, 0, 0);
        r.sample(.05, 0, 0, 1, 0, 0, 0, 0);
        check(r.turnWake(1) > .1 && r.turnWake(1) < .3 && r.turnWake(0) == 0, "no nace en el extremo libre");
        close(r.turnWake(weight(1)) / r.turnWake(1), weight(1), "se perdió la progresión hacia la punta");
        var beforeBrake = r.turnWake(1);
        for (int tick = 2; tick <= 35; tick++) {
            r.sample(tick / 20., 0, 0, 0, 0, 0, 0, 0);
            if (tick == 2) check(r.turnWake(1) < beforeBrake && r.turnWake(1) > .1, "el faldón paró en seco");
        }
        check(Math.abs(r.turnWake(1)) < .001, "no volvió a reposo");
        r.reset();
        r.sample(2, 0, 0, -1, 0, 0, 0, 0);
        var dry = r.turnWake(1);
        r.reset();
        r.sample(2, 0, 0, -1, 0, 1, 0, 0);
        close(r.turnWake(1), dry * .4, "el agua no frenó el giro");
    }

    private static void export() {
        var r = new CapeResponse();
        // Warm up to the periodic response of two one-second legs. The
        // viewer uses its closed form so a seek isn't tied to frame history.
        final int cycle = 40;
        r.sample(0, .34, 0, -1, 0, 0, 0, 0, -1);
        for (int tick = 1; tick <= 11 * cycle; tick++) {
            double time = tick / 20.0;
            int direction = (tick-1) % cycle < cycle / 2 ? 1 : -1;
            r.sample(time, .34, 0, direction, 0, 0, 0, 0, direction);
            if (tick < 10 * cycle) continue;
            System.out.print((tick - 10 * cycle) / 20.0);
            for (int seg = 1; seg <= 4; seg++) {
                double q = weight(seg), bias = r.sideAt(q);
                System.out.print("\t" + CapeResponse.sideYaw(r.turnWake(q), bias, q) + "\t" + CapeResponse.sideRoll(0, bias, q));
            }
            System.out.println();
        }
    }

    private static double after(int fps) {
        var r = new CapeResponse();
        update(r, 0, 1, 0);
        for (int f = 1; f <= fps / 10; f++) update(r, f / (double)fps, -1, 0);
        return r.sideAt(1);
    }

    private static double weight(int segment) { return CapeResponse.weightAt(segment, 4); }
    private static double bound(double x, double max) { return Math.max(-max, Math.min(max, x)); }

    private static void update(CapeResponse r, double time, double side, double water) {
        r.sample(time, .34, 0, 0, 0, water, 0, 0, side);
    }

    private static void close(double a, double b, String label) { check(Math.abs(a - b) < 1e-12, label); }
    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
    }
}
