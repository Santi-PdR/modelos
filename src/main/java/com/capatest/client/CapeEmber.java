package com.capatest.client;

/** Appearance only: the server still sends the same impulses and number of sparks. */
public final class CapeEmber {
    private static final int SPRITE_STEPS = 12;
    static final int LAST_SPRITE = 2 * SPRITE_STEPS;
    private static final double SPRITE_HALF_TICKS = 2.5;
    private static final double FIRST_CHANGE = .25, SECOND_CHANGE = .63;

    private CapeEmber() {}

    public record Look(int frame, double alpha, double scale, double red, double green, double blue) {}

    private static final double BANK_LIMIT = .44;
    private static final double BANK_DEAD = .0035, BANK_FULL = .024;
    private static final double BANK_IN_START = .02, BANK_IN_END = .14;
    private static final double BANK_OUT_START = .38, BANK_OUT_END = .78;

    static float renderFraction(float partialTick) {
        return Float.isFinite(partialTick) ? Math.max(0, Math.min(1, partialTick)) : 0;
    }

    // Positive drift on the screen leans the top of the sprite to the right.
    // Side travel, not an angle atan2 across the view axis, keeps it calm
    // when the ember moves directly towards or away from the camera.
    static double bank(double progress, double screenSide) {
        if (!Double.isFinite(progress) || !Double.isFinite(screenSide)) return 0;
        double motion = ease(BANK_DEAD, BANK_FULL, Math.abs(screenSide));
        double life = ease(BANK_IN_START, BANK_IN_END, progress) * (1 - ease(BANK_OUT_START, BANK_OUT_END, progress));
        return Math.copySign(BANK_LIMIT * motion * life, -screenSide);
    }

    static double renderProgress(int age, int lifetime, float partialTick) {
        if (age <= 0 || lifetime <= 0) return 0;
        double fraction = renderFraction(partialTick);
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
        double p = Double.isFinite(progress) ? Math.max(0, Math.min(1, progress)) : 0;
        double trail = Double.isFinite(streak) ? Math.max(0, Math.min(1, streak)) : 0;
        double clock = Double.isFinite(phase) ? phase : 0;
        double glint = .5 + .5 * Math.sin(clock + p * 7.5);
        double fade = ease(0, .16, p) * (1 - ease(.36, 1, p));
        double cool = ease(.22, .93, p);
        // A warm rose core on ignition, blending back to violet before
        // the final sprite. Keep the opacity envelope, quad and impulse.
        double heat = 1 - ease(.14, .58, p);
        int frame = p < FIRST_CHANGE ? 0 : p < SECOND_CHANGE ? 1 : 2;
        return new Look(frame, (.79 + .06 * glint + .07 * trail) * fade,
                1 - .43 * p + .05 * glint, 1 - .39 * cool,
                .98 - .18 * cool - .055 * heat, .93 + .07 * cool - .20 * heat);
    }

    private static double ease(double lo, double hi, double p) {
        double t = Math.max(0, Math.min(1, (p - lo) / (hi - lo)));
        return t * t * (3 - 2 * t);
    }
}
