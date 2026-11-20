package com.stainkatana.katana.client;

/** Ease-in-out cubic adapted from heconis' Cinema Scope (MIT). */
public final class SceneCurve {
    private SceneCurve() { }
    /** A short triangular impulse, returning to zero within four client ticks. */
    public static double impactEnvelope(double ticks) {
        if (!Double.isFinite(ticks) || ticks < 0 || ticks >= 4) return 0;
        return ticks < 1 ? ease(ticks) : 1.0 - ease((ticks - 1.0) / 3.0);
    }
    public static double ease(double value) {
        double t = Math.max(0.0, Math.min(1.0, value));
        return t < 0.5 ? 4.0 * t * t * t : 1.0 - Math.pow(-2.0 * t + 2.0, 3.0) / 2.0;
    }
}
