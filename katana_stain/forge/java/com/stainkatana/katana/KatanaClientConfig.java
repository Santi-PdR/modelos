package com.stainkatana.katana;

import net.minecraftforge.common.ForgeConfigSpec;

/** Client-only visual preferences; no gameplay values are accepted from clients. */
public final class KatanaClientConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue ULTIMATE_FRAME;
    public static final ForgeConfigSpec.DoubleValue BAR_FRACTION;
    public static final ForgeConfigSpec.DoubleValue ZOOM_FRACTION;
    public static final ForgeConfigSpec.DoubleValue CAMERA_ROLL;
    public static final ForgeConfigSpec.BooleanValue SHOW_HUD, HUD_LEFT, BLOOD_FLASH, VANILLA_SWINGS;
    static {
        ForgeConfigSpec.Builder builder = new ForgeConfigSpec.Builder();
        builder.push("ultimate_scene");
        ULTIMATE_FRAME = builder.comment("Cinematic framing for the local player's ultimate. Disable for accessibility.")
                .define("enabled", true);
        BAR_FRACTION = builder.comment("Maximum bar height as a fraction of the screen; zero disables bars.")
                .defineInRange("barFraction", 0.055, 0.0, 0.12);
        ZOOM_FRACTION = builder.comment("Maximum FOV reduction; zero disables zoom.")
                .defineInRange("zoomFraction", 0.04, 0.0, 0.10);
        CAMERA_ROLL = builder.comment("Maximum view-only tilt in degrees on ultimate strokes. Set to zero for motion sensitivity.")
                .defineInRange("impactRollDegrees", 0.65, 0.0, 2.0);
        builder.pop();
        builder.push("interface");
        SHOW_HUD = builder.comment("Show small cooldown panel while holding the katana.").define("showHud", true);
        HUD_LEFT = builder.comment("Legacy setting; the HUD is now positioned at the middle right.").define("hudLeft", true);
        VANILLA_SWINGS = builder.comment("Animate ordinary katana swings without Better Combat; disable if another animation mod conflicts.").define("vanillaSwings", true);
        BLOOD_FLASH = builder.comment("Show subtle red tint after successful blood paralysis.").define("bloodFlash", true);
        builder.pop();
        SPEC = builder.build();
    }
    private KatanaClientConfig() { }
}
