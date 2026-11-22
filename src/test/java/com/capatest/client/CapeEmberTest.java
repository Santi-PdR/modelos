package com.capatest.client;

import java.util.Locale;

public final class CapeEmberTest {
    private CapeEmberTest() {}

    public static void main(String[] args) {
        boolean samples = args.length == 1 && args[0].equals("--samples");
        int count = 0;
        for (int life : new int[] {26, 31, 39, 47}) {
            for (double streak : new double[] {0, .43, 1}) {
                for (double phase : new double[] {0, .82, 1.91, 3.13}) {
                    double width = Double.POSITIVE_INFINITY;
                    int visible = 0;
                    for (int age = 0; age <= life; age++) {
                        double p = (double) age / life;
                        CapeEmber.Look look = CapeEmber.look(p, streak, phase);
                        check(look.alpha() >= 0 && look.alpha() <= 1, "opacity out of range");
                        check(look.scale() < width && look.scale() > .5, "ember stops shrinking");
                        check(look.red() >= .60 && look.red() <= 1 && look.green() >= .79 && look.green() <= 1
                                && look.blue() >= .92 && look.blue() <= 1, "tint out of range");
                        if (age == 0 || age == life) check(look.alpha() == 0, "pop at start or end");
                        if (look.alpha() * .85 >= .1) visible |= 1 << look.frame();
                        width = look.scale();
                        if (samples) System.out.printf(Locale.ROOT, "%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\t%s%n",
                                p, streak, phase, look.frame(), look.alpha(), look.scale(),
                                look.red(), look.green(), look.blue());
                        count++;
                    }
                    check(visible == 7, "one of the three sprites never shows above the shader cutoff");
                }
            }
        }
        if (!samples) {
            System.out.println("Brasas: " + count + " muestras de color, cobertura y tamaño");
            checkRenderClock();
        }
    }

    private static void checkRenderClock() {
        check(CapeEmber.renderProgress(0, 26, .75F) == 0, "visible before the first tick");
        check(CapeEmber.renderProgress(26, 26, 1) == 1, "nonzero lifetime tail");
        check(CapeEmber.renderProgress(2, 26, Float.NaN) == 1.0 / 26, "invalid render fraction broke the clock");
        double peakOld = 0, peakRender = 0;
        for (int life = 26; life <= 47; ++life) {
            for (int age = 1; age <= life; ++age) {
                check(CapeEmber.renderProgress(age, life, 1) == CapeEmber.renderProgress(age + 1, life, 0),
                        "appearance changed discontinuously at a tick boundary");
            }
            for (int fps : new int[]{30, 60, 144}) {
                double old = 0, current = 0;
                for (int i = 1; i <= Math.ceil(life * fps / 20.0); ++i) {
                    double elapsed = i * 20.0 / fps;
                    int ticks = (int) elapsed;
                    double stepped = CapeEmber.look(ticks / (double) life, 1, .82).alpha();
                    double sampled = CapeEmber.look(CapeEmber.renderProgress(ticks + 1, life, (float)(elapsed - ticks)),
                            1, .82).alpha();
                    check(Math.abs(sampled - current) < .34 * 20 / fps, "opacity jumped between rendered frames");
                    if (fps == 60) {
                        peakOld = Math.max(peakOld, Math.abs(stepped - old));
                        peakRender = Math.max(peakRender, Math.abs(sampled - current));
                    }
                    old = stepped;
                    current = sampled;
                }
            }
        }
        check(peakRender < peakOld * .40, "sub-tick sampling did not reduce the opacity steps");
        System.out.printf(Locale.ROOT, "Brasas a 60 FPS: salto máximo de alfa %.4f → %.4f (perfil, 22 vidas).%n",
                peakOld, peakRender);
    }

    private static void check(boolean condition, String error) {
        if (!condition) throw new AssertionError(error);
    }
}
