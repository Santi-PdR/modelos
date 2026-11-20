package com.stainkatana.katana;

import net.minecraftforge.common.ForgeConfigSpec;

/** Client-only visual preferences; no gameplay values are accepted from clients. */
public final class KatanaClientConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue ULTIMATE_FRAME;
    public static final ForgeConfigSpec.DoubleValue BAR_FRACTION;
    public static final ForgeConfigSpec.DoubleValue ZOOM_FRACTION;
    static {
        ForgeConfigSpec.Builder builder = new ForgeConfigSpec.Builder();
        builder.push("ultimate_scene");
        ULTIMATE_FRAME = builder.comment("Cinematic framing for the local player's ultimate. Disable for accessibility.")
                .define("enabled", true);
        BAR_FRACTION = builder.comment("Maximum bar height as a fraction of the screen; zero disables bars.")
                .defineInRange("barFraction", 0.055, 0.0, 0.12);
        ZOOM_FRACTION = builder.comment("Maximum FOV reduction; zero disables zoom.")
                .defineInRange("zoomFraction", 0.04, 0.0, 0.10);
        builder.pop();
        SPEC = builder.build();
    }
    private KatanaClientConfig() { }
}
