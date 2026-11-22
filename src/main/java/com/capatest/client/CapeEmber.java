package com.capatest.client;

/** Appearance only: the server still sends the same impulses and number of sparks. */
public final class CapeEmber {
    private CapeEmber() {}

    public record Look(int frame, double alpha, double scale, double red, double green, double blue) {}

    static double renderProgress(int age, int lifetime, float partialTick) {
        if (age <= 0 || lifetime <= 0) return 0;
        double fraction = Float.isFinite(partialTick) ? Math.max(0, Math.min(1, partialTick)) : 0;
        // TextureSheetParticle draws between its previous and current
        // positions; sample the same interval of the appearance curve.
        return Math.min(1, (age - 1 + fraction) / lifetime);
    }

    public static Look look(double progress, double streak, double phase) {
        double p = Math.max(0, Math.min(1, progress));
        double glint = .5 + .5 * Math.sin(phase + p * 7.5);
        double fade = ease(0, .16, p) * (1 - ease(.36, 1, p));
        double cool = ease(.22, .93, p);
        int frame = p < .25 ? 0 : p < .63 ? 1 : 2;
        return new Look(frame, (.79 + .06 * glint + .07 * streak) * fade,
                1 - .43 * p + .05 * glint, 1 - .39 * cool, .98 - .18 * cool, .93 + .07 * cool);
    }

    private static double ease(double lo, double hi, double p) {
        double t = Math.max(0, Math.min(1, (p - lo) / (hi - lo)));
        return t * t * (3 - 2 * t);
    }
}
