package com.capatest.item;

/** Una lectura del portador para el clip, el color emisivo y las chispas. */
public enum CapeState {
    IDLE("idle",               new Aura(1, 0.004, 0.003, 0.34, 0.010)),
    WALK("moving",             new Aura(1, 0.009, 0.011, 0.40, 0.010)),
    SPRINT("sprint",            new Aura(2, 0.012, 0.029, 0.50, 0.010)),
    AIR("air",                 new Aura(2, 0.021, 0.027, 0.55, 0.011)),
    FALL("fall",               new Aura(2, 0.010, 0.023, 0.46, 0.017)),
    SNEAK("sneak",             new Aura(1, 0.003, 0.002, 0.35, 0.009)),
    SWIM("swim",               new Aura(1, 0.009, 0.007, 0.37, 0.010)),
    BLIGHT("deterioro",         new Aura(3, 0.023, 0.017, 0.39, 0.015));

    public record Aura(int count, double sideways, double trail, double depth, double lift) {}
    public record Glow(float red, float green, float blue) {}

    private final String clip;
    private final Aura aura;

    CapeState(String clip, Aura aura) {
        this.clip = "animation." + clip;
        this.aura = aura;
    }

    public String clip() { return this.clip; }
    public Aura aura() { return this.aura; }

    public static boolean deteriorated(float health, float maxHealth, int damage, int maxDamage) {
        return (maxHealth > 0.0F && health <= maxHealth * 0.5F)
                || (maxDamage > 0 && damage >= maxDamage * 0.65D);
    }

    public static CapeState select(boolean blight, boolean elytra, boolean water,
                                   boolean airborne, boolean crouching, boolean sprinting,
                                   double horizontalSquared, double vertical) {
        if (blight) return BLIGHT;
        if (elytra) return AIR;
        if (water) return SWIM;
        if (airborne) return vertical < -0.08D ? FALL : AIR;
        if (crouching) return SNEAK;
        if (horizontalSquared <= 0.0009D) return IDLE;
        return sprinting ? SPRINT : WALK;
    }

    /** Tiempos en segundos del mundo; se limita al RGB, nunca al alfa. */
    public Glow glow(double seconds) {
        return switch (this) {
            case IDLE -> rose(0.72 + 0.17 * wave(seconds, 3.6), 0.0);
            case WALK -> rose(0.79 + 0.21 * wave(seconds, 1.0), 0.0);
            case SPRINT -> rose(0.87 + 0.13 * wave(seconds, 0.72), 0.10);
            case AIR -> rose(0.87 + 0.12 * wave(seconds, 1.35), 0.18);
            case FALL -> rose(0.74 + 0.25 * wave(seconds, 0.90), 0.04);
            case SNEAK -> rose(0.55 + 0.12 * wave(seconds, 2.6), 0.0);
            case SWIM -> rose(0.66 + 0.27 * wave(seconds, 3.2), 0.35);
            case BLIGHT -> {
                double peak = wave(seconds, 3.0);
                double echo = 1.0 - peak;
                // Latido doble de relieve amplio, sin destello a negro.
                double beat = 0.62 * peak * peak * peak + 0.38 * echo * echo * echo;
                yield rose(0.63 + 0.37 * beat / 0.62, 0.28);
            }
        };
    }

    private static double wave(double t, double period) {
        return 0.5 + 0.5 * Math.cos(t * (Math.PI * 2.0 / period));
    }

    private static Glow rose(double intensity, double cool) {
        return new Glow((float) (intensity * (1.0 - 0.27 * cool)),
                (float) (intensity * (0.67 + 0.25 * cool)),
                (float) (intensity * (0.86 + 0.33 * cool)));
    }
}
