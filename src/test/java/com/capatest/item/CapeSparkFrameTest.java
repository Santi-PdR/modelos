package com.capatest.item;

public final class CapeSparkFrameTest {
    private static final double SCALE = 0.9375;
    private static final double FEET = (1.501F - 1.5F) * SCALE;
    private static final double EPS = 1e-12;

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            samples();
            return;
        }
        if (args.length == 1 && args[0].equals("--crouch-samples")) {
            crouchSamples();
            return;
        }
        upright();
        crouch();
        glide();
        swim();
        System.out.println("CapeSparkFrame: anclaje vertical intacto, pivote agachado, giro, nado y salida del agua verificados");
    }

    private static void upright() {
        for (double yaw : new double[]{0, 45, 90, -90, 180, 779}) {
            for (double height : new double[]{1.8, 1.5, .6}) {
                CapeSparkFrame f = CapeSparkFrame.upright(yaw, height);
                double stature = Math.max(.36, height / 1.8);
                if (f.posed()) throw new AssertionError("upright frame classified as pitched");
                for (CapeState mode : CapeState.values()) {
                    for (int beat = 0; beat < 4; beat++) {
                        for (int index = 0; index < mode.aura().count(); index++) {
                            for (double noise : new double[]{0, .5, 1}) {
                                var s = mode.spark(beat, index, height > 1, noise, noise, noise);
                                expect(f.birth(s), baseline(yaw, s.side(), s.height() * stature, s.depth()));
                            }
                        }
                    }
                }
                expect(f.impulse(-.029, .017, .011), baseline(yaw, -.029, .017, .011));
            }
        }
    }

    private static void crouch() {
        double pivot = 1.5, feet = FEET - .125, lowered = pivot - 3.2F / 16.0;
        for (double yaw : new double[]{0, 45, 90, -90, 180, 779}) {
            var f = CapeSparkFrame.crouch(yaw);
            if (f.posed()) throw new AssertionError("the crouched torso disabled collar births");
            // Pivot, one block down along the torso, and one block behind it.
            expect(f.point(0, pivot, 0), baseline(yaw, 0, lowered * SCALE + feet, 0));
            expect(f.point(0, pivot - 1, 0), baseline(yaw, 0,
                    (lowered - Math.cos(.5)) * SCALE + feet, Math.sin(.5) * SCALE));
            expect(f.point(.2, pivot, 1), baseline(yaw, .2 * SCALE,
                    (lowered + Math.sin(.5)) * SCALE + feet, Math.cos(.5) * SCALE));
            expect(f.impulse(-.029, .017, .011), baseline(yaw, -.029, .017, .011));
        }
    }

    private static void crouchSamples() {
        var frame = CapeSparkFrame.crouch(180);
        // The three permitted grounded SNEAK origins, including all jitter directions.
        for (int pulse : new int[]{0, 2, 6}) {
            for (double a : new double[]{0, .5, 1}) {
                for (double b : new double[]{0, .5, 1}) {
                    for (double c : new double[]{0, .5, 1}) {
                        var s = CapeState.SNEAK.spark(pulse, 0, true, a, b, c);
                        var p = frame.birth(s);
                        System.out.println(s.side() + "\t" + s.height() + "\t" + s.depth() + "\t"
                                + p.x() + "\t" + p.y() + "\t" + p.z());
                    }
                }
            }
        }
    }

    private static void glide() {
        // Facing +Z, level gliding: the +back axis now points straight up.
        var flat = CapeSparkFrame.glide(0, 0, 12, 0, 1, 0, 2);
        expect(flat.point(.2, .8, .6), .2 * SCALE, .6 * SCALE, .8 * SCALE + FEET);
        // Five ticks: 25% of the -90° pitch. Yaw projects the pitched point, not the other way round.
        var start = CapeSparkFrame.glide(90, 0, 5, -1, 0, -1, 0);
        double z = .6 * SCALE, y = .8 * SCALE + FEET;
        double theta = Math.PI / 8;
        expect(start.point(.2, .8, .6), z * Math.cos(theta) - y * Math.sin(theta),
                y * Math.cos(theta) + z * Math.sin(theta), .2 * SCALE);
        // 90° between heading and motion. The turn precedes the outer pitch;
        // check both signs and a zero-length heading/velocity.
        expect(CapeSparkFrame.glide(0, 0, 18, 0, 1, 1, 0).point(.2, .8, .6), -z, .2 * SCALE, y);
        expect(CapeSparkFrame.glide(0, 0, 18, 0, 1, -1, 0).point(.2, .8, .6), z, -.2 * SCALE, y);
        expect(CapeSparkFrame.glide(0, 0, 18, 0, 0, 1, 0).point(.2, .8, .6), flat.point(.2, .8, .6));
        expect(CapeSparkFrame.glide(0, 0, 18, 0, 1, 0, 0).point(.2, .8, .6), flat.point(.2, .8, .6));
        // View straight up: once the ramp completes, the root is upright but still has the AIR drape.
        var up = CapeSparkFrame.glide(0, -90, 18, 0, 1, 0, 2);
        expect(up.point(.2, .8, .6), .2 * SCALE, y, -z);
        if (up.birth(new CapeState.Spark(.2, .8, .6, false)).z() >= -z) {
            throw new AssertionError("AIR origins didn't follow the extended cloth");
        }
        expect(flat.impulse(.02, .01, .03), .02, .01, -.03);
    }

    private static void swim() {
        double z = .6 * SCALE, y = .8 * SCALE + FEET;
        var stroke = CapeSparkFrame.swim(0, 0, 1, true, true);
        expect(stroke.point(.2, .8, .6), .2 * SCALE, z + .3F, y - 1);
        // Half blend at a -30° look pitch: -30° total while in water, -45° out of it.
        var start = CapeSparkFrame.swim(0, -30, .5, true, true);
        expect(start.point(.2, .8, .6), .2 * SCALE,
                (y - 1) * Math.sqrt(.75) + (z + .3F) * .5,
                (y - 1) * .5 - (z + .3F) * Math.sqrt(.75));
        var exit = CapeSparkFrame.swim(0, -30, .5, false, false);
        expect(exit.point(.2, .8, .6), .2 * SCALE, (y + z) / Math.sqrt(2), (y - z) / Math.sqrt(2));
        expect(exit.birth(new CapeState.Spark(.2, .8, .6, false)), exit.point(.2, .8, .6));
    }

    private static CapeSparkFrame.Offset baseline(double yaw, double side, double height, double depth) {
        double a = Math.toRadians(yaw);
        return new CapeSparkFrame.Offset(Math.sin(a) * depth + Math.cos(a) * side, height,
                -Math.cos(a) * depth + Math.sin(a) * side);
    }

    private static void expect(CapeSparkFrame.Offset got, CapeSparkFrame.Offset want) {
        expect(got, want.x(), want.y(), want.z());
    }

    private static void expect(CapeSparkFrame.Offset got, double x, double y, double z) {
        if (!(Math.abs(got.x() - x) < EPS && Math.abs(got.y() - y) < EPS && Math.abs(got.z() - z) < EPS)) {
            throw new AssertionError(got + " != (" + x + ", " + y + ", " + z + ")");
        }
    }

    private static void samples() {
        // Yaw=180 cancels the renderer's base yaw, for a direct comparison to the authored mesh.
        for (CapeState clip : new CapeState[]{CapeState.AIR, CapeState.SWIM}) {
            CapeSparkFrame posed = clip == CapeState.AIR
                    ? CapeSparkFrame.glide(180, 0, 12, 0, -1, 0, -2)
                    : CapeSparkFrame.swim(180, 0, 1, true, true);
            for (int beat = 0; beat < 4; beat++) {
                for (double a : new double[]{0, .5, 1}) {
                    for (double b : new double[]{0, .5, 1}) {
                        for (double c : new double[]{0, .5, 1}) {
                            var spark = clip.spark(beat, 0, false, a, b, c);
                            System.out.print(clip.name() + "\t" + (a == .5 && b == .5 && c == .5 ? 1 : 0));
                            for (var p : new CapeSparkFrame.Offset[]{CapeSparkFrame.upright(180, .6).birth(spark),
                                    posed.point(spark.side(), spark.height(), spark.depth()), posed.birth(spark)}) {
                                System.out.print("\t" + p.x() + "\t" + p.y() + "\t" + p.z());
                            }
                            System.out.println();
                        }
                    }
                }
            }
        }
    }
}
