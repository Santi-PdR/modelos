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
        if (!samples) System.out.println("Brasas: " + count + " muestras de color, cobertura y tamaño");
    }

    private static void check(boolean condition, String error) {
        if (!condition) throw new AssertionError(error);
    }
}
