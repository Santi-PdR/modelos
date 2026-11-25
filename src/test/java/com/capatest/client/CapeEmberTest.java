package com.capatest.client;

import java.util.Locale;

public final class CapeEmberTest {
    private CapeEmberTest() {}

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--blend-samples")) {
            blendSamples();
            return;
        }
        if (args.length == 1 && args[0].equals("--bank-samples")) {
            checkBank(true);
            return;
        }
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
                                && look.blue() >= .73 && look.blue() <= 1, "tint out of range");
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
            checkSpriteTimeline();
            checkBank(false);
            var hot = CapeEmber.look(.16, .43, .82);
            var cool = CapeEmber.look(.55, .43, .82);
            check(hot.alpha() > .79 && hot.red() - hot.blue() > .25 && cool.blue() > cool.red(),
                    "no se ve la transición de rosa cálido a violeta");
            check(CapeEmber.look(Double.NaN, Double.NaN, Double.NaN).equals(CapeEmber.look(0, 0, 0)),
                    "el reloj o impulso inválido envenenó el sprite");
            check(CapeEmber.look(Double.POSITIVE_INFINITY, 2, Double.NaN).equals(CapeEmber.look(0, 1, 0)),
                    "la apariencia no acotó sus entradas");
        }
    }

    private static void checkBank(boolean samples) {
        double[] drifts = {-.04, -.027, -.019, -.010, -.003, 0, .003, .010, .019, .027, .04};
        for (double drift : drifts) {
            double prev = 0;
            for (int i = 0; i <= 200; i++) {
                double p = i / 200.0, bank = CapeEmber.bank(p, drift);
                check(Math.abs(bank) <= .44 && bank == -CapeEmber.bank(p, -drift), "bank no longer mirrors");
                check(bank * drift <= 0 && Math.abs(bank-prev) < .031, "wrong turn or sudden tilt");
                if (Math.abs(drift) <= .003 || p <= .02 || p >= .78)
                    check(bank == 0, "a still, unborn or cold ember leans");
                if (samples) System.out.printf(Locale.ROOT, "%s\t%s\t%s%n", p, drift, bank);
                prev = bank;
            }
        }
        check(CapeEmber.bank(.2, .04) < -.42 && Math.abs(CapeEmber.bank(.2, .01)) < .12,
                "tilt no longer reads with lateral speed");
        check(CapeEmber.bank(.2, Double.NaN) == 0 && CapeEmber.bank(Double.POSITIVE_INFINITY, .04) == 0,
                "non-finite drift or clock tilted the billboard");
        if (!samples) System.out.println("Brasas: inclinación simétrica y acotada, neutra de frente o al apagarse.");
    }

    private static void checkSpriteTimeline() {
        int steps = CapeEmber.LAST_SPRITE / 2;
        for (int life = 26; life <= 47; ++life) {
            int visited = 0, previous = 0;
            for (int sample = 0; sample <= life * 64; ++sample) {
                int index = CapeEmber.spriteIndex(sample / (64.0 * life), life);
                check(index >= previous && index <= 2 * steps, "spark frame regressed or overshot");
                visited |= 1 << index;
                previous = index;
            }
            check(visited == (1 << (2 * steps + 1)) - 1, "unreachable intermediate sprite");
            for (double p : new double[]{.05,.42,.91})
                check(CapeEmber.spriteIndex(p, life) == CapeEmber.look(p, 0, 0).frame() * steps,
                        "key sprite changed outside the transition");
        }
        System.out.println("Brasas: secuencia completa con los tres fotogramas clave intactos.");
    }

    private static void blendSamples() {
        int route = 0;
        for (int life = 26; life <= 47; ++life) {
            for (int fps : new int[]{30,60,144}) {
                double interval = 20.0/fps;
                for (int pair = 0; pair < 2; ++pair) {
                    double center = (pair == 0 ? .25 : .63) * life;
                    for (double offset : new double[]{0,.43,.83}) {
                        for (double phase : new double[]{.05,.82,1.91,3.13}) {
                            ++route;
                            double streak = life < 35 ? 1 : 0;
                            for (double at = center - 2.5 + (offset-1)*interval; at <= center + 2.5 + 2*interval; at += interval) {
                                int tick = (int) at;
                                double p = CapeEmber.renderProgress(tick + 1, life, (float) (at - tick));
                                var look = CapeEmber.look(p, streak, phase);
                                System.out.printf(Locale.ROOT, "%d\t%d\t%d\t%d\t%s\t%d\t%d\t%s\t%s\t%s\t%s%n",
                                        route, fps, pair, life, p, look.frame(), CapeEmber.spriteIndex(p, life),
                                        look.alpha(), look.red(), look.green(), look.blue());
                            }
                        }
                    }
                }
            }
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
