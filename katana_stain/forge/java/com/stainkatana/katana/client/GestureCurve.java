package com.stainkatana.katana.client;

/** First-person contact weight in inspect-clip ticks, independent of playback speed. */
public final class GestureCurve {
    private GestureCurve() { }

    public static float contact(int clipTick) {
        float in = Math.max(0F, Math.min(1F, (clipTick - 3F) / 9F));
        float out = Math.max(0F, Math.min(1F, (52F - clipTick) / 14F));
        float amount = Math.min(in, out);
        return amount * amount * (3F - 2F * amount);
    }
}
