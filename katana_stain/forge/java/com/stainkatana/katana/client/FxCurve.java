package com.stainkatana.katana.client;

/** Small, bounded interpolation for slash quads. No gameplay state lives here. */
public final class FxCurve {
    private FxCurve() { }
    private static float clamp(float value) {
        return Float.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
    }
    private static float smooth(float value) {
        float t = clamp(value);
        return t * t * (3 - 2 * t);
    }
    public static float size(float ageFraction) {
        return .82F + .18F * smooth(clamp(ageFraction) / .35F);
    }
    public static float opacity(float ageFraction) {
        return 1F - smooth((clamp(ageFraction) - .65F) / .35F);
    }
}
