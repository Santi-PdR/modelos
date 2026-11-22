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
    private static final double WAKE_LIMIT = .55;
    private static final double WAKE_DEAD_ZONE = .008;
    private static final double INNER_WAKE_SCALE = 12.0;
    private static final double EDGE_WAKE_SCALE = 20.0;
    private static final double WAKE_WATER_DAMPING = .80;
    private static final double LAND_EDGE_SHARE = .72;
    private static final double LAND_INNER_SHARE = .90;
    private static final int GAIN_UNITS = 4096;
    private static final double TICK_SECONDS = 1 / 20.0;

    private double dusk;
    private double lastTarget;
    private double last = Double.NaN;

    public Gains sample(int block, int sky, float skyIntensity, double seconds, int wearerId) {
        return sample(block, sky, skyIntensity, seconds, wearerId, CapeResponse.SpeedWake.NONE);
    }

    Gains sample(int block, int sky, float skyIntensity, double seconds, int wearerId, CapeResponse.SpeedWake wake) {
        // A malformed partial-tick/time from a renderer must not poison this
        // persistent clock. Reuse the last finite sample, or epoch zero initially.
        if (!Double.isFinite(seconds)) seconds = Double.isFinite(last) ? last : 0;
        // Raw skylight still reads 15 outside at midnight. Use the sky
        // brightness that feeds the vanilla lightmap, not raw sky alone.
        double target = darkness(Math.max(block, sky * (double) skyIntensity));
        double dt = seconds - last;
        if (dt == 0) return gains(dusk, seconds, wearerId, wake);
        last = seconds;
        // Allow one ULP of clock rounding at the ten-tick boundary.
        if (!Double.isFinite(dt) || dt < 0 || (dt > .5 && dt - .5 > Math.ulp(seconds))) {
            dusk = target;
        } else if (target == lastTarget) {
            advance(target, dt);
        } else {
            // Don't let a new light reading rewrite the unseen part of a
            // short frame gap. Continue the old fade up to the latest tick.
            if (dt > TICK_SECONDS) advance(lastTarget, dt - TICK_SECONDS);
            advance(target, Math.min(dt, TICK_SECONDS));
        }
        lastTarget = target;
        return gains(dusk, seconds, wearerId, wake);
    }

    private void advance(double target, double dt) {
        double rate = target > dusk ? 5.0 : 9.0;
        dusk += (target - dusk) * -Math.expm1(-dt * rate);
    }

    public static double darkness(double light) {
        // Bad light-map inputs must fail closed (no extra glow), not poison the
        // per-wearer exposure clock with NaN and keep the cape lit indefinitely.
        if (!Double.isFinite(light)) return 0;
        double t = Math.max(0, Math.min(1, (light - DARK_LEVEL) / (LIGHT_LEVEL - DARK_LEVEL)));
        return 1 - t * t * (3 - 2 * t);
    }

    public static Gains gains(double dusk, double seconds, int wearerId) {
        return gains(dusk, seconds, wearerId, CapeResponse.SpeedWake.NONE);
    }

    static Gains gains(double dusk, double seconds, int wearerId, CapeResponse.SpeedWake wake) {
        dusk = Double.isFinite(dusk) ? Math.max(0, Math.min(1, dusk)) : 0;
        seconds = Double.isFinite(seconds) ? seconds : 0;
        if (wake == null) wake = CapeResponse.SpeedWake.NONE;
        double edgeWake = finiteNonNegative(wake.edge());
        double innerWake = finiteNonNegative(wake.inner());
        double water = Double.isFinite(wake.water()) ? Math.max(0, Math.min(1, wake.water())) : 0;
        double phase = seconds / PERIOD + wearerId * SEED_SHIFT;
        double inner = INNER_BASE + INNER_PULSE * wave(phase);
        double edge = EDGE_BASE + EDGE_PULSE * wave(phase - EDGE_DELAY);
        // The extra light is subtle in mixed lighting and zero at full day.
        // Limit the strength smoothly even when a wearer moves very fast.
        double contrast = dusk * dusk * (1 - WAKE_WATER_DAMPING * water);
        return new Gains(DAY_GAIN + dusk * (edge - DAY_GAIN) + contrast * boost(edgeWake, EDGE_WAKE_SCALE),
                DAY_GAIN + dusk * (inner - DAY_GAIN) + contrast * boost(innerWake, INNER_WAKE_SCALE));
    }

    private static double finiteNonNegative(double value) {
        return Double.isFinite(value) ? Math.max(0, value) : 0;
    }

    double dusk() { return dusk; }

    static Gains hemGains(double dusk, Gains moving, double seconds, int wearerId, double heat) {
        if (moving == null) moving = gains(0, seconds, wearerId);
        dusk = Double.isFinite(dusk) ? Math.max(0, Math.min(1, dusk)) : 0;
        if (!(heat > 0) || !Double.isFinite(heat) || dusk == 0) return moving;
        var still = gains(dusk, seconds, wearerId);
        // Fill part of the unused .40 gain budget. Landing and braking can
        // coincide without doubling the flash. Daylight leaves UV2 intact.
        double room = WAKE_LIMIT * dusk * dusk;
        double mix = Math.min(1, heat);
        return new Gains(moving.edge + LAND_EDGE_SHARE * mix * Math.max(0, still.edge + room - moving.edge),
                moving.inner + LAND_INNER_SHARE * mix * Math.max(0, still.inner + room - moving.inner));
    }

    private static double boost(double wake, double scale) {
        double strength = Math.max(0, finiteNonNegative(wake) - WAKE_DEAD_ZONE) * scale;
        if (!(strength > 0)) return 0;
        // Avoid infinity/infinity if a finite but corrupt speed sample overflows
        // while scaled; high impulses simply saturate at the visual budget.
        return WAKE_LIMIT * (Double.isInfinite(strength) ? 1 : strength / (1 + strength));
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
