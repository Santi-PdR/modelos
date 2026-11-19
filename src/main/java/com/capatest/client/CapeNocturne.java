package com.capatest.client;

/** Smooth per-wearer halo response. This never changes the core tint or coverage. */
public final class CapeNocturne {
    private static final double DARK_LEVEL = 3.0;
    private static final double LIGHT_LEVEL = 13.0;
    private static final double DAY_GAIN = 0.46;
    private static final double INNER_BASE = 1.20;
    private static final double INNER_PULSE = 0.22;
    private static final double EDGE_BASE = 1.34;
    private static final double EDGE_PULSE = 0.29;
    private static final double EDGE_DELAY = 0.18;
    private static final double PERIOD = 3.40;
    private static final double SEED_SHIFT = 0.137;
    private static final int GAIN_UNITS = 4096;

    private double dusk;
    private double last = Double.NaN;

    public Gains sample(int block, int sky, float skyIntensity, double seconds, int wearerId) {
        // Raw skylight still reads 15 outside at midnight. Use the sky
        // brightness that feeds the vanilla lightmap, not raw sky alone.
        double target = darkness(Math.max(block, sky * (double) skyIntensity));
        double dt = seconds - last;
        last = seconds;
        if (!Double.isFinite(dt) || dt < 0 || dt > .5) {
            dusk = target;
        } else if (dt > 0) {
            double rate = target > dusk ? 5.0 : 9.0;
            dusk += (target - dusk) * -Math.expm1(-dt * rate);
        }
        return gains(dusk, seconds, wearerId);
    }

    public static double darkness(double light) {
        double t = Math.max(0, Math.min(1, (light - DARK_LEVEL) / (LIGHT_LEVEL - DARK_LEVEL)));
        return 1 - t * t * (3 - 2 * t);
    }

    public static Gains gains(double dusk, double seconds, int wearerId) {
        double phase = seconds / PERIOD + wearerId * SEED_SHIFT;
        double inner = INNER_BASE + INNER_PULSE * wave(phase);
        double edge = EDGE_BASE + EDGE_PULSE * wave(phase - EDGE_DELAY);
        return new Gains(DAY_GAIN + dusk * (edge - DAY_GAIN), DAY_GAIN + dusk * (inner - DAY_GAIN));
    }

    private static double wave(double phase) {
        return .5 + .5 * Math.cos(2 * Math.PI * phase);
    }

    public record Gains(double edge, double inner) {
        /** Two positive signed-short values in NEW_ENTITY's otherwise unused halo UV2. */
        public int packed() {
            int low = (int) Math.round(edge * GAIN_UNITS);
            int high = (int) Math.round(inner * GAIN_UNITS);
            return low | (high << 16);
        }
    }
}
