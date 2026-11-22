package com.capatest.item;

/** Una lectura del portador para el clip, el color emisivo y las chispas. */
public enum CapeState {
    IDLE("idle",               new Aura(2, 0.004, 0.003, 0.010)),
    WALK("moving",             new Aura(1, 0.009, 0.011, 0.010)),
    SPRINT("sprint",            new Aura(2, 0.012, 0.029, 0.010)),
    AIR("air",                 new Aura(2, 0.021, 0.027, 0.011)),
    FALL("fall",               new Aura(2, 0.010, 0.023, 0.017)),
    SNEAK("sneak",             new Aura(1, 0.003, 0.002, 0.009)),
    SWIM("swim",               new Aura(1, 0.009, 0.007, 0.010)),
    BLIGHT("deterioro",         new Aura(3, 0.023, 0.017, 0.015));

    public record Aura(int count, double sideways, double trail, double lift) {}
    public record Glow(float red, float green, float blue) {}

    private final String clip;
    private final Aura aura;

    CapeState(String clip, Aura aura) {
        this.clip = "animation." + clip;
        this.aura = aura;
    }

    public String clip() { return this.clip; }
    public Aura aura() { return this.aura; }

    public record Spark(double side, double height, double depth, boolean collar) {}

    // Centers in wearer-local blocks (x, height, back), near/far side of
    // the registered design. Separate the yoke, flank, split and low hem;
    // do not spawn an even cloud in the volume of the cloth.
    private static final double[][][] SPARK_ORIGINS = {
            {{-.655, 1.545, .395}, { .436, 1.448, .336}},
            {{-.503, 1.075, .421}, { .551,  .492, .455}},
            {{-.229,  .067, .624}, { .413,  .173, .640}},
            {{-.493,  .176, .369}, { .600,  .113, .553}}
    };
    private static final double[][] SPARK_JITTER = {
            {.025, .081, .021}, {.028, .105, .029},
            {.047, .065, .039}, {.038, .076, .033}
    };

    /** Ash follows four parts of the silhouette; only grounded wearers get high sparks. */
    public Spark spark(int pulse, int index, boolean grounded, double a, double b, double c) {
        boolean collar = grounded && switch (this) {
            case IDLE, BLIGHT -> index == 1;
            case WALK -> pulse % 3 == 0;
            case SNEAK -> (pulse & 3) == 0;
            default -> false;
        };
        int beat = this == SNEAK ? pulse >>> 1 : pulse;
        int side = (beat + (index == 0 ? 0 : 1)) & 1;
        int band = collar ? 0 : grounded && (index == 1 || (beat & 3) == 3) ? 1
                : ((beat + index) & 2) == 0 ? 2 : 3;
        double[] origin = SPARK_ORIGINS[band][side];
        double[] jitter = SPARK_JITTER[band];
        return new Spark(origin[0] + jitter[0] * (2.0 * a - 1.0),
                origin[1] + jitter[1] * (2.0 * b - 1.0),
                origin[2] + jitter[2] * (2.0 * c - 1.0), collar);
    }

    public static boolean deteriorated(float health, float maxHealth, int damage, int maxDamage) {
        return (maxHealth > 0.0F && health <= maxHealth * 0.5F)
                || (maxDamage > 0 && damage >= maxDamage * 0.65D);
    }

    /** Shared inputs, with separate playback and cosmetic selection policies. */
    public record Wearer(boolean blight, boolean elytra, boolean water, boolean airborne,
                         boolean crouching, boolean sprinting, double horizontalSquared, double vertical) {
        public static final Wearer STILL = new Wearer(false, false, false, false, false, false, 0, 0);

        /** A handhold supports the cloth without inventing floor contact or zeroing travel. */
        public Wearer withSupport() {
            return airborne ? new Wearer(blight, elytra, water, false, crouching, sprinting, horizontalSquared, vertical) : this;
        }

        /** A vehicle carries the wearer. Its travel is not a step, sprint or free fall. */
        public Wearer asPassenger() {
            return new Wearer(blight, elytra, water, false, false, false, 0, vertical);
        }

        public CapeState cosmeticState() {
            return select(blight, elytra, water, airborne, crouching, sprinting, horizontalSquared, vertical);
        }
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
