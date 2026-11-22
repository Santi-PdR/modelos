package com.capatest.client;

/** Appearance only: the server still sends the same impulses and number of sparks. */
public final class CapeEmber {
    private static final int SPRITE_STEPS = 12;
    static final int LAST_SPRITE = 2 * SPRITE_STEPS;
    private static final double SPRITE_HALF_TICKS = 2.5;
    private static final double FIRST_CHANGE = .25, SECOND_CHANGE = .63;

    private CapeEmber() {}

    public record Look(int frame, double alpha, double scale, double red, double green, double blue) {}

    static double renderProgress(int age, int lifetime, float partialTick) {
        if (age <= 0 || lifetime <= 0) return 0;
        double fraction = Float.isFinite(partialTick) ? Math.max(0, Math.min(1, partialTick)) : 0;
        // TextureSheetParticle draws between its previous and current
        // positions; sample the same interval of the appearance curve.
        return Math.min(1, (age - 1 + fraction) / lifetime);
    }

    /** Nearest preblended sprite at the same interpolated time as the particle position. */
    static int spriteIndex(double progress, int lifetime) {
        // Each change spans five ticks of life, regardless of streak or FPS.
        double width = SPRITE_HALF_TICKS / lifetime;
        if (progress < FIRST_CHANGE + width)
            return (int) Math.round(SPRITE_STEPS * ease(FIRST_CHANGE - width, FIRST_CHANGE + width, progress));
        return SPRITE_STEPS + (int) Math.round(SPRITE_STEPS * ease(SECOND_CHANGE - width, SECOND_CHANGE + width, progress));
    }

    public static Look look(double progress, double streak, double phase) {
        double p = Math.max(0, Math.min(1, progress));
        double glint = .5 + .5 * Math.sin(phase + p * 7.5);
        double fade = ease(0, .16, p) * (1 - ease(.36, 1, p));
        double cool = ease(.22, .93, p);
        // A warm rose core on ignition, blending back to violet before
        // the final sprite. Keep the opacity envelope, quad and impulse.
        double heat = 1 - ease(.14, .58, p);
        int frame = p < FIRST_CHANGE ? 0 : p < SECOND_CHANGE ? 1 : 2;
        return new Look(frame, (.79 + .06 * glint + .07 * streak) * fade,
                1 - .43 * p + .05 * glint, 1 - .39 * cool,
                .98 - .18 * cool - .055 * heat, .93 + .07 * cool - .20 * heat);
    }

    private static double ease(double lo, double hi, double p) {
        double t = Math.max(0, Math.min(1, (p - lo) / (hi - lo)));
        return t * t * (3 - 2 * t);
    }
}
