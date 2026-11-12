package dev.holorelic;

import net.minecraftforge.common.ForgeConfigSpec;

public final class RelicConfig {
    public enum Shoulder { LEFT, RIGHT }
    public static final ForgeConfigSpec CLIENT;
    public static final ForgeConfigSpec SERVER;
    public static final ForgeConfigSpec.EnumValue<Shoulder> SHOULDER;
    public static final ForgeConfigSpec.DoubleValue SCALE, X, Y, Z;
    public static final ForgeConfigSpec.BooleanValue LOW_QUALITY, GLOW;
    public static final ForgeConfigSpec.IntValue GLITCH_MIN, GLITCH_MAX;
    static {
        var b = new ForgeConfigSpec.Builder();
        SHOULDER = b.comment("RIGHT mirrors model X; offsets are blocks in body-local space.")
                .defineEnum("shoulder", Shoulder.LEFT);
        SCALE = b.defineInRange("scale", 1.0, 0.1, 4.0);
        X = b.defineInRange("offsetX", 0.0, -3.0, 3.0);
        Y = b.defineInRange("offsetY", 0.0, -3.0, 3.0);
        Z = b.comment("Positive moves further behind the body.").defineInRange("offsetZ", 0.08, -3.0, 3.0);
        LOW_QUALITY = b.define("lowQuality", false);
        GLOW = b.comment("Disable extra glow pass for shader compatibility. Base remains fullbright.")
                .define("glowLayer", true);
        CLIENT = b.build();
        b = new ForgeConfigSpec.Builder();
        GLITCH_MIN = b.defineInRange("glitchMinSeconds", 20, 1, 3600);
        GLITCH_MAX = b.comment("Clamped to at least the minimum at runtime.").defineInRange("glitchMaxSeconds", 60, 1, 3600);
        SERVER = b.build();
    }
    private RelicConfig() {}
}
